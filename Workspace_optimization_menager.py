from PyQt5.QtWidgets import (
    QWidget, QListWidget, QVBoxLayout, QTabWidget, QPushButton, QHBoxLayout,
    QListWidgetItem, QMenu, QFileDialog, QMessageBox, QFrame, QLabel, QSizePolicy, QTextEdit
)
from PyQt5.QtCore import Qt, QEvent
import numpy as np
from Ploting_handler import PlottingHandler


class OptimizationWorkspaceManager(QWidget):
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

    def __init__(self, parent=None):
        super().__init__(parent)
        self.optimizations, self.result_lists = [], []
        self.selected_inputs_list = []
        self._build_ui()

    def _build_ui(self):
        self.tabs = QTabWidget(documentMode=True, tabPosition=QTabWidget.North)
        self.tabs.setMinimumHeight(40)
        self.tabs.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tabs.customContextMenuRequested.connect(self._show_tab_context_menu)

        plot_combined_button = QPushButton("Plot on Same Graph")
        plot_combined_button.setStyleSheet(OptimizationWorkspaceManager.style)
        plot_combined_button.clicked.connect(self._plot_selected_combined)

        plot_separate_button = QPushButton("Plot Separately")
        plot_separate_button.setStyleSheet(OptimizationWorkspaceManager.style)
        plot_separate_button.clicked.connect(self._plot_selected_separate)

        container = QWidget()
        container.setObjectName("LeftTopBottomBorder")

        container.setStyleSheet("""
            #LeftTopBottomBorder {
                border-left: 1px solid black;
                border-top: 2px solid black;
                border-bottom: 2px solid black;
                border-right: 2px solid black;
                background-color: white;
            }
        """)
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(6, 6, 6, 6)
        container_layout.addWidget(self.tabs)

        button_layout = QHBoxLayout()
        button_layout.addWidget(plot_combined_button)
        button_layout.addWidget(plot_separate_button)
        container_layout.addLayout(button_layout)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(container)
        layout.setStretch(0, 1)

        self.setStyleSheet(self._style())
        self.installEventFilter(self)

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def setup_layout(self):
        self.setStyleSheet(self._style())

    def _style(self):
        return """
            QTabWidget::pane {
                border: none;
                top: -1px;
            }
            QTabBar::tab {
                min-width: 120px;
                font-size: 13px;
                font-weight: bold;
                font-family: Arial;
                padding: 6px 12px;
                background-color: #ffffff;
                border: 2px solid black;
                border-bottom: none;
                margin-right: 4px;
            }
            QTabBar::tab:selected {
                background-color: #f0f0f0;
                border-color: black;
            }
            QTabBar::tab:hover {
                background-color: #e6e6e6;
            }
            QListWidget {
                background-color: white;
                font-size: 12px;
                font-family: Arial;
                border: none;
                outline: none;
            }
            QListWidget::item {
                padding: 6px 10px;
                margin: 4px;
                background-color: white;
                border: none;
                border-radius: 4px;
                outline: none;
            }
            QListWidget::item:selected {
                background-color: #e0e0e0;
                color: black;
                border: none;
                outline: none;
            }
            QListWidget::item:focus {
                outline: none;
            }
        """

    def create_section_label(self, text):
        label = QLabel(text)
        label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                font-weight: bold;
                padding: 4px;
                background-color: white;
                border: none;
            }
        """)
        return label

    def add_optimization_results(self, name, optimization_results, selected_inputs):
        filtered = {k: v for k, v in optimization_results.items() if v is not None and hasattr(v, '__len__') and len(v) > 0}
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        tab.setStyleSheet("background-color: white;")
        tab_layout.setContentsMargins(0, 0, 0, 0)
    
        result_list = QListWidget()
        result_list.setSelectionMode(QListWidget.MultiSelection)
        result_list.itemDoubleClicked.connect(lambda item: PlottingHandler.show_workspace_item_details(self, item))
        result_list.setContextMenuPolicy(Qt.CustomContextMenu)
        result_list.customContextMenuRequested.connect(lambda pos: self._show_context_menu(result_list, pos))
        result_list.installEventFilter(self)
    
        for key, val in filtered.items():
            item = QListWidgetItem(str(key))
            item.setData(Qt.UserRole, val)
            result_list.addItem(item)

        tab_layout.addWidget(result_list)
        self.tabs.addTab(tab, name)

        self.optimizations.append(filtered)
        self.result_lists.append(result_list)

        if not hasattr(self, 'selected_inputs_list'):
            self.selected_inputs_list = []  
        self.selected_inputs_list.append(selected_inputs.copy() if selected_inputs else {})

    def get_selected_inputs(self, index=None):
        if index is None:
            index = self.tabs.currentIndex()
        if 0 <= index < len(self.selected_inputs_list):
            return self.selected_inputs_list[index]
        return {}

    def _get_current_tab_results(self):
        index = self.tabs.currentIndex()
        if index < 0 or index >= len(self.result_lists):
            return None, None
        return self.result_lists[index], self.optimizations[index]

    def _get_selected_data(self):
        result_list, _ = self._get_current_tab_results()
        if not result_list:
            return {}
        return {item.text(): item.data(Qt.UserRole) for item in result_list.selectedItems()}

    def _close_tab(self, index):
        if 0 <= index < len(self.optimizations):
            self.optimizations.pop(index)
            self.result_lists.pop(index)
            self.selected_inputs_list.pop(index)
            self.tabs.removeTab(index)

    def _show_tab_context_menu(self, pos):
        index = self.tabs.tabBar().tabAt(pos)
        if index >= 0:
            menu = QMenu(self)
            delete_action = menu.addAction("Delete Optimization Tab")
            if menu.exec_(self.tabs.mapToGlobal(pos)) == delete_action:
                self._close_tab(index)

    def _show_context_menu(self, list_widget, pos):
        item = list_widget.itemAt(pos)
        if item:
            menu = QMenu(self)
            delete_action = menu.addAction("Delete")
            if menu.exec_(list_widget.mapToGlobal(pos)) == delete_action:
                list_widget.takeItem(list_widget.row(item))

    def _plot_selected_combined(self):
        selected_data = self._get_selected_data()
        if not selected_data:
            QMessageBox.warning(self, "No Selection", "Please select results to plot.")
            return
        PlottingHandler._show_multi_series_popup(self, selected_data)

    def _plot_selected_separate(self):
        selected_data = self._get_selected_data()
        if not selected_data:
            QMessageBox.warning(self, "No Selection", "Please select results to plot separately.")
            return
        PlottingHandler.show_multi_series_separate_popup(self, selected_data)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.MouseButtonPress:
            for lst in self.result_lists:
                if not lst.geometry().contains(lst.mapFromGlobal(event.globalPos())):
                    lst.clearSelection()
        elif event.type() == QEvent.KeyPress and isinstance(obj, QListWidget) and event.key() == Qt.Key_Delete:
            item = obj.currentItem()
            if item:
                obj.takeItem(obj.row(item))
                return True
        return super().eventFilter(obj, event)


class FinancialWorkspaceManager(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.financial_data = []
        self.metadata_list = []
        self._build_ui()

    def _build_ui(self):
        self.tabs = QTabWidget(documentMode=True, tabPosition=QTabWidget.North)
        self.tabs.setMinimumHeight(40)

        container = QWidget()
        container.setObjectName("LeftTopBottomBorder")
        
        container.setStyleSheet("""
            #LeftTopBottomBorder {
                border-left: 2px solid black;
                border-top: 2px solid black;
                border-bottom: 2px solid black;
                border-right: None;
                background-color: white;
            }
        """)

        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(6, 6, 6, 6)
        container_layout.addWidget(self.tabs)

        button_layout = QHBoxLayout()
        container_layout.addLayout(button_layout)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(container)
        layout.setStretch(0, 1)

        self.setStyleSheet(self._style())

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def setup_layout(self):
        self.setStyleSheet(self._style())

    def _style(self):
        return """
            QTabWidget::pane {
                border: none;
                top: -1px;
            }
            QTabBar::tab {
                min-width: 120px;
                font-size: 13px;
                font-weight: bold;
                font-family: Arial;
                padding: 6px 12px;
                background-color: #ffffff;
                border: 2px solid black;
                border-bottom: none;
                margin-right: 4px;
            }
            QTabBar::tab:selected {
                background-color: #f0f0f0;
                border-color: black;
            }
            QTabBar::tab:hover {
                background-color: #e6e6e6;
            }
            QListWidget {
                background-color: white;
                font-size: 12px;
                font-family: Arial;
                border: none;
                outline: none;
            }
            QListWidget::item {
                padding: 6px 10px;
                margin: 4px;
                background-color: white;
                border: none;
                border-radius: 4px;
                outline: none;
            }
            QListWidget::item:selected {
                background-color: #e0e0e0;
                color: black;
                border: none;
                outline: none;
            }
            QListWidget::item:focus {
                outline: none;
            }
        """

    def create_section_label(self, text):
        label = QLabel(text)
        label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                font-weight: bold;
                padding: 4px;
                background-color: white;
                border: none;
            }
        """)
        return label

    def add_financial_summary(self, name, optimization_results, metadata, selected_inputs):
        roi_dict = self._calculate_financials(optimization_results, metadata, selected_inputs)

        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)

        list_widget = QListWidget()
        for key, val in roi_dict.items():
            if str(key).startswith("_"):      
                continue
            display = f"{key}: {val:.2f}" if isinstance(val, float) else f"{key}: {val}"
            item = QListWidgetItem(display)
            list_widget.addItem(item)

        tab_layout.addWidget(list_widget)
        self.tabs.addTab(tab, name)
        self.financial_data.append(roi_dict)
        self.metadata_list.append(metadata)

    def _calculate_financials(self, optimization_results, metadata, selected_inputs):
        battery_replacements = 2
    
        def safe_array(key):
            """Return a 8760-length float array; fall back to zeros if key missing/None/wrong shape."""
            v = optimization_results.get(key, None)
            if v is None:
                return np.zeros(8760, dtype=float)
            arr = np.asarray(v, dtype=float)
            if arr.shape == (8760,):
                return arr
            if arr.ndim == 0:
                return np.full(8760, float(arr), dtype=float)
            return np.zeros(8760, dtype=float)

        def buy_price_array():
            for k in ("Buy Price",):
                arr = safe_array(k)
                if np.any(arr): 
                    return arr
            return np.zeros(8760, dtype=float)

        tech_key_map = {
            "PV": "PV Generation",
            "Wind": "Wind Generation",
            "Heat Pump": "Heat Pump Inputs",
            "Thermal Storage": "Buffer Tank Inputs",
            "Battery": "Battery Inputs",
            "Solar Collector": "Solar Collector Inputs"
        }


        emissions = selected_inputs.get("CO₂ Emissions", {})
        thermal_emissions = emissions.get('Thermal Emission Inputs', {})
        mode = thermal_emissions.get('mode', '')
        fuel_price = float(thermal_emissions.get('fuel_price', 0) or 0)
        system_efficiancy = float(thermal_emissions.get('system_efficiency', 1) or 1)

        heating_demand = float(np.sum(safe_array("Heating Demand")))

        if mode == 'yearly fuel consumption':
            fuel_consumption = float(thermal_emissions.get('fuel_consumption', 0) or 0)
            old_thermal_cost = fuel_consumption * fuel_price
        else:
            eff = system_efficiancy if system_efficiancy > 0 else 1.0
            old_thermal_cost = heating_demand * fuel_price / eff

        used_techs = {tech: key in metadata for tech, key in tech_key_map.items()}

        capex = 0.0
        opex_annual = 0.0

        for tech, used in used_techs.items():
            if not used:
                continue

            meta_key = tech_key_map[tech]
            tech_meta = metadata.get(meta_key, {})

            try:
                capex_value = float(tech_meta.get("capex", 0) or 0)
                opex_value = float(tech_meta.get("opex", 0) or 0)
            except (TypeError, ValueError):
                raise ValueError(f"Invalid capex/opex format for {tech} in metadata: {tech_meta}")

            if tech == "Battery":
                capex += capex_value * battery_replacements
            else:
                capex += capex_value
                opex_annual += opex_value

        grid_to_hp_heat = safe_array("Grid → Heat Pump (heating)")
        price_series = buy_price_array()
        new_thermal_cost = float(np.sum(grid_to_hp_heat * price_series))


        diff_thermal_cost = max(old_thermal_cost - new_thermal_cost, 0.0)

        # 20-year totals
        opex = opex_annual * 20.0
        total_cost = capex + opex

        net_profit = float(np.sum(safe_array("Net profit")))
        savings_electricity = float(np.sum(safe_array("Savings")))
        savings = savings_electricity
        sum_net_profit = net_profit + savings + diff_thermal_cost

        total_sum_net_profit = sum_net_profit * 20.0
        total_sum_net_profit_minus_opex = total_sum_net_profit - opex

        roi_percent = ((total_sum_net_profit_minus_opex - capex) / capex) * 100.0 if capex > 0 else 0.0
        payback_time = (capex / (sum_net_profit - opex_annual)
                        if (sum_net_profit - opex_annual) > 0 else float("inf"))

        results = {
            "Technologies Used": ", ".join([k for k, v in used_techs.items() if v]),
            "Total CAPEX [€]": round(capex, 2),
            "Total OPEX (20 years) [€]": round(opex, 2),
            "Total Cost [€]": round(total_cost, 2),
            "Net profit + Saved Profit [€]": round(sum_net_profit, 2),
            "Total Profit (20 years) [€]": round(total_sum_net_profit, 2),
            "Net Profit - OPEX (20 years) [€]": round(total_sum_net_profit_minus_opex, 2),
            "ROI (20 years) [%]": round(roi_percent, 2),
            "Payback Time [years]": round(payback_time, 2) if payback_time != float("inf") else "∞"
        }
        
        results["_old_thermal_cost"] = old_thermal_cost
        results["_new_thermal_cost"] = new_thermal_cost
        results["_diff_thermal_cost"] = diff_thermal_cost
        return results

