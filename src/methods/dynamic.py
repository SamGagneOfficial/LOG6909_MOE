import numpy as np

from cost import CostFunction
from simulation import task_steps

EPS = 1e-9


class DynamicProgrammingEMS:

    def __init__(
        self,
        cost_function : CostFunction,
        energy_step: float = 0.1,           # [kWh] resolution of the battery energy levels
        scenarios=None,                     # PV profiles [kW] to average the cost-to-go over; None: the forecast only
        closed_loop: bool = False,          # True: policy reacting to the measured PV; False: plan followed blindly
        name: str = "DP"
    ):
        self.cost_func = cost_function
        self.energy_step = energy_step
        self.scenarios = None if scenarios is None else np.atleast_2d(scenarios)
        self.closed_loop = closed_loop
        self.name = name
        self.state_count = 0
        self.expected_cost = None

    def _transition_costs(self, levels, battery, pv, load, dt):
        # Cost of moving from every energy level (rows) to every other (columns) during one step.
        # pv may be one value or an array of scenarios, giving one cost matrix per scenario.
        cf = self.cost_func
        pv = np.asarray(pv, dtype=float)[..., None, None]
        delta = levels[None, :] - levels[:, None]       # Stored energy change [kWh]

        ch = np.where(delta > 0, delta / battery.efficiency / dt, 0.0)     # [kW] at the terminals
        dis = np.where(delta < 0, -delta * battery.efficiency / dt, 0.0)

        grid = load + ch - pv - dis
        imp = np.maximum(grid, 0.0)
        exp = np.maximum(-grid, 0.0)
        excess = np.maximum(imp - cf.peak_threshold, 0.0)

        cost = dt * (
            cf.import_coeff * imp
            - cf.export_coeff * exp
            + cf.battery_coeff * (ch + dis)
            + cf.peak_coeff * excess ** 2
        )

        # Battery power limit, and charging from PV only
        feasible = (ch <= battery.max_power + EPS) & (dis <= battery.max_power + EPS) & (ch <= pv + EPS)

        return np.where(feasible, cost, np.inf), ch - dis

    def _build_graph(self, order, steps, n_steps, committed):
        # Task side of the state: (tasks started, load committed for the next steps).
        # Tasks are started in a fixed order (latest feasible start first); a decision is how many to start.
        # Returns, per step, each state's choices as (tasks started now, load now, next state).
        release = [steps[task["id"]]["release"] for task in order]
        latest = [steps[task["id"]]["latest"] for task in order]
        duration = [steps[task["id"]]["duration"] for task in order]
        n_tasks = len(order)
        tail_length = max(1, max(duration) - 1, len(np.trim_zeros(committed, "b")))

        start = (0, tuple(np.pad(committed, (0, tail_length))[:tail_length]))
        layer = [start]
        graph = []

        for t in range(n_steps):
            choices = {}
            next_layer = set()

            for k, tail in layer:

                # Tasks that cannot wait any longer must start now
                n_min = 0
                while k + n_min < n_tasks and latest[k + n_min] <= t:
                    n_min += 1

                n_max = 0
                while k + n_max < n_tasks and release[k + n_max] <= t:
                    n_max += 1

                added = np.zeros(tail_length + 1)
                options = []
                for n in range(n_max + 1):
                    if n > 0:
                        added[:duration[k + n - 1]] += order[k + n - 1]["power"]

                    if n < n_min:
                        continue

                    new_tail = tuple(
                        (tail[i + 1] if i + 1 < tail_length else 0.0) + added[i + 1]
                        for i in range(tail_length)
                    )
                    options.append((n, tail[0] + added[0], (k + n, new_tail)))
                    next_layer.add((k + n, new_tail))

                choices[(k, tail)] = options

            graph.append(choices)
            layer = next_layer

        return start, graph, layer

    def _backward(self, graph, final_layer, n_tasks, levels, battery, scenarios, dt):
        # Expected cost-to-go of every state and energy level, averaged over the PV scenarios.
        # The decision at each step is taken knowing that step's PV (measured), not the following ones.
        n_steps = len(graph)

        values = [None] * (n_steps + 1)
        values[n_steps] = {
            key: np.zeros(len(levels)) if key[0] == n_tasks else np.full(len(levels), np.inf)
            for key in final_layer
        }

        for t in reversed(range(n_steps)):
            cache = {}
            values[t] = {}

            for key, options in graph[t].items():
                best = np.full((len(scenarios), len(levels)), np.inf)

                for _, load, next_key in options:
                    if load not in cache:
                        cache[load] = self._transition_costs(levels, battery, scenarios[:, t], load, dt)[0]

                    q = (cache[load] + values[t + 1][next_key][None, None, :]).min(axis=2)
                    best = np.minimum(best, q)

                values[t][key] = best.mean(axis=0)

        return values

    def _execute(self, start, graph, values, order, levels, battery, pv, start_level, dt):
        # Follows the cost-to-go: at each step, the action minimising the cost now plus the cost-to-go,
        # for the PV seen at that step and the battery level actually reached.
        starts = {}
        battery_plan = np.zeros(len(graph))
        key, level = start, start_level

        for t, choices in enumerate(graph):
            best = (np.inf, None, None, None, None)

            for n, load, next_key in choices[key]:
                cost, setpoint = self._transition_costs(levels, battery, pv[t], load, dt)
                row = cost[level] + values[t + 1][next_key]
                j = int(np.argmin(row))

                if row[j] < best[0]:
                    best = (row[j], n, next_key, j, setpoint[level, j])

            _, n, next_key, j, battery_plan[t] = best

            for i in range(key[0], key[0] + n):
                starts[order[i]["id"]] = t

            key, level = next_key, j

        return starts, battery_plan

    def solve(self, forecast, tasks, battery, deltaT, actual=None, committed=None):
        # Returns a schedule {task id: start step} and the battery power [kW, + charge] that was applied.
        # Open loop: the plan is computed on the forecast and followed whatever happens.
        # Closed loop: the cost-to-go is used as a policy on the actual PV, read one step at a time.
        # The profiles may cover only the rest of the day; committed: load [kW] of tasks already running.
        n_steps = len(forecast)
        committed = np.zeros(n_steps) if committed is None else np.asarray(committed, dtype=float)

        steps = {task["id"]: task_steps(task, deltaT, n_steps) for task in tasks}
        order = sorted(tasks, key=lambda task: (steps[task["id"]]["latest"], steps[task["id"]]["release"], task["id"]))

        levels = np.arange(battery.min_energy, battery.max_energy + EPS, self.energy_step)
        start_level = int(np.argmin(np.abs(levels - battery.energy)))

        # Scenarios cover the whole day: keep the part matching the remaining steps
        scenarios = np.atleast_2d(forecast) if self.scenarios is None else self.scenarios[:, -n_steps:]

        start, graph, final_layer = self._build_graph(order, steps, n_steps, committed)
        values = self._backward(graph, final_layer, len(order), levels, battery, scenarios, deltaT)

        self.state_count = sum(len(choices) for choices in graph)
        self.expected_cost = values[0][start][start_level]

        pv = actual if self.closed_loop and actual is not None else forecast
        starts, battery_plan = self._execute(start, graph, values, order, levels, battery, pv, start_level, deltaT)

        return {"starts": starts, "battery": battery_plan}
