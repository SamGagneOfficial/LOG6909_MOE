# Cost coefficient study

35 configuration-days, baseline day otherwise. Regret in % of the best known cost that day; the costs change with the coefficients.

## Regret (% of best cost) by peak penalty ($/kw²h)

| Peak penalty ($/kW²h) | Regime | MILP | DP plan | DP policy | SDP policy | Pred (smart) | Greedy |
|---|---|---|---|---|---|---|---|
| 0.5 | day-ahead | 3.62 | 6.90 | 3.49 | 3.14 | 46.08 | 230.40 |
| 0.5 | on arrival | 95.22 | 98.57 | 100.87 | 95.16 | 97.03 | 230.40 |
| 1 | day-ahead | 6.33 | 11.64 | 5.88 | 5.17 | 82.43 | 377.81 |
| 1 | on arrival | 157.72 | 158.96 | 163.76 | 154.09 | 159.83 | 377.81 |
| 1.5 | day-ahead | 6.88 | 16.28 | 8.69 | 7.46 | 105.44 | 483.96 |
| 1.5 | on arrival | 198.19 | 203.85 | 208.64 | 196.75 | 205.48 | 483.96 |

## Mean daily peak import (kW) by peak penalty ($/kw²h)

| Peak penalty ($/kW²h) | Regime | MILP | DP plan | DP policy | SDP policy | Pred (smart) | Greedy |
|---|---|---|---|---|---|---|---|
| 0.5 | day-ahead | 4.89 | 4.93 | 4.81 | 4.72 | 6.64 | 13.77 |
| 0.5 | on arrival | 7.11 | 7.05 | 7.56 | 7.51 | 7.84 | 13.77 |
| 1 | day-ahead | 4.83 | 4.91 | 4.78 | 4.74 | 6.96 | 13.77 |
| 1 | on arrival | 7.04 | 6.98 | 7.58 | 7.41 | 7.84 | 13.77 |
| 1.5 | day-ahead | 4.84 | 4.91 | 4.86 | 4.76 | 6.96 | 13.77 |
| 1.5 | on arrival | 6.96 | 6.99 | 7.58 | 7.41 | 7.84 | 13.77 |

## Import above the threshold (kWh/day) by peak penalty ($/kw²h)

| Peak penalty ($/kW²h) | Regime | MILP | DP plan | DP policy | SDP policy | Pred (smart) | Greedy |
|---|---|---|---|---|---|---|---|
| 0.5 | day-ahead | 7.41 | 8.00 | 7.85 | 7.86 | 10.73 | 13.73 |
| 0.5 | on arrival | 13.15 | 13.22 | 13.31 | 12.91 | 12.03 | 13.73 |
| 1 | day-ahead | 7.42 | 7.97 | 7.88 | 7.86 | 10.81 | 13.73 |
| 1 | on arrival | 13.24 | 13.24 | 13.27 | 12.82 | 12.03 | 13.73 |
| 1.5 | day-ahead | 7.34 | 7.96 | 7.86 | 7.85 | 10.70 | 13.73 |
| 1.5 | on arrival | 13.14 | 13.24 | 13.26 | 12.77 | 12.03 | 13.73 |

## Battery throughput (kWh/day) by peak penalty ($/kw²h)

| Peak penalty ($/kW²h) | Regime | MILP | DP plan | DP policy | SDP policy | Pred (smart) | Greedy |
|---|---|---|---|---|---|---|---|
| 0.5 | day-ahead | 7.42 | 7.42 | 7.58 | 7.62 | 6.10 | 5.48 |
| 0.5 | on arrival | 6.99 | 8.90 | 9.02 | 8.62 | 5.83 | 5.48 |
| 1 | day-ahead | 7.48 | 7.86 | 8.14 | 8.02 | 6.17 | 5.48 |
| 1 | on arrival | 7.12 | 9.38 | 9.86 | 9.14 | 5.83 | 5.48 |
| 1.5 | day-ahead | 6.78 | 8.02 | 8.50 | 8.10 | 6.10 | 5.48 |
| 1.5 | on arrival | 7.02 | 9.38 | 9.98 | 9.42 | 5.83 | 5.48 |

