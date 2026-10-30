"""
Phase 3: compares the EMS methods on computing time, solution quality and robustness.

Three studies, from one set of runs in a process pool:
- Factors: one factor varies at a time around a baseline day (arrival skew, cloudiness, number of
  tasks, battery capacity; ten levels each, plus bimodal arrivals), each configuration repeated over
  several days (other PV and task seeds). Quality is the regret: cost above the best schedule known for that day.
- Scaling: computing time against the number of tasks (the tasks factor), fitted as time ~ n^k on log-log axes.
- Power: grid import over the baseline day, for a few methods.
A separate study (--study costs) varies the cost coefficients instead: peak penalty, grid prices, peak threshold.
Every method runs under both task-information regimes: tasks known day-ahead, or revealed on arrival.

Usage: python src/experiments.py [--study factors|costs] [--days 3] [--workers 10] [--plot-only]
Results go to results/: CSV files, a summary, and one figure per factor (two panels, one per regime).
"""
import argparse
import copy
import csv
import os
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np

from pv_system import PVSystem
from factory import Factory
from battery import Battery
from cost import CostFunction
from forecast import PVPredictor
from simulation import evaluate_schedule

from methods.greedy import GreedyEMS
from methods.milp import MilpEMS
from methods.dynamic import DynamicProgrammingEMS
from methods.predictive import PredictiveEMS
from methods.replanning import ReplanningEMS

TIME_STEP = 0.25
DAY = 172
RESULTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")

BASELINE = {"skew": 0.0, "profile": "uniform", "cloud": 0.4, "tasks": 50, "capacity": 10,
            "peak_coeff": 0.5, "threshold": 3.0, "prices": "default"}

# Skew: signed rate [1/h] of the exponential arrival profile, > 0 early, < 0 late, 0 uniform
FACTORS = {
    "skew": [k / 10 for k in range(-5, 6)],
    "cloud": [k / 10 for k in range(10)],
    "tasks": list(range(10, 101, 10)),
    "capacity": list(range(2, 21, 2)),
    "profile": ["uniform", "bimodal"],
}
PLOTTED = ["skew", "cloud", "tasks", "capacity"]   # Bimodal arrivals have no level axis: summary table only

# Grid prices [$/kWh] (import, export). Storing 1 kWh of PV surplus then saves about
# 0.9 import - export - 0.19 (wear on charge and discharge): about -0.16 $, +0.03 $ and +0.20 $
PRICES = {"cheap grid": (0.15, 0.10), "default": (0.30, 0.05), "expensive grid": (0.45, 0.02)}

COST_FACTORS = {
    "peak_coeff": [0.5, 1.0, 1.5],
    "prices": list(PRICES),
    "threshold": [3.0, 4.0, 5.0],
}

# Cost study: the quantity each coefficient should act on
COST_METRICS = {
    "peak_coeff": ("peak_kw", "Mean daily peak import (kW)"),
    "prices": ("battery_throughput_kwh", "Battery throughput (kWh/day)"),
    "threshold": ("peak_kw", "Mean daily peak import (kW)"),
}

FACTOR_LABELS = {
    "peak_coeff": "Peak penalty ($/kW²h)",
    "prices": "Grid prices (import / export)",
    "threshold": "Peak threshold (kW)",
    "skew": "Arrival skew (1/h): late < 0 < early",
    "profile": "Task arrival profile",
    "cloud": "Average cloudiness",
    "tasks": "Number of tasks",
    "capacity": "Battery capacity (kWh)",
}

SCENARIOS = 10                     # PV scenarios for the SDP (and their average as forecast); 20 doubled its time
SIZES = FACTORS["tasks"]           # Numbers of tasks of the scaling study

POWER_METHODS = ["Greedy", "MILP", "DP policy", "Pred (smart)"]

METHODS = ["MILP", "DP plan", "DP policy", "SDP policy", "Pred (smart)", "Greedy"]
REGIMES = ["day-ahead", "on arrival"]
REGIME_TITLES = {"day-ahead": "Tasks known day-ahead", "on arrival": "Tasks revealed on arrival"}

