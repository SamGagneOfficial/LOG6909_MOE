# LOG6909 – Energy management system for a solar-powered factory

This project simulates a small factory that runs on rooftop solar panels, a battery and the grid. It compares four ways of ordering the factory's tasks during the day on three criteria: computing time, quality of the solution and robustness.

Everything is simulated: PV production, factory tasks, battery and grid.

## The model

- **PV:** a 20 kW array with 21 % efficiency (peak around 3,9 kW on the simulated day). Clouds follow an AR(1) process, so production is uncertain.
- **Factory:** tasks arrive between 6 h and 16 h. Each one has a power draw, a duration and a deadline 2 h after it arrives.
- **Battery:** limited capacity and power, with charge/discharge efficiency and a wear cost.
- **Grid:**
  - imports cost 0,30 $/kWh and exports earn 0,05 $/kWh;
  - imports above 3 kW pay a squared peak penalty;
  - late tasks cost 200 $/h.
- **Time step:** 15 minutes (96 steps per day).

Every method returns task start times and battery setpoints. The same simulator scores them on the actual PV ([src/simulation.py](src/simulation.py)).

## Methods compared

| Method | File | Idea |
|---|---|---|
| Greedy | [greedy.py](src/methods/greedy.py) | Starts each task as soon as it is cheap enough, or at the latest start that keeps its deadline |
| Dynamic programming | [dynamic.py](src/methods/dynamic.py) | Bellman recursion over tasks started, committed load and battery energy; can run as a policy that reads the measured PV |
| MILP | [milp.py](src/methods/milp.py) | Binary start variables, solved with CBC (PuLP), 10 s time limit and 1 % gap |
| Predictive | [predictive.py](src/methods/predictive.py) | Rolling 3 h horizon using a clear-sky-index PV forecast and simple battery rules |

[src/methods/algorithms.md](src/methods/algorithms.md) describes each algorithm, its programming pattern and the performance to expect from it.

Each method runs under two regimes:

- **Tasks known day-ahead.**
- **Tasks revealed on arrival.** The MILP and DP re-plan at every arrival through [replanning.py](src/methods/replanning.py).

## Project layout

```
src/
  pv_system.py, factory.py, battery.py, cost.py   # simulated components and the cost function
  forecast.py                                     # PV predictor (clear-sky index persistence)
  simulation.py                                   # scores a schedule on the actual PV
  main.py                                         # single-day comparison, printed as a table
  experiments.py                                  # full studies, CSV results and figures
  methods/                                        # the scheduling algorithms
results/                                          # CSV files, summaries and figures
```

## Running

Python 3.11. Install the dependencies:

```
pip install -r requirements.txt
```

Use the following commands:

```
python src/main.py                                # compare all methods on one day
python src/experiments.py                         # factor study (~10 min with 10 workers)
python src/experiments.py --study costs           # cost-coefficient study
python src/experiments.py --plot-only             # redraw figures and summaries from the CSVs
```

Options: `--days N` sets the number of days per configuration (default 3) and `--workers N` sets the number of processes.

## Studies and results

**Factor study:**
- **Factors varied:** one factor at a time around a baseline day (arrival skew, cloudiness, number of tasks, battery capacity, plus bimodal arrivals).
- **Quality measure:** regret, the cost above the best schedule known for that day.

**Cost study:** varies the peak penalty, the grid prices and the peak threshold.

Results are written to [results/](results/):

- [summary.md](results/summary.md)
- [summary_costs.md](results/summary_costs.md)
- figures with French labels: `regret_*.png`, `scaling.png`, `power_baseline.png`, `cost_*.png`

Main findings (mean regret, $/day):

| Method | Day-ahead | On arrival |
|---|---|---|
| MILP | 0,36 | 25,10 |
| DP policy | 1,21 | 26,62 |
| Predictive | 11,20 | 22,76 |
| Greedy | 56,14 | 56,14 |

- **Tasks known in advance:** the exact methods (MILP, DP) are close to the best schedule.
- **Tasks revealed on arrival:**
  - knowing less about the tasks costs more than the choice of method;
  - the predictive method is the most robust, especially with late or bimodal arrivals.
- **Greedy:** instantaneous, but costs far more.
