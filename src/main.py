
import matplotlib.pyplot as plt
import numpy as np
import copy
import time

from pv_system import PVSystem
from factory import Factory
from battery import Battery

from methods.greedy import GreedyEMS
from methods.milp import MilpEMS
from methods.dynamic import DynamicProgrammingEMS
from methods.predictive import PredictiveEMS
from methods.replanning import ReplanningEMS

from forecast import PVPredictor

from cost import CostFunction
from simulation import evaluate_schedule


def run(strategies, forecast, actual, tasks, battery, time_step, cost_function):
    # Each strategy plans on the forecast; online strategies may also read the actual PV one step at a time.
    # Every result is scored on the actual PV.
    performances = {}

    for strategy in strategies:
        start = time.perf_counter()
        plan = strategy.solve(forecast.copy(), copy.deepcopy(tasks), copy.deepcopy(battery), time_step, actual.copy())
        elapsed = time.perf_counter() - start

        result = evaluate_schedule(actual, tasks, battery, time_step, plan["starts"], cost_function, plan["battery"])
        result["schedule"] = plan["starts"]
        result["solve_time"] = elapsed
        performances[strategy.name] = result

    return performances


def report(title, performances, n_tasks):
    print(f"\n=== {title} ===")
    print(f"{'Method':<26}{'Total $':>9}{'Grid $':>9}{'Batt $':>9}{'Peak $':>9}"
          f"{'Peak kW':>9}{'Done':>7}{'Late h':>8}{'Time s':>9}")

    for name, result in performances.items():
        costs = result["costs"]
        print(f"{name:<26}{result['total_cost']:>9.2f}{costs['grid_cost']:>9.2f}{costs['battery_cost']:>9.2f}"
              f"{costs['peak_cost']:>9.2f}{result['peak_kw']:>9.2f}{result['completed']:>4}/{n_tasks:<2}"
              f"{result['late_hours']:>8.2f}{result['solve_time']:>9.3f}")