# Figures: the four main methods, labelled in French (the summaries stay in English)
PLOT_METHODS = ["MILP", "DP policy", "Pred (smart)", "Greedy"]
NAMES_FR = {"MILP": "MILP", "DP policy": "Programmation dynamique", "Pred (smart)": "Prédictive", "Greedy": "Glouton"}
REGIMES_FR = {"day-ahead": "Tâches connues la veille", "on arrival": "Tâches révélées à leur arrivée"}
LABELS_FR = {
    "skew": "Asymétrie des arrivées (1/h) : tardives < 0 < hâtives",
    "cloud": "Nébulosité moyenne",
    "tasks": "Nombre de tâches",
    "capacity": "Capacité de la batterie (kWh)",
    "peak_coeff": "Pénalité de pointe ($/kW²h)",
    "prices": "Prix du réseau ($/kWh, achat / vente)",
    "threshold": "Seuil de pointe (kW)",
}
PRICES_FR = {"cheap grid": "réseau bon marché", "default": "par défaut", "expensive grid": "réseau cher"}
METRICS_FR = {
    "peak_kw": "Pointe d'import quotidienne moyenne (kW)",
    "battery_throughput_kwh": "Énergie transitée par la batterie (kWh/jour)",
}


def fr(value):
    # Number with a decimal comma
    return f"{value:g}".replace(".", ",")

# Categorical slots of the reference palette, in fixed order, one per method
COLORS = {
    "MILP": "#2a78d6",
    "DP plan": "#1baf7a",
    "DP policy": "#eb6834",            # Shown in the figures: kept apart from the Greedy green
    "SDP policy": "#eda100",
    "Pred (smart)": "#e87ba4",
    "Greedy": "#008300",
}

INK = "#444444"
MUTED = "#555555"
GRID = "#e5e5e5"
AXIS = "#bbbbbb"


# ---------------------------------------------------------------- Simulation

def configurations(factors):
    # Baseline, then each factor's other levels, the rest kept at the baseline
    configs = [("baseline", "-", dict(BASELINE))]
    for factor, levels in factors.items():
        for level in levels:
            if level != BASELINE[factor]:
                configs.append((factor, level, dict(BASELINE, **{factor: level})))
    return configs


def setup(config, day):
    # The day's PV (actual, scenarios and their average as forecast), tasks, battery and costs
    pv = PVSystem(max_power=20, efficiency=0.21, latitude=45.5)
    actual = pv.gen_daily_power(TIME_STEP, DAY, True, seed=200 + day, cloud_average=config["cloud"])
    scenarios = np.array([
        pv.gen_daily_power(TIME_STEP, DAY, True, seed=seed, cloud_average=config["cloud"])
        for seed in range(100, 100 + SCENARIOS)
    ])
    clear_sky = pv.gen_daily_power(TIME_STEP, DAY, False)

    skew = config["skew"]
    profile = config["profile"] if skew == 0 else ("early" if skew > 0 else "late")
    tasks = Factory(job_type_amount=3).gen_daily_tasks(
        task_amount=config["tasks"], seed=42 + day, arrival_profile=profile, time_step=TIME_STEP,
        decay=abs(skew) or 0.3
    )

    battery = Battery(
        capacity=config["capacity"], voltage=48, max_current=100, cur_charge=0.5, efficiency=0.95,
        max_charge=0.9, max_discharge=0.2, lifetime_throughput=30000, replacement_cost=3000.00
    )

    import_coeff, export_coeff = PRICES[config["prices"]]
    cost_function = CostFunction(
        battery_coeff=battery.degradation_cost_per_kwh, export_coeff=export_coeff, import_coeff=import_coeff,
        peak_coeff=config["peak_coeff"], peak_threshold=config["threshold"], task_delay_coeff=200.0
    )

    return actual, scenarios, scenarios.mean(axis=0), clear_sky, tasks, battery, cost_function


