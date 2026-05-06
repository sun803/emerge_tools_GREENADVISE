import numpy as np

from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QProgressBar, QPushButton, QMessageBox, QHBoxLayout, QSizePolicy, QSpacerItem
from PyQt5.QtCore import Qt
import pyomo.environ as pye
from cbc_path_resolver import get_cbc_executable_path
import traceback


class OptimizationInputPreparator:
    unmet_penalty = 10000

    def __init__(self, selected_inputs):
        self.inputs = selected_inputs
        self.required_length = 8760
        self._check_required_inputs()
        self._initialize_defaults()
        self._unpack_inputs()

    def get_scenarios(self):
        stoch = self.inputs.get("stochastic", {})
        if not stoch:
            # nema stohastike -> 1 scenarij iz determinističkih inputa
            scenario = {}
            for k in ["Price Data", "PV Generation", "Wind Generation",
                      "Solar Collector Generation", "Electricity Demand",
                      "Sell Price", "Thermal Price"]:
                if k in self.inputs:
                    scenario[k] = self.inputs[k]
            if "Thermal Demand" in self.inputs:
                td = self.inputs["Thermal Demand"]
                scenario["Thermal Demand"] = {
                    "heating": td.get("heating"),
                    "cooling": td.get("cooling"),
                }
            return [scenario], [1.0]

        # Odredi broj scenarija iz prve liste koju nađemo (ili iz pod-liste u dictu)
        n_scenarios = None
        for key, val in stoch.items():
            if isinstance(val, list):
                n_scenarios = len(val)
                break
            elif isinstance(val, dict):
                for subk, subv in val.items():
                    if isinstance(subv, list):
                        n_scenarios = len(subv)
                        break
            if n_scenarios is not None:
                break
        if n_scenarios is None:
            raise ValueError("Invalid 'stochastic' structure: no list-of-scenarios found.")

        scenarios = []
        for s in range(n_scenarios):
            sc = {}
            for key, val in stoch.items():
                if isinstance(val, list):
                    sc[key] = val[s]
                elif isinstance(val, dict):
                    sub = {}
                    for subk, subv in val.items():
                        if isinstance(subv, list):
                            sub[subk] = subv[s]
                        else:
                            sub[subk] = subv
                    sc[key] = sub
                else:
                    sc[key] = val

            # deterministički fallback za ključeve koji nisu u 'stochastic'
            for k in ["Price Data", "PV Generation", "Wind Generation",
                      "Solar Collector Generation", "Electricity Demand",
                      "Sell Price", "Thermal Price"]:
                if k not in sc and k in self.inputs:
                    sc[k] = self.inputs[k]
            if "Thermal Demand" not in sc and "Thermal Demand" in self.inputs:
                td = self.inputs["Thermal Demand"]
                sc["Thermal Demand"] = {
                    "heating": td.get("heating"),
                    "cooling": td.get("cooling"),
                }

            scenarios.append(sc)

        probs = [1.0 / n_scenarios] * n_scenarios
        return scenarios, probs

    def _check_required_inputs(self):
        if "Price Data" not in self.inputs:
            raise ValueError("Missing 'Price Data' input.")

        if not any(k in self.inputs for k in ["Electricity Demand", "Thermal Demand", "Thermal + Electricity Demand"]):
            raise ValueError("At least one type of demand is required.")

    def _initialize_defaults(self):
        self.pv_generation = np.zeros(self.required_length)
        self.wind_generation = np.zeros(self.required_length)
        self.pv_capacity = 0
        self.wind_capacity = 0

        self.battery_capacity = self.battery_efficiency = self.battery_rated_power = None
        self.buffer_capacity = self.buffer_rated_power = self.buffer_retention = None

        self.heat_pump_cop = 1
        self.heat_pump_eer = 1
        self.heat_pump_heating_capacity = self.heat_pump_cooling_capacity = None

        self.heating_demand = np.zeros(self.required_length)
        self.cooling_demand = np.zeros(self.required_length)
        self.electricity_demand = np.zeros(self.required_length)

        self.buy_price = np.zeros(self.required_length)
        self.sell_price = np.zeros(self.required_length)
        self.thermal_price = np.zeros(self.required_length)

        self.grid_limit = float('inf')
        self.solar_collector_generation = np.zeros(self.required_length)

        # NOVO: buyback faktor (ako je konstantan)
        self.buyback_factor = None

    def _to_float_array(self, val):
        arr = np.array(val, dtype=float)
        if arr.shape[0] != self.required_length:
            raise ValueError(f"Expected array of length {self.required_length}, got {arr.shape[0]}")
        return arr

    def _unpack_inputs(self):
        try:
           self.grid_limit = float(self.inputs["Grid Power Limit"])
        except ValueError:
           raise ValueError(f"Invalid grid power limit: {self.grid_limit}")

        price_data = self.inputs["Price Data"]
        self.buy_price = self._to_float_array(price_data)

        price_inputs = self.inputs.get("Price Data Inputs", {})
        buyback_str = price_inputs.get("buyback")
        emissions = self.inputs.get("CO₂ Emissions", {})
        thermal_emission = emissions.get("Thermal Emission Inputs", {})

        if "Thermal Demand" in self.inputs:
            fuel_price_raw = thermal_emission.get("fuel_price", 0)
            try:
                thermal_price = float(fuel_price_raw)
            except (ValueError, TypeError):
                thermal_price = 0.0
            self.thermal_price = np.ones(self.required_length) * thermal_price
        else:
            self.thermal_price = np.zeros(self.required_length)

        if buyback_str is not None:
            try:
                self.buyback_factor = float(buyback_str)
                self.sell_price = self.buy_price * self.buyback_factor
            except (ValueError, TypeError):
                raise ValueError(f"Invalid buyback factor: {buyback_str}")
        # ako nema buyback-a, sell_price ostaje što jest (npr. 0) ili ga daješ kroz scenarije

        skip_thermal = "Thermal + Electricity Demand" in self.inputs

        if skip_thermal:
            self.electricity_demand = self._to_float_array(self.inputs["Thermal + Electricity Demand"])
        else:
            td = self.inputs.get("Thermal Demand", {})
            if "heating" in td:
                self.heating_demand = self._to_float_array(td["heating"])
            if "cooling" in td:
                self.cooling_demand = self._to_float_array(td["cooling"])

            if "Electricity Demand" in self.inputs:
                self.electricity_demand = self._to_float_array(self.inputs["Electricity Demand"])

        if "PV Generation" in self.inputs:
            self.pv_generation = self._to_float_array(self.inputs["PV Generation"])
            self.pv_capacity = self.pv_generation.max()

        if "Wind Generation" in self.inputs:
            self.wind_generation = self._to_float_array(self.inputs["Wind Generation"])
            self.wind_capacity = self.wind_generation.max()

        if "Solar Collector Generation" in self.inputs:
            self.solar_collector_generation = self._to_float_array(self.inputs["Solar Collector Generation"])

        if "Battery Inputs" in self.inputs:
            b = self.inputs["Battery Inputs"]
            self.battery_capacity = float(b.get("capacity", 0))
            self.battery_efficiency = float(b.get("efficiency", 100)) / 100.0
            self.battery_rated_power = float(b.get("rated_power", 0))

        if not skip_thermal:
            if "Buffer Tank Inputs" in self.inputs:
                buf = self.inputs["Buffer Tank Inputs"]
                self.buffer_capacity = float(buf.get("capacity", 0))
                self.buffer_rated_power = float(buf.get("rated power", 0))
                self.buffer_retention = float(buf.get("retention factor", 100)) / 100.0

            if "Heat Pump Inputs" in self.inputs:
                hp = self.inputs["Heat Pump Inputs"]
                self.heat_pump_cop = float(hp.get("cop", 1))
                self.heat_pump_eer = float(hp.get("eer", 1))
                self.heat_pump_heating_capacity = float(hp.get("heating_capacity", 0))
                self.heat_pump_cooling_capacity = float(hp.get("cooling_capacity", 0))


    def create_model_variables(self, model, preparator):
        import pyomo.environ as pye
    
        scenarios, probs = self.get_scenarios()
        S = range(len(scenarios))
        T = range(1, 8761)
    
        model = pye.ConcreteModel()
        model.T = pye.Set(initialize=T, ordered=True)
        model.S = pye.Set(initialize=S, ordered=True)
    
        # PV
        if preparator.pv_generation.any():
            model.pv_to_load = pye.Var(model.T, model.S, domain=pye.NonNegativeReals)
            model.pv_to_grid = pye.Var(model.T, model.S, domain=pye.NonNegativeReals)
            if preparator.battery_capacity:
                model.pv_to_batt = pye.Var(model.T, model.S, domain=pye.NonNegativeReals)
            if preparator.heat_pump_heating_capacity:
                model.pv_to_hp_heat = pye.Var(model.T, model.S, domain=pye.NonNegativeReals)
            if preparator.heat_pump_cooling_capacity:
                model.pv_to_hp_cool = pye.Var(model.T, model.S, domain=pye.NonNegativeReals)
            if preparator.electricity_demand.any():
                model.pv_lost = pye.Var(model.T, model.S, domain=pye.NonNegativeReals)
    
        # WIND
        if preparator.wind_generation.any():
            model.wind_to_load = pye.Var(model.T, model.S, domain=pye.NonNegativeReals)
            model.wind_to_grid = pye.Var(model.T, model.S, domain=pye.NonNegativeReals)
            if preparator.battery_capacity:
                model.wind_to_batt = pye.Var(model.T, model.S, domain=pye.NonNegativeReals)
            if preparator.heat_pump_heating_capacity:
                model.wind_to_hp_heat = pye.Var(model.T, model.S, domain=pye.NonNegativeReals)
            if preparator.heat_pump_cooling_capacity:
                model.wind_to_hp_cool = pye.Var(model.T, model.S, domain=pye.NonNegativeReals)
            if preparator.electricity_demand.any():
                model.wind_lost = pye.Var(model.T, model.S, domain=pye.NonNegativeReals)
    
        # BATT
        if preparator.battery_capacity:
            if preparator.heat_pump_heating_capacity:
                model.batt_to_hp_heat = pye.Var(model.T, model.S, domain=pye.NonNegativeReals)
            if preparator.heat_pump_cooling_capacity:
                model.batt_to_hp_cool = pye.Var(model.T, model.S, domain=pye.NonNegativeReals)
    
            model.grid_to_batt = pye.Var(model.T, model.S, domain=pye.NonNegativeReals)
            model.batt_to_load = pye.Var(model.T, model.S, domain=pye.NonNegativeReals)
            model.batt_to_grid = pye.Var(model.T, model.S, domain=pye.NonNegativeReals)
            model.charge = pye.Var(model.T, model.S, domain=pye.NonNegativeReals)
            model.discharge = pye.Var(model.T, model.S, domain=pye.NonNegativeReals)
            model.batt_soe = pye.Var(range(0, 8761), model.S, domain=pye.NonNegativeReals,
                                     bounds=(0, preparator.battery_capacity))
            model.x = pye.Var(model.T, model.S, bounds=(0, 1))
            for s in S:
                model.batt_soe[0, s].fix(0)
    
        # GRID
        # (samo potrošnja na load + unmet; NE definiramo grid_to_hp_* ovdje!)
        if preparator.electricity_demand.any():
            model.grid_to_load = pye.Var(model.T, model.S, domain=pye.NonNegativeReals)
            model.unmet_electricity_demand = pye.Var(model.T, model.S, domain=pye.NonNegativeReals)
    
        # THERMAL UNMET
        if preparator.heating_demand.any() and preparator.cooling_demand.any():
            model.unmet_heating_demand = pye.Var(model.T, model.S, domain=pye.NonNegativeReals)
            model.unmet_cooling_demand = pye.Var(model.T, model.S, domain=pye.NonNegativeReals)
        elif preparator.heating_demand.any():
            model.unmet_heating_demand = pye.Var(model.T, model.S, domain=pye.NonNegativeReals)
        else:
            model.unmet_cooling_demand = pye.Var(model.T, model.S, domain=pye.NonNegativeReals)
    
        # HP
        if preparator.heat_pump_heating_capacity or preparator.heat_pump_cooling_capacity:
            if preparator.heat_pump_heating_capacity:
                model.electricity_to_hp_heat = pye.Var(model.T, model.S, domain=pye.NonNegativeReals)
                model.hp_heat_to_load = pye.Var(
                    model.T, model.S, domain=pye.NonNegativeReals,
                    bounds=(0, preparator.heat_pump_heating_capacity)
                )
                # Moved here: grid_to_hp_heat uvijek postoji kad postoji HP heating
                model.grid_to_hp_heat = pye.Var(model.T, model.S, domain=pye.NonNegativeReals)
    
            if preparator.heat_pump_cooling_capacity:
                model.electricity_to_hp_cool = pye.Var(model.T, model.S, domain=pye.NonNegativeReals)
                model.hp_cool_to_load = pye.Var(
                    model.T, model.S, domain=pye.NonNegativeReals,
                    bounds=(0, preparator.heat_pump_cooling_capacity)
                )
                # Moved here: grid_to_hp_cool uvijek postoji kad postoji HP cooling
                model.grid_to_hp_cool = pye.Var(model.T, model.S, domain=pye.NonNegativeReals)
    
            if preparator.buffer_capacity:
                model.hp_to_buffer = pye.Var(model.T, model.S, domain=pye.NonNegativeReals)
    
        # SC
        if preparator.solar_collector_generation.any():
            model.solar_to_buffer = pye.Var(model.T, model.S, domain=pye.NonNegativeReals)
            model.solar_curtail = pye.Var(model.T, model.S, domain=pye.NonNegativeReals)
    
        # BT
        if preparator.buffer_capacity:
            model.buffer_to_load = pye.Var(model.T, model.S, domain=pye.NonNegativeReals)
            model.buffer_charge = pye.Var(model.T, model.S, domain=pye.NonNegativeReals)
            model.buffer_discharge = pye.Var(model.T, model.S, domain=pye.NonNegativeReals)
            model.buffer_soe = pye.Var(range(0, 8761), model.S, domain=pye.NonNegativeReals,
                                       bounds=(0, preparator.buffer_capacity))
            model.buffer_x = pye.Var(model.T, model.S, bounds=(0, 1))
            for s in S:
                model.buffer_soe[0, s].fix(0)
    
        return model


    def add_constraints_and_objective(self, model):
        import pyomo.environ as pye
        T = model.T
        S = model.S
        scenarios, probs = self.get_scenarios()

        # GRID POWER LIMIT
        if (hasattr(model, "grid_to_load") 
            or hasattr(model, "grid_to_batt")
            or hasattr(model, "grid_to_hp")
            or hasattr(model, "pv_to_grid") 
            or hasattr(model, "wind_to_grid") 
            or hasattr(model, "batt_to_grid")):

            def grid_power_limit(m, t, s):
                limit = 0
                if hasattr(m, "grid_to_load"):      limit += m.grid_to_load[t, s]
                if hasattr(m, "grid_to_batt"):      limit += m.grid_to_batt[t, s]
                if hasattr(m, "grid_to_hp_heat"):   limit += m.grid_to_hp_heat[t, s]
                if hasattr(m, "grid_to_hp_cool"):   limit += m.grid_to_hp_cool[t, s]
                if hasattr(m, "pv_to_grid"):        limit += m.pv_to_grid[t, s]
                if hasattr(m, "wind_to_grid"):      limit += m.wind_to_grid[t, s]
                if hasattr(m, "batt_to_grid"):      limit += m.batt_to_grid[t, s]
                return limit <= self.grid_limit
            model.grid_power_limit = pye.Constraint(T, S, rule=grid_power_limit)

        # POWER BALLANCE
        if (hasattr(model, "pv_to_load") 
            or hasattr(model, "batt_to_load") 
            or hasattr(model, "grid_to_load") 
            or hasattr(model, "wind_to_load")):

            def power_balance(m, t, s):
                scenario = scenarios[s]
                supply = 0
                if hasattr(m, "pv_to_load"):
                    supply += m.pv_to_load[t, s]
                if hasattr(m, "batt_to_load"):
                    supply += m.batt_to_load[t, s]
                if hasattr(m, "grid_to_load"):
                    supply += m.grid_to_load[t, s]
                if hasattr(m, "wind_to_load"):
                    supply += m.wind_to_load[t, s]
                if hasattr(m, "unmet_electricity_demand"):
                    supply += m.unmet_electricity_demand[t, s]
                return supply == scenario["Electricity Demand"][t - 1]
            model.power_balance = pye.Constraint(T, S, rule=power_balance)

        # PV ALLOCATION
        if hasattr(model, "pv_to_load"):
            def pv_allocation(m, t, s):
                scenario = scenarios[s]
                total = m.pv_to_load[t, s]
                if hasattr(m, "pv_to_batt"): total += m.pv_to_batt[t, s]
                if hasattr(m, "pv_to_grid"): total += m.pv_to_grid[t, s]
                if hasattr(m, "pv_to_hp_heat"): total += m.pv_to_hp_heat[t, s]
                if hasattr(m, "pv_to_hp_cool"): total += m.pv_to_hp_cool[t, s]
                if hasattr(m, "pv_lost"): total += m.pv_lost[t, s]
                return total == scenario.get("PV Generation", np.zeros(self.required_length))[t - 1]
            model.pv_allocation = pye.Constraint(T, S, rule=pv_allocation)

        # WIND ALLOCATION
        if hasattr(model, "wind_to_load"):
            def wind_allocation(m, t, s):
                scenario = scenarios[s]
                total = m.wind_to_load[t, s]
                if hasattr(m, "wind_to_batt"): total += m.wind_to_batt[t, s]
                if hasattr(m, "wind_to_grid"): total += m.wind_to_grid[t, s]
                if hasattr(m, "wind_to_hp_heat"): total += m.wind_to_hp_heat[t, s]
                if hasattr(m, "wind_to_hp_cool"): total += m.wind_to_hp_cool[t, s]
                if hasattr(m, "wind_lost"): total += m.wind_lost[t, s]
                return total == scenario.get("Wind Generation", np.zeros(self.required_length))[t - 1]
            model.wind_allocation = pye.Constraint(T, S, rule=wind_allocation)

        # BATT CHARGE LINK
        if hasattr(model, "charge"):
            def battery_charge_link(m, t, s):
                total = 0
                if hasattr(m, "pv_to_batt"): total += m.pv_to_batt[t, s]
                if hasattr(m, "grid_to_batt"): total += m.grid_to_batt[t, s]
                if hasattr(m, "wind_to_batt"): total += m.wind_to_batt[t, s]
                return m.charge[t, s] == total
            model.charge_link = pye.Constraint(T, S, rule=battery_charge_link)

        # BATT DISCHARGE LINK
        if hasattr(model, "discharge"):
            def battery_discharge_link(m, t, s):
                total = 0
                if hasattr(m, "batt_to_load"): total += m.batt_to_load[t, s]
                if hasattr(m, "batt_to_grid"): total += m.batt_to_grid[t, s]
                if hasattr(m, "batt_to_hp_heat"): total += m.batt_to_hp_heat[t, s]
                if hasattr(m, "batt_to_hp_cool"): total += m.batt_to_hp_cool[t, s]
                return m.discharge[t, s] == total
            model.discharge_link = pye.Constraint(T, S, rule=battery_discharge_link)

        # BATT SOE BALLANCE
        if hasattr(model, "batt_soe"):
            def soe_balance(m, t, s):
                return m.batt_soe[t, s] == m.batt_soe[t - 1, s] + m.charge[t, s] * self.battery_efficiency - m.discharge[t, s] / self.battery_efficiency
            model.soe_balance = pye.Constraint(T, S, rule=soe_balance)

        if hasattr(model, "x"):
            model.charge_limit = pye.Constraint(T, S, rule=lambda m, t, s: m.charge[t, s] <= self.battery_rated_power * m.x[t, s])
            model.discharge_limit = pye.Constraint(T, S, rule=lambda m, t, s: m.discharge[t, s] <= self.battery_rated_power * (1 - m.x[t, s]))

        # HP ALLOCATION
        if hasattr(model, "electricity_to_hp_heat"):
            def heat_output_rule(m, t, s):
                return m.hp_heat_to_load[t, s] == self.heat_pump_cop * m.electricity_to_hp_heat[t, s]
            model.heat_output_eq_heat = pye.Constraint(T, S, rule=heat_output_rule)

        if hasattr(model, "electricity_to_hp_cool"):
            def cool_output_rule(m, t, s):
                return m.hp_cool_to_load[t, s] == self.heat_pump_eer * m.electricity_to_hp_cool[t, s]
            model.heat_output_eq_cool = pye.Constraint(T, S, rule=cool_output_rule)

        # HEATING DEMAND BALLANCE
        if np.sum(self.heating_demand) > 0:
            def heat_balance_rule(m, t, s):
                scenario = scenarios[s]
                hp_output = m.hp_heat_to_load[t, s] if hasattr(m, "hp_heat_to_load") else 0
                buffer_out = m.buffer_to_load[t, s] if hasattr(m, "buffer_to_load") else 0
                buffer_in = m.hp_to_buffer[t, s] if hasattr(m, "hp_to_buffer") else 0
                unmet = m.unmet_heating_demand[t, s] if hasattr(m, "unmet_heating_demand") else 0
                demand = scenario.get("Thermal Demand", {}).get("heating", np.zeros(self.required_length))[t - 1]
                return hp_output + buffer_out + unmet == demand + buffer_in
            model.heat_balance = pye.Constraint(T, S, rule=heat_balance_rule)

        # COOLING DEMAND BALLANCE
        if np.sum(self.cooling_demand) > 0:
            def cool_balance_rule(m, t, s):
                scenario = scenarios[s]
                hp_output = m.hp_cool_to_load[t, s] if hasattr(m, "hp_cool_to_load") else 0
                unmet = m.unmet_cooling_demand[t, s] if hasattr(m, "unmet_cooling_demand") else 0
                demand = scenario.get("Thermal Demand", {}).get("cooling", np.zeros(self.required_length))[t - 1]
                return hp_output + unmet == demand
            model.cool_balance = pye.Constraint(T, S, rule=cool_balance_rule)

        # SC ALLOCATION
        if hasattr(model, "solar_to_buffer"):
            def solar_rule(m, t, s):
                scenario = scenarios[s]
                generation = scenario.get("Solar Collector Generation", np.zeros(self.required_length))[t - 1]
                return generation == m.solar_to_buffer[t, s] + m.solar_curtail[t, s]
            model.solar_allocation = pye.Constraint(T, S, rule=solar_rule)

        # BUFFER TANK SOE BALLANCE
        if hasattr(model, "buffer_soe"):
            def heat_soe_dynamics_rule(m, t, s):
                hp_buf = m.hp_to_buffer[t, s] if hasattr(m, "hp_to_buffer") else 0
                solar_buf = m.solar_to_buffer[t, s] if hasattr(m, "solar_to_buffer") else 0
                return m.buffer_soe[t, s] == self.buffer_retention * m.buffer_soe[t - 1, s] + hp_buf + solar_buf - m.buffer_to_load[t, s]
            model.heat_soe_balance = pye.Constraint(T, S, rule=heat_soe_dynamics_rule)

        # BT CHARGE LIMIT
        if hasattr(model, "hp_to_buffer") or hasattr(model, "solar_to_buffer"):
            def heat_charge_limit_rule(m, t, s):
                hp = m.hp_to_buffer[t, s] if hasattr(m, "hp_to_buffer") else 0
                sol = m.solar_to_buffer[t, s] if hasattr(m, "solar_to_buffer") else 0
                curtail = m.solar_curtail[t, s] if hasattr(m, "solar_curtail") else 0
                return hp + (sol - curtail) <= self.buffer_rated_power
            model.heat_ch_limit = pye.Constraint(T, S, rule=heat_charge_limit_rule)

        # BT DISCHARGE LIMIT
        if hasattr(model, "buffer_to_load"):
            def heat_discharge_limit_rule(m, t, s):
                return m.buffer_to_load[t, s] <= self.buffer_rated_power
            model.heat_dch_limit = pye.Constraint(T, S, rule=heat_discharge_limit_rule)

        # HP ELECTRICAL BOUNDS
        if hasattr(model, "electricity_to_hp_heat"):
            def elec_bound_rule_heat(m, t, s):
                return m.electricity_to_hp_heat[t, s] <= self.heat_pump_heating_capacity / self.heat_pump_cop
            model.elec_bound_heat = pye.Constraint(T, S, rule=elec_bound_rule_heat)

        if hasattr(model, "electricity_to_hp_cool"):
            def elec_bound_rule_cool(m, t, s):
                return m.electricity_to_hp_cool[t, s] <= self.heat_pump_cooling_capacity / self.heat_pump_eer
            model.elec_bound_cool = pye.Constraint(T, S, rule=elec_bound_rule_cool)

        # HP HEATING ELECTRICITY BOUND
        if (hasattr(model, "electricity_to_hp_heat") and
            (hasattr(model, "grid_to_hp_heat") or hasattr(model, "pv_to_hp_heat")
             or hasattr(model, "wind_to_hp_heat") or hasattr(model, "batt_to_hp_heat"))):
        
            def hp_heat_power_allocation_rule(m, t, s):
                total = 0
                if hasattr(m, "grid_to_hp_heat"): total += m.grid_to_hp_heat[t, s]
                if hasattr(m, "pv_to_hp_heat"):   total += m.pv_to_hp_heat[t, s]
                if hasattr(m, "wind_to_hp_heat"): total += m.wind_to_hp_heat[t, s]
                if hasattr(m, "batt_to_hp_heat"): total += m.batt_to_hp_heat[t, s]
                return m.electricity_to_hp_heat[t, s] == total
            model.hp_heat_allocation = pye.Constraint(T, S, rule=hp_heat_power_allocation_rule)

        # HP COOLING ELECTRICITY BOUND
        if (hasattr(model, "electricity_to_hp_cool") and
            (hasattr(model, "grid_to_hp_cool") or hasattr(model, "pv_to_hp_cool")
             or hasattr(model, "wind_to_hp_cool") or hasattr(model, "batt_to_hp_cool"))):

            def hp_cool_power_allocation_rule(m, t, s):
                total = 0
                if hasattr(m, "grid_to_hp_cool"): total += m.grid_to_hp_cool[t, s]
                if hasattr(m, "pv_to_hp_cool"):   total += m.pv_to_hp_cool[t, s]
                if hasattr(m, "wind_to_hp_cool"): total += m.wind_to_hp_cool[t, s]
                if hasattr(m, "batt_to_hp_cool"): total += m.batt_to_hp_cool[t, s]
                return m.electricity_to_hp_cool[t, s] == total
            model.hp_cool_allocation = pye.Constraint(T, S, rule=hp_cool_power_allocation_rule)

        # Update Objective
        def objective_rule(m):
            total_profit = 0
            scenarios, probs = self.get_scenarios()

            for s in m.S:
                scenario = scenarios[s]
                profit = 0

                for t in m.T:
                    buy = scenario["Price Data"][t - 1]
                    sell = self.sell_price[t - 1]  # moze poslije stohastika
                    thermal_price = self.thermal_price[t - 1]  # isto scenario-based

                    # REVENUE
                    if hasattr(m, "pv_to_grid"):
                        profit += m.pv_to_grid[t, s] * sell
                    if hasattr(m, "batt_to_grid"):
                        profit += m.batt_to_grid[t, s] * sell
                    if hasattr(m, "wind_to_grid"):
                        profit += m.wind_to_grid[t, s] * sell

                    if hasattr(m, "pv_to_load"):        profit += m.pv_to_load[t, s] * buy
                    if hasattr(m, "pv_to_hp_heat"):     profit += m.pv_to_hp_heat[t, s] * buy
                    if hasattr(m, "pv_to_hp_cool"):     profit += m.pv_to_hp_cool[t, s] * buy
                    if hasattr(m, "wind_to_load"):      profit += m.wind_to_load[t, s] * buy
                    if hasattr(m, "wind_to_hp_heat"):   profit += m.wind_to_hp_heat[t, s] * buy
                    if hasattr(m, "wind_to_hp_cool"):   profit += m.wind_to_hp_cool[t, s] * buy
                    if hasattr(m, "batt_to_load"):      profit += m.batt_to_load[t, s] * buy
                    if hasattr(m, "batt_to_hp_heat"):   profit += m.batt_to_hp_heat[t, s] * buy
                    if hasattr(m, "batt_to_hp_cool"):   profit += m.batt_to_hp_cool[t, s] * buy
                    if hasattr(m, "solar_to_buffer"):   profit += m.solar_to_buffer[t, s] * thermal_price

                    # COST
                    if hasattr(m, "grid_to_load"):      profit -= m.grid_to_load[t, s] * buy
                    if hasattr(m, "grid_to_batt"):      profit -= m.grid_to_batt[t, s] * buy
                    if hasattr(m, "grid_to_hp_heat"):   profit -= m.grid_to_hp_heat[t, s] * buy
                    if hasattr(m, "grid_to_hp_cool"):   profit -= m.grid_to_hp_cool[t, s] * buy

                    # UNMET PENALITIES
                    if hasattr(m, "unmet_electricity_demand"):
                        profit -= self.unmet_penalty * m.unmet_electricity_demand[t, s]
                    if hasattr(m, "unmet_heating_demand"):
                        profit -= self.unmet_penalty * m.unmet_heating_demand[t, s]
                    if hasattr(m, "unmet_cooling_demand"):
                        profit -= self.unmet_penalty * m.unmet_cooling_demand[t, s]
                    if hasattr(m, "pv_lost"):
                        profit -= self.unmet_penalty * m.pv_lost[t, s]
                    if hasattr(m, "wind_lost"):
                        profit -= self.unmet_penalty * m.wind_lost[t, s]

                total_profit += probs[s] * profit

            return total_profit

        model.obj = pye.Objective(rule=objective_rule, sense=pye.maximize)
        return model

    def extract_results(self, model):
        import pyomo.environ as pye
        results = {}
    
        T_range = range(1, 8761)
        scenarios, probs = self.get_scenarios()
        S_range = range(len(scenarios))
    
        # helperi za scenarijski prosjek
        def _scen_avg_simple(key):
            try:
                arrays = []
                for s, sc in enumerate(scenarios):
                    if key not in sc:
                        return None
                    arr = np.array(sc[key], dtype=float)
                    if arr.shape[0] != self.required_length:
                        return None
                    arrays.append(arr * probs[s])
                return sum(arrays)
            except Exception:
                return None
    
        def _scen_avg_thermal(subkey):
            try:
                arrays = []
                found_any = False
                for s, sc in enumerate(scenarios):
                    td = sc.get("Thermal Demand")
                    if not isinstance(td, dict) or subkey not in td:
                        # dopuštamo scenarije bez tog subkeya, ali tada nema doprinosa
                        continue
                    arr = np.array(td[subkey], dtype=float)
                    if arr.shape[0] != self.required_length:
                        return None
                    arrays.append(arr * probs[s])
                    found_any = True
                return sum(arrays) if found_any else None
            except Exception:
                return None
    
        def _scen_avg_electricity():
            out = _scen_avg_simple("Electricity Demand")
            if out is not None:
                return out

    
        # Pyomo varijable -> očekivanja
        def get_series(var):
            if not hasattr(model, var):
                return None
            var_obj = getattr(model, var)
            try:
                return np.array([
                    sum(pye.value(var_obj[t, s]) * probs[s] for s in S_range)
                    for t in T_range
                ])
            except:
                return None
    
        def arr(name):
            a = results.get(name)
            return a if isinstance(a, np.ndarray) else np.zeros(self.required_length)
    
        # Ulazne serije (scenarijski prosjek)
        pv_gen = _scen_avg_simple("PV Generation")
        wind_gen = _scen_avg_simple("Wind Generation")
        sc_gen = _scen_avg_simple("Solar Collector Generation")
    
        if pv_gen is None and np.any(self.pv_generation): pv_gen = self.pv_generation
        if wind_gen is None and np.any(self.wind_generation): wind_gen = self.wind_generation
        if sc_gen is None and np.any(self.solar_collector_generation): sc_gen = self.solar_collector_generation
    
        if pv_gen is not None and np.any(pv_gen): results["PV Generation"] = pv_gen
        if wind_gen is not None and np.any(wind_gen): results["Wind Generation"] = wind_gen
        if sc_gen is not None and np.any(sc_gen): results["Solar Collector Generation"] = sc_gen
    
        elec_dem = _scen_avg_electricity()
        heat_dem = _scen_avg_thermal("heating")
        cool_dem = _scen_avg_thermal("cooling")

        if elec_dem is None and np.any(self.electricity_demand): elec_dem = self.electricity_demand
        if heat_dem is None and np.any(self.heating_demand): heat_dem = self.heating_demand
        if cool_dem is None and np.any(self.cooling_demand): cool_dem = self.cooling_demand

        if elec_dem is not None and np.any(elec_dem): results["Electricity Demand"] = elec_dem
        if heat_dem is not None and np.any(heat_dem): results["Heating Demand"] = heat_dem
        if cool_dem is not None and np.any(cool_dem): results["Cooling Demand"] = cool_dem

        # Cijene: Buy kao E[Price Data]; Sell preferira E[Sell Price], inače buyback * E[Buy]; Thermal E[Thermal Price]
        results["Buy Price"] = np.array([
            sum(scenarios[s]["Price Data"][t] * probs[s] for s in S_range)
            for t in range(self.required_length)
        ])
    
        sell_avg = _scen_avg_simple("Sell Price")
        if sell_avg is not None:
            results["Sell Price"] = sell_avg
        elif self.buyback_factor is not None:
            results["Sell Price"] = results["Buy Price"] * self.buyback_factor
        else:
            results["Sell Price"] = self.sell_price
    
        thermal_avg = _scen_avg_simple("Thermal Price")
        results["Thermal Price"] = thermal_avg if thermal_avg is not None else self.thermal_price
    
        # Transferi (očekivanja varijabli)
        results["PV → Load"] = get_series("pv_to_load")
        results["PV → Grid"] = get_series("pv_to_grid")
        results["PV → Battery"] = get_series("pv_to_batt")
        results["PV → Heat Pump (heating)"] = get_series("pv_to_hp_heat")
        results["PV → Heat Pump (cooling)"] = get_series("pv_to_hp_cool")
    
        results["Wind → Load"] = get_series("wind_to_load")
        results["Wind → Grid"] = get_series("wind_to_grid")
        results["Wind → Battery"] = get_series("wind_to_batt")
        results["Wind → Heat Pump (heating)"] = get_series("wind_to_hp_heat")
        results["Wind → Heat Pump (cooling)"] = get_series("wind_to_hp_cool")
    
        results["Grid → Load"] = get_series("grid_to_load")
        results["Grid → Battery"] = get_series("grid_to_batt")
        results["Grid → Heat Pump (heating)"] = get_series("grid_to_hp_heat")
        results["Grid → Heat Pump (cooling)"] = get_series("grid_to_hp_cool")
    
        results["Battery → Load"] = get_series("batt_to_load")
        results["Battery → Grid"] = get_series("batt_to_grid")
        results["Battery → Heat Pump (heating)"] = get_series("batt_to_hp_heat")
        results["Battery → Heat Pump (cooling)"] = get_series("batt_to_hp_cool")
        results["Battery charge"] = get_series("charge")
        results["Battery discharge"] = get_series("discharge")
        results["Battery SOE"] = get_series("batt_soe")
    
        if self.buffer_capacity:
            results["Heat Pump → Heating Load + Buffer Tank"] = get_series("hp_heat_to_load")
        else:
            results["Heat Pump → Heating Load"] = get_series("hp_heat_to_load")
        results["Heat Pump → Cooling Load"] = get_series("hp_cool_to_load")
        results["Heat Pump → Buffer Tank"] = get_series("hp_to_buffer")
    
        results["Buffer Tank → Heating Load"] = get_series("buffer_to_load")
        results["Buffer Tank SOE"] = get_series("buffer_soe")
    
        results["Solar Collector → Buffer Tank"] = get_series("solar_to_buffer")
        results["Unmet Solar Collector → Buffer Tank"] = get_series("solar_curtail")
    
        results["Unmet Electricity Demand"] = get_series("unmet_electricity_demand")
        results["Unmet Heating Demand"] = get_series("unmet_heating_demand")
        results["Unmet Cooling Demand"] = get_series("unmet_cooling_demand")
        results["PV Lost"] = get_series("pv_lost")
        results["Wind Lost"] = get_series("wind_lost")
    
        # Financije
        results["Revenue"] = (
            arr("PV → Grid") +
            arr("Wind → Grid") +
            arr("Battery → Grid")
        ) * results["Sell Price"]
    
        results["Cost"] = (
            arr("Grid → Load") +
            arr("Grid → Battery") +
            arr("Grid → Heat Pump (heating)") +
            arr("Grid → Heat Pump (cooling)")
        ) * results["Buy Price"]
    
        results["Savings"] = (
            (
                arr("PV → Load") +
                arr("PV → Heat Pump (heating)") +
                arr("PV → Heat Pump (cooling)") +
                arr("Battery → Load") +
                arr("Battery → Heat Pump (heating)") +
                arr("Battery → Heat Pump (cooling)") +
                arr("Wind → Load") +
                arr("Wind → Heat Pump (heating)") +
                arr("Wind → Heat Pump (cooling)")
            ) * results["Buy Price"]
            + arr("Solar Collector → Buffer Tank") * results["Thermal Price"]
        )
    
        results["Net profit"] = results["Revenue"] - results["Cost"]
    
        # makni prazne nizove
        results = {k: v for k, v in results.items() if not isinstance(v, np.ndarray) or np.any(v)}
        return results