def main():

    time_step = 0.25  # [hours]
    day = 172

    pv = PVSystem(
        max_power=20,       # [kiloWatts]
        efficiency=0.21,
        latitude=45.5       #Latitude of Montreal [deg]
    )

    # Actual PV [kW] of the simulated day, cloudy
    actual = np.array(pv.gen_daily_power(time_step=time_step, day=day, is_cloudy=True, seed=42))

    # Possible days known in advance (same cloud model, other seeds), and their average as the forecast
    scenarios = np.array([
        pv.gen_daily_power(time_step=time_step, day=day, is_cloudy=True, seed=seed)
        for seed in range(100, 120)
    ])
    forecast = scenarios.mean(axis=0)

    # Clear-sky PV [kW], from the sun's geometry only, used by the predictors as an upper bound
    clear_sky = np.array(pv.gen_daily_power(time_step=time_step, day=day, is_cloudy=False))

    factory = Factory(job_type_amount=3)

    tasks = factory.gen_daily_tasks(
            task_amount=50,
            seed=42
        )

    battery = Battery(
        capacity = 10,                 #[kWh]
        voltage = 48,                  #[Volts]
        max_current = 100,             #[Amps]
        cur_charge = 0.5,              #Initial state of charge
        efficiency = 0.95,
        max_charge = 0.9,              #Max SoC
        max_discharge = 0.2,           #Min SoC
        lifetime_throughput = 30000,   #[kWh]
        replacement_cost = 3000.00     #[$], leading to a 0.10 $/kWh decay cost with 3000$/30MWh
    )

    # Time axis in hours
    times = np.arange(len(actual)) * time_step

    cost_function = CostFunction(
        battery_coeff=battery.degradation_cost_per_kwh,     # [$/kWh]
        export_coeff=0.05,                                  # [$/kWh]
        import_coeff=0.30,                                  # [$/kWh]
        peak_coeff=0.50,                                    # [$/(kW^2 h)] on squared import above peak_threshold
        peak_threshold=3.0,                                 # [kW]
        task_delay_coeff=200.0                              # [$/h] per late task
        )

    def planners():
        # Day planners: they optimise over a task list
        return [
            MilpEMS(cost_function, time_limit=10),
            DynamicProgrammingEMS(cost_function, name="DP plan"),
            DynamicProgrammingEMS(cost_function, closed_loop=True, name="DP policy"),
            DynamicProgrammingEMS(cost_function, scenarios=scenarios, closed_loop=True, name="SDP policy")
        ]

    predictor = PVPredictor("smart_persistence", window=4, clear_sky=clear_sky)

    # Tasks locked the day before (e.g. submission deadline): the planners see the full day's list
    day_ahead = planners() + [
        PredictiveEMS(cost_function, predictor, tasks_known_ahead=True, name="Pred (smart)"),
        GreedyEMS(cost_function)
    ]

    # Tasks revealed on arrival: planners re-plan the rest of the day whenever tasks arrive
    on_arrival = [ReplanningEMS(planner, name=planner.name) for planner in planners()] + [
        PredictiveEMS(cost_function, predictor, name="Pred (smart)"),
        GreedyEMS(cost_function)
    ]

    # Reference: everything known, PV included
    reference = run([DynamicProgrammingEMS(cost_function, name="DP")], actual, actual, tasks, battery, time_step, cost_function)
    report("Perfect knowledge (lower bound)", reference, len(tasks))

    # PV planned on the average of the scenarios, measured on the actual cloudy day
    known = run(day_ahead, forecast, actual, tasks, battery, time_step, cost_function)
    report("Tasks known day-ahead", known, len(tasks))

    performances = run(on_arrival, forecast, actual, tasks, battery, time_step, cost_function)
    report("Tasks revealed on arrival", performances, len(tasks))

    print(f"\n{'Cost of not knowing the day':<28}" + "".join(f"{name:>14}" for name in performances))
    print(f"{'':<28}" + "".join(
        f"{performances[name]['total_cost'] - known[name]['total_cost']:>+14.2f}" for name in performances
    ))

    plotted = ["Greedy", "MILP", "SDP policy", "Pred (smart)"]
    performances = {name: performances[name] for name in plotted}

    fig, axes = plt.subplots(
        3, 1,
        figsize=(12, 10),
        sharex=True
    )

    # 1. PV power and scheduled load
    axes[0].plot(times, actual, color="black", label="PV actual")
    axes[0].plot(times, forecast, color="black", linestyle=":", label="PV forecast")
    for name, result in performances.items():
        axes[0].step(times, result["load"], where="post", label=f"Load ({name})")
    axes[0].set_title("PV production and factory load (tasks revealed on arrival)")
    axes[0].set_ylabel("Power (kW)")
    axes[0].legend()
    axes[0].grid(True)

    # 2. Grid exchange and battery SoC
    for name, result in performances.items():
        axes[1].step(times, result["grid"], where="post", label=f"Grid import ({name})")
    axes[1].set_ylabel("Power (kW)")
    axes[1].set_title("Grid exchange (+ import / - export) and battery SoC")
    axes[1].grid(True)
    soc_axis = axes[1].twinx()
    for name, result in performances.items():
        soc_axis.plot(times, result["soc"], linestyle="--", label=f"SoC ({name})")
    soc_axis.set_ylabel("SoC")
    soc_axis.set_ylim(0, 1)
    axes[1].legend(loc="upper left")
    soc_axis.legend(loc="upper right")

    # 3. Task schedule of the cheapest method: window [arrival, deadline] and scheduled execution
    best_name = min(performances, key=lambda name: performances[name]["total_cost"])
    schedule = performances[best_name]["schedule"]
    for task in tasks:
        axes[2].barh(
            task["id"],
            task["deadline"] - task["arrival"],
            left=task["arrival"],
            height=0.7,
            color="lightgray"
        )

        if task["id"] in schedule:
            axes[2].barh(
                task["id"],
                task["duration"],
                left=schedule[task["id"]] * time_step,
                height=0.5,
                color=f"C{task['type']}"
            )

    axes[2].set_title(f"Task windows (gray) and {best_name} schedule (colored by type)")
    axes[2].set_xlabel("Time of day (hours)")
    axes[2].set_ylabel("Task ID")
    axes[2].set_xlim(0, 24)
    axes[2].set_xticks(range(0, 25, 2))
    axes[2].grid(True, axis="x")

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
