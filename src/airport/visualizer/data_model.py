from __future__ import annotations

import glob
import os
import re
from bisect import bisect_right
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import pandas as pd


@dataclass
class PassengerEvent:
    time: float
    end_time: float       # time + duration when duration exists, else == time
    event: str
    station: Optional[str]
    visual_time: float = 0.0       # adjusted time for smooth visual transitions
    visual_end_time: float = 0.0   # adjusted end_time for visual transitions


@dataclass
class PassengerTimeline:
    passenger_id: int
    gate_type: str
    seat_type: str
    bags: int = 0
    cost: float = 0.0
    events: List[PassengerEvent] = field(default_factory=list)
    arrival_time: float = 0.0
    departure_time: float = 0.0
    visual_departure_time: float = 0.0


@dataclass
class PassengerState:
    current_station: Optional[str]
    next_station: Optional[str]
    fraction: float
    station_arrival_time: float
    event: str


@dataclass
class StatsTimeSeries:
    arrival_times: List[float] = field(default_factory=list)
    boarding_events: List[Tuple[float, float]] = field(default_factory=list)
    refund_events: List[Tuple[float, float]] = field(default_factory=list)
    late_times: List[float] = field(default_factory=list)
    queue_times: List[float] = field(default_factory=list)
    dequeue_times: List[float] = field(default_factory=list)
    departure_events: List[Tuple[float, float]] = field(default_factory=list)
    gate_boarding_times: Dict[str, List[float]] = field(default_factory=dict)
    worker_count: int = 0


@dataclass
class DayBoundary:
    day: int
    start_time: float
    end_time: float


# Event ordering for sorting events that share the same timestamp
_EVENT_ORDER = {
    'Arrival': 0,
    'Process Start': 1,
    'Check-in Queue': 2,
    'Check-in Start': 3,
    'Check-in': 4,
    'Security Queue': 5,
    'Security Start': 6,
    'Security Screening': 7,
    'Gate Arrival': 8,
    'Boarding': 9,
    'Queue': 10,
    'Boarding from Queue': 11,
    'Refund': 12,
    'Late': 13,
}

# Station category classification
_STATION_CATEGORIES = [
    ('business_checkin', re.compile(r'Business Counter', re.IGNORECASE)),
    ('coach_checkin', re.compile(r'Coach Counter', re.IGNORECASE)),
    ('security', re.compile(r'Security Station', re.IGNORECASE)),
    ('regional_gate', re.compile(r'Regional Gate', re.IGNORECASE)),
    ('provincial_gate', re.compile(r'Provincial Gate', re.IGNORECASE)),
]


# Visual travel time injected between events at different stations (seconds).
# This gives the viewer time to see passengers walk between stations.
MIN_VISUAL_TRAVEL = 45.0

# Extra time passenger lingers at final station before fading out
FADE_OUT_BUFFER = 30.0


