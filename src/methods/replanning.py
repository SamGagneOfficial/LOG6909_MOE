import copy

import numpy as np

from simulation import dispatch_setpoint, load_profile, task_steps


class ReplanningEMS:
    # Online use of a day planner (MILP, DP...): tasks are only known once they arrive.
    # Whenever new tasks arrive, the planner re-optimises the rest of the day from the current state
    # (measured battery, running tasks, known tasks not started yet); its plan is followed until the next re-plan.
    # Re-plans are at least `interval` steps apart: tasks arriving in between wait for the next one,
    # which must stay shorter than the slack of any task (2 h window minus at most 1 h of duration here).

    def __init__(
        self,
        planner,
        interval: int = 1,                  # [steps] minimal time between two re-plans
        expected_arrivals: bool = False,    # Reserve room for the tasks still to come, as PredictiveEMS does
        window: int = 4,                    # [steps] past arrivals used for that estimate
        horizon: int = 12,                  # [steps] over which the expected load is spread
        name: str | None = None
    ):
        self.planner = planner
        self.interval = interval
        self.expected_arrivals = expected_arrivals
        self.window = window
        self.horizon = horizon
        self.name = name or f"{planner.name} (replan)"
        self.replans = 0

    def solve(self, forecast, tasks, battery, deltaT, actual=None):
        actual = forecast if actual is None else actual
        n_steps = len(forecast)
        battery = copy.deepcopy(battery)

        steps = {task["id"]: task_steps(task, deltaT, n_steps) for task in tasks}
        arrivals = sorted({steps[task["id"]]["release"] for task in tasks})

        starts = {}
        battery_plan = np.zeros(n_steps)
        self.replans = 0

        # Re-plan steps: the next arrival, but no sooner than `interval` steps after the previous re-plan
        replans = [arrivals[0]]
        for arrival in arrivals:
            if arrival > replans[-1]:
                replans.append(max(arrival, replans[-1] + self.interval))
        boundaries = [0] + replans + [n_steps]

        # Before the first arrival, no task: PV surplus is stored
        battery_plan[:arrivals[0]] = actual[:arrivals[0]]
        for t in range(arrivals[0]):
            dispatch_setpoint(battery, actual[t], battery_plan[t], deltaT, True)

        for i, t0 in enumerate(replans):
            t1 = boundaries[i + 2]

            # Known tasks not started yet, with times shifted so that t0 becomes step 0
            known = [
                dict(task, arrival=max(0.0, task["arrival"] - t0 * deltaT), deadline=task["deadline"] - t0 * deltaT)
                for task in tasks
                if steps[task["id"]]["release"] <= t0 and task["id"] not in starts
            ]
            committed = load_profile(tasks, starts, deltaT, n_steps)[t0:]

            # Tasks still to come, estimated from the energy arrived over the last window and
            # spread as a background load over the next hours. Planned around, never scheduled.
            expected = np.zeros(n_steps - t0)
            if self.expected_arrivals:
                arrived = sum(
                    task["power"] * task["duration"] for task in tasks
                    if t0 - self.window < steps[task["id"]]["release"] <= t0
                )
                expected[:self.horizon] = arrived / (self.window * deltaT)

            plan = self.planner.solve(
                forecast[t0:], known, copy.deepcopy(battery), deltaT, actual[t0:], committed=committed + expected
            )
            self.replans += 1

            # Follow the plan until the next arrival
            for task_id, s in plan["starts"].items():
                if s < t1 - t0:
                    starts[task_id] = t0 + s

            battery_plan[t0:t1] = plan["battery"][:t1 - t0]

            load = load_profile(tasks, starts, deltaT, n_steps)
            for t in range(t0, t1):
                # The plan was made for the expected load too: never discharge more than the actual deficit
                # (the rest would be exported) nor charge more than the actual surplus (it would be imported)
                if self.expected_arrivals:
                    battery_plan[t] = min(max(battery_plan[t], -max(load[t] - actual[t], 0.0)),
                                          max(actual[t] - load[t], 0.0))
                dispatch_setpoint(battery, actual[t] - load[t], battery_plan[t], deltaT, True)

        return {"starts": starts, "battery": battery_plan}