class OptimizationRunner(QThread):
    finished = pyqtSignal(dict, dict, dict)
    failed = pyqtSignal(str)

    def __init__(self, preparator, metadata, selected_inputs):
        super().__init__()
        self.preparator = preparator
        self.input_metadata = metadata
        self.selected_inputs = selected_inputs
        self._stop_requested = False

    def request_stop(self):
        self._stop_requested = True

    def _setup_solver(self):
        cbc_path = get_cbc_executable_path()
        solver = pye.SolverFactory('cbc', executable=cbc_path)
        solver.options.update({"seconds": 300, "ratio": 0.01})
        return solver
    
    def run(self):
        try:
            if self._stop_requested:
                self.failed.emit("Optimization cancelled by user.")
                return

            model = pye.ConcreteModel()
            model = self.preparator.create_model_variables(model, self.preparator)
            model = self.preparator.add_constraints_and_objective(model)

            result = self._setup_solver().solve(model, tee=False)

            if self._stop_requested:
                self.failed.emit("Optimization cancelled by user.")
                return

            if result.solver.status != pye.SolverStatus.ok:
                self.failed.emit("Optimization failed or was infeasible.")
                return

            results = self.preparator.extract_results(model)
            self.finished.emit(results, self.input_metadata, self.selected_inputs)

        except Exception as e:
            tb = traceback.format_exc()
            self.failed.emit(f"{str(e)}\n\nTraceback:\n{tb}")
            self.failed.emit(str(e))