class SimulationData:
    """Loads all day CSV files, builds per-passenger event timelines,
    and provides efficient time-based queries for the visualizer."""

    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.df: pd.DataFrame = pd.DataFrame()
        self.day_boundaries: List[DayBoundary] = []
        self.passengers: Dict[int, PassengerTimeline] = {}
        self.station_categories: Dict[str, List[str]] = {}
        self.all_stations: List[str] = []
        self.min_time: float = 0.0
        self.max_time: float = 0.0

        # Sorted list of (arrival_time, passenger_id) for efficient window queries
        self._sorted_arrivals: List[Tuple[float, int]] = []
        self.stats: StatsTimeSeries = StatsTimeSeries()

        self._load()

    def _load(self) -> None:
        csv_files = sorted(
            glob.glob(os.path.join(self.data_dir, 'day_*_log.csv')),
            key=lambda f: int(re.search(r'day_(\d+)', f).group(1))
        )
        if not csv_files:
            return

        frames = []
        for path in csv_files:
            day_num = int(re.search(r'day_(\d+)', path).group(1))
            df = pd.read_csv(path)
            df['_day'] = day_num
            frames.append(df)

        self.df = pd.concat(frames, ignore_index=True)

        # Record day boundaries
        for day_num, grp in self.df.groupby('_day'):
            self.day_boundaries.append(DayBoundary(
                day=int(day_num),
                start_time=float(grp['Time'].min()),
                end_time=float(grp['Time'].max()),
            ))
        self.day_boundaries.sort(key=lambda b: b.day)

        self.min_time = float(self.df['Time'].min())
        self.max_time = float(self.df['Time'].max())

        self._discover_stations()
        self._build_timelines()
        self._build_stats()

    def _discover_stations(self) -> None:
        raw = self.df['Station'].dropna().unique()
        categories: Dict[str, List[str]] = {}
        for name in raw:
            name_str = str(name)
            matched = False
            for cat, pattern in _STATION_CATEGORIES:
                if pattern.search(name_str):
                    categories.setdefault(cat, []).append(name_str)
                    matched = True
                    break
            if not matched:
                # Skip flight departure stations and other non-physical stations
                continue

        # Sort each category by the numeric suffix
        def _sort_key(s: str) -> int:
            m = re.search(r'(\d+)', s)
            return int(m.group(1)) if m else 0

        for cat in categories:
            categories[cat].sort(key=_sort_key)

        self.station_categories = categories
        self.all_stations = [s for names in categories.values() for s in names]

    def _build_timelines(self) -> None:
        # Filter to passenger events only (have a Passenger ID)
        pdf = self.df[self.df['Passenger ID'].notna()].copy()
        pdf['Passenger ID'] = pdf['Passenger ID'].astype(int)

        for pid, group in pdf.groupby('Passenger ID'):
            group = group.copy()
            group['_event_order'] = group['Event'].map(
                lambda e: _EVENT_ORDER.get(e, 99)
            )
            group = group.sort_values(['Time', '_event_order'])
            rows = group.to_dict('records')
            if not rows:
                continue

            gate_type = str(rows[0].get('Gate Type', ''))
            seat_type = str(rows[0].get('Seat Type', ''))
            bags_raw = rows[0].get('Bags')
            bags = int(bags_raw) if pd.notna(bags_raw) else 0
            cost_raw = rows[0].get('Cost')
            cost = float(cost_raw) if pd.notna(cost_raw) else 0.0

            # Deduplicate gate bug: keep first Gate Arrival / Boarding only
            seen_gate_arrival = False
            seen_boarding = False
            events: List[PassengerEvent] = []
            for row in rows:
                ev_name = str(row['Event'])
                if ev_name == 'Gate Arrival':
                    if seen_gate_arrival:
                        continue
                    seen_gate_arrival = True
                elif ev_name == 'Boarding':
                    if seen_boarding:
                        continue
                    seen_boarding = True

                t = float(row['Time'])
                dur = row.get('Duration')
                end_t = t + float(dur) if pd.notna(dur) else t
                station = str(row['Station']) if pd.notna(row.get('Station')) else None
                events.append(PassengerEvent(
                    time=t,
                    end_time=end_t,
                    event=ev_name,
                    station=station,
                ))

            if not events:
                continue

            self._compute_visual_times(events)

            timeline = PassengerTimeline(
                passenger_id=pid,
                gate_type=gate_type,
                seat_type=seat_type,
                bags=bags,
                cost=cost,
                events=events,
                arrival_time=events[0].time,
                departure_time=events[-1].end_time,
                visual_departure_time=events[-1].visual_end_time,
            )
            self.passengers[pid] = timeline

        # Build sorted arrival list for efficient range queries
        self._sorted_arrivals = sorted(
            (tl.arrival_time, pid) for pid, tl in self.passengers.items()
        )

    def _build_stats(self) -> None:
        """Pre-compute sorted event lists for the real-time stats panel."""
        cats = self.station_categories
        worker_count = (
            len(cats.get('business_checkin', []))
            + len(cats.get('coach_checkin', []))
            + len(cats.get('security', []))
        )

        arrival_times = []
        boarding_events = []
        refund_events = []
        late_times = []
        queue_times = []
        dequeue_times = []
        gate_boarding: Dict[str, List[float]] = {}

        for tl in self.passengers.values():
            arrival_times.append(tl.arrival_time)
            for ev in tl.events:
                if ev.event in ('Boarding', 'Boarding from Queue'):
                    boarding_events.append((ev.time, tl.cost))
                    if ev.station:
                        gate_boarding.setdefault(ev.station, []).append(ev.time)
                    if ev.event == 'Boarding from Queue':
                        dequeue_times.append(ev.time)
                elif ev.event == 'Refund':
                    refund_events.append((ev.time, tl.cost))
                elif ev.event == 'Late':
                    late_times.append(ev.time)
                elif ev.event == 'Queue':
                    queue_times.append(ev.time)

        # Flight departures from raw DataFrame (no Passenger ID).
        departure_events = []
        flight_df = self.df[self.df['Event'] == 'Flight Departure']
        for _, row in flight_df.iterrows():
            cost = float(row['Cost']) if pd.notna(row.get('Cost')) else 0.0
            departure_events.append((float(row['Time']), cost))

        # Sort all lists by time for bisect queries
        arrival_times.sort()
        boarding_events.sort()
        refund_events.sort()
        late_times.sort()
        queue_times.sort()
        dequeue_times.sort()
        departure_events.sort()
        for times in gate_boarding.values():
            times.sort()

        self.stats = StatsTimeSeries(
            arrival_times=arrival_times,
            boarding_events=boarding_events,
            refund_events=refund_events,
            late_times=late_times,
            queue_times=queue_times,
            dequeue_times=dequeue_times,
            departure_events=departure_events,
            gate_boarding_times=gate_boarding,
            worker_count=worker_count,
        )

    @staticmethod
    def _compute_visual_times(events: List[PassengerEvent]) -> None:
        """Inject visual travel time between events at different stations.

        When consecutive events occur at different physical positions but share the
        same (or very close) timestamps, there is no time window for the viewer to
        see the passenger move. This pushes later events forward in *visual* time
        so interpolation produces visible movement through the airport.
        """
        # Seed visual times from actual times
        for ev in events:
            ev.visual_time = ev.time
            ev.visual_end_time = ev.end_time

        # Cascade: ensure minimum gap between events at different stations
        for i in range(1, len(events)):
            prev = events[i - 1]
            curr = events[i]

            # Only inject travel time when the station actually changes
            prev_station = prev.station
            curr_station = curr.station
            if prev_station != curr_station:
                earliest_arrival = prev.visual_end_time + MIN_VISUAL_TRAVEL
                if curr.visual_time < earliest_arrival:
                    curr.visual_time = earliest_arrival
                    # Preserve the event's internal duration
                    duration = curr.end_time - curr.time
                    curr.visual_end_time = curr.visual_time + duration
            else:
                # Same station: ensure visual ordering is consistent
                if curr.visual_time < prev.visual_end_time:
                    curr.visual_time = prev.visual_end_time
                    duration = curr.end_time - curr.time
                    curr.visual_end_time = curr.visual_time + duration

    def get_passenger_state(
        self, timeline: PassengerTimeline, t: float
    ) -> Optional[PassengerState]:
        """Return the passenger's visual state at time t, or None if inactive.

        Uses visual_time for smooth interpolated movement.
        station_arrival_time is the visual_time of the current event - used for FIFO queue ordering.
        """
        if t < timeline.arrival_time or t > timeline.visual_departure_time + FADE_OUT_BUFFER:
            return None

        events = timeline.events
        # bisect on visual_time to find position
        vtimes = [e.visual_time for e in events]
        idx = bisect_right(vtimes, t) - 1
        if idx < 0:
            # Before first visual event - place at entrance
            return PassengerState('Entrance', events[0].station, 0.0, events[0].visual_time, 'Arrival')

        current = events[idx]

        # Inside a duration-based event (e.g. security screening): stay put
        if current.visual_end_time > current.visual_time and t < current.visual_end_time:
            return PassengerState(current.station, current.station, 0.0, current.visual_time, current.event)

        # Interpolate toward next event
        if idx + 1 < len(events):
            nxt = events[idx + 1]
            start_t = current.visual_end_time
            end_t = nxt.visual_time
            if end_t > start_t:
                frac = min(1.0, max(0.0, (t - start_t) / (end_t - start_t)))
            else:
                frac = 1.0
            return PassengerState(current.station, nxt.station, frac, current.visual_time, current.event)

        # Past last event - stay at final station
        return PassengerState(current.station, current.station, 0.0, current.visual_time, current.event)

    def get_active_passengers(self, t: float) -> Dict[int, PassengerState]:
        """Return {pid: PassengerState} for all passengers active at simulation time t."""
        result: Dict[int, PassengerState] = {}
        for arrival_t, pid in self._sorted_arrivals:
            if arrival_t > t:
                break
            tl = self.passengers[pid]
            state = self.get_passenger_state(tl, t)
            if state is not None:
                result[pid] = state
        return result

    @classmethod
    def from_directory(cls, data_dir: Optional[str] = None) -> SimulationData:
        if data_dir is None:
            data_dir = os.path.join(
                os.path.dirname(__file__), '..', 'data'
            )
        return cls(data_dir)
