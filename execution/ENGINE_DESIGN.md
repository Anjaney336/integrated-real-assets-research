# Deterministic execution laboratory

Educational single-instrument price-time-priority matching and event replay in Python 3.12; AI-assisted implementation. Review and understand the code before describing it in interviews. This is not production exchange infrastructure or a profitable trading strategy.

## Reproduce from repository root
```
python -m unittest discover -v
python run.py
```
No third-party dependencies. The fixture seed is 20261024. The command creates a 10,000-event synthetic stream, repeats matching five times, checks identical output hashes and persists/replays 250 events through SQLite. Machine-specific timings are in results/benchmark.json and are not network latency or production throughput.

## Design
Integer price ticks and quantities; per-price FIFO queues and price heaps; GTC/IOC orders; partial fills and cancellation; resting-order execution price; quantity and live-order admission guards. SQLite transactions persist an append-only event record before replacing in-memory state. Identical event-ID retries return the prior result, conflicting retries fail. Restart reconstructs state and checks event sequence, result and SHA-256 chain. Corrupt replay closes the database before raising.

## Validation
12 core matching/replay unit tests include an independent list/sort reference across 10 seeds and 5,000 events, price/time priority, volume conservation, invalid-input atomicity, cancellation, restart, duplicate retries and tamper detection. The independent oracle is deliberately structurally different from the heap implementation.

## Data provenance and assumptions
Named source: code-generated synthetic IID events, [run.py](https://github.com/Anjaney336/quant-execution-lab/blob/main/run.py). Generated/access date: 2026-10-24. No employer, customer or exchange data. Price ticks 95â€“105, quantities 1â€“30, random side; every third order IOC. These are test assumptions, not market-calibrated distributions. Input/output hashes accompany results.

## Limitations
One writer, one instrument, no networking, auctions, replace orders, fees, positions, exchange connectivity or distributed recovery. Copying book state for persistence prioritises clarity over speed. Hash chains are not authenticated and are not a security guarantee. Timing excludes persistence, JSON encoding and networking. No C++, latency advantage or exchange realism is claimed.
