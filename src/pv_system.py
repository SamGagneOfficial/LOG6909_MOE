import math
import numpy as np


class PVSystem:

    def __init__(self, max_power: float, efficiency: float, latitude: float):

        self.max_power = max_power
        self.efficiency = efficiency
        self.latitude = math.radians(latitude)

    def solar_declination(self, day: int) -> float:
        return math.radians(23.44 * math.sin(math.radians(360 / 365) * (day - 81)))

    def solar_elevation_factor(self, day: int, hour: float) -> float:

        decl = self.solar_declination(day)
        hour_angle = math.radians((360/24) * (hour - 12))

        sin_alpha = (
            math.sin(self.latitude) * math.sin(decl)
            + math.cos(self.latitude) * math.cos(decl) * math.cos(hour_angle)
        )

        return max(0.0, sin_alpha)

    def gen_daily_cloud_cover(
        self,
        time_step: float = 0.25,
        start_value: float = 0.1,
        average: float = 0.4,
        persistence: float = 0.9,
        perturbation: float = 0.1,
        seed: int = 42
    ) -> np.ndarray:

        if time_step <= 0 or 24 % time_step != 0:
            raise ValueError(
                "time_step must be positive and divide 24 hours"
            )

        if not 0 <= average <= 1:
            raise ValueError("average must be in [0, 1]")

        if not 0 <= persistence < 1:
            raise ValueError("persistence must be in [0, 1)")

        if perturbation < 0:
            raise ValueError("perturbation must be non-negative")

        rng = np.random.default_rng(seed)
        n_steps = int(24 / time_step)

        cloudiness = np.empty(n_steps)
        cloudiness[0] = start_value

        for step in range(1, n_steps):
            previous = cloudiness[step - 1]

            cloudiness[step] = np.clip(
                persistence * previous
                + (1 - persistence) * average
                + rng.normal(0, perturbation),
                0, 1
            )

        return cloudiness

    def gen_daily_power(
        self,
        time_step: float = 0.25,
        day: int = 172,
        is_cloudy: bool = False,
        seed: int = 42,
        cloud_average: float = 0.4          # Long-run cloudiness the cover tends to (0-1)
    ) -> np.ndarray:

        if time_step <= 0 or 24 % time_step != 0:
            raise ValueError(
                "time_step must be positive and divide 24 hours"
            )

        n_steps = int(24 / time_step)

        hours = np.arange(n_steps) * time_step

        solar_factor = np.array([
            self.solar_elevation_factor(day, hour)
            for hour in hours
        ])

        power = self.max_power * self.efficiency * solar_factor

        if is_cloudy:
            cloudiness = self.gen_daily_cloud_cover(
                time_step=time_step, start_value=cloud_average, average=cloud_average, seed=seed
            )

            # Simplified relationship: 80% attenuation
            # at maximum cloudiness.
            transmission = 1.0 - 0.8 * cloudiness

            power *= transmission

        return power