def build_methods(cost_function, scenarios, clear_sky):
    def planners():
        return [
            MilpEMS(cost_function, time_limit=10, mip_gap=0.01),
            DynamicProgrammingEMS(cost_function, name="DP plan"),
            DynamicProgrammingEMS(cost_function, closed_loop=True, name="DP policy"),
            DynamicProgrammingEMS(cost_function, scenarios=scenarios, closed_loop=True, name="SDP policy"),
        ]

    def predictor():
        return PVPredictor("smart_persistence", window=4, clear_sky=clear_sky)

    return {
        "day-ahead": planners() + [
            PredictiveEMS(cost_function, predictor(), tasks_known_ahead=True, name="Pred (smart)"),
            GreedyEMS(cost_function),
        ],
        # Re-planned at every arrival: waiting between re-plans cost about 8 $/day at a 1 h interval.
        # No expected arrivals: tested, the predictive EMS's estimate did not help the planners
        # (MILP +1 to +12 $/day; it mostly makes them discharge early for load that never comes)
        "on arrival": [ReplanningEMS(planner, interval=1, name=planner.name) for planner in planners()] + [
            PredictiveEMS(cost_function, predictor(), name="Pred (smart)"),
            GreedyEMS(cost_function),
        ],
    }


def run_methods(config, day):
    # Every method under both regimes on one day; yields (regime, method name, result, time, limit hits)
    actual, scenarios, forecast, clear_sky, tasks, battery, cost_function = setup(config, day)

    for regime, methods in build_methods(cost_function, scenarios, clear_sky).items():
        for method in methods:
            solver = getattr(method, "planner", method)
            hits = getattr(solver, "limit_hits", 0)

            start = time.perf_counter()
            plan = method.solve(forecast.copy(), copy.deepcopy(tasks), copy.deepcopy(battery), TIME_STEP, actual.copy())
            elapsed = time.perf_counter() - start

            result = evaluate_schedule(actual, tasks, battery, TIME_STEP, plan["starts"], cost_function, plan["battery"])
            yield regime, method.name, result, elapsed, getattr(solver, "limit_hits", 0) - hits


def factor_job(factor, level, config, day):
    actual, _, _, _, tasks, battery, cost_function = setup(config, day)
    reference = DynamicProgrammingEMS(cost_function).solve(actual, copy.deepcopy(tasks), battery, TIME_STEP, actual)
    floor = evaluate_schedule(actual, tasks, battery, TIME_STEP, reference["starts"], cost_function, reference["battery"])

    rows = []
    profiles = {"pv": actual} if factor == "baseline" and day == 0 else None

    for regime, name, result, elapsed, hits in run_methods(config, day):
        rows.append({
            "factor": factor,
            "level": level,
            **config,
            "day": day,
            "regime": regime,
            "method": name,
            "total_cost": result["total_cost"],
            **{key: value for key, value in result["costs"].items() if key != "total_cost"},
            "peak_kw": result["peak_kw"],
            "excess_kwh": result["excess_kwh"],
            "pv_self_consumption": result["pv_self_consumption"],
            "battery_throughput_kwh": result["battery_throughput_kwh"],
            "late_hours": result["late_hours"],
            "unfinished": result["unfinished"],
            "violations": result["violations"],
            "solve_time": elapsed,
            "limit_hits": hits,
            "perfect_cost": floor["total_cost"],
        })
        if profiles is not None and name in POWER_METHODS:
            profiles[f"{regime}|{name}"] = result["grid"]

    return "factor", rows, profiles


def run_job(job):
    return factor_job(*job)


# ---------------------------------------------------------------- Analysis

def rebase(rows):
    # The perfect-knowledge DP keeps a fixed task order, so another method can beat it (the MILP does,
    # when many tasks arrive together). Regret is therefore taken above the best schedule found that day,
    # by any method or by the reference: every schedule is valid, so this is the tightest known bound.
    best = {}
    for r in rows:
        key = (r["factor"], r["level"], r["day"])
        best[key] = min(best.get(key, r["perfect_cost"]), r["total_cost"])
    for r in rows:
        r["best_cost"] = best[(r["factor"], r["level"], r["day"])]
        r["regret"] = r["total_cost"] - r["best_cost"]
    return rows


def level_runs(rows, factor, level, regime, method):
    # Runs at one level of a factor: that factor's configurations, plus the baseline at its level
    return [r for r in rows if r[factor] == level and r["regime"] == regime and r["method"] == method
            and r["factor"] in (factor, "baseline")]


