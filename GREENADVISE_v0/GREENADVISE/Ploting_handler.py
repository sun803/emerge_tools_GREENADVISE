from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QPushButton, QLabel,
                             QHBoxLayout, QLineEdit, QMessageBox, QTableWidget,
                             QTableWidgetItem, QCalendarWidget, QDialogButtonBox,
                             QWidget, QSpinBox, QToolButton, QFrame, QScrollArea)

from PyQt5.QtCore import Qt, QLocale, QDate
from PyQt5.QtGui import QIcon
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import numpy as np
from matplotlib.figure import Figure

class PlottingHandler:
    _last_start_date = QDate(2025, 1, 1)
    _last_end_date = QDate(2025, 1, 1)
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

    style_text = ("""
        QTableWidget {
            background-color: white;
            gridline-color: black;
            font-size: 12px;
            border: 2px solid black; 
        }
        QHeaderView::section {
            background-color: #f0f0f0;
            font-weight: bold;
            padding: 4px;
            border: 1px solid #ccc;
        }
        QTableWidget::item:selected {
            background-color: #f0f0f0;
            color: black;
        }
    """)

    @staticmethod
    def show_workspace_item_details(parent, item):
        value = item.data(Qt.UserRole)
        title = item.text()

        if isinstance(value, (list, np.ndarray)) and len(value) == 8760:
            PlottingHandler._show_array_popup(parent, value, title)
        else:
            PlottingHandler._show_text_popup(parent, value, title)

    @staticmethod
    def _show_text_popup(parent, value, title):
        if isinstance(value, dict):
            dialog = QDialog(parent)
            dialog.setWindowTitle(title)

            layout = QVBoxLayout(dialog)

            table = QTableWidget()
            table.setColumnCount(2)
            table.setStyleSheet(PlottingHandler.style_text)
            table.setHorizontalHeaderLabels(["Key", "Value"])
            table.setRowCount(len(value))
            table.verticalHeader().setVisible(False)
            table.setEditTriggers(QTableWidget.NoEditTriggers)

            for row, (key, val) in enumerate(value.items()):
                table.setItem(row, 0, QTableWidgetItem(str(key)))
                table.setItem(row, 1, QTableWidgetItem(str(val)))

            table.resizeColumnsToContents()
            table.resizeRowsToContents()
            layout.addWidget(table)

            close_btn = QPushButton("Close")
            close_btn.setStyleSheet(PlottingHandler.style)
            close_btn.clicked.connect(dialog.close)
            layout.addWidget(close_btn, alignment=Qt.AlignRight)

            width = table.sizeHintForColumn(0) + table.sizeHintForColumn(1) + 60
            height = min(500, table.verticalHeader().length() + 100)
            dialog.resize(width, height)

            dialog.exec_()
        else:
            msg = QMessageBox(parent)
            msg.setWindowTitle(title)
            msg.setTextInteractionFlags(Qt.TextSelectableByMouse)
            msg.setText(str(value))
            msg.exec_()

    @staticmethod
    def _show_array_popup(parent, array, title):
        dialog = QDialog(parent)
        dialog.setWindowTitle(f"{title} - Preview")
        dialog.setFixedSize(240, 150)

        layout = QVBoxLayout(dialog)
        yearly_btn = QPushButton("Hourly preview (8760 points)")
        yearly_btn.setStyleSheet(PlottingHandler.style)
        monthly_btn = QPushButton("Monthly preview (12 points)")
        monthly_btn.setStyleSheet(PlottingHandler.style)
        layout.addWidget(yearly_btn)
        layout.addWidget(monthly_btn)

        yearly_btn.clicked.connect(lambda: (dialog.close(), PlottingHandler._plot_array(parent, array, title, mode="yearly")))
        monthly_btn.clicked.connect(lambda: (dialog.close(), PlottingHandler._plot_array(parent, array, title, mode="monthly")))
        dialog.exec_()

    @staticmethod
    def _plot_array(parent, array, title, mode="yearly"):
        PlottingHandler._create_single_plot_dialog(parent, array, title, mode, modal=True)

    @staticmethod
    def _plot_array_non_blocking(parent, array, title, mode="yearly"):
        PlottingHandler._create_single_plot_dialog(parent, array, title, mode, modal=False)

    @staticmethod
    def _hide_year_and_customize_header(calendar_widget):
        fixed_year = 2025
        jan_date = QDate(fixed_year, 1, 1)
        dec_date = QDate(fixed_year, 12, 31)

        calendar_widget.setLocale(QLocale(QLocale.English))
        calendar_widget.setMinimumDate(jan_date)
        calendar_widget.setMaximumDate(dec_date)
        calendar_widget.setSelectedDate(jan_date)
        calendar_widget.setCurrentPage(2025, 1)
        calendar_widget.setGridVisible(True)

        calendar_widget.setStyleSheet("""
            QCalendarWidget QWidget {
                alternate-background-color: #f0f0f0;
            }
            QCalendarWidget QToolButton {
                background-color: white;
                color: black;
                font-weight: bold;
                font-size: 14px;
                border: none;
            }
            QCalendarWidget QSpinBox {
                width: 0px;
                height: 0px;
                font-size: 0px;
            }
            QCalendarWidget QAbstractItemView:enabled {
                color: black;
                selection-background-color: #f0f0f0;
                selection-color: black;
            }
            QCalendarWidget QToolButton::menu-indicator {
                image: none;
            }
            QCalendarWidget QToolButton#qt_calendar_prevmonth,
            QCalendarWidget QToolButton#qt_calendar_nextmonth {
                color: black;
                background-color: white;
                border: none;
            }
            QMenu {
                background-color: white;
                color: black;
                font-size: 13px;
            }
            QMenu::item {
                padding: 6px 20px;
            }
            QMenu::item:selected {
                background-color: #f0f0f0;
                color: black;
            }
""")

        header = calendar_widget.findChild(QWidget, "qt_calendar_navigationbar")
        if header:
            for child in header.children():
                if isinstance(child, QSpinBox):
                    child.hide()
                elif isinstance(child, QToolButton):
                    if child.text().isdigit() or "2025" in child.text():
                        child.hide()
                    elif child.objectName() == "qt_calendar_prevmonth":
                        child.setText("<")
                        child.setIcon(QIcon())
                    elif child.objectName() == "qt_calendar_nextmonth":
                        child.setText(">")
                        child.setIcon(QIcon())

    @staticmethod
    def _create_single_plot_dialog(parent, array, title, mode, modal):
        plot_dialog = QDialog(parent)
        plot_dialog.setAttribute(Qt.WA_DeleteOnClose)
        plot_dialog.setWindowTitle(f"{title} - {mode.capitalize()} Preview")
        plot_dialog.resize(1000, 600)

        layout = QVBoxLayout(plot_dialog)
        input_layout = QHBoxLayout()


        if mode == "yearly":
            calendar_btn = QPushButton("Calendar")
            calendar_btn.setStyleSheet(PlottingHandler.style)
            input_layout.addWidget(calendar_btn)


        start_label = QLabel("Start")
        start_label.setStyleSheet("font-weight: bold;")
        start_input = QLineEdit()
        start_input.setPlaceholderText("0" if mode == "yearly" else "1")
        input_layout.addWidget(start_label)
        input_layout.addWidget(start_input)


        end_label = QLabel("End")
        end_label.setStyleSheet("font-weight: bold;")
        end_input = QLineEdit()
        end_input.setPlaceholderText("8759" if mode == "yearly" else "12")
        input_layout.addWidget(end_label)
        input_layout.addWidget(end_input)
    

        plot_btn = QPushButton("Plot Range")
        plot_btn.setStyleSheet(PlottingHandler.style)
        input_layout.addWidget(plot_btn)
        

        layout.addLayout(input_layout)
        

        fig = plt.figure(figsize=(10, 5))
        ax = fig.add_subplot(111)
        canvas = FigureCanvas(fig)
        
        canvas_frame = QFrame()
        canvas_layout = QVBoxLayout(canvas_frame)
        canvas_layout.setContentsMargins(0, 0, 0, 0)
        canvas_layout.addWidget(canvas)
        
        canvas_frame.setStyleSheet("""
            QFrame {
                border: 2px solid black;
                background-color: white;
            }
        """)
        
        layout.addWidget(canvas_frame)


        close_btn = QPushButton("Close")
        close_btn.setStyleSheet(PlottingHandler.style)
        close_btn.clicked.connect(plot_dialog.close)
        layout.addWidget(close_btn, alignment=Qt.AlignRight)

        def plot_data():
            ax.clear()
            arr = np.array(array)

            if mode == "yearly" and len(arr) != 8760:
                QMessageBox.critical(parent, "Invalid Data", f"'{title}' does not contain 8760 hourly values.")
                return

            try:
                start = int(start_input.text()) if start_input.text() else (0 if mode == "yearly" else 1)
                end = int(end_input.text()) if end_input.text() else (8759 if mode == "yearly" else 12)

                if mode == "yearly":
                    if not (0 <= start <= end < 8760):
                        raise ValueError("Invalid range for yearly data.")
                    ax.plot(np.arange(start, end + 1), arr[start:end + 1], linewidth=0.8, color='black')
                    ax.set_xlabel("Hour of Year")
                    if any(kw in title.lower() for kw in ["price", "cost", "revenue", "net profit", "savings", "tariff"]):
                        ylabel = "€/kWh"
                    else:
                        ylabel = "kWh"
                    ax.set_ylabel(ylabel)
                    ax.set_title(f"{title} - Hourly {start} to {end}")
                else:
                    if not (1 <= start <= end <= 12):
                        raise ValueError("Invalid range for monthly data.")
                    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
                    month_labels = months[start - 1:end]
                    monthly_sum = [np.sum(arr[i*730:(i+1)*730]) if i != 11 else np.sum(arr[i*730:]) for i in range(12)]
                    selected_data = monthly_sum[start - 1:end]
                    ax.bar(month_labels, selected_data, color='black')
                    ax.set_xlabel("Month")
                    if any(kw in title.lower() for kw in ["price", "cost", "revenue", "net profit", "savings"]):
                        ylabel = "€/kWh"
                    else:
                        ylabel = "kWh"
                    ax.set_ylabel(ylabel)
                    ax.set_title(f"{title} - Monthly {months[start-1]} to {months[end-1]}")

                ax.grid(True)
            except Exception as e:
                QMessageBox.warning(parent, "Invalid Input", str(e))
            canvas.draw()

        def open_calendar_popup():
            calendar_dialog = QDialog(parent)
            calendar_dialog.setWindowTitle("Select Start and End Dates")
            calendar_dialog.setFixedSize(560, 500)

            main_layout = QVBoxLayout(calendar_dialog)

            outer_frame = QFrame()
            outer_frame.setFrameShape(QFrame.Box)
            outer_frame.setStyleSheet("""
                QFrame {
                    border: 2px solid black;
                    background-color: white;
                }
            """)
            outer_layout = QVBoxLayout(outer_frame)
            outer_layout.setContentsMargins(14, 14, 14, 14)
            outer_layout.setSpacing(18)

            start_label = QLabel("Start Date")
            start_label.setAlignment(Qt.AlignCenter)
            start_label.setStyleSheet("font-weight: bold; font-size: 14px;")
            outer_layout.addWidget(start_label)

            start_calendar = QCalendarWidget()
            PlottingHandler._hide_year_and_customize_header(start_calendar)
            start_calendar.setSelectedDate(PlottingHandler._last_start_date)
            outer_layout.addWidget(start_calendar)

            end_label = QLabel("End Date")
            end_label.setAlignment(Qt.AlignCenter)
            end_label.setStyleSheet("font-weight: bold; font-size: 14px;")
            outer_layout.addWidget(end_label)

            end_calendar = QCalendarWidget()
            PlottingHandler._hide_year_and_customize_header(end_calendar)
            end_calendar.setSelectedDate(PlottingHandler._last_end_date)
            outer_layout.addWidget(end_calendar)

            main_layout.addWidget(outer_frame)

            button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
            button_box.setStyleSheet(PlottingHandler.style)
            main_layout.addWidget(button_box)

            def apply_dates():
                start_qdate = start_calendar.selectedDate()
                end_qdate = end_calendar.selectedDate()
                start_day = start_qdate.dayOfYear()
                end_day = end_qdate.dayOfYear()

                if end_day < start_day:
                    QMessageBox.warning(parent, "Invalid Range", "End date must not be before start date.")
                    return

                start_hour = (start_day - 1) * 24
                end_hour = end_day * 24 - 1

                if 0 <= start_hour <= end_hour < 8760:
                    start_input.setText(str(start_hour))
                    end_input.setText(str(end_hour))
                    plot_data()
                    PlottingHandler._last_start_date = start_qdate
                    PlottingHandler._last_end_date = end_qdate
                    calendar_dialog.accept()
                else:
                    QMessageBox.warning(parent, "Invalid Range", "Date range is outside valid bounds.")

            button_box.accepted.connect(apply_dates)
            button_box.rejected.connect(calendar_dialog.reject)

            calendar_dialog.exec_()

        if mode == 'yearly':
            calendar_btn.clicked.connect(open_calendar_popup)

        plot_btn.clicked.connect(plot_data)
        plot_data()
        plot_dialog.finished.connect(lambda: plt.close(fig))

        if modal:
            plot_dialog.exec_()
        else:
            plot_dialog.show()

    @staticmethod
    def _show_multi_series_popup(parent, results_dict):
        PlottingHandler._show_mode_choice_popup(parent, results_dict, combined=True)

    @staticmethod
    def show_multi_series_separate_popup(parent, results_dict):
        PlottingHandler._show_mode_choice_popup(parent, results_dict, combined=False)

    @staticmethod
    def _show_mode_choice_popup(parent, results_dict, combined):
        dialog = QDialog(parent)
        dialog.setWindowTitle("Plot Options")
        dialog.setFixedSize(240, 150)

        layout = QVBoxLayout(dialog)
        yearly_btn = QPushButton("Hourly preview (8760 points)")
        yearly_btn.setStyleSheet(PlottingHandler.style)
        monthly_btn = QPushButton("Monthly preview (12 points)")
        monthly_btn.setStyleSheet(PlottingHandler.style)

        layout.addWidget(yearly_btn)
        layout.addWidget(monthly_btn)

        def handle_choice(mode):
            dialog.close()
            if combined:
                PlottingHandler._plot_multi_array(parent, results_dict, mode)
            else:
                for title, array in results_dict.items():
                    PlottingHandler._plot_array_non_blocking(parent, array, title, mode)

        yearly_btn.clicked.connect(lambda: handle_choice("yearly"))
        monthly_btn.clicked.connect(lambda: handle_choice("monthly"))
        dialog.exec_()

    @staticmethod
    def _plot_multi_array(parent, results_dict, mode="yearly"):
        plot_dialog = QDialog(parent)
        plot_dialog.setWindowTitle(f"{mode.capitalize()} Combined Preview")
        plot_dialog.resize(1000, 600)

        layout = QVBoxLayout(plot_dialog)
        input_layout = QHBoxLayout()

        if mode == "yearly":
            calendar_btn = QPushButton("Calendar")
            calendar_btn.setStyleSheet(PlottingHandler.style)
            input_layout.addWidget(calendar_btn)

        start_label = QLabel("Start:")
        start_label.setStyleSheet("font-weight: bold;")
        start_input = QLineEdit()
        start_input.setPlaceholderText("0" if mode == "yearly" else "1")
        input_layout.addWidget(start_label)
        input_layout.addWidget(start_input)
    
        end_label = QLabel("End:")
        end_label.setStyleSheet("font-weight: bold;")
        end_input = QLineEdit()
        end_input.setPlaceholderText("8759" if mode == "yearly" else "12")
        input_layout.addWidget(end_label)
        input_layout.addWidget(end_input)
    
        plot_btn = QPushButton("Plot Range")
        plot_btn.setStyleSheet(PlottingHandler.style)
        input_layout.addWidget(plot_btn)
    
        layout.addLayout(input_layout)
    
        fig = plt.figure(figsize=(10, 5))
        ax = fig.add_subplot(111)
        canvas = FigureCanvas(fig)
    
        canvas_frame = QFrame()
        canvas_layout = QVBoxLayout(canvas_frame)
        canvas_layout.setContentsMargins(0, 0, 0, 0)
        canvas_layout.addWidget(canvas)
    
        canvas_frame.setStyleSheet("""
            QFrame {
                border: 2px solid black;
                background-color: white;
            }
        """)

        layout.addWidget(canvas_frame)

        close_btn = QPushButton("Close")
        close_btn.setStyleSheet(PlottingHandler.style)
        close_btn.clicked.connect(plot_dialog.close)
        layout.addWidget(close_btn, alignment=Qt.AlignRight)

        def plot_data():
            ax.clear()
            cmap = plt.cm.get_cmap("tab10")
            try:
                start = int(start_input.text()) if start_input.text() else (0 if mode == "yearly" else 1)
                end = int(end_input.text()) if end_input.text() else (8759 if mode == "yearly" else 12)
                for i, (title, array) in enumerate(results_dict.items()):
                    arr = np.array(array)

                    if not np.issubdtype(arr.dtype, np.number):
                        QMessageBox.critical(parent, "Invalid Data", f"'{title}' contains non-numeric values.")
                        return

                    if mode == "yearly" and len(arr) != 8760:
                        QMessageBox.critical(parent, "Invalid Data", f"'{title}' does not contain 8760 hourly values.")
                        return

                    if mode == "yearly":
                        if not (0 <= start <= end < 8760):
                            raise ValueError("Invalid range for yearly data.")
                        ax.plot(np.arange(start, end + 1), arr[start:end + 1], label=title,
                                linewidth=0.8, color=cmap(i % 10))
                    else:
                        if not (1 <= start <= end <= 12):
                            raise ValueError("Invalid range for monthly data.")
                        months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul",
                                  "Aug", "Sep", "Oct", "Nov", "Dec"]
                        month_labels = months[start - 1:end]
                        monthly_sum = [np.sum(arr[i*730:(i+1)*730]) if i != 11 else np.sum(arr[i*730:])
                                       for i in range(12)]
                        selected_data = monthly_sum[start - 1:end]
                        ax.plot(month_labels, selected_data, label=title, color=cmap(i % 10), marker='o')
    
                ax.set_xlabel("Hour of Year" if mode == "yearly" else "Month")
                if mode == "yearly":
                    ax.set_title("Hourly Combined Plot")
                else:
                    ax.set_title("Monthly Combined Plot")
                ax.grid(True)
                ax.legend()
            except Exception as e:
                QMessageBox.warning(parent, "Invalid Input", str(e))
            canvas.draw()

        def open_calendar_popup():
            calendar_dialog = QDialog(parent)
            calendar_dialog.setWindowTitle("Select Start and End Dates")
            calendar_dialog.setFixedSize(560, 500)

            main_layout = QVBoxLayout(calendar_dialog)

            outer_frame = QFrame()
            outer_frame.setFrameShape(QFrame.Box)
            outer_frame.setStyleSheet("""
                QFrame {
                    border: 2px solid black;
                    background-color: white;
                }
            """)
            outer_layout = QVBoxLayout(outer_frame)
            outer_layout.setContentsMargins(14, 14, 14, 14)
            outer_layout.setSpacing(18)

            start_label = QLabel("Start Date")
            start_label.setAlignment(Qt.AlignCenter)
            start_label.setStyleSheet("font-weight: bold; font-size: 14px;")
            outer_layout.addWidget(start_label)

            start_calendar = QCalendarWidget()
            PlottingHandler._hide_year_and_customize_header(start_calendar)
            start_calendar.setSelectedDate(PlottingHandler._last_start_date)
            outer_layout.addWidget(start_calendar)

            end_label = QLabel("End Date")
            end_label.setAlignment(Qt.AlignCenter)
            end_label.setStyleSheet("font-weight: bold; font-size: 14px;")
            outer_layout.addWidget(end_label)

            end_calendar = QCalendarWidget()
            PlottingHandler._hide_year_and_customize_header(end_calendar)
            end_calendar.setSelectedDate(PlottingHandler._last_end_date)
            outer_layout.addWidget(end_calendar)

            main_layout.addWidget(outer_frame)

            button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
            button_box.setStyleSheet(PlottingHandler.style)
            main_layout.addWidget(button_box)

            def apply_dates():
                start_qdate = start_calendar.selectedDate()
                end_qdate = end_calendar.selectedDate()
                start_day = start_qdate.dayOfYear()
                end_day = end_qdate.dayOfYear()

                if end_day < start_day:
                    QMessageBox.warning(parent, "Invalid Range", "End date must not be before start date.")
                    return

                start_hour = (start_day - 1) * 24
                end_hour = end_day * 24 - 1

                if 0 <= start_hour <= end_hour < 8760:
                    start_input.setText(str(start_hour))
                    end_input.setText(str(end_hour))
                    plot_data()
                    PlottingHandler._last_start_date = start_qdate
                    PlottingHandler._last_end_date = end_qdate
                    calendar_dialog.accept()
                else:
                    QMessageBox.warning(parent, "Invalid Range", "Date range is outside valid bounds.")

            button_box.accepted.connect(apply_dates)
            button_box.rejected.connect(calendar_dialog.reject)

            calendar_dialog.exec_()

        if mode == "yearly":
            calendar_btn.clicked.connect(open_calendar_popup)

        plot_btn.clicked.connect(plot_data)
        plot_data()
        plot_dialog.finished.connect(lambda: plt.close(fig))
        plot_dialog.exec_()

    @staticmethod
    def create_three_pie_charts_widget(selected_inputs, optimization_results, financial_summary, emissions_summary):
        def safe_array(key):
            val = np.array(optimization_results.get(key))
            return val if isinstance(val, np.ndarray) and val.shape == (8760,) else np.zeros(8760)

        # Pie 1: PV Self-consumption vs Grid Import
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

        # remaining_battery_SOE = safe_array("Battery SOE")[-1]#remaning charge in battery

        imported_from_grid = (
                        safe_array("Grid → Load")+
                        safe_array("Grid → Battery")+
                        safe_array("Grid → Heat Pump (heating)")+
                        safe_array("Grid → Heat Pump (cooling)")
                        )#All i have imported from the grid
        grid_import = np.sum(imported_from_grid)

        pie1_labels = ["Self Consumption", "Grid Import"]
        pie1_values = [self_consumption/(self_consumption + grid_import), grid_import/(self_consumption + grid_import)]

        # Pie 2: Profit / Savings / Cost
        emissions = selected_inputs.get("CO₂ Emissions", {})
        thermal_emissions = emissions.get('Thermal Emission Inputs', {}) or {}
        mode = thermal_emissions.get('mode', '')

        fuel_price = float(thermal_emissions.get('fuel_price', 0) or 0)
        system_efficiency = float(thermal_emissions.get('system_efficiency', 1) or 1)
        if system_efficiency <= 0:
            system_efficiency = 1.0  # guard
        
        heating_demand = float(np.sum(safe_array("Heating Demand")))

        if mode == 'yearly fuel consumption':
            fuel_consumption = float(thermal_emissions.get('fuel_consumption', 0) or 0)
            old_thermal_cost = fuel_consumption * fuel_price
        else:
            # cost = energy / efficiency * fuel_price
            old_thermal_cost = heating_demand * fuel_price / system_efficiency

        # Prefer the price you PAY for electricity.
        def buy_price_array():
            for k in ("Buy Price",
                      "Electricity Price Buy",
                      "Electricity Buy Price",
                      "Price Buy",
                      "Electricity Price"):
                arr = safe_array(k)
                if np.any(arr):
                    return arr
            return np.zeros(8760, dtype=float)
        
        grid_to_hp_heat = safe_array("Grid → Heat Pump (heating)")
        if not np.any(grid_to_hp_heat):
            grid_to_hp_heat = safe_array("Grid -> Heat Pump (heating)")
        
        price_series = buy_price_array()
        new_thermal_cost = float(np.sum(grid_to_hp_heat * price_series))
        
        diff_thermal_cost = max(old_thermal_cost - new_thermal_cost, 0.0)  # Thermal Savings (€/yr)

        # Existing pie inputs
        net_profit = safe_array("Net profit")
        savings = safe_array("Savings")
        cost = safe_array("Cost")
        
        cost_sum = float(np.sum(cost))
        pie2_labels = ["Net Profit", "Electricity Savings", "Thermal Savings", "Cost"]
        pie2_raw = [
            float(np.sum(net_profit)),
            float(np.sum(savings)),
            float(diff_thermal_cost),
            float(cost_sum),
        ]

        sumed = sum(pie2_raw)
        pie2_values = [v / sumed for v in pie2_raw] if sumed > 0 else [0.0] * len(pie2_raw)

        # Pie 3: CO₂ Emissions
        co2_base_el = emissions_summary.get("[Electricity] CO₂ emission before optimization [kg]", 0)
        co2_saved_el = emissions_summary.get("[Electricity] Saved emission after optimization [kg]", 0)
        co2_base_th = emissions_summary.get("[Thermal] CO₂ emission before optimization [kg]", 0)
        co2_saved_th = emissions_summary.get("[Thermal] Saved emission after optimization [kg]", 0)

        co2_base = co2_base_el + co2_base_th
        co2_saved = co2_saved_el + co2_saved_th

        pie3_labels = ["CO₂ Emitted", "CO₂ Saved"]
        if co2_base != 0:
            pie3_values = [(co2_base - co2_saved)/co2_base,  co2_saved/co2_base]
        else:
            pie3_values = [0, 0]

        chart_container = QWidget()
        chart_layout = QHBoxLayout(chart_container)
        chart_layout.setContentsMargins(10, 10, 10, 10)
        chart_layout.setSpacing(20)

        chart_data = [
            (pie1_labels, pie1_values, "Self consumption & Grid"),
            (pie2_labels, pie2_values, "Savings & Cost"),
            (pie3_labels, pie3_values, "CO₂ Balance"),
        ]

        for labels, values, title in chart_data:
            filtered = [(label, val) for label, val in zip(labels, values) if val > 1e-2]
            if not filtered:
                filtered = [("No Data", 1)]

            filtered_labels, filtered_values = zip(*filtered)

            fig = Figure(figsize=(4.2, 2))  
            ax = fig.add_axes([0.25, 0.15, 0.45, 0.7])  

            if all(v <= 1e-2 for v in values):
                ax.text(0.5, 0.5, "No Data", ha='center', va='center', fontsize=10)
            else:
                wedges, texts, autotexts = ax.pie(
                    filtered_values,
                    labels=None,
                    autopct=lambda p: f'{p:.1f}%' if p > 3 else '',
                    startangle=90,
                    textprops={'fontsize': 8}
                )

                ax.legend(
                    wedges,
                    filtered_labels,
                    loc="center left",
                    bbox_to_anchor=(0.9, 0.8),
                    fontsize=8,
                    title_fontsize=9
                )

            ax.set_title(title, fontsize=10, pad=12)
            ax.axis('equal')

            canvas = FigureCanvas(fig)
            canvas.setMinimumWidth(300)  
            chart_layout.addWidget(canvas)

        chart_container.setMinimumWidth(3 * 310)

        scroll_area = QScrollArea()
        scroll_area.setWidget(chart_container)
        scroll_area.setWidgetResizable(False)
        scroll_area.setFrameShape(QScrollArea.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        return scroll_area

