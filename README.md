
# Smiths Falls Airport - Discrete Event Simulation

A SimPy-based discrete event simulation modeling passenger flow through a small regional airport. Built to evaluate operational performance under varying configurations and identify bottlenecks in the passenger pipeline.

## Problem Statement

Smiths Falls airport services two flight types - regional and provincial - each with different capacities, schedules, and passenger classes. The airport must process all passengers through a shared pipeline of check-in counters, security screening, and departure gates, each with limited capacity.

The core question: **given a fixed arrival rate and flight schedule, how do staffing levels and resource allocation affect passenger throughput, wait times, and revenue?**

Specific operational constraints that make this interesting:

- **Regional flights:** coach only, 40 seats, depart hourly starting at 00:30. If a flight is full, the passenger queues for the next one (no one is turned away).
- **Provincial flights:** 140 coach + 40 business seats, depart every 6 hours. If a flight is full, business passengers who arrived early (>90 min before departure) get a refund. Late arrivals are simply turned away.
- **Check-in:** business and coach passengers use separate counters. Service time includes boarding pass printing, bag check, and random delays.
- **Security:** passengers are routed to provincial or regional screening based on their flight type.
- **Single arrival process:** all passengers arrive via one Poisson process (exponential inter-arrival times), then are randomly classified as regional or provincial.

## Simulation Study Goals

1. **Identify bottlenecks** - which station creates the longest queues under default parameters?
2. **Resource sensitivity** - how does adding a check-in counter or security machine affect overall throughput?
3. **Revenue analysis** - total ticket revenue vs operational costs (flights + staff) across different configurations.
4. **Queue behavior** - regional gate overflow queue dynamics: how long do passengers wait, and does the queue grow unboundedly at high arrival rates?

## How It Works

This is a forward **Monte Carlo simulation** walking a **Markov chain** - each passenger's next state depends only on their current state and random service times. It is not MCMC (there is no acceptance rule and we are not sampling from an intractable distribution). We are observing system behavior under stochastic inputs.

The simulation uses SimPy's process-based discrete event model:
- Each passenger is a SimPy **process** (a generator that yields events)
- Stations wrap SimPy **Resources** (limited capacity servers with automatic queuing)
- The regional gate uses a SimPy **Store** for overflow queuing
- Service times are drawn from exponential and geometric distributions via NumPy

## Running

```bash
source venv/bin/activate
python -m src.airport.simulation      # run the sim (interactive prompts for parameters)
python -m src.airport.visualizer      # launch PyQt6 playback visualizer
```

The simulation generates daily CSV logs in `src/airport/data/`. The visualizer replays passenger movement through the airport with real-time stats, flight board, and histogram analysis.

## Hardcoded Parameters

These values are baked into the simulation and not exposed as user-configurable inputs:

### Ticket Prices

| Passenger Type | Price |
|---|---|
| Business (provincial) | $1,000 |
| Coach (provincial) | $500 |
| Coach (regional/commuter) | $200 |

### Flight Operating Costs

| Flight Type | Cost per Departure |
|---|---|
| Provincial | $12,000 |
| Regional | $1,500 |

### Staff Cost

- $20/hr per worker (check-in counters + security stations)

### Refund Rule

- Business passengers who arrived more than 90 minutes before departure and find no seats receive a full ticket refund ($1,000)
- Late arrivals (within 90 min) are turned away with no refund

### Flight Capacity

| Flight Type | Coach Seats | Business Seats |
|---|---|---|
| Regional | 40 | - |
| Provincial | 140 | 40 |

### Flight Schedule

| Flight Type | First Departure | Interval |
|---|---|---|
| Regional | 00:30 | Every hour |
| Provincial | 00:00 | Every 6 hours |

## Architecture Diagrams

### Class Diagram

Full class hierarchy, SimPy Resource/Store ownership, composition and dependencies. ([mermaid source](class_diagram.md))

![Class Diagram](class_diagram.png)

### Sequence Diagram

Passenger lifecycle through the pipeline: check-in (Resource), security (Resource), gate (Store for regional overflow, Event.succeed() for provincial). ([mermaid source](sequence_diagram.md))

![Sequence Diagram](sequence_diagram.png)

## Dependencies

Python 3.9+, SimPy, NumPy, Pandas, Matplotlib, PyQt6

```bash
pip install simpy numpy pandas matplotlib pyqt6
```