def scaling_rows(rows):
    # The tasks factor and the baseline: every size, all else at the baseline
    return [r for r in rows if r["factor"] in ("tasks", "baseline")]


def scaling_points(rows, regime, method):
    # Mean time per size, and whether any run at that size hit the MILP time limit (censored)
    sizes, times, censored = [], [], []
    for n in sorted({r["tasks"] for r in rows}):
        runs = [r for r in rows if r["tasks"] == n and r["regime"] == regime and r["method"] == method]
        if runs:
            sizes.append(n)
            times.append(np.mean([r["solve_time"] for r in runs]))
            censored.append(any(r["limit_hits"] > 0 for r in runs))
    return np.array(sizes), np.array(times), np.array(censored)


def fit_order(sizes, times, censored):
    # Least squares on log t = k log n + c, over the uncensored points: time ~ n^k
    keep = ~censored & (times > 0)
    if keep.sum() < 3:
        return None
    x, y = np.log(sizes[keep]), np.log(times[keep])
    k, c = np.polyfit(x, y, 1)
    r2 = 1 - np.sum((y - (k * x + c)) ** 2) / np.sum((y - y.mean()) ** 2)
    return k, c, r2


def summarise(rows, scaling):
    lines = ["# Phase 3 results", ""]
    lines.append(f"{len({(r['factor'], r['level'], r['day']) for r in rows})} configuration-days. "
                 f"Regret = cost above the best schedule known for that day (any method, or a DP knowing "
                 f"the actual PV and every task).")

    def table(title, header, body, note=None):
        lines.extend(["", f"## {title}", ""])
        if note:
            lines.extend([note, ""])
        lines.extend(["| " + " | ".join(header) + " |", "|" + "---|" * len(header)])
        lines.extend("| " + " | ".join(cells) + " |" for cells in body)

    def select(**filters):
        return [r for r in rows if all(r[k] == v for k, v in filters.items())]

    body = []
    for regime in REGIMES:
        for method in METHODS:
            runs = select(regime=regime, method=method)
            regret = np.array([r["regret"] for r in runs])
            issues = sum(r["unfinished"] + r["violations"] + (r["late_hours"] > 0) for r in runs)
            body.append([regime, method, f"{np.mean([r['total_cost'] for r in runs]):.2f}",
                         f"{regret.mean():.2f}", f"{regret.std():.2f}",
                         f"{np.mean([r['solve_time'] for r in runs]):.3f}", str(int(issues))])
    table("Overall", ["Regime", "Method", "Mean cost $", "Mean regret $", "Regret std $", "Mean time s",
                      "Late/unfinished"], body)

    for factor, levels in FACTORS.items():
        body = []
        for level in levels:
            for regime in REGIMES:
                body.append([str(level), regime] + [
                    f"{np.mean([r['regret'] for r in level_runs(rows, factor, level, regime, m)]):.2f}"
                    for m in METHODS
                ])
        table(f"Mean regret $ by {FACTOR_LABELS[factor].lower()}", [FACTOR_LABELS[factor], "Regime"] + METHODS, body)

    body = []
    for method in METHODS:
        gap = (np.mean([r["total_cost"] for r in select(regime="on arrival", method=method)])
               - np.mean([r["total_cost"] for r in select(regime="day-ahead", method=method)]))
        body.append([method, f"{gap:+.2f}"])
    table("Cost of not knowing the day's tasks (on arrival minus day-ahead, mean $)", ["Method", "Extra cost $"], body)

    body = []
    for regime in REGIMES:
        for method in METHODS:
            sizes, times, censored = scaling_points(scaling, regime, method)
            fit = fit_order(sizes, times, censored)
            body.append([regime, method, f"{times[0]:.3f}", f"{times[-1]:.3f}",
                         f"n^{fit[0]:.2f}" if fit else "-", f"{fit[2]:.2f}" if fit else "-",
                         str(int(censored.sum()))])
    table("Computing time against the number of tasks n", ["Regime", "Method", f"Time at n={SIZES[0]} s",
          f"Time at n={SIZES[-1]} s", "Fitted order", "R²", "Sizes at MILP limit"], body,
          note=f"Mean of {len({r['day'] for r in scaling})} days per size, n = {SIZES[0]} to {SIZES[-1]}. Fitted as time ~ n^k on "
               f"log-log axes, sizes where a MILP solve hit its 10 s limit excluded.")

    return "\n".join(lines) + "\n"


