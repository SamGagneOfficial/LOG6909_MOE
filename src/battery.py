class Battery:
    def __init__(
        self,
        capacity,                   # Internal stored energy, kWh
        voltage,                    # Volts
        max_current,                # Amperes
        cur_charge=0.5,             # Initial SoC
        efficiency=0.95,            # Represents transfer loss
        max_charge=0.8,             # Maximum SoC to minimize aging
        max_discharge=0.2,          # Minimum SoC to minimize aging
        lifetime_throughput=None,   # Lifetime throughput, kWh
        replacement_cost=0.0        # Currency units, amount necessary for replacement/maintenance
    ):
        if capacity <= 0:
            raise ValueError("Capacity must be positive.")
        if voltage <= 0 or max_current <= 0:
            raise ValueError("Voltage and current limit must be positive.")
        if not 0 < efficiency <= 1:
            raise ValueError("Efficiency must be in (0, 1].")
        if not 0 <= max_discharge <= cur_charge <= max_charge <= 1:
            raise ValueError("Invalid state-of-charge limits.")
        if lifetime_throughput is not None and lifetime_throughput <= 0:
            raise ValueError("Lifetime throughput must be positive.")

        self.capacity = capacity
        self._voltage = voltage
        self._max_current = max_current
        self.efficiency = efficiency

        self.max_charge = max_charge
        self.max_discharge = max_discharge
        self._energy = capacity * cur_charge

        self.lifetime_throughput = lifetime_throughput
        self.replacement_cost = replacement_cost

        self.throughput = 0.0
        self.age = 0.0  # Fraction of lifetime consumed

    @property
    def voltage(self):
        return self._voltage

    @property
    def max_current(self):
        return self._max_current

    @property
    def energy(self):
        return self._energy

    @property
    def soc(self):
        return self.energy / self.capacity

    @property
    def min_energy(self):
        return self.capacity * self.max_discharge

    @property
    def max_energy(self):
        return self.capacity * self.max_charge

    @property
    def isFull(self):
        return self.energy >= self.max_energy

    @property
    def isEmpty(self):
        return self.energy <= self.min_energy

    @property
    def max_power(self):
        # [kW], from V * A = W
        return self._voltage * self._max_current / 1000

    @property
    def degradation_cost_per_kwh(self):
        if self.lifetime_throughput is None:
            return 0.0
        return self.replacement_cost / self.lifetime_throughput

    def charge(self, power, dt, toApply : bool = False):
        # Power in kW; dt in hours.
        power = max(power, 0.0)

        # Electrical energy supplied at the terminals, limited by the max current.
        input_energy = min(power, self.max_power) * dt

        # Internal energy stored, accounting for efficiency.
        stored_energy = input_energy * self.efficiency

        # Respect the battery's maximum SoC.
        room = self.max_energy - self._energy
        actual_stored = min(stored_energy, max(0.0, room))

        # Input energy corresponding to the accepted storage.
        accepted_input = actual_stored / self.efficiency

        # Energy not accepted by the battery, including what exceeds the max current.
        rejected_energy = power * dt - accepted_input

        if toApply:
            self._energy += actual_stored
            self._record_throughput(accepted_input)

        return accepted_input, rejected_energy

    
    def discharge(self, power, dt, toApply : bool = False):
        # Power in kW; dt in hours.
        power = max(power, 0.0)

        # Requested energy delivered to the load.
        requested_output = power * dt

        # Internal energy required to deliver that output, limited by the max current.
        required_stored = min(power, self.max_power) * dt / self.efficiency

        # Energy available above the minimum SoC.
        available_stored = max(0.0, self._energy - self.min_energy)

        actual_stored = min(required_stored, available_stored)

        # Actual electrical energy delivered.
        actual_output = actual_stored * self.efficiency

        # Demand the battery could not satisfy.
        unmet_demand = requested_output - actual_output

        if toApply:
            self._energy -= actual_stored
            self._record_throughput(actual_output)

        return actual_output, -unmet_demand


    def _record_throughput(self, energy):
        self.throughput += energy

        if self.lifetime_throughput is not None:
            self.age = self.throughput / self.lifetime_throughput

    @property
    def accumulated_degradation_cost(self):
        return self.age * self.replacement_cost
