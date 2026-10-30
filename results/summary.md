# Phase 3 results

117 configuration-days. Regret = cost above the best schedule known for that day (any method, or a DP knowing the actual PV and every task).

## Overall

| Regime | Method | Mean cost $ | Mean regret $ | Regret std $ | Mean time s | Late/unfinished |
|---|---|---|---|---|---|---|
| day-ahead | MILP | 38.72 | 0.36 | 0.44 | 5.630 | 0 |
| day-ahead | DP plan | 39.90 | 1.55 | 1.61 | 1.751 | 0 |
| day-ahead | DP policy | 39.56 | 1.21 | 1.91 | 1.783 | 0 |
| day-ahead | SDP policy | 39.49 | 1.13 | 1.92 | 8.856 | 0 |
| day-ahead | Pred (smart) | 49.55 | 11.20 | 9.67 | 1.307 | 0 |
| day-ahead | Greedy | 94.50 | 56.14 | 42.66 | 0.003 | 0 |
| on arrival | MILP | 63.45 | 25.10 | 20.94 | 12.156 | 0 |
| on arrival | DP plan | 64.67 | 26.32 | 21.54 | 1.867 | 0 |
| on arrival | DP policy | 64.98 | 26.62 | 22.65 | 1.864 | 0 |
| on arrival | SDP policy | 64.20 | 25.84 | 22.12 | 8.703 | 0 |
| on arrival | Pred (smart) | 61.12 | 22.76 | 17.00 | 0.315 | 0 |
| on arrival | Greedy | 94.50 | 56.14 | 42.66 | 0.003 | 0 |

## Mean regret $ by arrival skew (1/h): late < 0 < early

| Arrival skew (1/h): late < 0 < early | Regime | MILP | DP plan | DP policy | SDP policy | Pred (smart) | Greedy |
|---|---|---|---|---|---|---|---|
| -0.5 | day-ahead | 0.00 | 2.53 | 2.52 | 2.33 | 37.00 | 145.75 |
| -0.5 | on arrival | 82.20 | 86.88 | 93.81 | 90.58 | 69.46 | 145.75 |
| -0.4 | day-ahead | 0.00 | 1.14 | 0.93 | 0.89 | 32.93 | 119.53 |
| -0.4 | on arrival | 75.05 | 77.01 | 80.95 | 79.20 | 60.60 | 119.53 |
| -0.3 | day-ahead | 0.38 | 0.86 | 0.75 | 0.46 | 28.06 | 92.02 |
| -0.3 | on arrival | 60.82 | 63.55 | 65.47 | 65.11 | 49.73 | 92.02 |
| -0.2 | day-ahead | 0.29 | 1.33 | 0.93 | 0.89 | 19.34 | 59.61 |
| -0.2 | on arrival | 41.17 | 42.88 | 45.32 | 43.24 | 33.26 | 59.61 |
| -0.1 | day-ahead | 0.52 | 0.74 | 0.30 | 0.23 | 13.60 | 42.40 |
| -0.1 | on arrival | 24.26 | 26.52 | 27.02 | 25.13 | 21.92 | 42.40 |
| 0.0 | day-ahead | 0.69 | 1.16 | 0.49 | 0.42 | 8.15 | 38.49 |
| 0.0 | on arrival | 19.61 | 20.35 | 20.27 | 19.20 | 20.07 | 38.49 |
| 0.1 | day-ahead | 0.25 | 1.41 | 1.08 | 1.00 | 5.80 | 28.47 |
| 0.1 | on arrival | 12.00 | 12.07 | 11.41 | 10.85 | 9.76 | 28.47 |
| 0.2 | day-ahead | 0.05 | 1.85 | 1.99 | 1.88 | 6.71 | 40.79 |
| 0.2 | on arrival | 12.86 | 13.73 | 13.25 | 12.14 | 11.32 | 40.79 |
| 0.3 | day-ahead | 0.00 | 2.71 | 2.74 | 2.69 | 8.69 | 59.32 |
| 0.3 | on arrival | 14.91 | 16.22 | 15.52 | 14.13 | 13.57 | 59.32 |
| 0.4 | day-ahead | 0.00 | 1.81 | 1.97 | 1.97 | 10.08 | 81.92 |
| 0.4 | on arrival | 18.66 | 19.09 | 18.47 | 17.80 | 17.64 | 81.92 |
| 0.5 | day-ahead | 0.00 | 2.96 | 3.19 | 3.21 | 10.50 | 88.83 |
| 0.5 | on arrival | 20.11 | 20.74 | 19.73 | 20.83 | 19.88 | 88.83 |

## Mean regret $ by average cloudiness

