# Scheduling algorithms of the EMS

This document describes the four scheduling algorithms compared in the project, the programming pattern behind each one, and the performance they can be expected to give on the three evaluation criteria: computing time, quality of the solution, and robustness. Expected behaviour is checked against the measured results in [results/summary.md](../../results/summary.md).

## 1. Common framework

**The problem.** A day is split into T = 96 steps of 15 min. Each task j has:
- a power p_j (1, 2 or 3 kW);
- a duration d_j (1 to 4 steps);
- a release step (its arrival);
- a latest start step, so that it ends before its deadline (2 h after arrival).

The EMS chooses each task's start step and, depending on the method, the battery power at each step. PV production is free, and the rest of the demand is met by the battery or by grid imports.

**The cost function** (`src/cost.py`) is the same for every method, and every schedule is scored afterwards by the same simulator (`simulation.evaluate_schedule`). Its terms are:
- grid import at 0.30 $/kWh;
- minus export at 0.05 $/kWh;
- battery wear at 0.10 $/kWh of throughput;
- a squared peak penalty, 0.5 $/(kW²·h) on the import above 3 kW;
- lateness at 200 $ per hour per task.

**A common interface (Strategy pattern).** Each algorithm is a class with the same method:

```python
solve(forecast, tasks, battery, deltaT, actual=None) -> {"starts": {task id: step}, "battery": plan or None}
```

Because every method has the same interface, the experiments treat them as interchangeable and score them on equal terms.

**Two information regimes.**
- **Tasks known day-ahead:** the whole day's task list is known before the day starts (for example, a factory that locks its orders the evening before).
- **Tasks revealed on arrival:** a task becomes known only when it arrives.

Planners such as the MILP and the DP need the whole task list. On arrival they are wrapped in `ReplanningEMS` (Decorator pattern), which:
- calls the planner again on the rest of the day each time new tasks arrive;
- takes into account the measured battery state and the tasks already running;
- follows the resulting plan until the next arrival.

The greedy and predictive methods are online by design, so they need no wrapper.

**What the methods know about PV.**
- **Planners:** a forecast, the mean of 10 cloud scenarios.
- **Online methods:** only the PV measured up to the current step.

**Quality measure.** Quality is the **regret**: the cost of a schedule minus the cost of the best schedule found for that day, by any method or by a DP that knows the actual PV and every task. A regret of 0 means the method found the best known schedule.

## 2. Greedy (`methods/greedy.py`)

### Description

The greedy method moves forward one step at a time and never revisits a decision. At each step:
1. It starts every released task that has reached its latest start, so no task is ever late.
2. Among the other released tasks, it computes the marginal cost of starting each one **now**: the cost of the current step with the task, minus the cost without it, per kWh of task energy. That cost includes the battery dispatch and the peak penalty.
3. It starts the cheapest task while its marginal cost is no higher than the import price, then repeats from step 2.
4. It applies the rule-based battery dispatch: charge from any PV surplus, and discharge to cover any deficit.

### Programming pattern

- **Paradigm:** a greedy (myopic) heuristic in an online simulation loop.
- **What it uses:** only the current step's PV, which is measured, so it is the same in both regimes.
- **What it skips:** no forecast and no lookahead.

### Expected performance

| Criterion | Expected | Measured |
|---|---|---|
| Computing time | About O(T · r²), where r is the number of released tasks waiting (small). Roughly linear in n. | n^0.9 to n^0.95, **under 10 ms** at n = 100 |
| Quality | Poor. A task deferred because "now" is expensive is forced to start at its latest start, whatever the cost then. Many forced starts land on the same step and create import peaks of 10 kW and more, which the squared penalty punishes heavily. | Mean regret **56 $/day**, the worst by far |
| Robustness | Unaffected by forecast errors, since it uses no forecast. Very sensitive to how tasks are grouped: arrivals bunched together become simultaneous forced starts. | Regret 31 → 58 $ from clear to cloudy days. 38 $ (uniform) → 146 $ (late skew) → 151 $ (bimodal) |

