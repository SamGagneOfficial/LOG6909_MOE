import copy

from cost import CostFunction
from simulation import dispatch, task_steps

EPS = 1e-9


class GreedyEMS:
    name = "Greedy"

    def __init__(self, cost_function : CostFunction):
        self.cost_func = cost_function

    def _step_cost(self, battery, net_power, dt):
        # Cost of the current step only (myopic), including import above the peak threshold
        flows = dispatch(battery, net_power, dt)

        return (
            self.cost_func.energy_cost(flows["battery_kwh"], flows["import_kwh"], flows["export_kwh"])
            + self.cost_func.peak_cost(flows["import_kwh"], dt)
        )

    def solve(self, forecast, tasks, battery, deltaT, actual=None):
        # Returns a schedule {task id: start step}, scored later by simulation.evaluate_schedule.
        # No battery plan: the battery follows the rule-based dispatch, as simulated here.
        # Online and myopic: at step i, only the measured PV power[i] is used, so it reads the actual profile.
        power = forecast if actual is None else actual
        n_steps = len(power)
        battery = copy.deepcopy(battery)

        steps = {task["id"]: task_steps(task, deltaT, n_steps) for task in tasks}
        pending = sorted(tasks, key=lambda task: steps[task["id"]]["latest"])
        running = {}        # task id -> [power, remaining steps]
        starts = {}

        for i in range(n_steps):

            running = {k: v for k, v in running.items() if v[1] > 0}
            load = sum(p for p, _ in running.values())

            released = [task for task in pending if steps[task["id"]]["release"] <= i]

            # Tasks that cannot wait any longer without missing their deadline
            for task in [task for task in released if steps[task["id"]]["latest"] <= i]:
                starts[task["id"]] = i
                running[task["id"]] = [task["power"], steps[task["id"]]["duration"]]
                load += task["power"]
                pending.remove(task)
                released.remove(task)

            # Optional tasks: start the cheapest while it beats importing the energy later
            while released:
                base = self._step_cost(battery, power[i] - load, deltaT)

                best_task = None
                best_rate = self.cost_func.import_coeff + EPS

                for task in released:
                    marginal = self._step_cost(battery, power[i] - load - task["power"], deltaT) - base
                    rate = marginal / (task["power"] * deltaT)

                    if rate <= best_rate:
                        best_task = task
                        best_rate = rate

                if best_task is None:
                    break

                starts[best_task["id"]] = i
                running[best_task["id"]] = [best_task["power"], steps[best_task["id"]]["duration"]]
                load += best_task["power"]
                pending.remove(best_task)
                released.remove(best_task)

            # The battery is applied once per step
            dispatch(battery, power[i] - load, deltaT, True)

            for task in running.values():
                task[1] -= 1

        return {"starts": starts, "battery": None}
