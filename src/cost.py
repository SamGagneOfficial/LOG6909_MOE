
class CostFunction:
    def __init__(
        self,
        battery_coeff: float = 0.0,         # [$/kWh] of battery throughput
        export_coeff: float = 0.0,          # [$/kWh] revenue for exported energy
        import_coeff: float = 0.0,          # [$/kWh] price of imported energy
        peak_coeff: float = 0.0,            # [$/(kW^2 h)] on the squared import above peak_threshold
        peak_threshold: float = 0.0,        # [kW] import level above which the peak cost applies
        task_delay_coeff: float = 0.0       # [$/h] per task, per hour it ends past its deadline
    ):
        self.battery_coeff = battery_coeff
        self.export_coeff = export_coeff
        self.import_coeff = import_coeff
        self.task_delay_coeff = task_delay_coeff
        self.peak_coeff = peak_coeff
        self.peak_threshold = peak_threshold

    def excess_power(self, import_kwh: float, dt: float):
        # Import above the threshold during one step [kW]
        return max(0.0, import_kwh / dt - self.peak_threshold)

    def peak_cost(self, import_kwh: float, dt: float):
        # Squared, so tall spikes cost much more than a long, low overshoot
        return self.peak_coeff * self.excess_power(import_kwh, dt) ** 2 * dt

    def energy_cost(
        self,
        battery_throughput_kwh: float = 0.0,
        import_kwh: float = 0.0,
        export_kwh: float = 0.0
    ):
        # Exports are a revenue, hence a negative cost
        return (
            self.import_coeff * import_kwh
            - self.export_coeff * export_kwh
            + self.battery_coeff * battery_throughput_kwh
        )

    def evaluate(
        self,
        battery_throughput_kwh: float = 0.0,
        import_kwh: float = 0.0,
        export_kwh: float = 0.0,
        squared_excess: float = 0.0,        # [kW^2 h], sum of excess_power^2 * dt
        late_hours: float = 0.0
    ):
        grid_cost = self.import_coeff * import_kwh - self.export_coeff * export_kwh

        battery_cost = self.battery_coeff * battery_throughput_kwh

        peak_cost = self.peak_coeff * squared_excess

        task_cost = self.task_delay_coeff * late_hours

        return {
            "grid_cost": grid_cost,
            "battery_cost": battery_cost,
            "peak_cost": peak_cost,
            "task_cost": task_cost,
            "total_cost": (
                grid_cost
                + battery_cost
                + peak_cost
                + task_cost
            ),
        }
