"""Per-station and per-category statistics engine.

Provides bisect-based queries at any playback time T, following the same
architectural pattern as StatsEngine (real-time, O(log n) lookups).

Computes: service time, wait time, utilization, and throughput per station
and per category (all security, all gates, etc.).
"""
from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass
from typing import Dict, List, TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from .data_model import SimulationData


@dataclass
class StationMetrics:
    """Stats for a single station at a given playback time T."""
    station_name: str
    category: str
    passengers_served: int
    avg_service_time: float
    max_service_time: float
    avg_wait_time: float
    max_wait_time: float
    utilization: float
    throughput: float


@dataclass
class CategoryMetrics:
    """Aggregate stats for all stations in a category at time T."""
    category: str
    station_count: int
    total_served: int
    avg_service_time: float
    avg_wait_time: float
    combined_utilization: float
    throughput: float
    avg_throughput: float


# Capacity per station type (total resource slots).
# Security: 1 provincial + 2 regional machines = 3
# Check-in counters: 1 resource each
# Gates: boarding is instant, utilization not meaningful
_CAPACITY = {
    'security': 3,
    'business_checkin': 1,
    'coach_checkin': 1,
    'regional_gate': 0,
    'provincial_gate': 0,
}

# Events that represent completed service (Duration = service time)
_SERVICE_EVENTS = {'Security Screening', 'Check-in'}

# Events that represent completed waiting (Duration = wait time)
_WAIT_EVENTS = {'Security Start', 'Check-in Start', 'Boarding from Queue'}

# Events that count as "served" for throughput (one per passenger processed)
_SERVED_EVENTS = {'Security Screening', 'Check-in', 'Boarding', 'Boarding from Queue',
                  'Refund', 'Late'}


@dataclass
class EntranceMetrics:
    """Arrival stats for the Entrance at a given playback time T."""
    total_arrived: int
    arrival_rate: float
    regional_count: int
    provincial_count: int
    coach_count: int
    business_count: int
    avg_bags: float


