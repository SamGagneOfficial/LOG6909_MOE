class SimpleEMS:

    def dispatch(self, pv_power, factory_demand, battery):

        if pv_power >= factory_demand:
            excess = pv_power - factory_demand
            battery.charge(excess, 1)
            return factory_demand

        else:
            deficit = factory_demand - pv_power
            battery_power = battery.discharge(deficit, 1)

            return pv_power + battery_power