| Average cloudiness | Regime | MILP | DP plan | DP policy | SDP policy | Pred (smart) | Greedy |
|---|---|---|---|---|---|---|---|
| 0.0 | day-ahead | 0.44 | 0.45 | 0.29 | 0.22 | 5.53 | 30.81 |
| 0.0 | on arrival | 14.27 | 14.42 | 14.68 | 14.28 | 11.73 | 30.81 |
| 0.1 | day-ahead | 0.62 | 0.74 | 0.67 | 0.27 | 5.95 | 32.32 |
| 0.1 | on arrival | 15.26 | 15.54 | 15.80 | 15.27 | 12.44 | 32.32 |
| 0.2 | day-ahead | 0.52 | 0.97 | 0.67 | 0.36 | 6.86 | 29.57 |
| 0.2 | on arrival | 16.86 | 17.19 | 17.43 | 16.77 | 16.60 | 29.57 |
| 0.3 | day-ahead | 0.75 | 1.07 | 0.54 | 0.36 | 7.29 | 35.66 |
| 0.3 | on arrival | 17.43 | 18.76 | 18.92 | 18.34 | 17.81 | 35.66 |
| 0.4 | day-ahead | 0.69 | 1.16 | 0.49 | 0.42 | 8.15 | 38.49 |
| 0.4 | on arrival | 19.61 | 20.35 | 20.27 | 19.20 | 20.07 | 38.49 |
| 0.5 | day-ahead | 0.61 | 1.07 | 0.38 | 0.36 | 8.54 | 39.95 |
| 0.5 | on arrival | 20.40 | 21.50 | 20.92 | 20.60 | 21.22 | 39.95 |
| 0.6 | day-ahead | 0.33 | 1.37 | 0.66 | 0.66 | 9.87 | 47.04 |
| 0.6 | on arrival | 21.19 | 22.79 | 22.47 | 21.46 | 21.91 | 47.04 |
| 0.7 | day-ahead | 0.30 | 1.16 | 0.58 | 0.64 | 10.28 | 50.86 |
| 0.7 | on arrival | 21.42 | 22.70 | 22.48 | 22.05 | 22.37 | 50.86 |
| 0.8 | day-ahead | 0.08 | 0.90 | 0.43 | 0.42 | 9.08 | 54.74 |
| 0.8 | on arrival | 21.01 | 22.91 | 22.35 | 22.27 | 22.58 | 54.74 |
| 0.9 | day-ahead | 0.10 | 1.29 | 0.62 | 0.66 | 10.31 | 57.55 |
| 0.9 | on arrival | 21.04 | 22.99 | 22.34 | 22.37 | 21.84 | 57.55 |

## Mean regret $ by number of tasks

| Number of tasks | Regime | MILP | DP plan | DP policy | SDP policy | Pred (smart) | Greedy |
|---|---|---|---|---|---|---|---|
| 10 | day-ahead | 0.20 | 0.22 | 0.03 | 0.03 | 1.00 | 1.21 |
| 10 | on arrival | 0.32 | 0.32 | 0.22 | 0.16 | 1.31 | 1.21 |
| 20 | day-ahead | 0.25 | 0.20 | 0.08 | 0.03 | 0.54 | 1.58 |
| 20 | on arrival | 0.54 | 0.82 | 0.63 | 0.52 | 1.49 | 1.58 |
| 30 | day-ahead | 0.29 | 0.18 | 0.19 | 0.02 | 0.83 | 2.33 |
| 30 | on arrival | 0.60 | 1.22 | 0.99 | 0.82 | 0.84 | 2.33 |
| 40 | day-ahead | 0.66 | 0.44 | 0.24 | 0.15 | 4.52 | 13.73 |
| 40 | on arrival | 10.32 | 10.99 | 10.55 | 10.02 | 10.02 | 13.73 |
| 50 | day-ahead | 0.69 | 1.16 | 0.49 | 0.42 | 8.15 | 38.49 |
| 50 | on arrival | 19.61 | 20.35 | 20.27 | 19.20 | 20.07 | 38.49 |
| 60 | day-ahead | 0.25 | 1.26 | 0.62 | 0.61 | 5.83 | 49.50 |
| 60 | on arrival | 22.85 | 23.48 | 22.99 | 22.38 | 21.57 | 49.50 |
| 70 | day-ahead | 0.40 | 1.85 | 1.27 | 1.12 | 10.81 | 81.11 |
| 70 | on arrival | 23.46 | 27.93 | 28.31 | 27.17 | 20.40 | 81.11 |
| 80 | day-ahead | 0.28 | 1.98 | 1.46 | 1.40 | 18.49 | 104.60 |
| 80 | on arrival | 43.36 | 42.10 | 42.16 | 42.90 | 38.90 | 104.60 |
| 90 | day-ahead | 0.00 | 5.91 | 6.11 | 5.97 | 32.91 | 134.33 |
| 90 | on arrival | 47.69 | 53.92 | 54.20 | 51.57 | 43.61 | 134.33 |
| 100 | day-ahead | 0.00 | 6.58 | 6.58 | 6.76 | 23.92 | 131.10 |
| 100 | on arrival | 55.01 | 56.74 | 55.08 | 54.99 | 50.02 | 131.10 |

## Mean regret $ by battery capacity (kwh)

