
import numpy as np

EPS = 1e-9

class Factory:

    def __init__(
        self,
        job_type_amount: int = 3,
        min_power: float = 1,                   #kW
        power_between_types: float = 1,         #kW
        durations: list[float] | None = None,
        type_distri: list[float] | None = None,
        duration_distri: list[float] | None = None
    ):
        self.processes = [
            min_power + i * power_between_types
            for i in range(job_type_amount)
        ]

        if job_type_amount <= 0:
            job_type_amount = 3

        if min_power <= 0:
            min_power = 1

        if power_between_types <= 0:
            power_between_types = 1

        if durations is None:
            durations = [0.25 * (i + 1) for i in range(4)]

        if type_distri is None:
            type_distri = [1 / job_type_amount] * job_type_amount

        if duration_distri is None:
            duration_distri = [1 / len(durations)] * len(durations)

        
        if len(type_distri) != job_type_amount:
            raise ValueError("One probability is required per type")

        if len(duration_distri) != len(durations):
            raise ValueError("One probability is required per duration time")

        if any(d <= 0 for d in durations):
            raise ValueError("Durations must be positive")

        if any(p < 0 for p in type_distri):
            raise ValueError("Probabilities must be non-negative, "
                             "with a positive sum")

        if any(p < 0 for p in duration_distri):
            raise ValueError("Probabilities must be non-negative, "
                                "with a positive sum")

        self.durations = durations
        self.t_distri = (np.array(type_distri, dtype=float) / sum(type_distri))
        self.d_distri = (np.array(duration_distri, dtype=float) / sum(duration_distri))

    arrival_profiles = ["uniform", "early", "late", "bimodal", "hourly"]

    def gen_arrivals(
        self,
        rng,
        task_amount: int,
        profile: str = "uniform",
        opening_time: float = 6,
        last_arrival: float = 16,
        decay: float = 0.3,                 # [1/h] rate of the early/late exponentials
        burst_spread: float = 0.5,          # [h] standard deviation of the bimodal bursts
        time_step: float = 0.25
    ) -> np.ndarray:
        # Arrival times [h] between opening_time and last_arrival, rounded down to the time step
        span = last_arrival - opening_time

        if profile == "hourly":
            # Former behaviour: tasks arrive in bursts on the hour
            return rng.integers(int(opening_time), int(last_arrival), size=task_amount).astype(float)

        if profile == "uniform":
            offsets = rng.uniform(0, span, size=task_amount)

        elif profile in ("early", "late"):
            # Truncated exponential sampled by inverse CDF: decreasing from the opening (early),
            # or its mirror, increasing towards the last arrival (late)
            u = rng.uniform(size=task_amount)
            offsets = -np.log(1 - u * (1 - np.exp(-decay * span))) / decay
            if profile == "late":
                offsets = span - offsets

        elif profile == "bimodal":
            # Half the tasks right after opening, half around midday
            midday = 12 - opening_time
            at_opening = rng.uniform(size=task_amount) < 0.5
            offsets = np.where(
                at_opening,
                np.abs(rng.normal(0, burst_spread, size=task_amount)),
                rng.normal(midday, burst_spread, size=task_amount)
            )

        else:
            raise ValueError(f"Unknown arrival profile, choose from {self.arrival_profiles}")

        offsets = np.clip(offsets, 0, span - EPS)
        return opening_time + np.floor(offsets / time_step) * time_step

    def gen_daily_tasks(
        self,
        task_amount: int = 50,
        max_delay: float = 2,
        closing_time: float = 18,
        seed: int = 42,
        arrival_profile: str = "uniform",
        time_step: float = 0.25,
        decay: float = 0.3                  # [1/h] rate of the early/late exponentials
    ) -> list[dict]:

        rng = np.random.default_rng(seed)

        task_types = rng.choice(
            len(self.processes),
            size=task_amount,
            p=self.t_distri
        )

        task_durations = rng.choice(
             self.durations,
             size=task_amount,
             p=self.d_distri
        )

        #Receiving jobs between 6am and 4pm
        arrivals = self.gen_arrivals(rng, task_amount, arrival_profile, decay=decay, time_step=time_step)

        tasks = []

        for i in range(task_amount):
             task_type = int(task_types[i])

             tasks.append({
                  "id"      : i,
                  "type"    : task_type,
                  "power"   : self.processes[task_type],
                  "duration": float(task_durations[i]),
                  "arrival" : float(min(arrivals[i], closing_time - max_delay)),
                  "deadline": float(min(arrivals[i] + max_delay, closing_time))
             })

        return sorted(tasks, key=lambda task: task["arrival"])