## Regret (% of best cost) by grid prices (import / export)

| Grid prices (import / export) | Regime | MILP | DP plan | DP policy | SDP policy | Pred (smart) | Greedy |
|---|---|---|---|---|---|---|---|
| cheap grid (0.15 / 0.10) | day-ahead | 5.06 | 10.87 | 5.20 | 4.56 | 73.53 | 366.11 |
| cheap grid (0.15 / 0.10) | on arrival | 153.42 | 172.24 | 171.96 | 165.53 | 154.85 | 366.11 |
| default (0.30 / 0.05) | day-ahead | 3.62 | 6.90 | 3.49 | 3.14 | 46.08 | 230.40 |
| default (0.30 / 0.05) | on arrival | 95.22 | 98.57 | 100.87 | 95.16 | 97.03 | 230.40 |
| expensive grid (0.45 / 0.02) | day-ahead | 2.77 | 5.00 | 2.62 | 2.41 | 33.31 | 156.67 |
| expensive grid (0.45 / 0.02) | on arrival | 69.26 | 74.12 | 74.10 | 71.83 | 70.54 | 156.67 |

## Mean daily peak import (kW) by grid prices (import / export)

| Grid prices (import / export) | Regime | MILP | DP plan | DP policy | SDP policy | Pred (smart) | Greedy |
|---|---|---|---|---|---|---|---|
| cheap grid (0.15 / 0.10) | day-ahead | 4.88 | 4.91 | 4.78 | 4.72 | 6.67 | 13.77 |
| cheap grid (0.15 / 0.10) | on arrival | 7.10 | 7.18 | 7.56 | 7.51 | 7.84 | 13.77 |
| default (0.30 / 0.05) | day-ahead | 4.89 | 4.93 | 4.81 | 4.72 | 6.64 | 13.77 |
| default (0.30 / 0.05) | on arrival | 7.11 | 7.05 | 7.56 | 7.51 | 7.84 | 13.77 |
| expensive grid (0.45 / 0.02) | day-ahead | 4.80 | 4.93 | 4.81 | 4.74 | 6.64 | 12.97 |
| expensive grid (0.45 / 0.02) | on arrival | 6.97 | 7.13 | 7.56 | 7.51 | 7.84 | 12.97 |

## Import above the threshold (kWh/day) by grid prices (import / export)

| Grid prices (import / export) | Regime | MILP | DP plan | DP policy | SDP policy | Pred (smart) | Greedy |
|---|---|---|---|---|---|---|---|
| cheap grid (0.15 / 0.10) | day-ahead | 7.32 | 8.00 | 7.86 | 7.86 | 10.68 | 13.73 |
| cheap grid (0.15 / 0.10) | on arrival | 13.39 | 14.00 | 13.93 | 13.79 | 12.03 | 13.73 |
| default (0.30 / 0.05) | day-ahead | 7.41 | 8.00 | 7.85 | 7.86 | 10.73 | 13.73 |
| default (0.30 / 0.05) | on arrival | 13.15 | 13.22 | 13.31 | 12.91 | 12.03 | 13.73 |
| expensive grid (0.45 / 0.02) | day-ahead | 7.45 | 8.01 | 7.87 | 7.86 | 10.73 | 13.61 |
| expensive grid (0.45 / 0.02) | on arrival | 13.06 | 13.40 | 13.44 | 13.22 | 12.03 | 13.61 |

## Battery throughput (kWh/day) by grid prices (import / export)

| Grid prices (import / export) | Regime | MILP | DP plan | DP policy | SDP policy | Pred (smart) | Greedy |
|---|---|---|---|---|---|---|---|
| cheap grid (0.15 / 0.10) | day-ahead | 7.36 | 7.54 | 7.62 | 7.58 | 6.10 | 5.48 |
| cheap grid (0.15 / 0.10) | on arrival | 6.87 | 9.62 | 9.38 | 9.42 | 5.83 | 5.48 |
| default (0.30 / 0.05) | day-ahead | 7.42 | 7.42 | 7.58 | 7.62 | 6.10 | 5.48 |
| default (0.30 / 0.05) | on arrival | 6.99 | 8.90 | 9.02 | 8.62 | 5.83 | 5.48 |
| expensive grid (0.45 / 0.02) | day-ahead | 8.06 | 7.50 | 7.58 | 7.66 | 6.10 | 5.48 |
| expensive grid (0.45 / 0.02) | on arrival | 7.14 | 8.78 | 8.42 | 8.74 | 5.83 | 5.48 |

