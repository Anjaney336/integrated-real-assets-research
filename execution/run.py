"""Reproducible synthetic fixture, replay check and explicitly local timings."""
from pathlib import Path
import argparse,hashlib,json,platform,random,statistics,tempfile,time
from book import Book,EventStore,canonical

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--events',type=int,default=10000);ap.add_argument('--output',default=str(Path(__file__).parent/'results'));a=ap.parse_args()
    if not 1<=a.events<=100000:ap.error('events must be 1..100000')
    out=Path(a.output);out.mkdir(parents=True,exist_ok=True);rng=random.Random(20261024)
    events=[dict(type='NEW',ts=i,order_id=f'o{i}',side=rng.choice(['B','S']),price=rng.randint(95,105),qty=rng.randint(1,30),tif='IOC' if i%3==0 else 'GTC') for i in range(a.events)]
    encoded='\n'.join(canonical(e) for e in events)+'\n';(out/'synthetic_events.jsonl').write_text(encoded)
    timings=[];digests=[]
    for _ in range(5):
        b=Book(max_live=100000);start=time.perf_counter_ns()
        results=[b.apply(e) for e in events];elapsed=time.perf_counter_ns()-start
        timings.append(elapsed/1e6);digests.append(hashlib.sha256(canonical([results,b.snapshot()]).encode()).hexdigest())
    assert len(set(digests))==1
    # Persistence uses the default admission guard; fixture is limited to a smaller replay workload.
    with tempfile.TemporaryDirectory() as temp:
        s=EventStore(Path(temp)/'events.db')
        for i,e in enumerate(events[:min(250,a.events)]):s.append(str(i),e)
        state=s.book.snapshot();chain=s.last_hash;s.close();s=EventStore(Path(temp)/'events.db');assert s.book.snapshot()==state and s.last_hash==chain;s.close()
    report={'dataset':'Synthetic IID order events; not exchange or employer data','generator':'run.py','seed':20261024,'generated_on':'2026-10-24','events':a.events,'input_sha256':hashlib.sha256(encoded.encode()).hexdigest(),'output_sha256':digests[0],'timing_ms_all_runs':timings,'median_ms':statistics.median(timings),'events_per_second_local':a.events/(statistics.median(timings)/1000),'python':platform.python_version(),'platform':platform.platform(),'processor':platform.processor(),'replay_events_verified':min(250,a.events),'limitations':'Single process local Python timing, no networking, persistence or serialization included in timed loop; not exchange latency or production throughput.'}
    (out/'benchmark.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
if __name__=='__main__':main()