class OptimizationPopup(QDialog):
    style = ("""
         QPushButton {
            background-color: white;
            color: black;
            font-weight: bold;
            font-size: 12px;
            border: 2px solid black;
            padding: 4px 12px;
        }
        QPushButton:hover {
            background-color: #f0f0f0;
        }
    """)
    def __init__(self, parent, preparator):
        super().__init__(parent)
        self.setWindowTitle("Optimization in Progress")
        self.setModal(True)
        self.setFixedSize(300, 100)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("Running optimization...")
        self.progress_bar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.progress_bar.setMinimumHeight(25)
        self.progress_bar.setMinimumWidth(300)
        layout.addWidget(self.progress_bar, alignment=Qt.AlignCenter)

        layout.addStretch()

        button_row = QHBoxLayout()
        button_row.addStretch()

        self.stop_button = QPushButton("Stop")
        self.stop_button.setStyleSheet(self.style)
        self.stop_button.setFixedWidth(80)
        self.stop_button.clicked.connect(self.stop_optimization)
        button_row.addWidget(self.stop_button, alignment=Qt.AlignBottom)

        layout.addLayout(button_row)

        self.runner_thread = OptimizationRunner(preparator, parent.input_metadata, parent.selected_inputs)
        self.runner_thread.finished.connect(self.on_finished)
        self.runner_thread.failed.connect(self.on_failed)
        self.runner_thread.start()

    def stop_optimization(self):
        self.runner_thread.request_stop()
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(1)
        self.progress_bar.setFormat("Stopping optimization...")
        self.stop_button.setDisabled(True)

    def on_finished(self, results_dict, metadata, selected_inputs):
        self.accept()
        QMessageBox.information(self, "Optimization Completed", "Optimization finished successfully.")

        index = self.parent().output_workspace.tabs.count() + 1

        self.parent().output_workspace.add_optimization_results(
            f"Optimization {index}", results_dict, selected_inputs
        )

        self.parent().financial_workspace.add_financial_summary(
            f"Optimization {index} ", results_dict, metadata, selected_inputs
        )
        financial_summary = self.parent().financial_workspace.financial_data[-1]

        self.parent().emissions_workspace.add_emissions_summary(
            f"Optimization {index} ", results_dict, metadata, selected_inputs
        )
        emissions_summary = self.parent().emissions_workspace.emission_data[-1]

        self.parent().text_analysis_workspace.add_analysis(
            f"Optimization {index} ", selected_inputs, results_dict, financial_summary, emissions_summary
        )

    def on_failed(self, message):
        self.reject()
        QMessageBox.critical(self, "Optimization Failed", message)