| Battery capacity (kWh) | Regime | MILP | DP plan | DP policy | SDP policy | Pred (smart) | Greedy |
|---|---|---|---|---|---|---|---|
| 2 | day-ahead | 0.49 | 1.34 | 0.70 | 0.58 | 5.94 | 38.26 |
| 2 | on arrival | 16.04 | 16.55 | 16.53 | 16.01 | 17.51 | 38.26 |
| 4 | day-ahead | 0.66 | 1.50 | 0.86 | 0.80 | 6.55 | 39.89 |
| 4 | on arrival | 17.26 | 18.31 | 18.18 | 17.62 | 18.58 | 39.89 |
| 6 | day-ahead | 0.92 | 1.27 | 0.67 | 0.59 | 7.34 | 38.22 |
| 6 | on arrival | 18.34 | 18.92 | 19.13 | 18.23 | 19.25 | 38.22 |
| 8 | day-ahead | 0.79 | 1.18 | 0.50 | 0.55 | 7.54 | 38.62 |
| 8 | on arrival | 19.23 | 19.56 | 19.81 | 18.91 | 19.84 | 38.62 |
| 10 | day-ahead | 0.69 | 1.16 | 0.49 | 0.42 | 8.15 | 38.49 |
| 10 | on arrival | 19.61 | 20.35 | 20.27 | 19.20 | 20.07 | 38.49 |
| 12 | day-ahead | 0.69 | 1.04 | 0.44 | 0.33 | 7.86 | 38.38 |
| 12 | on arrival | 19.79 | 20.42 | 20.49 | 19.70 | 20.65 | 38.38 |
| 14 | day-ahead | 0.54 | 0.98 | 0.46 | 0.39 | 8.05 | 38.82 |
| 14 | on arrival | 20.03 | 20.94 | 20.97 | 19.93 | 20.61 | 38.82 |
| 16 | day-ahead | 0.71 | 0.98 | 0.44 | 0.34 | 8.25 | 38.60 |
| 16 | on arrival | 20.23 | 20.49 | 20.66 | 20.16 | 20.08 | 38.60 |
| 18 | day-ahead | 0.57 | 0.97 | 0.43 | 0.37 | 8.70 | 36.19 |
| 18 | on arrival | 20.11 | 20.82 | 21.04 | 20.07 | 19.71 | 36.19 |
| 20 | day-ahead | 0.58 | 0.93 | 0.32 | 0.31 | 7.98 | 36.16 |
| 20 | on arrival | 20.29 | 21.21 | 20.79 | 20.67 | 20.56 | 36.16 |

## Mean regret $ by task arrival profile

| Task arrival profile | Regime | MILP | DP plan | DP policy | SDP policy | Pred (smart) | Greedy |
|---|---|---|---|---|---|---|---|
| uniform | day-ahead | 0.69 | 1.16 | 0.49 | 0.42 | 8.15 | 38.49 |
| uniform | on arrival | 19.61 | 20.35 | 20.27 | 19.20 | 20.07 | 38.49 |
| bimodal | day-ahead | 0.00 | 4.08 | 3.95 | 3.94 | 15.18 | 151.28 |
| bimodal | on arrival | 52.72 | 53.85 | 57.00 | 54.47 | 27.09 | 151.28 |

## Cost of not knowing the day's tasks (on arrival minus day-ahead, mean $)

| Method | Extra cost $ |
|---|---|
| MILP | +24.73 |
| DP plan | +24.77 |
| DP policy | +25.42 |
| SDP policy | +24.71 |
| Pred (smart) | +11.56 |
| Greedy | +0.00 |

## Computing time against the number of tasks n

Mean of 3 days per size, n = 10 to 100. Fitted as time ~ n^k on log-log axes, sizes where a MILP solve hit its 10 s limit excluded.

| Regime | Method | Time at n=10 s | Time at n=100 s | Fitted order | R² | Sizes at MILP limit |
|---|---|---|---|---|---|---|
| day-ahead | MILP | 1.162 | 4.252 | n^-0.03 | 0.00 | 4 |
| day-ahead | DP plan | 0.096 | 7.524 | n^1.89 | 0.95 | 0 |
| day-ahead | DP policy | 0.086 | 7.918 | n^1.95 | 0.96 | 0 |
| day-ahead | SDP policy | 0.339 | 32.344 | n^1.95 | 0.95 | 0 |
| day-ahead | Pred (smart) | 0.136 | 2.761 | n^1.27 | 0.99 | 0 |
| day-ahead | Greedy | 0.001 | 0.006 | n^0.88 | 0.97 | 0 |
| on arrival | MILP | 3.512 | 14.333 | n^0.65 | 0.89 | 0 |
| on arrival | DP plan | 0.246 | 5.008 | n^1.28 | 0.98 | 0 |
| on arrival | DP policy | 0.237 | 5.087 | n^1.28 | 0.98 | 0 |
| on arrival | SDP policy | 0.653 | 17.622 | n^1.37 | 0.98 | 0 |
| on arrival | Pred (smart) | 0.032 | 0.751 | n^1.35 | 0.99 | 0 |
| on arrival | Greedy | 0.001 | 0.006 | n^0.97 | 0.93 | 0 |