The greedy method is the baseline. It's the cheapest method to run and is independent of the information regime, but it gives the worst schedules.

## 3. Mixed-integer linear programming, MILP (`methods/milp.py`)

### Description

The whole day (or the rest of the day, when re-planning) is written as one optimisation model and solved with the CBC solver through PuLP.

**Variables:**
- `x[j, s]` ∈ {0, 1}: 1 if task j starts at step s, for s between its release and its latest start;
- battery charge and discharge power;
- grid import and export;
- stored energy;
- the excess import above 3 kW.

**Constraints:**
- each task starts exactly once;
- the power balance at each step: PV + discharge + import = load + charge + export;
- the battery energy balance, with its efficiency, capacity and power limits;
- the battery charges only from PV;
- the excess import is at least the import minus 3 kW.

**Objective:**
- The cost function above, written in linear form.
- The squared peak term is not linear, so it is approximated from below by its tangent lines at 0, 0.5, 1, …, 30 kW. Because the solver minimises, it lands on the highest tangent, which is a close approximation of excess².

**Solver settings:** a time limit of 10 s and a 1 % optimality gap.

The model returns both the start times and a battery power plan, which the simulator then applies on the actual PV.

### Programming pattern

- **Paradigm:** declarative mathematical programming. The code only *describes* the problem (variables, constraints, objective) and hands it to a general-purpose solver.
- **Inside the solver:** branch and bound on the binary variables, with a linear relaxation solved at each node.
- **Planning style:** open loop. The plan is computed once on the forecast and is not changed during the day, except through re-planning on arrival.

### Expected performance

| Criterion | Expected | Measured |
|---|---|---|
| Computing time | **NP-hard in general**: the worst case is exponential in the number of binary variables (5 to 8 per task, one per possible start step). The model is small, about 300 binaries at n = 50, but how fast branch and bound finishes depends on how "hard" that day's instance is, not on n. | No polynomial order fits day-ahead (R² ≈ 0). 4 of the 10 sizes hit the 10 s limit, including small ones. On arrival, ~n^0.7, but 4 to 17 s per day, the slowest method |
| Quality | **Optimal for its model** (within 1 %), with a free task order. Its only gaps come from the tangent approximation and from the forecast error on PV. | **Best day-ahead**: regret 0.36 $/day. On arrival: 25.1 $ |
| Robustness | Open loop, so a PV forecast error is never corrected during the day. Each re-plan sees only the tasks known so far, so in that regime it optimises well for the present but can't anticipate. | Day-ahead regret stays below 1 $ at every cloud level and every arrival profile. On arrival it degrades with late or bimodal arrivals (82 $ at skew −0.5, 53 $ bimodal) |

The MILP is the best method when the whole task list is known in advance. Its costs are an unpredictable solving time, which is why it needs a time limit, and a dependence on a solver library.

## 4. Dynamic programming, DP (`methods/dynamic.py`)

### Description

The day is a sequence of decisions made one step at a time. The **state** at step t combines:
- **tasks started so far:** to keep the state space small, tasks are started in a fixed order, sorted by latest start, so this is just a number k;
- **the committed load:** the power still owed in the next steps to tasks already running;
- **the battery's stored energy:** discretised in 0.1 kWh levels, which gives 70 levels for a 10 kWh battery.

The **decision** at each step is how many of the next tasks in the order to start, which can't be fewer than the tasks that have reached their latest start, plus the battery's next energy level.

The algorithm runs in two passes:
1. **Building the graph, forward:** it lists the reachable task states at each step.
2. **Backward induction (Bellman equation):** it computes the minimum cost-to-go of every state, from the end of the day back to the start:
   `V_t(state, energy) = min over decisions of [ cost of step t + V_{t+1}(next state, next energy) ]`.
   For each task decision, the step cost for all battery energy transitions is computed as one matrix (vectorised in NumPy).

