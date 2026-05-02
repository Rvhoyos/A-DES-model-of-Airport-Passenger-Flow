from dataclasses import dataclass
import simpy
from .logger import Logger


@dataclass
class SimulationContext:
    env: simpy.Environment
    logger: Logger
    simulation_time: int