class EmissionsWorkspaceManager(QWidget):
    el_emission_dict = {
        "\nThe following data refers only to": "",
        "\nCO₂ emission before optimization [kg]": 0,
        "CO₂ emission after optimization [kg]": 0,
        "Saved emission after optimization [kg]": 0,
        "Saved emission after optimization [€]": 0,
        "Emission reduction [%]": 0,

        "\nExternal cost before optimization [€]": 0,

        "External cost breakdown before optimization [€]":
        "\n  • Climate Change - 0"
        "\n  • Particulate Matter - 0"
        "\n  • Toxicity - 0",

        "\nExternal cost after optimization [€]": 0,

        "External cost breakdown after optimization [€]":
        "\n  • Climate Change - 0"
        "\n  • Particulate Matter - 0"
        "\n  • Toxicity - 0",

        "Saved external cost after optimization [€]": 0,
        "External cost reduction [%]": 0,
    }

    th_emission_dict = el_emission_dict.copy()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.emission_data = []
        self.metadata_list = []
        self._build_ui()

    def _build_ui(self):
        self.tabs = QTabWidget(documentMode=True, tabPosition=QTabWidget.North)
        self.tabs.setMinimumHeight(40)

        container = QWidget()
        container.setObjectName("LeftTopBottomBorder")
        
        container.setStyleSheet("""
            #LeftTopBottomBorder {
                border-left: 2px solid black;
                border-top: None;
                border-bottom: 2px solid black;
                border-right: None;
                background-color: white;
            }
        """)

        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(6, 6, 6, 6)
        container_layout.addWidget(self.tabs)

        button_layout = QHBoxLayout()
        container_layout.addLayout(button_layout)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(container)
        layout.setStretch(0, 1)  

        self.setStyleSheet(self._style())

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def setup_layout(self):
        self.setStyleSheet(self._style())

    def _style(self):
        return """
            QTabWidget::pane {
                border: none;
                top: -1px;
            }
            QTabBar::tab {
                min-width: 120px;
                font-size: 13px;
                font-weight: bold;
                font-family: Arial;
                padding: 6px 12px;
                background-color: #ffffff;
                border: 2px solid black;
                border-bottom: none;
                margin-right: 4px;
            }
            QTabBar::tab:selected {
                background-color: #f0f0f0;
                border-color: black;
            }
            QTabBar::tab:hover {
                background-color: #e6e6e6;
            }
            QListWidget {
                background-color: white;
                font-size: 12px;
                font-family: Arial;
                border: none;
                outline: none;
            }
            QListWidget::item {
                padding: 6px 10px;
                margin: 4px;
                background-color: white;
                border: none;
                border-radius: 4px;
                outline: none;
            }
            QListWidget::item:selected {
                background-color: #e0e0e0;
                color: black;
                border: none;
                outline: none;
            }
            QListWidget::item:focus {
                outline: none;
            }
        """

    def create_section_label(self, text):
        label = QLabel(text)
        label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                font-weight: bold;
                padding: 4px;
                background-color: white;
                border: none;
            }
        """)
        return label

    def add_emissions_summary(self, name, optimization_results, metadata, selected_inputs):

        emissions_report = self._calculate_emissions(optimization_results, metadata, selected_inputs)

        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)

        list_widget = QListWidget()
        for key, val in emissions_report.items():
            display = f"{key}: {val:.2f}" if isinstance(val, float) else f"{key}: {val}"
            item = QListWidgetItem(display)
            list_widget.addItem(item)

        tab_layout.addWidget(list_widget)
        self.tabs.addTab(tab, name)
        self.emission_data.append(emissions_report)
        self.metadata_list.append(metadata)

    def _calculate_emissions(self, optimization_results, metadata, selected_inputs):
        import numpy as np
    
        def safe_array(key):
            v = optimization_results.get(key, None)
            if v is None:
                return np.zeros(8760, dtype=float)
            arr = np.asarray(v, dtype=float)
            if arr.shape == (8760,):
                return arr
            if arr.ndim == 0:
                return np.full(8760, float(arr), dtype=float)
            return np.zeros(8760, dtype=float)
    
        def to_float(x, default=0.0):
            try:
                if x is None:
                    return default
                if isinstance(x, str) and x.strip() == "":
                    return default
                return float(x)
            except (TypeError, ValueError):
                return default
    
        # reset dicts to avoid stari podaci
        self.el_emission_dict = {}
        self.th_emission_dict = {}
    
        saved_emissions = None
        saved_emissions_eur = None
        saved_emissions_th = None
        saved_emissions_th_eur = None
        saved_external_cost = None
        saved_external_cost_th = None
    
        CO2_electric = 0.0
        CO2_thermal = 0.0
    
        electricity_demand = float(np.sum(safe_array("Electricity Demand")))
    
        emissions = selected_inputs.get("CO₂ Emissions", {})
        emissions_inputs = emissions.get('Emission Inputs', {})
        CO2_price = to_float(emissions_inputs.get("emission_price"), 0.0)
        CO2_emission_value = to_float(emissions_inputs.get("emission_value"), 0.0)
        system_efficiency = to_float(emissions_inputs.get("system_efficiency"), 1.0)
        yearly_fuel_consumption = to_float(emissions_inputs.get("fuel_consumption"), 0.0)
        mode = emissions_inputs.get("mode", '')
    
        if mode == 'yearly fuel consumption':
            CO2_electric = yearly_fuel_consumption * CO2_emission_value
        else:
            eff = system_efficiency if 0 < system_efficiency < 1 else 1.0
            CO2_electric = CO2_emission_value / eff
    

        external_cost = selected_inputs.get("External Cost", {})
        external_cost_inputs = external_cost.get("External Cost Inputs", {})
        mode_ex_c = external_cost_inputs.get("mode", '')
        external_health_price_el = to_float(external_cost_inputs.get("external_ht_cost"), 0.0)
        external_particulate_price_el = to_float(external_cost_inputs.get("external_pm_cost"), 0.0)
        if mode_ex_c == 'External cost manual':
            eff = system_efficiency if system_efficiency > 0 else 1.0
            external_health_price_el /= eff
            external_particulate_price_el /= eff
    
        if electricity_demand != 0:
            if CO2_electric == 0:
                self.el_emission_dict["\nThe following data refers only to"] = "Electricity"
            else:
                base_electricity_emissions = electricity_demand * CO2_electric
    
                base_external_cost_climate_change = CO2_electric * electricity_demand * CO2_price
                base_external_cost_particulate_matter = external_particulate_price_el * electricity_demand
                base_external_cost_toxicity = external_health_price_el * electricity_demand
                base_external_cost = (base_external_cost_climate_change +
                                      base_external_cost_particulate_matter +
                                      base_external_cost_toxicity)
    
                electricity_import_after_optimization = float(np.sum(safe_array("Grid → Load")))
                electricity_emissions_after_optimization = electricity_import_after_optimization * CO2_electric
    
                saved_emissions = base_electricity_emissions - electricity_emissions_after_optimization
                saved_emissions_eur = saved_emissions * CO2_price
                saved_emission_pct = (100 * saved_emissions / base_electricity_emissions
                                      if base_electricity_emissions > 0 else 0.0)
    
                after_external_cost_climate_change = CO2_electric * electricity_import_after_optimization * CO2_price
                after_external_cost_particulate_matter = external_particulate_price_el * electricity_import_after_optimization
                after_external_cost_toxicity = external_health_price_el * electricity_import_after_optimization
                electricity_external_cost_after_optimization = (after_external_cost_climate_change +
                                                                after_external_cost_particulate_matter +
                                                                after_external_cost_toxicity)
    
                saved_external_cost = base_external_cost - electricity_external_cost_after_optimization
                saved_external_cost_pct = (100 * saved_external_cost / base_external_cost
                                           if base_external_cost > 0 else 0.0)
    
                self.el_emission_dict = {
                    "\nThe following data refers only to": "Electricity",
                    "CO₂ emission before optimization [kg]": base_electricity_emissions,
                    "CO₂ emission after optimization [kg]": electricity_emissions_after_optimization,
                    "Saved emission after optimization [kg]": saved_emissions,
                    "Saved emission after optimization [€]": saved_emissions_eur,
                    "Emission reduction [%]": saved_emission_pct,
                    "External cost before optimization [€]": base_external_cost,
                    "External cost breakdown before optimization [€]":
                        f"\n  • Climate Change - {base_external_cost_climate_change:.2f}"
                        f"\n  • Particulate Matter - {base_external_cost_particulate_matter:.2f}"
                        f"\n  • Toxicity - {base_external_cost_toxicity:.2f}",
                    "External cost after optimization [€]": electricity_external_cost_after_optimization,
                    "External cost breakdown after optimization [€]":
                        f"\n  • Climate Change - {after_external_cost_climate_change:.2f}"
                        f"\n  • Particulate Matter - {after_external_cost_particulate_matter:.2f}"
                        f"\n  • Toxicity - {after_external_cost_toxicity:.2f}",
                    "Saved external cost after optimization [€]": saved_external_cost,
                    "External cost reduction [%]": saved_external_cost_pct,
                }
        else:
            self.el_emission_dict["\nThe following data refers only to"] = "Electricity"
    
        heating_demand = float(np.sum(safe_array("Heating Demand")))
        if heating_demand != 0:
            emissions_th = selected_inputs.get("CO₂ Emissions", {})
            emissions_inputs_th = emissions_th.get('Thermal Emission Inputs', {})
            CO2_price_th = to_float(emissions_inputs_th.get("emission_price"), 0.0)
            CO2_emission_value_th = to_float(emissions_inputs_th.get("emission_value"), 0.0)
            system_efficiency_th = to_float(emissions_inputs_th.get("system_efficiency"), 1.0)
            yearly_fuel_consumption_th = to_float(emissions_inputs_th.get("fuel_consumption"), 0.0)
            mode_th = emissions_inputs_th.get("mode", '')
    
            if mode_th == 'yearly fuel consumption':
                CO2_thermal = yearly_fuel_consumption_th * CO2_emission_value_th
            else:
                eff_th = system_efficiency_th if 0 < system_efficiency_th < 1 else 1.0
                CO2_thermal = CO2_emission_value_th / eff_th
    
            external_cost_inputs_th = selected_inputs.get("External Cost", {}) \
                                                  .get("Thermal External Cost Inputs", {})
            mode_ex_c_th = external_cost_inputs_th.get("mode", '')
            external_health_price_th = to_float(external_cost_inputs_th.get("external_ht_cost"), 0.0)
            external_particulate_price_th = to_float(external_cost_inputs_th.get("external_pm_cost"), 0.0)
            if mode_ex_c_th == 'External cost manual':
                eff_th = system_efficiency_th if system_efficiency_th > 0 else 1.0
                external_health_price_th /= eff_th
                external_particulate_price_th /= eff_th
    
            if CO2_thermal == 0:
                self.th_emission_dict["\nThe following data refers only to"] = 'Thermal'
            else:
                base_thermal_emissions = heating_demand * CO2_thermal
    
                base_external_cost_climate_change_th = CO2_thermal * heating_demand * CO2_price_th
                base_external_cost_particulate_matter_th = external_particulate_price_th * heating_demand
                base_external_cost_toxicity_th = external_health_price_th * heating_demand
                base_external_cost_th = (base_external_cost_climate_change_th +
                                         base_external_cost_particulate_matter_th +
                                         base_external_cost_toxicity_th)
    
                hp_heating_after_optimization = float(np.sum(safe_array("Grid → Heat Pump (heating)")))
                hp_cooling_after_optimization = float(np.sum(safe_array("Grid → Heat Pump (cooling)")))
    
                if hp_heating_after_optimization > 0 or hp_cooling_after_optimization > 0:
                    # HP koristi STRUJU -> koristi EL koeficijente za "external cost"
                    thermal_import_after_optimization = hp_heating_after_optimization + hp_cooling_after_optimization
                    thermal_emissions_after_optimization = thermal_import_after_optimization * CO2_electric
    
                    saved_emissions_th = base_thermal_emissions - thermal_emissions_after_optimization
                    saved_emissions_th_eur = saved_emissions_th * CO2_price_th
                    saved_emission_pct_th = (100 * saved_emissions_th / base_thermal_emissions
                                             if base_thermal_emissions > 0 else 0.0)
    
                    after_external_cost_climate_change_th = CO2_electric * thermal_import_after_optimization * CO2_price
                    after_external_cost_particulate_matter_th = external_particulate_price_el * thermal_import_after_optimization
                    after_external_cost_toxicity_th = external_health_price_el * thermal_import_after_optimization
    
                    thermal_external_cost_after_optimization = (after_external_cost_climate_change_th +
                                                                after_external_cost_particulate_matter_th +
                                                                after_external_cost_toxicity_th)
                else:
                    thermal_import_after_optimization = 0.0
                    thermal_emissions_after_optimization = 0.0
    
                    saved_emissions_th = base_thermal_emissions - thermal_emissions_after_optimization
                    saved_emissions_th_eur = saved_emissions_th * CO2_price_th
                    saved_emission_pct_th = (100 * saved_emissions_th / base_thermal_emissions
                                             if base_thermal_emissions > 0 else 0.0)
    
                    after_external_cost_climate_change_th = CO2_thermal * thermal_import_after_optimization * CO2_price_th
                    after_external_cost_particulate_matter_th = external_particulate_price_th * thermal_import_after_optimization
                    after_external_cost_toxicity_th = external_health_price_th * thermal_import_after_optimization
    
                    thermal_external_cost_after_optimization = (after_external_cost_climate_change_th +
                                                                after_external_cost_particulate_matter_th +
                                                                after_external_cost_toxicity_th)
    
                saved_external_cost_th = base_external_cost_th - thermal_external_cost_after_optimization
                saved_external_cost_pct_th = (100 * saved_external_cost_th / base_external_cost_th
                                              if base_external_cost_th > 0 else 0.0)
    
                self.th_emission_dict = {
                    "\nThe following data refers only to": 'Thermal',
                    "CO₂ emission before optimization [kg]": base_thermal_emissions,
                    "CO₂ emission after optimization [kg]": thermal_emissions_after_optimization,
                    "Saved emission after optimization [kg]": saved_emissions_th,
                    "Saved emission after optimization [€]": saved_emissions_th_eur,
                    "Emission reduction [%]": saved_emission_pct_th,
                    "Thermal External cost before optimization [€]": base_external_cost_th,
                    "Thermal External cost breakdown before optimization [€]":
                        f"\n  • Climate Change - {base_external_cost_climate_change_th:.2f}"
                        f"\n  • Particulate Matter - {base_external_cost_particulate_matter_th:.2f}"
                        f"\n  • Toxicity - {base_external_cost_toxicity_th:.2f}",
                    "External cost after optimization [€]": thermal_external_cost_after_optimization,
                    "External cost breakdown after optimization [€]":
                        f"\n  • Climate Change - {after_external_cost_climate_change_th:.2f}"
                        f"\n  • Particulate Matter - {after_external_cost_particulate_matter_th:.2f}"
                        f"\n  • Toxicity - {after_external_cost_toxicity_th:.2f}",
                    "Saved external cost after optimization [€]": saved_external_cost_th,
                    "External cost reduction [%]": saved_external_cost_pct_th,
                }
        else:
            self.th_emission_dict["\nThe following data refers only to"] = "Thermal"
    
        def prefix_keys(d, prefix):
            return {f"{prefix} {k.strip()}": v for k, v in d.items()}
    
        result = {}
        if saved_emissions is not None:
            result.update(prefix_keys(self.el_emission_dict, "[Electricity]"))
        if saved_emissions_th is not None:
            result.update(prefix_keys(self.th_emission_dict, "[Thermal]"))
    
        total_saved_em_eur = 0.0
        if saved_emissions_eur is not None:
            total_saved_em_eur += saved_emissions_eur
        if saved_emissions_th_eur is not None:
            total_saved_em_eur += saved_emissions_th_eur
        result["Total saved on Emissions [€]"] = total_saved_em_eur

        total_saved_ext_eur = 0.0
        if saved_external_cost is not None:
            total_saved_ext_eur += saved_external_cost
        if saved_external_cost_th is not None:
            total_saved_ext_eur += saved_external_cost_th
        result["Total saved on External costs [€]"] = total_saved_ext_eur

        return result


class OptimizationTextAnalysisManager(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        self.tabs = QTabWidget(documentMode=True, tabPosition=QTabWidget.North)
        self.tabs.setMinimumHeight(40)

        container = QWidget()
        container.setObjectName("LeftTopBottomBorder")
        
        container.setStyleSheet("""
            #LeftTopBottomBorder {
                border-left: None;
                border-top: None;
                border-bottom: 4px solid black;
                border-right: None;
                background-color: white;
            }
        """)

        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(6, 6, 6, 6)
        container_layout.addWidget(self.tabs)

        button_layout = QHBoxLayout()
        container_layout.addLayout(button_layout)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(container)
        layout.setStretch(0, 1)

        self.setStyleSheet(self._style())

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def setup_layout(self):
        self.setStyleSheet(self._style())

    def _style(self):
        return """
            QTabWidget::pane {
                border: none;
                top: -1px;
            }
            QTabBar::tab {
                min-width: 120px;
                font-size: 13px;
                font-weight: bold;
                font-family: Arial;
                padding: 6px 12px;
                background-color: #ffffff;
                border: 2px solid black;
                border-bottom: none;
                margin-right: 4px;
            }
            QTabBar::tab:selected {
                background-color: #f0f0f0;
                border-color: black;
            }
            QTabBar::tab:hover {
                background-color: #e6e6e6;
            }
            QListWidget {
                background-color: white;
                font-size: 12px;
                font-family: Arial;
                border: none;
                outline: none;
            }
            QListWidget::item {
                padding: 6px 10px;
                margin: 4px;
                background-color: white;
                border: none;
                border-radius: 4px;
                outline: none;
            }
            QListWidget::item:selected {
                background-color: #e0e0e0;
                color: black;
                border: none;
                outline: none;
            }
            QListWidget::item:focus {
                outline: none;
            }
        """

    def create_section_label(self, text):
        label = QLabel(text)
        label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                font-weight: bold;
                padding: 4px;
                background-color: white;
                border: none;
            }
        """)
        return label

    def add_analysis(self, name, selected_inputs, optimization_results, financial_summary, emissions_summary):
        text = self._generate_text_analysis(financial_summary, emissions_summary, optimization_results, name)

        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)


        charts_widget = PlottingHandler.create_three_pie_charts_widget( 
            selected_inputs, optimization_results, financial_summary, emissions_summary
        )
        layout.addWidget(charts_widget)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)  

        text_widget = QTextEdit()
        text_widget.setReadOnly(True)
        text_widget.setStyleSheet("""
            QTextEdit {
                background-color: white;
                font-family: Arial;
                font-size: 12px;
                border: none;
            }
        """)
        text_widget.setText(text)

        layout.addWidget(text_widget)
        self.tabs.addTab(tab, name)

    def _generate_text_analysis(self, financial, emissions, optimization_results, tab_name="this optimization"):

        def safe_array(key):
            val = optimization_results.get(key)
            return val if isinstance(val, np.ndarray) and val.shape == (8760,) else np.zeros(8760)

        capex = financial.get("Total CAPEX [€]", 0)
        opex = financial.get("Total OPEX (20 years) [€]", 0)
        total_cost = financial.get("Total Cost [€]", 0)
        payback = financial.get("Payback Time [years]", "∞")
        old_thermal_cost = financial.get("_old_thermal_cost", 0)
        new_thermal_cost = financial.get("_new_thermal_cost", 0)
        diff_thermal_cost = financial.get("_diff_thermal_cost", 0)

        electricity_demand = np.sum(safe_array("Electricity Demand"))
        heating_demand = np.sum(safe_array("Heating Demand"))
        cooling_demand = np.sum(safe_array("Cooling Demand"))


        usage_of_renewables = (
                            safe_array("PV → Load")+
                            safe_array("Wind → Load")+
                            safe_array("PV → Heat Pump (heating)")+
                            safe_array("PV → Heat Pump (cooling)")+
                            safe_array("Wind → Heat Pump (heating)")+
                            safe_array("Wind → Heat Pump (cooling)")+
                            safe_array("Battery charge") - safe_array("Grid → Battery")+
                            safe_array("Battery discharge") - safe_array("Battery → Grid")
                            )#all i have used from my Renewables
        self_consumption = np.sum(usage_of_renewables)


        imported_from_grid = (
                        safe_array("Grid → Load")+
                        safe_array("Grid → Battery")+
                        safe_array("Grid → Heat Pump (heating)")+
                        safe_array("Grid → Heat Pump (cooling)")
                        )#All i have imported from the grid
        grid_import = np.sum(imported_from_grid)

        if electricity_demand > 0:
            base_grid_import_pct = 100
        else:
            base_grid_import_pct = 0

        if self_consumption > 0 and grid_import > 0:
            self_consumption_pct = 100*self_consumption/(self_consumption + grid_import)
            grid_import_pct = 100*grid_import/(self_consumption + grid_import)
        elif self_consumption < 0 and grid_import > 0:
            self_consumption_pct = 0
            grid_import_pct = 100
        elif self_consumption > 0 and grid_import < 0:
            self_consumption_pct = 100
            grid_import_pct = 0
        else:
            self_consumption_pct = 0
            grid_import_pct = 0


        revenue = np.sum(safe_array(("Revenue")))
        savings = np.sum(safe_array(("Savings")))
        cost = np.sum(safe_array(("Cost")))
        unmet_elec = np.sum(safe_array(("Unmet Electricity Demand")))
        unmet_heat = np.sum(safe_array(("Unmet Heating Demand")))
        unmet_cool = np.sum(safe_array(("Unmet Cooling Demand")))
        pv_lost = np.sum(safe_array(("PV Lost")))
        wind_lost = np.sum(safe_array(("Wind Lost")))
        unmet_buffer = np.sum(safe_array(("Unmet Solar Collector → Buffer Tank")))

        # CO₂ Emissions
        co2_base = emissions.get("[Electricity] CO₂ emission before optimization [kg]", 0)
        co2_saved = emissions.get("[Electricity] Saved emission after optimization [kg]", 0)
        co2_pct = emissions.get("[Electricity] Emission reduction [%]", 0)
        co2_emitted_pct = 100 - co2_pct if co2_base > 0 else 0

        # External Cost
        base_ext_cost = emissions.get("[Electricity] External cost before optimization [€]", 0)
        optimized_ext_cost = emissions.get("[Electricity] External cost after optimization [€]", 0)
        ext_cost_saved = emissions.get("[Electricity] Saved external cost after optimization [€]", 0)
        ext_cost_saved_pct = emissions.get("[Electricity] External cost reduction [%]", 0)


        html = "<html><body style='font-family:Arial; font-size:13px;'>"

        # Profitability sentence
        if isinstance(payback, (int, float)) and payback <= 20:
            html += f"<p><b><span style='color:green;'>In {tab_name}, your total investment in selected technologies of €{total_cost:.2f} is profitable within a 20-year period.</span></b></p>"
        else:
            html += f"<p><b><span style='color:red;'>In {tab_name}, your total investment in selected technologies of €{total_cost:.2f} is not profitable within 20 years. Try lowering the total cost of technologies, adjusting your demand, or resizing your technology capacities.</span></b></p>"

        # Financials
        html += f"<p><b>Your capital expenditure is</b> <span style='color:blue;'>€{capex:.2f}</span> <b>and total operating expenses are</b> <span style='color:blue;'>€{opex:.2f}</span>. <b>Your return on investment is expected within</b> <span style='color:blue;'>{payback} years</span>.</p>"

        if electricity_demand > 0:
            # Demand coverage
            html += f"<p><b>Before optimization you have imported </b> <span style='color:green;'>{base_grid_import_pct:.1f}%</span> <b> of electricity from grid, while after optimization your technologies cover</b> <span style='color:green;'>{self_consumption_pct:.1f}%</span> <b>of your demand, while the remaining</b> <span style='color:blue;'>{grid_import_pct:.1f}%</span> <b>is still imported from the grid.</b></p>"

        # Unmet electricity
        if unmet_elec == 0:
            html += "<p><b><span style='color:green;'>You have dimensioned your electricity technology capacities well, and all your electricity consumption is met.</span></b></p>"
        else:
            html += f"<p><b><span style='color:red;'>You have an unmet electricity demand of {unmet_elec:.1f} kWh. Consider expanding your technology capacities or increasing your grid limit.</span></b></p>"
        
        #savings thermal
        if diff_thermal_cost > 0:
            html += f"<p><b>In your base case for heating, your yearly cost of heating was <span style='color:red;'>€{old_thermal_cost:.2f}</span>. By electrifying your heating system, your yearly heating cost is reduced to €{new_thermal_cost:.2f}. You will be saving <span style='color:green;'>€{diff_thermal_cost:.2f}</span> each year on heating.</span></b></p>"
        # Unmet thermal
        if heating_demand != 0 or cooling_demand != 0:
            if unmet_heat == 0 and unmet_cool == 0:
                html += "<p><b><span style='color:green;'>You have sized your thermal technology capacities correctly, covering all your thermal energy needs.</span></b></p>"
            elif unmet_heat  != 0  and unmet_cool == 0:
                html += f"<p><b><span style='color:red;'>You have an unmet heating demand of {unmet_heat:.1f} kWh-thermal. Consider expanding your thermal technology capacities.</span></b></p>"
            elif unmet_heat == 0 and unmet_cool  != 0:
                html += f"<p><b><span style='color:red;'>You have an unmet cooling demand of {unmet_cool:.1f} kWh-thermal. Consider expanding your thermal technology capacities.</span></b></p>"
            else:
                html += f"<p><b><span style='color:red;'>You have an unmet heating demand of {unmet_heat:.1f} kWh-thermal and unmet cooling demand of {unmet_cool:.1f} kWh-thermal. Consider expanding your thermal technology capacities.</span></b></p>"

            if unmet_buffer != 0:
                html += f"<p><b><span style='color:red;'>You have lost heating generation { unmet_buffer:.1f} kWh-thermal, due to undersized buffer tank capacity. Consider increasing themral storage or decreasing area of solar collector. </span></b></p>"

        #PV and Wind lost
        if pv_lost == 0 and wind_lost == 0:
            pass
        elif pv_lost != 0 and wind_lost == 0:
            html += f"<p><b><span style='color:red;'>You have lost PV generation of { pv_lost:.1f} kWh, due to grid export limit, full batteries or already fulfilled demand. Consider increasing storage, lower PV rated power or increasing grid limit. </span></b></p>"
        elif pv_lost == 0 and wind_lost != 0:
            html += f"<p><b><span style='color:red;'>You have lost wind generation of { wind_lost:.1f} kWh, due to grid export limit, full batteries or already fulfilled demand. Consider increasing storage, lower wind turbine rated power or increasing grid limit. </span></b></p>"
        else:
            html += f"<p><b><span style='color:red;'>You have lost wind generation of { wind_lost:.1f} kWh and lost PV generation of { pv_lost:.1f} kWh, due to grid export limit, full batteries or already fulfilled demand. Consider increasing storage, lower wind turbine rated power or increasing grid limit. </span></b></p>"

        # Revenue/savings/cost
        html += f"<p><b>You generate profit by selling excess energy to the grid and performing energy price arbitrage when prices are high, earning a total of</b> <span style='color:green;'>€{revenue:.2f}</span>.</p>"
        html += f"<p><b>You save money on electricity bills by producing your own renewable energy and using smart storage, reaching total savings of</b> <span style='color:green;'>€{savings:.2f}</span>.</p>"
        html += f"<p><b>To cover remaining demand not met by your technologies and by performing energy price arbitrage when prices are low, you spend</b> <span style='color:#aa6600;'>€{cost:.2f}</span> <b>on grid electricity purchases.</b></p>"

        if base_ext_cost != 0:
            #EXternal cost
            html += "<p><b>By reducing emissions, you have also reduced your external costs — which include hidden economic damages from pollution such as health care expenses, environmental degradation, and premature deaths.</b></p>"
            html += f"<p><b>Your estimated external cost before optimization was</b> <span style='color:#aa6600;'>€{base_ext_cost:.2f}</span>, <b>while after optimization it dropped to</b> <span style='color:green;'>€{optimized_ext_cost:.2f}</span>.</p>"
            html += f"<p><b>This means you have saved approximately</b> <span style='color:green;'>€{ext_cost_saved:.2f}</span> <b>in hidden health and environmental costs — a</b> <span style='color:green;'>{ext_cost_saved_pct:.1f}%</span> <b>reduction in total external cost.</b></p>"
            html += "<p><b>This reduction helps alleviate pressure on healthcare systems and reduces long-term societal burdens caused by fossil fuel-based energy production.</b></p>"

        if co2_saved != 0:
            # CO2
            html += f"<p><b>With renewable technologies, which are carbon neutral, you have saved</b> <span style='color:green;'>{co2_saved:.2f} kg</span>, <b>which equals</b> <span style='color:green;'>{co2_pct:.1f}%</span> <b>of your total CO₂ footprint; the rest comes from grid imports</b> <span style='color:red;'>({co2_emitted_pct:.1f}%).</span></p>"

        if heating_demand != 0 or cooling_demand != 0:
            html += "<p><b>By using thermal generation and storage, you have reduced thermal CO₂ emissions to zero.</b></p>"

        html += "<p><b>By producing more of your own clean energy, you help secure better health and a more resilient future.</b></p>"
        html += "<p><b>By choosing renewable technologies and storage, you reduce pollution, protect local health, lower your electricity costs, and contribute to building a cleaner, more affordable energy system for everyone.</b></p>"

        html += "</body></html>"
        return html
