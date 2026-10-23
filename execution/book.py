"""Single-instrument, integer-tick, price-time simulator. No broker integration."""
from collections import deque
from copy import deepcopy
import hashlib
import heapq
import json
import sqlite3


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), allow_nan=False)


class Book:
    def __init__(self, max_quantity=10000, max_live=1000):
        self.max_quantity, self.max_live = max_quantity, max_live
        self.orders, self.seen = {}, set()
        self.levels = {'B': {}, 'S': {}}
        self.heaps = {'B': [], 'S': []}
        self.timestamp = -1
        self.sequence = 0

    def _best(self, side):
        heap, levels = self.heaps[side], self.levels[side]
        while heap:
            price = -heap[0] if side == 'B' else heap[0]
            queue = levels[price]
            while queue and queue[0] not in self.orders:
                queue.popleft()
            if queue:
                return self.orders[queue[0]]
            heapq.heappop(heap)
            del levels[price]
        return None

    def apply(self, event):
        if not isinstance(event, dict):
            raise ValueError('event must be an object')
        kind = event.get('type')
        fields = {'type', 'ts', 'order_id'} | ({'side', 'price', 'qty', 'tif'} if kind == 'NEW' else set())
        if kind not in {'NEW', 'CANCEL'} or set(event) != fields:
            raise ValueError('unknown type or unexpected/missing fields')
        ts, oid = event['ts'], event['order_id']
        if type(ts) is not int or ts < self.timestamp:
            raise ValueError('nondecreasing integer timestamps required')
        if not isinstance(oid, str) or not oid or len(oid) > 64:
            raise ValueError('invalid order ID')
        if kind == 'CANCEL':
            if oid not in self.orders:
                raise ValueError('cannot cancel inactive order')
            removed = self.orders.pop(oid)
            self.timestamp = ts
            return {'cancelled_qty': removed['qty'], 'trades': [], 'resting_qty': 0, 'expired_qty': 0}
        if oid in self.seen:
            raise ValueError('order IDs cannot be reused')
        side, price, qty, tif = (event[k] for k in ('side', 'price', 'qty', 'tif'))
        if side not in {'B', 'S'} or tif not in {'GTC', 'IOC'}:
            raise ValueError('invalid side or time-in-force')
        if type(price) is not int or not 0 < price <= 10**9:
            raise ValueError('positive integer price ticks required')
        if type(qty) is not int or not 0 < qty <= self.max_quantity:
            raise ValueError('quantity guardrail')
        # Conservative admission cap also applies to potentially fully crossing orders.
        if len(self.orders) >= self.max_live:
            raise ValueError('live-order admission cap')
        self.timestamp, self.sequence = ts, self.sequence + 1
        self.seen.add(oid)
        opposite = 'S' if side == 'B' else 'B'
        remaining, trades = qty, []
        while remaining:
            maker = self._best(opposite)
            if maker is None or (side == 'B' and maker['price'] > price) or (side == 'S' and maker['price'] < price):
                break
            size = min(remaining, maker['qty'])
            trades.append({'maker': maker['id'], 'taker': oid, 'price': maker['price'], 'qty': size})
            remaining -= size
            maker['qty'] -= size
            if not maker['qty']:
                del self.orders[maker['id']]
        resting = remaining if tif == 'GTC' else 0
        if resting:
            if price not in self.levels[side]:
                self.levels[side][price] = deque()
                heapq.heappush(self.heaps[side], -price if side == 'B' else price)
            self.levels[side][price].append(oid)
            self.orders[oid] = {'id': oid, 'side': side, 'price': price, 'qty': resting, 'sequence': self.sequence}
        return {'trades': trades, 'resting_qty': resting, 'expired_qty': remaining-resting, 'cancelled_qty': 0}

    def snapshot(self):
        return {'orders': sorted(self.orders.values(), key=lambda x:x['sequence']), 'timestamp': self.timestamp,
                'sequence': self.sequence, 'seen': sorted(self.seen)}


class EventStore:
    """One writer. Commit before replacing in-memory state; reconnect and replay after failure."""
    def __init__(self, path):
        self.db = sqlite3.connect(path)
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute('CREATE TABLE IF NOT EXISTS events(seq INTEGER PRIMARY KEY, event_id TEXT UNIQUE NOT NULL, payload TEXT NOT NULL, result TEXT NOT NULL, digest TEXT NOT NULL)')
        self.db.commit()
        self.book, self.last_hash = Book(), ''
        try:
            for seq, eid, payload, result, digest in self.db.execute('SELECT * FROM events ORDER BY seq'):
                if seq != self.book_event_count()+1:
                    raise ValueError('event sequence corruption')
                expected = self.digest(self.last_hash, seq, eid, payload, result)
                if digest != expected:
                    raise ValueError('event hash-chain mismatch')
                if canonical(self.book.apply(json.loads(payload))) != result:
                    raise ValueError('replay result mismatch')
                self.last_hash, self.count = digest, seq
        except Exception:
            self.db.close()
            raise

    def book_event_count(self):
        return getattr(self, 'count', 0)

    @staticmethod
    def digest(previous, seq, eid, payload, result):
        return hashlib.sha256(canonical([previous,seq,eid,payload,result]).encode()).hexdigest()

    def append(self, event_id, event):
        if not isinstance(event_id,str) or not event_id or len(event_id)>64:
            raise ValueError('invalid event ID')
        payload = canonical(event)
        old = self.db.execute('SELECT payload,result FROM events WHERE event_id=?',(event_id,)).fetchone()
        if old:
            if old[0] != payload:
                raise ValueError('conflicting duplicate event')
            return json.loads(old[1])
        candidate = deepcopy(self.book)
        result = canonical(candidate.apply(event))
        seq = self.book_event_count()+1
        digest = self.digest(self.last_hash,seq,event_id,payload,result)
        with self.db:
            self.db.execute('INSERT INTO events VALUES(?,?,?,?,?)',(seq,event_id,payload,result,digest))
        self.book,self.last_hash,self.count = candidate,digest,seq
        return json.loads(result)

    def close(self):
        self.db.close()
