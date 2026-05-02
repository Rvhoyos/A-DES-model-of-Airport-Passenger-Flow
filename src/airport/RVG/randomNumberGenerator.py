from abc import ABC, abstractmethod
import numpy as np


# todo refactor to use this class in the aiport.py and related classes.
class RandomNumberGenerator(ABC):
    @abstractmethod
    def generate(self):
        pass


class ExponentialRandomNumberGenerator(RandomNumberGenerator):
    def __init__(self, rate):
        self.rate = rate

    def generate(self):
        return np.random.exponential(1 / self.rate)  # 1/rate = mean time between events


class NormalRandomNumberGenerator(RandomNumberGenerator):
    def __init__(self, mean, variance):
        self.mean = mean
        self.variance = variance

    def generate(self):
        return np.random.normal(self.mean, np.sqrt(self.variance))


class GeometricRandomNumberGenerator(RandomNumberGenerator):
    def __init__(self, p):
        self.p = p

    def generate(self):
        return np.random.geometric(p=self.p) - 1  # Subtracting 1 because geometric distribution starts at 1