def summarise_costs(rows):
    lines = ["# Cost coefficient study", ""]
    lines.append(f"{len({(r['factor'], r['level'], r['day']) for r in rows})} configuration-days, baseline day "
                 f"otherwise. Regret in % of the best known cost that day; the costs change with the coefficients.")

    for factor, levels in COST_FACTORS.items():
        for title, value in [
            ("Regret (% of best cost)", lambda runs: 100 * np.mean([r["regret"] for r in runs])
                                                     / np.mean([r["best_cost"] for r in runs])),
            ("Mean daily peak import (kW)", lambda runs: np.mean([r["peak_kw"] for r in runs])),
            ("Import above the threshold (kWh/day)", lambda runs: np.mean([r["excess_kwh"] for r in runs])),
            ("Battery throughput (kWh/day)", lambda runs: np.mean([r["battery_throughput_kwh"] for r in runs])),
        ]:
            lines.extend(["", f"## {title} by {FACTOR_LABELS[factor].lower()}", "",
                          "| " + " | ".join([FACTOR_LABELS[factor], "Regime"] + METHODS) + " |",
                          "|" + "---|" * (len(METHODS) + 2)])
            for level in levels:
                for regime in REGIMES:
                    cells = [f"{value(level_runs(rows, factor, level, regime, m)):.2f}" for m in METHODS]
                    lines.append("| " + " | ".join([level_name(factor, level), regime] + cells) + " |")

    return "\n".join(lines) + "\n"


def level_name(factor, level):
    if factor == "prices":
        return f"{level} ({PRICES[level][0]:.2f} / {PRICES[level][1]:.2f})"
    return f"{level:g}"


# ---------------------------------------------------------------- Figures

def style(ax, xlabel, ylabel=None, title=None):
    ax.grid(True, axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(AXIS)
    ax.tick_params(colors=MUTED, labelsize=9)
    if ax.get_yscale() == "linear":
        from matplotlib.ticker import FuncFormatter
        ax.yaxis.set_major_formatter(FuncFormatter(lambda value, _: fr(value)))
    ax.set_xlabel(xlabel, fontsize=9, color=MUTED)
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=9, color=MUTED)
    if title:
        ax.set_title(title, fontsize=11)


