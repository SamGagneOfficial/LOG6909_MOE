import time

import numpy as np
import pulp

from cost import CostFunction
from simulation import task_steps


class MilpEMS:
    name = "MILP"

    def __init__(
        self,
        cost_function : CostFunction,
        peak_resolution: float = 0.5,       # [kW] spacing of the tangents approximating the squared peak
        peak_range: float = 30.0,           # [kW] largest excess modelled with fine tangents
        time_limit: float = 60.0,           # [s] solver time limit
        mip_gap: float = 0.0                # Relative optimality gap at which the solver may stop
    ):
        self.mip_gap = mip_gap
        self.limit_hits = 0                 # Solves stopped by the time limit, counted across calls
        self.cost_func = cost_function
        self.peak_points = np.append(np.arange(0.0, peak_range + 1e-9, peak_resolution), [40.0, 60.0, 100.0])
        self.time_limit = time_limit
        self.objective = None
        self.status = None

    def solve(self, power, tasks, battery, deltaT, actual=None, committed=None):
        # Optimisation until the end of the day on the PV forecast (power), planned once: the actual profile is never seen.
        # committed: load [kW] of tasks already running, per step.
        # Returns a schedule {task id: start step} and the planned battery power [kW, + charge],
        # scored later by simulation.evaluate_schedule
        n_steps = len(power)
        cf = self.cost_func
        T = range(n_steps)

        model = pulp.LpProblem("ems", pulp.LpMinimize)

        # Task start decisions: x[j, s] = 1 if task j starts at step s
        steps = {task["id"]: task_steps(task, deltaT, n_steps) for task in tasks}
        x = {
            (task["id"], s): pulp.LpVariable(f"x_{task['id']}_{s}", cat="Binary")
            for task in tasks
            for s in range(steps[task["id"]]["release"], steps[task["id"]]["latest"] + 1)
        }

        for task in tasks:
            model += pulp.lpSum(v for (j, _), v in x.items() if j == task["id"]) == 1, f"start_{task['id']}"

        # Load at step t: tasks started within the last `duration` steps
        power_of = {task["id"]: task["power"] for task in tasks}
        load = [[] if committed is None else [committed[t]] for t in T]
        for (j, s), v in x.items():
            for t in range(s, min(s + steps[j]["duration"], n_steps)):
                load[t].append(power_of[j] * v)

        # Energy flows [kW] and battery energy [kWh]
        ch = [pulp.LpVariable(f"ch_{t}", 0, min(battery.max_power, power[t])) for t in T]   # charging from PV only
        dis = [pulp.LpVariable(f"dis_{t}", 0, battery.max_power) for t in T]
        imp = [pulp.LpVariable(f"imp_{t}", 0) for t in T]
        exp = [pulp.LpVariable(f"exp_{t}", 0) for t in T]
        energy = [pulp.LpVariable(f"e_{t}", battery.min_energy, battery.max_energy) for t in range(n_steps + 1)]
        excess = [pulp.LpVariable(f"excess_{t}", 0) for t in T]
        squared = [pulp.LpVariable(f"squared_{t}", 0) for t in T]

        model += energy[0] == battery.energy, "initial_energy"

        for t in T:
            model += power[t] + dis[t] + imp[t] == pulp.lpSum(load[t]) + ch[t] + exp[t], f"balance_{t}"
            model += (
                energy[t + 1] == energy[t]
                + battery.efficiency * ch[t] * deltaT
                - dis[t] * deltaT / battery.efficiency
            ), f"battery_{t}"

            # Squared excess, from below by tangents of e^2 at each point a: 2*a*e - a^2
            model += excess[t] >= imp[t] - cf.peak_threshold, f"excess_{t}"
            for k, a in enumerate(self.peak_points):
                model += squared[t] >= 2 * a * excess[t] - a * a, f"tangent_{t}_{k}"

        model += pulp.lpSum(
            deltaT * (
                cf.import_coeff * imp[t]
                - cf.export_coeff * exp[t]
                + cf.battery_coeff * (ch[t] + dis[t])
                + cf.peak_coeff * squared[t]
            )
            for t in T
        )

        start = time.perf_counter()
        model.solve(pulp.PULP_CBC_CMD(msg=False, timeLimit=self.time_limit, gapRel=self.mip_gap))
        if time.perf_counter() - start >= 0.95 * self.time_limit:
            self.limit_hits += 1

        self.status = pulp.LpStatus[model.status]
        self.objective = pulp.value(model.objective)

        starts = {j: s for (j, s), v in x.items() if v.value() is not None and v.value() > 0.5}
        battery_plan = np.array([(ch[t].value() or 0.0) - (dis[t].value() or 0.0) for t in T])

        return {"starts": starts, "battery": battery_plan}
