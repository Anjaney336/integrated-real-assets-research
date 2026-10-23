import json
import random
import sqlite3
import tempfile
import unittest
from pathlib import Path
from book import Book, EventStore

def new(i,side='B',price=100,qty=10,ts=1,tif='GTC'):
    return dict(type='NEW',ts=ts,order_id=str(i),side=side,price=price,qty=qty,tif=tif)

class Reference:
    """Independent slow list/sort oracle: no heaps or price queues."""
    def __init__(self): self.orders=[];self.sequence=0
    def apply(self,e):
        if e['type']=='CANCEL':
            o=next(o for o in self.orders if o['id']==e['order_id']);self.orders.remove(o)
            return {'trades':[],'resting_qty':0,'expired_qty':0,'cancelled_qty':o['qty']}
        self.sequence+=1; remaining=e['qty'];trades=[]
        eligible=sorted([o for o in self.orders if o['side']!=e['side'] and (o['price']<=e['price'] if e['side']=='B' else o['price']>=e['price'])],key=lambda o:(o['price'] if e['side']=='B' else -o['price'],o['sequence']))
        for o in eligible:
            n=min(remaining,o['qty']);remaining-=n;o['qty']-=n
            trades.append(dict(maker=o['id'],taker=e['order_id'],price=o['price'],qty=n))
            if not o['qty']:self.orders.remove(o)
            if not remaining:break
        resting=remaining if e['tif']=='GTC' else 0
        if resting:self.orders.append(dict(id=e['order_id'],side=e['side'],price=e['price'],qty=resting,sequence=self.sequence))
        return dict(trades=trades,resting_qty=resting,expired_qty=remaining-resting,cancelled_qty=0)

class BookTests(unittest.TestCase):
    def test_fifo_and_partial_fill(self):
        b=Book();b.apply(new('a','S',100,5));b.apply(new('b','S',100,8))
        r=b.apply(new('c','B',100,9));self.assertEqual([t['maker'] for t in r['trades']],['a','b']);self.assertEqual(b.orders['b']['qty'],4)
    def test_price_priority_and_resting_price(self):
        b=Book();b.apply(new('a','S',101));b.apply(new('b','S',99))
        r=b.apply(new('c','B',105,15));self.assertEqual([t['price'] for t in r['trades']],[99,101])
    def test_ioc_expiry(self):
        b=Book();b.apply(new('a','S',100,3));r=b.apply(new('b',qty=10,tif='IOC'))
        self.assertEqual(r['expired_qty'],7);self.assertFalse(b.orders)
    def test_cancel_does_not_trade(self):
        b=Book();b.apply(new('a','S'));b.apply(dict(type='CANCEL',ts=1,order_id='a'))
        self.assertFalse(b.apply(new('b'))['trades'])
    def test_level_recreated_after_cancel(self):
        b=Book();b.apply(new('a','S'));b.apply(dict(type='CANCEL',ts=1,order_id='a'));b.apply(new('b','S'));self.assertEqual(b.apply(new('c'))['trades'][0]['maker'],'b')
    def test_invalid_inputs_atomic(self):
        b=Book();b.apply(new('a',ts=5));before=b.snapshot()
        for e in [new('x',qty=0,ts=5),new('x',qty=True,ts=5),new('x',price=1.5,ts=5),new('a',ts=5),new('x',ts=4),new('x',side='X',ts=5)]:
            with self.assertRaises(ValueError):b.apply(e)
            self.assertEqual(before,b.snapshot())
    def test_limits_and_unique_order_ids(self):
        b=Book(max_live=1);b.apply(new('a'))
        with self.assertRaises(ValueError):b.apply(new('b'))
        b.apply(dict(type='CANCEL',ts=1,order_id='a'))
        with self.assertRaises(ValueError):b.apply(new('a'))
    def test_randomised_reference_and_conservation(self):
        for seed in range(10):
            rng=random.Random(seed);b=Book();ref=Reference();submitted=traded=cancelled=expired=0
            for i in range(500):
                if b.orders and rng.random()<.15:e=dict(type='CANCEL',ts=i,order_id=rng.choice(sorted(b.orders)))
                else:e=new(f'{seed}-{i}',rng.choice(['B','S']),rng.randint(90,110),rng.randint(1,50),i,rng.choice(['GTC','IOC']))
                r=b.apply(e);self.assertEqual(r,ref.apply(e))
                submitted+=e.get('qty',0);traded+=sum(t['qty'] for t in r['trades']);cancelled+=r['cancelled_qty'];expired+=r['expired_qty']
                self.assertEqual(submitted,2*traded+cancelled+expired+sum(o['qty'] for o in b.orders.values()))
                self.assertEqual(b.snapshot()['orders'],sorted(ref.orders,key=lambda o:o['sequence']))
                bids=[o['price'] for o in b.orders.values() if o['side']=='B'];asks=[o['price'] for o in b.orders.values() if o['side']=='S']
                if bids and asks:self.assertLess(max(bids),min(asks))
    def test_store_retry_and_conflict(self):
        with tempfile.TemporaryDirectory() as d:
            s=EventStore(Path(d)/'events.db');e=new('a');r=s.append('e1',e)
            self.assertEqual(s.append('e1',e),r);self.assertEqual(s.book_event_count(),1)
            with self.assertRaises(ValueError):s.append('e1',new('b'))
            s.close()
    def test_restart_replay(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'events.db';s=EventStore(path);s.append('1',new('a','S'));s.append('2',new('b',qty=4));state=s.book.snapshot();digest=s.last_hash;s.close()
            s=EventStore(path);self.assertEqual(s.book.snapshot(),state);self.assertEqual(s.last_hash,digest);s.close()
    def test_rejected_event_not_persisted(self):
        with tempfile.TemporaryDirectory() as d:
            s=EventStore(Path(d)/'events.db')
            with self.assertRaises(ValueError):s.append('1',new('a',qty=-1))
            self.assertEqual(s.db.execute('SELECT COUNT(*) FROM events').fetchone()[0],0);s.close()
    def test_tampering_detected(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'events.db';s=EventStore(path);s.append('1',new('a'));s.db.execute("UPDATE events SET result='{}'");s.db.commit();s.close()
            with self.assertRaises(ValueError):EventStore(path)

if __name__=='__main__':unittest.main()