def plot_factor(rows, factor, path):
    import matplotlib.pyplot as plt

    shown = [m for m in PLOT_METHODS if m != "Greedy"]   # Greedy's regret is an order of magnitude above, see summary
    levels = FACTORS[factor]
    x = np.arange(len(levels))

    # Each regime keeps its own scale: regret on arrival is about ten times larger
    fig, axes = plt.subplots(1, len(REGIMES), figsize=(12, 4))

    for ax, regime in zip(axes, REGIMES):
        values = []
        for method in shown:
            means = [np.mean([r["regret"] for r in level_runs(rows, factor, level, regime, method)]) for level in levels]
            ax.plot(x, means, color=COLORS[method], linewidth=2, marker="o", markersize=6,
                    markeredgecolor="white", markeredgewidth=1.2, label=NAMES_FR[method])
            values += means

        ax.set_xticks(x, [fr(level) for level in levels])
        ax.set_xlim(-0.4, len(levels) - 0.6)
        if regime == "day-ahead":
            ax.set_ylim(bottom=0)
        else:
            # On arrival the methods sit close together far above zero: the axis spans the data only
            pad = 0.08 * (max(values) - min(values))
            ax.set_ylim(max(0.0, min(values) - pad), max(values) + pad)
        style(ax, LABELS_FR[factor], "Regret moyen ($/jour)", REGIMES_FR[regime])

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=len(shown), frameon=False, fontsize=9, bbox_to_anchor=(0.5, 1.02))
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_cost(rows, factor, path):
    # The coefficient's target quantity (peak or battery use) per method, Greedy included
    import matplotlib.pyplot as plt

    metric, _ = COST_METRICS[factor]
    ylabel = METRICS_FR[metric]
    levels = COST_FACTORS[factor]
    x = np.arange(len(levels))

    fig, axes = plt.subplots(1, len(REGIMES), figsize=(12, 4), sharey=True)

    for ax, regime in zip(axes, REGIMES):
        for method in PLOT_METHODS:
            means = [np.mean([r[metric] for r in level_runs(rows, factor, level, regime, method)]) for level in levels]
            ax.plot(x, means, color=COLORS[method], linewidth=2, marker="o", markersize=6,
                    markeredgecolor="white", markeredgewidth=1.2, label=NAMES_FR[method])

        if factor == "threshold":
            ax.plot(x, levels, color=MUTED, linestyle="--", linewidth=1, label="Seuil de pointe")

        if factor == "prices":
            ticks = [f"{PRICES_FR[level]}\n({PRICES[level][0]:.2f} / {PRICES[level][1]:.2f})".replace(".", ",") for level in levels]
        else:
            ticks = [fr(level) for level in levels]
        ax.set_xticks(x, ticks)
        ax.set_xlim(-0.3, len(levels) - 0.7)
        style(ax, LABELS_FR[factor], ylabel if regime == REGIMES[0] else None, REGIMES_FR[regime])

    # Once both panels are drawn: on the first one, it would freeze the shared top at that panel's data
    axes[0].set_ylim(bottom=0)

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=len(labels), frameon=False, fontsize=9, bbox_to_anchor=(0.5, 1.02))
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_scaling(scaling, path):
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, len(REGIMES), figsize=(12, 4.5), sharey=True)

    for ax, regime in zip(axes, REGIMES):
        for method in PLOT_METHODS:
            sizes, times, censored = scaling_points(scaling, regime, method)
            fit = fit_order(sizes, times, censored)
            label = f"{NAMES_FR[method]}  ~ n^{abs(fit[0]) if abs(fit[0]) < 0.05 else fit[0]:.1f}".replace(".", ",") if fit else NAMES_FR[method]
            ax.plot(sizes, times, color=COLORS[method], linewidth=2, label=label)
            # Hollow markers: a MILP solve hit its time limit, so the time is a lower bound
            ax.scatter(sizes[~censored], times[~censored], color=COLORS[method], s=36, edgecolor="white",
                       linewidth=1.2, zorder=3)
            ax.scatter(sizes[censored], times[censored], facecolor="white", edgecolor=COLORS[method], s=36,
                       linewidth=1.5, zorder=3)

        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xticks(SIZES, [str(n) for n in SIZES])
        ax.minorticks_off()
        style(ax, "Nombre de tâches n (échelle log)",
              "Temps de calcul par jour (s, échelle log)" if regime == REGIMES[0] else None, REGIMES_FR[regime])
        ax.grid(True, axis="x", color=GRID, linewidth=0.8)
        # Below the panel: the fitted orders differ per regime, and inside it the legend covers lines
        ax.legend(frameon=False, fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=2)

    fig.text(0.5, -0.12, "Ordre ajusté : temps ~ n^k sur les points pleins. Points creux : une résolution MILP a "
             "atteint sa limite de 10 s (le temps est une borne inférieure).", ha="center", fontsize=8, color=MUTED)
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_power(profiles, path):
    import matplotlib.pyplot as plt

    times = np.arange(len(profiles["pv"])) * TIME_STEP
    fig, axes = plt.subplots(1, len(REGIMES), figsize=(12, 4), sharey=True)

    for ax, regime in zip(axes, REGIMES):
        ax.fill_between(times, profiles["pv"], step=None, color="#e0e0dc", label="Production PV")
        ax.axhline(3.0, color=MUTED, linestyle="--", linewidth=1, label="Seuil de pointe (3 kW)")
        for method in POWER_METHODS:
            ax.step(times, np.maximum(profiles[f"{regime}|{method}"], 0.0), where="post",
                    color=COLORS[method], linewidth=1.6, label=NAMES_FR[method])

        ax.set_xlim(4, 20)
        ax.set_xticks(range(4, 21, 2))
        ax.set_ylim(bottom=0)
        style(ax, "Heure de la journée (h)", "Import du réseau (kW)" if regime == REGIMES[0] else None,
              REGIMES_FR[regime])

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=len(labels), frameon=False, fontsize=9, bbox_to_anchor=(0.5, 1.02))
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def write_cost_outputs(rows):
    import matplotlib
    matplotlib.use("Agg")

    rows = rebase(rows)
    with open(os.path.join(RESULTS, "summary_costs.md"), "w", encoding="utf-8") as file:
        file.write(summarise_costs(rows))
    for factor in COST_FACTORS:
        plot_cost(rows, factor, os.path.join(RESULTS, f"cost_{factor}.png"))


