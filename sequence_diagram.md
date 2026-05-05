---
config:
  layout: elk
---
sequenceDiagram
    participant S as Simulation
    participant A as Airport
    participant CC as CheckinCounter
    participant CR as counter : Resource
    participant SS as SecurityScreening
    participant SR as machine : Resource
    participant F as Flight
    participant RG as RegionalGate
    participant Q as queue : Store
    participant PG as ProvincialGate

    S->>A: env.process(process_passenger(p))

    Note over A: Stage 1: Check-in (routed by seat_type)
    alt business passenger
        A->>A: counters = business_class_counters
    else coach passenger
        A->>A: counters = coach_counters
    end
    A->>A: _find_shortest_queue(counters)
    A->>CC: yield env.process(handle_check_in(p))
    CC->>CR: yield counter.request()
    Note over CC,CR: blocked until counter is free
    CR-->>CC: granted
    Note over CC: compute service time:<br/>boarding_pass + bags + delays
    CC->>CC: yield env.timeout(total_time)
    Note over CC: sim time advances
    CC-->>A: check-in complete

    Note over A: Stage 2: Security (routed by gate_type)
    alt commuter
        A->>A: machines = [s.regional_machine]
    else provincial
        A->>A: machines = [s.provincial_machine]
    end
    A->>A: _find_shortest_queue(screening)
    A->>SS: yield env.process(screen_passenger(p))
    SS->>SR: yield machine.request()
    Note over SS,SR: blocked until machine is free
    SR-->>SS: granted
    SS->>SS: yield env.timeout(screening_time)
    Note over SS: sim time advances
    SS-->>A: screening complete

    Note over A: Stage 3: Gate (routed by gate_type, round-robin)
    alt commuter -> RegionalGate
        A->>RG: yield env.process(handle_passenger(p))
        RG->>RG: find_current_flight()
        alt seats available
            RG->>F: board_passenger(p)
            Note over RG,F: plain method call, no yield
            F-->>RG: boarded
            RG-->>A: done
        else flight full
            RG->>Q: yield queue.put(p)
            Note over Q: passenger stored in SimPy Store
            RG-->>A: done (passenger waits in queue)
            Note over Q: process_queue() runs separately:<br/>yield queue.get() -> board on next flight
        end
    else provincial -> ProvincialGate
        A->>PG: yield env.process(handle_passenger(p))
        PG->>PG: find_current_flight()
        alt seats available
            PG->>F: board_passenger(p)
            Note over PG,F: plain method call, no yield
            F-->>PG: boarded
        else no seats + arrived early (>90min before departure)
            Note over PG: Refund - passenger leaves
        else no seats + arrived late
            Note over PG: Late - passenger leaves
        end
        PG->>PG: yield Event(env).succeed()
        Note over PG: already-resolved event,<br/>no sim time passes
        PG-->>A: done
    end