Three variants share this code:
- **DP plan (open loop):** the cost-to-go is computed on the forecast, and the resulting plan is followed whatever the actual PV.
- **DP policy (closed loop):** the same cost-to-go, used as a **policy**. At each step, the decision is re-chosen from the PV actually measured and the battery level actually reached.
- **SDP policy (stochastic DP):** the cost-to-go is **averaged over 10 PV scenarios**, with each decision taken once the step's PV is known. The policy then accounts for how uncertain the future PV is, not only for its mean.

### Programming pattern

- **Paradigm:** dynamic programming, i.e. backward induction over a state graph with memoised values. This exploits the problem's step-by-step structure: an optimal schedule for the rest of the day depends only on the current state.
- **DP plan:** a deterministic planner (open loop).
- **DP policy and SDP:** they turn the same tables into a **feedback policy**. This is the main advantage of DP over the MILP: once computed, it says what to do in *any* state, not only along one forecast path.

### Expected performance

| Criterion | Expected | Measured |
|---|---|---|
| Computing time | O(T · S · A · L²), where S is the number of task states per step, A the decisions per state and L the number of battery levels. S and A grow with the number of tasks pending at the same time, so roughly with n² for a fixed day length. L² grows with battery capacity. The SDP multiplies the cost by the number of scenarios. | DP: **n^1.9 to n^2.0** day-ahead (8 s at n = 100). SDP: n^2.1 (33 s). On arrival n^1.3 to n^1.4, since each re-plan has fewer tasks. Battery size 2 → 20 kWh: DP 0.6 → 2.0 s, SDP 0.8 → 38 s |
| Quality | Optimal **within its restrictions**: the fixed task order and the 0.1 kWh battery grid. The fixed order can miss schedules a MILP finds when many tasks arrive together. The closed-loop variants should beat the plan when the PV differs from the forecast. | Day-ahead regret: plan 1.55 $, policy 1.21 $, SDP **1.13 $**. On arrival: 25.8 to 26.6 $ |
| Robustness | The policy variants correct forecast errors step by step, and the SDP also plans for PV uncertainty. Like the MILP, on arrival each re-plan sees only the tasks known so far. | Day-ahead regret stays below 3 $ at every cloud level and every arrival profile. The policy and SDP variants beat the plan in most settings. On arrival: same weaknesses as the MILP (up to 94 $ with late arrivals) |

DP gives near-optimal schedules with a time that grows predictably with problem size, unlike the MILP. It's the only planner that turns naturally into a policy that reacts to the measured PV. Its limits are the state-space growth, which is quadratic in tasks and increases quickly with battery size, and the fixed task order needed to keep the state space small.

## 5. Prediction-based EMS (`methods/predictive.py`, `forecast.py`)

### Description

An online controller that makes decisions with a short rolling horizon (H = 12 steps, 3 h). At each step t it does the following:

1. **PV prediction from the last hour:** a rolling window of 4 measurements.
   - **Methods available:** persistence, window average, Taylor extrapolation (first and second order, a polynomial fitted on the window), and **smart persistence**.
   - **Method used:** smart persistence. It applies the window's clear-sky index (measured PV / clear-sky PV) to the clear-sky profile ahead.
2. **Arrival estimate:** the task energy that arrived in the last hour is assumed to keep arriving. It is added as a flat background load over the horizon, which stops the empty future steps from looking free.
3. **Battery rules derived from the cost function:**
   - charge any PV surplus;
   - discharge first to keep the import under the 3 kW peak threshold;
   - discharge beyond that only with energy above a **reserve**, sized for the import above the threshold predicted over the horizon.
4. **Task placement:**
   - The known tasks are placed in order of urgency (latest start first), each in the slot with the lowest predicted cost over the horizon. The predicted cost includes simulating the battery under the rules above, and values the energy left in the battery at the end.
   - Every task is then re-placed in turn with all the others in place, for up to 3 passes or until no task moves.
