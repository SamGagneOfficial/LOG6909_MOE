import copy
import math

import numpy as np

from battery import Battery
from cost import CostFunction

EPS = 1e-9


def task_steps(task, dt, n_steps):
    # Converts a task's hour-based fields into step indices
    release = math.ceil(task["arrival"] / dt - EPS)
    duration = max(1, math.ceil(task["duration"] / dt - EPS))
    deadline = math.floor(task["deadline"] / dt + EPS)

    # Latest start meeting the deadline, and the end of the horizon
    latest = min(deadline - duration, n_steps - duration)

    return {
        "release": release,
        "duration": duration,
        "latest": max(latest, release)
    }


def dispatch(battery : Battery, net_power, dt, toApply : bool = False):
    # net_power > 0: PV surplus [kW], net_power < 0: deficit [kW]
    if net_power >= 0:
        throughput, grid = battery.charge(net_power, dt, toApply)
    else:
        throughput, grid = battery.discharge(-net_power, dt, toApply)

    return {
        "battery_kwh": throughput,
        "import_kwh": max(0.0, -grid),
        "export_kwh": max(0.0, grid)
    }


def dispatch_setpoint(battery : Battery, net_power, setpoint, dt, toApply : bool = False):
    # Follows a planned battery power [kW] (+ charge / - discharge), within the battery's limits.
    # The grid covers whatever remains.
    if setpoint >= 0:
        throughput, _ = battery.charge(setpoint, dt, toApply)
        battery_kw = throughput / dt
    else:
        throughput, _ = battery.discharge(-setpoint, dt, toApply)
        battery_kw = -throughput / dt

    grid_kw = battery_kw - net_power

    return {
        "battery_kwh": throughput,
        "import_kwh": max(0.0, grid_kw) * dt,
        "export_kwh": max(0.0, -grid_kw) * dt
    }


def load_profile(tasks, starts, dt, n_steps):
    load = np.zeros(n_steps)

    for task in tasks:
        if task["id"] not in starts:
            continue

        start = starts[task["id"]]
        steps = task_steps(task, dt, n_steps)
        load[start:min(start + steps["duration"], n_steps)] += task["power"]

    return load


def evaluate_schedule(power, tasks, battery : Battery, dt, starts, cost_function : CostFunction, battery_plan=None):
    # Common evaluator: every strategy is scored by the same simulation.
    # Without a battery_plan [kW per step], the battery follows the rule-based dispatch.
    n_steps = len(power)
    battery = copy.deepcopy(battery)

    load = load_profile(tasks, starts, dt, n_steps)

    battery_kwh = import_kwh = export_kwh = excess_kwh = squared_excess = 0.0
    grid_kw = np.zeros(n_steps)
    soc = np.zeros(n_steps)

    for i in range(n_steps):
        if battery_plan is None:
            flows = dispatch(battery, power[i] - load[i], dt, True)
        else:
            flows = dispatch_setpoint(battery, power[i] - load[i], battery_plan[i], dt, True)

        battery_kwh += flows["battery_kwh"]
        import_kwh += flows["import_kwh"]
        export_kwh += flows["export_kwh"]
        excess = cost_function.excess_power(flows["import_kwh"], dt)
        excess_kwh += excess * dt
        squared_excess += excess ** 2 * dt

        grid_kw[i] = (flows["import_kwh"] - flows["export_kwh"]) / dt
        soc[i] = battery.soc

    late_hours = 0.0
    unfinished = 0
    violations = 0

    for task in tasks:
        steps = task_steps(task, dt, n_steps)

        if task["id"] not in starts:
            # Never started: as late as if it ran right after the end of the day
            unfinished += 1
            late_hours += n_steps * dt + task["duration"] - task["deadline"]
            continue

        start = starts[task["id"]]

        if start < steps["release"]:
            violations += 1

        end = start + steps["duration"]

        if end > n_steps:
            unfinished += 1

        late_hours += max(0.0, end * dt - task["deadline"])

    peak_kw = max(0.0, grid_kw.max())

    costs = cost_function.evaluate(
        battery_throughput_kwh=battery_kwh,
        import_kwh=import_kwh,
        export_kwh=export_kwh,
        squared_excess=squared_excess,
        late_hours=late_hours
    )

    pv_kwh = power.sum() * dt

    return {
        "costs": costs,
        "total_cost": costs["total_cost"],
        "import_kwh": import_kwh,
        "export_kwh": export_kwh,
        "battery_throughput_kwh": battery_kwh,
        "battery_age": battery.age,
        "peak_kw": peak_kw,
        "excess_kwh": excess_kwh,
        "pv_self_consumption": 1 - export_kwh / pv_kwh if pv_kwh > 0 else 0.0,
        "completed": len(tasks) - unfinished,
        "unfinished": unfinished,
        "late_hours": late_hours,
        "violations": violations,
        "load": load,
        "grid": grid_kw,
        "soc": soc
    }
