import copy

import numpy as np

from cost import CostFunction
from forecast import PVPredictor
from simulation import dispatch_setpoint, task_steps

EPS = 1e-9


class PredictiveEMS:

    def __init__(
        self,
        cost_function : CostFunction,
        predictor : PVPredictor,
        horizon: int = 12,                  # [steps] lookahead, 3 h at 15 min
        predict_arrivals: bool = True,      # Expect as much task energy to arrive as in the last window
        tasks_known_ahead: bool = False,    # True: tasks are known before they arrive (within the lookahead)
        passes: int = 3,                    # Improvement passes re-placing each task given all the others
        name: str | None = None
    ):
        self.passes = passes
        self.cost_func = cost_function
        self.predictor = predictor
        self.horizon = horizon
        self.predict_arrivals = predict_arrivals and not tasks_known_ahead
        self.tasks_known_ahead = tasks_known_ahead
        self.name = name or f"Pred ({predictor.method})"

    def _battery_setpoint(self, battery, load, pv, reserve, dt):
        # Rules: charge any PV surplus; discharge first to keep the import under the peak threshold;
        # discharge beyond that only with the energy above the reserve. Returns [kW], + charge.
        net = load - pv
        if net <= 0:
            return -net

        shave = max(0.0, net - self.cost_func.peak_threshold)
        spare = max(0.0, battery.energy - battery.min_energy - reserve) * battery.efficiency / dt

        return -(shave + min(net - shave, spare))

    def _reserve(self, battery, load, pv, dt):
        # Stored energy kept for the predicted import above the peak threshold [kWh]
        excess = np.maximum(load - pv - self.cost_func.peak_threshold, 0.0)
        return min(excess.sum() * dt / battery.efficiency, battery.max_energy - battery.min_energy)

    def _horizon_cost(self, battery, load, pv, reserve, dt):
        # Predicted cost over the lookahead, with the battery simulated from its measured state
        cf = self.cost_func
        battery = copy.copy(battery)
        cost = 0.0

        for h in range(len(load)):
            setpoint = self._battery_setpoint(battery, load[h], pv[h], reserve, dt)
            flows = dispatch_setpoint(battery, pv[h] - load[h], setpoint, dt, True)
            cost += cf.energy_cost(flows["battery_kwh"], flows["import_kwh"], flows["export_kwh"])
            cost += cf.peak_cost(flows["import_kwh"], dt)

        # Energy left in the battery will avoid imports later
        stored_value = cf.import_coeff * battery.efficiency - cf.battery_coeff
        return cost - stored_value * battery.energy

    def solve(self, forecast, tasks, battery, deltaT, actual=None):
        # Online: at step t, only the PV measured up to t and the tasks arrived by t are known.
        # Returns a schedule {task id: start step} and the battery power [kW, + charge] applied.
        power = forecast if actual is None else actual
        n_steps = len(power)
        H = self.horizon
        window = self.predictor.window
        battery = copy.deepcopy(battery)

        steps = {task["id"]: task_steps(task, deltaT, n_steps) for task in tasks}
        pending = sorted(tasks, key=lambda task: (steps[task["id"]]["latest"], task["id"]))
        running = []        # [power, remaining steps]
        starts = {}
        battery_plan = np.zeros(n_steps)

        for t in range(n_steps):

            running = [task for task in running if task[1] > 0]

            # Measured PV now, predicted PV for the rest of the lookahead
            pv = np.concatenate(([power[t]], self.predictor.predict(power[:t + 1], H - 1)))

            committed = np.zeros(H)
            for p, remaining in running:
                committed[:remaining] += p

            # Task energy arriving later, estimated from the arrivals of the last window.
            # Spread as a steady background load over the whole lookahead, now included, so that
            # it does not favour any slot: it only stops the later, still empty, steps from looking free.
            expected = np.zeros(H)
            if self.predict_arrivals:
                arrived = sum(
                    task["power"] * task["duration"] for task in tasks
                    if t - window < steps[task["id"]]["release"] <= t
                )
                expected[:] = arrived / (window * deltaT)

            visible = t + H if self.tasks_known_ahead else t
            known = [task for task in pending if steps[task["id"]]["release"] <= visible]
            reserve = self._reserve(battery, committed + expected, pv, deltaT)

            # Plan of the known tasks over the lookahead: placed by urgency (latest start first), each in its
            # cheapest predicted slot, then re-placed given all the others until no task moves.
            # Only the tasks planned for now are started; the others are planned again at the next step.
            tentative = committed.copy()
            slots = {}

            for _ in range(1 + self.passes):
                moved = False

                for task in known:
                    s = steps[task["id"]]
                    first = max(t, s["release"])
                    last = max(first, min(s["latest"], t + H - s["duration"]))

                    if task["id"] in slots:
                        previous = slots[task["id"]]
                        tentative[previous - t:previous - t + s["duration"]] -= task["power"]

                    best_slot, best_cost = first, np.inf
                    for slot in range(first, last + 1):
                        load = tentative.copy()
                        load[slot - t:slot - t + s["duration"]] += task["power"]
                        cost = self._horizon_cost(battery, load + expected, pv, reserve, deltaT)

                        if cost < best_cost - EPS:
                            best_slot, best_cost = slot, cost

                    tentative[best_slot - t:best_slot - t + s["duration"]] += task["power"]
                    moved = moved or slots.get(task["id"]) != best_slot
                    slots[task["id"]] = best_slot

                if not moved:
                    break

            for task in known:
                if slots[task["id"]] == t:
                    s = steps[task["id"]]
                    starts[task["id"]] = t
                    running.append([task["power"], s["duration"]])
                    pending.remove(task)

            # Apply the battery rules on the actual step
            load = sum(p for p, _ in running)
            battery_plan[t] = self._battery_setpoint(battery, load, power[t], reserve, deltaT)
            dispatch_setpoint(battery, power[t] - load, battery_plan[t], deltaT, True)

            for task in running:
                task[1] -= 1

        return {"starts": starts, "battery": battery_plan}