5. **Commit and repeat:** only tasks placed at the current step t are started. The others are planned again at the next step (receding horizon, as in model predictive control).

### Programming pattern

- **Paradigm:** **rolling-horizon / model-predictive control** with a rule-based battery.
- **Inside each step:** a local search (best slot per task, then improvement passes).
- **Interchangeable forecasting:** the predictor is a separate component, so the forecasting method can be swapped without touching the controller (Strategy pattern again).
- **No solver and no full-day model:** it never optimises the whole day, only the next 3 hours, and only what it has already seen.

### Expected performance

| Criterion | Expected | Measured |
|---|---|---|
| Computing time | O(T · P · m · H²): P passes, m tasks known within the horizon, and H slots × H steps simulated per candidate. For a fixed day, m grows roughly with n. | **n^1.25 to n^1.4**: 0.75 s at n = 100 on arrival, the fastest after the greedy. Independent of battery size |
| Quality | Below the planners when everything is known in advance, because of the 3 h horizon and rule-based battery. Should be **competitive on arrival**, since the planners then lose their main advantage (seeing the whole day), while its arrival estimate still makes room for tasks not yet known. | Day-ahead regret 11.2 $ (well behind the planners, well ahead of the greedy). **Best on arrival: 22.8 $** |
| Robustness | Smart persistence follows the actual cloud conditions of the last hour. Re-deciding at every step with a battery reserve kept for peaks should help when tasks come in waves. The arrival estimate alone does not explain it: given to the planners, it did not improve them. Its weak point is fast, large swings in cloud cover within the horizon. | On arrival it is the most robust to the arrival pattern: 69 $ vs 82 to 94 $ for the planners at skew −0.5, and **27 $ vs 53 to 57 $ with bimodal arrivals**. On cloudy days it is level with the planners (about 22 $ at cloudiness ≥ 0.6) |

The predictive EMS is the practical choice when tasks are only known as they arrive. It's fast, needs no solver, and gives the best results in that regime. When the full task list is known in advance, an exact planner beats it.

## 6. Summary

| | Greedy | MILP | DP (plan / policy / SDP) | Predictive |
|---|---|---|---|---|
| Programming pattern | Myopic online heuristic | Declarative model + branch-and-bound solver | Backward induction over a state graph; feedback policy | Rolling-horizon (MPC-like) local search + rules |
| Needs the full task list | No | Yes (re-plans on arrival) | Yes (re-plans on arrival) | No |
| Uses a PV forecast | No (current step only) | Yes (scenario mean) | Yes (mean, or 10 scenarios for SDP) | Last-hour prediction |
| Time complexity | ~O(n), milliseconds | Exponential worst case, unpredictable | ~O(n²), grows with battery levels² and scenarios | ~O(n^1.3) |
| Time at n = 100, day-ahead / on arrival | < 0.01 s / < 0.01 s | 4.4 s* / 17 s | 8 s (SDP 33 s) / 5 s (SDP 18 s) | 2.8 s / 0.75 s |
| Regret, day-ahead | 56.1 $ | **0.36 $** | 1.55 / 1.21 / 1.13 $ | 11.2 $ |
| Regret, on arrival | 56.1 $ | 25.1 $ | 26.3 / 26.6 / 25.8 $ | **22.8 $** |
| Most sensitive to | Grouped arrivals (forced starts) | Solving time; late arrivals when re-planning | State-space size; late arrivals when re-planning | Large cloud changes within the horizon |

\* Some sizes stopped at the 10 s time limit, so the MILP times are lower bounds.

**Main conclusion.** The ranking depends on the information available:
- **Tasks known day-ahead:** the exact planners win clearly (MILP, then the DP policies).
- **Tasks revealed on arrival:** all the planners lose about 22 to 25 $/day, and the cheap predictive method becomes the best.

In this problem, knowing the task list in advance is worth more than choosing a better optimisation algorithm.

*Times were measured with 10 jobs running in parallel, so they overstate single-run times. The fitted orders are less affected.*