def write_outputs(rows, profiles):
    import matplotlib
    matplotlib.use("Agg")

    rows = rebase(rows)
    with open(os.path.join(RESULTS, "summary.md"), "w", encoding="utf-8") as file:
        file.write(summarise(rows, scaling_rows(rows)))

    for factor in PLOTTED:
        plot_factor(rows, factor, os.path.join(RESULTS, f"regret_{factor}.png"))
    plot_scaling(scaling_rows(rows), os.path.join(RESULTS, "scaling.png"))
    plot_power(profiles, os.path.join(RESULTS, "power_baseline.png"))


# ---------------------------------------------------------------- Files

def write_csv(path, rows):
    with open(path, "w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path):
    rows = []
    with open(path, newline="") as file:
        for row in csv.DictReader(file):
            for key, value in row.items():
                try:
                    row[key] = int(value) if key in ("tasks", "capacity", "day", "limit_hits") else float(value)
                except ValueError:
                    pass
            if "level" in row:
                row["level"] = str(row["level"])
            rows.append(row)
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--study", choices=["factors", "costs"], default="factors")
    parser.add_argument("--days", type=int, default=3, help="Days (seeds) per factor configuration")
    parser.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 2))
    parser.add_argument("--plot-only", action="store_true", help="Redraw summary and figures from the CSV files")
    args = parser.parse_args()

    os.makedirs(RESULTS, exist_ok=True)
    paths = {name: os.path.join(RESULTS, f"{name}.csv") for name in ("experiments", "power_baseline", "costs")}
    factors = FACTORS if args.study == "factors" else COST_FACTORS

    if not args.plot_only:
        # Largest problems first, so that they do not finish last on their own
        jobs = sorted(
            [(factor, level, config, day) for factor, level, config in configurations(factors) for day in range(args.days)],
            key=lambda job: -job[2]["tasks"]
        )
        print(f"{len(jobs)} jobs on {args.workers} workers (computing times are measured in parallel)")

        rows, profiles = [], None
        start = time.perf_counter()
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            futures = [pool.submit(run_job, job) for job in jobs]
            for i, future in enumerate(as_completed(futures), 1):
                _, job_rows, job_profiles = future.result()
                rows.extend(job_rows)
                profiles = profiles or job_profiles
                print(f"  {i}/{len(jobs)} done ({time.perf_counter() - start:.0f} s)", flush=True)

        if args.study == "costs":
            write_csv(paths["costs"], rows)
        else:
            write_csv(paths["experiments"], rows)
            power_rows = [{"time_h": t * TIME_STEP, **{key: values[t] for key, values in profiles.items()}}
                          for t in range(len(profiles["pv"]))]
            write_csv(paths["power_baseline"], power_rows)

    if args.study == "costs":
        write_cost_outputs(read_csv(paths["costs"]))
        print(open(os.path.join(RESULTS, "summary_costs.md"), encoding="utf-8").read())
        return

    rows = read_csv(paths["experiments"])
    power = read_csv(paths["power_baseline"])
    profiles = {key: np.array([row[key] for row in power]) for key in power[0] if key != "time_h"}

    write_outputs(rows, profiles)
    print(open(os.path.join(RESULTS, "summary.md"), encoding="utf-8").read())


if __name__ == "__main__":
    main()