## Regret (% of best cost) by peak threshold (kw)

| Peak threshold (kW) | Regime | MILP | DP plan | DP policy | SDP policy | Pred (smart) | Greedy |
|---|---|---|---|---|---|---|---|
| 3 | day-ahead | 3.62 | 6.90 | 3.49 | 3.14 | 46.08 | 230.40 |
| 3 | on arrival | 95.22 | 98.57 | 100.87 | 95.16 | 97.03 | 230.40 |
| 4 | day-ahead | 3.70 | 3.63 | 1.84 | 0.44 | 37.78 | 140.22 |
| 4 | on arrival | 69.59 | 70.60 | 74.03 | 72.31 | 79.69 | 140.22 |
| 5 | day-ahead | 2.61 | 1.64 | 2.11 | 0.16 | 11.00 | 36.38 |
| 5 | on arrival | 34.06 | 37.96 | 40.30 | 37.07 | 42.12 | 36.38 |

## Mean daily peak import (kW) by peak threshold (kw)

| Peak threshold (kW) | Regime | MILP | DP plan | DP policy | SDP policy | Pred (smart) | Greedy |
|---|---|---|---|---|---|---|---|
| 3 | day-ahead | 4.89 | 4.93 | 4.81 | 4.72 | 6.64 | 13.77 |
| 3 | on arrival | 7.11 | 7.05 | 7.56 | 7.51 | 7.84 | 13.77 |
| 4 | day-ahead | 5.16 | 5.09 | 5.04 | 4.41 | 7.08 | 11.81 |
| 4 | on arrival | 6.96 | 6.96 | 7.48 | 7.42 | 8.04 | 11.81 |
| 5 | day-ahead | 5.98 | 5.75 | 5.99 | 5.23 | 6.47 | 8.27 |
| 5 | on arrival | 6.93 | 7.10 | 7.58 | 7.43 | 7.77 | 8.27 |

## Import above the threshold (kWh/day) by peak threshold (kw)

| Peak threshold (kW) | Regime | MILP | DP plan | DP policy | SDP policy | Pred (smart) | Greedy |
|---|---|---|---|---|---|---|---|
| 3 | day-ahead | 7.41 | 8.00 | 7.85 | 7.86 | 10.73 | 13.73 |
| 3 | on arrival | 13.15 | 13.22 | 13.31 | 12.91 | 12.03 | 13.73 |
| 4 | day-ahead | 1.93 | 1.91 | 1.48 | 1.11 | 5.12 | 6.57 |
| 4 | on arrival | 6.99 | 6.83 | 7.13 | 7.17 | 6.88 | 6.57 |
| 5 | day-ahead | 0.93 | 0.71 | 0.70 | 0.20 | 1.41 | 2.17 |
| 5 | on arrival | 3.27 | 3.77 | 3.89 | 3.63 | 3.63 | 2.17 |

## Battery throughput (kWh/day) by peak threshold (kw)

| Peak threshold (kW) | Regime | MILP | DP plan | DP policy | SDP policy | Pred (smart) | Greedy |
|---|---|---|---|---|---|---|---|
| 3 | day-ahead | 7.42 | 7.42 | 7.58 | 7.62 | 6.10 | 5.48 |
| 3 | on arrival | 6.99 | 8.90 | 9.02 | 8.62 | 5.83 | 5.48 |
| 4 | day-ahead | 5.20 | 5.29 | 5.65 | 5.73 | 6.00 | 6.00 |
| 4 | on arrival | 6.30 | 7.46 | 7.70 | 7.50 | 5.67 | 6.00 |
| 5 | day-ahead | 4.49 | 3.93 | 3.93 | 3.73 | 5.88 | 6.36 |
| 5 | on arrival | 5.59 | 6.54 | 6.54 | 6.74 | 5.85 | 6.36 |