class StationStatsEngine:
    """Bisect-based per-station statistics, queryable at any playback time."""

    def __init__(self, data: SimulationData):
        self._data = data
        self._station_categories = data.station_categories
        self._category_for: Dict[str, str] = {}

        # Per-station sorted arrays (built once at init)
        self._service_times: Dict[str, List[float]] = {}
        self._service_durations: Dict[str, List[float]] = {}
        self._wait_times: Dict[str, List[float]] = {}
        self._wait_durations: Dict[str, List[float]] = {}
        self._served_times: Dict[str, List[float]] = {}

        # Entrance arrival arrays
        self._arrival_times: List[float] = []
        self._arrival_regional_times: List[float] = []
        self._arrival_provincial_times: List[float] = []
        self._arrival_coach_times: List[float] = []
        self._arrival_business_times: List[float] = []
        self._arrival_bags: List[float] = []

        self._build(data)

    def _build(self, data: SimulationData) -> None:
        # Build category lookup
        for cat, stations in data.station_categories.items():
            for station in stations:
                self._category_for[station] = cat

        df = data.df
        if df.empty:
            return

        # Filter to rows with Station and Duration
        has_station = df['Station'].notna()
        has_duration = df['Duration'].notna()

        # Build service time arrays
        service_mask = has_station & has_duration & df['Event'].isin(_SERVICE_EVENTS)
        service_df = df[service_mask].sort_values('Time')
        for station, grp in service_df.groupby('Station'):
            station_str = str(station)
            if station_str not in self._category_for:
                continue
            self._service_times[station_str] = grp['Time'].tolist()
            self._service_durations[station_str] = grp['Duration'].tolist()

        # Build wait time arrays
        wait_mask = has_station & has_duration & df['Event'].isin(_WAIT_EVENTS)
        wait_df = df[wait_mask].sort_values('Time')
        for station, grp in wait_df.groupby('Station'):
            station_str = str(station)
            if station_str not in self._category_for:
                continue
            self._wait_times[station_str] = grp['Time'].tolist()
            self._wait_durations[station_str] = grp['Duration'].tolist()

        # Build served counts (for throughput - counts all passengers processed)
        served_mask = has_station & df['Event'].isin(_SERVED_EVENTS)
        served_df = df[served_mask].sort_values('Time')
        for station, grp in served_df.groupby('Station'):
            station_str = str(station)
            if station_str not in self._category_for:
                continue
            self._served_times[station_str] = grp['Time'].tolist()

        # Build entrance arrival arrays
        arrivals = df[df['Event'] == 'Arrival'].sort_values('Time')
        if not arrivals.empty:
            self._arrival_times = arrivals['Time'].tolist()
            self._arrival_bags = arrivals['Bags'].fillna(0).tolist()
            regional = arrivals[arrivals['Gate Type'] == 'commuter'].sort_values('Time')
            provincial = arrivals[arrivals['Gate Type'] == 'provincial'].sort_values('Time')
            self._arrival_regional_times = regional['Time'].tolist()
            self._arrival_provincial_times = provincial['Time'].tolist()
            coach = arrivals[arrivals['Seat Type'] == 'coach'].sort_values('Time')
            business = arrivals[arrivals['Seat Type'] == 'business'].sort_values('Time')
            self._arrival_coach_times = coach['Time'].tolist()
            self._arrival_business_times = business['Time'].tolist()

    def compute_station(self, station: str, t: float) -> StationMetrics:
        """Compute stats for a station up to playback time t."""
        category = self._category_for.get(station, 'unknown')

        # Service time stats
        svc_times = self._service_times.get(station, [])
        svc_durs = self._service_durations.get(station, [])
        svc_idx = bisect_right(svc_times, t)
        svc_slice = svc_durs[:svc_idx]

        if svc_slice:
            avg_service = np.mean(svc_slice)
            max_service = max(svc_slice)
        else:
            avg_service = 0.0
            max_service = 0.0

        # Wait time stats
        wait_times = self._wait_times.get(station, [])
        wait_durs = self._wait_durations.get(station, [])
        wait_idx = bisect_right(wait_times, t)
        wait_slice = wait_durs[:wait_idx]

        if wait_slice:
            avg_wait = np.mean(wait_slice)
            max_wait = max(wait_slice)
        else:
            avg_wait = 0.0
            max_wait = 0.0

        # Utilization: sum(service_durations) / (elapsed * capacity)
        capacity = _CAPACITY.get(category, 0)
        if capacity > 0 and t > 0:
            total_busy = sum(svc_slice)
            utilization = min(1.0, total_busy / (t * capacity))
        else:
            utilization = 0.0

        # Throughput: passengers served per hour (uses broader served count)
        served_times = self._served_times.get(station, [])
        passengers_served = bisect_right(served_times, t)
        throughput = (passengers_served / t * 3600) if t > 0 else 0.0

        return StationMetrics(
            station_name=station,
            category=category,
            passengers_served=passengers_served,
            avg_service_time=avg_service,
            max_service_time=max_service,
            avg_wait_time=avg_wait,
            max_wait_time=max_wait,
            utilization=utilization,
            throughput=throughput,
        )

    def compute_category(self, category: str, t: float) -> CategoryMetrics:
        """Aggregate stats for all stations in a category up to time t."""
        stations = self._station_categories.get(category, [])
        if not stations:
            return CategoryMetrics(
                category=category, station_count=0, total_served=0,
                avg_service_time=0.0, avg_wait_time=0.0,
                combined_utilization=0.0, throughput=0.0, avg_throughput=0.0,
            )

        all_svc_durs: List[float] = []
        all_wait_durs: List[float] = []
        total_busy = 0.0
        total_served = 0

        for station in stations:
            svc_times = self._service_times.get(station, [])
            svc_durs = self._service_durations.get(station, [])
            svc_idx = bisect_right(svc_times, t)
            all_svc_durs.extend(svc_durs[:svc_idx])
            total_busy += sum(svc_durs[:svc_idx])

            wait_times = self._wait_times.get(station, [])
            wait_durs = self._wait_durations.get(station, [])
            wait_idx = bisect_right(wait_times, t)
            all_wait_durs.extend(wait_durs[:wait_idx])

            served_times = self._served_times.get(station, [])
            total_served += bisect_right(served_times, t)

        station_count = len(stations)
        avg_service = float(np.mean(all_svc_durs)) if all_svc_durs else 0.0
        avg_wait = float(np.mean(all_wait_durs)) if all_wait_durs else 0.0

        capacity = _CAPACITY.get(category, 0)
        if capacity > 0 and t > 0:
            combined_utilization = min(1.0, total_busy / (t * capacity * station_count))
        else:
            combined_utilization = 0.0

        throughput = (total_served / t * 3600) if t > 0 else 0.0
        avg_throughput = throughput / station_count if station_count > 0 else 0.0

        return CategoryMetrics(
            category=category,
            station_count=station_count,
            total_served=total_served,
            avg_service_time=avg_service,
            avg_wait_time=avg_wait,
            combined_utilization=combined_utilization,
            throughput=throughput,
            avg_throughput=avg_throughput,
        )

    def compute_entrance(self, t: float) -> EntranceMetrics:
        """Compute arrival stats up to playback time t."""
        idx = bisect_right(self._arrival_times, t)
        regional = bisect_right(self._arrival_regional_times, t)
        provincial = bisect_right(self._arrival_provincial_times, t)
        coach = bisect_right(self._arrival_coach_times, t)
        business = bisect_right(self._arrival_business_times, t)
        avg_bags = float(np.mean(self._arrival_bags[:idx])) if idx > 0 else 0.0
        rate = (idx / t * 3600) if t > 0 else 0.0

        return EntranceMetrics(
            total_arrived=idx,
            arrival_rate=rate,
            regional_count=regional,
            provincial_count=provincial,
            coach_count=coach,
            business_count=business,
            avg_bags=avg_bags,
        )

    def category_for(self, station: str) -> str:
        """Return the category name for a station."""
        return self._category_for.get(station, 'unknown')
