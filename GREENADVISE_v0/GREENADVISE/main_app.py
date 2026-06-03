from PyQt5.QtCore import Qt, QCoreApplication
QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts)

import sys
from PyQt5.QtGui import QPixmap, QFont, QIcon
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel,
    QVBoxLayout, QHBoxLayout, QToolBar, QAction, QMessageBox, QPushButton,
    QGridLayout, QSizePolicy, QSpacerItem, QWidgetAction, QSplitter
)



from toolbar_buttons import (
    GenerationPopupHandler, StoragePopupHandler,
    ThermalDemandPopupHandler, ElectricityDemandPopupHandler, PricePopupHandler,
    EmissionsPopupHandler, ThermalEmissionsPopupHandler, PreviousSystemPopupHandler
)

from Prepare_data import PrepareData
from Workspace_menager import WorkspaceManager
from Workspace_optimization_menager import (OptimizationWorkspaceManager,
                                            FinancialWorkspaceManager,
                                            EmissionsWorkspaceManager,
                                            OptimizationTextAnalysisManager)
from Export_data import export_to_excel
from map_widget import MapWidget
from resources import resource_path


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GREENADVISE")
        self.setWindowIcon(QIcon(resource_path("images/Greenadvise_logo.png")))
        self.setStyleSheet("background-color: white;")
        self.setMinimumSize(600, 400)
        self.optimization_popup = None

        self._init_toolbar()
        self._show_initial_selection()

    def _init_toolbar(self):
        self.toolbar = QToolBar("Main Toolbar")
        self.toolbar.setMovable(False)
        self.addToolBar(self.toolbar)

        def add_action(label, handler):
            action = QAction(label, self)
            action.triggered.connect(handler)
            self.toolbar.addAction(action)

        self.toolbar.setStyleSheet("""
            QToolBar { background-color: white; }
            QToolButton { font-weight: bold; font-size: 12px; padding: 6px 10px; }
            QToolButton:hover { background-color: #f0f0f0; }
        """)

        add_action("Return to \n main menu", self._show_initial_selection)
        self.toolbar.addSeparator()
        add_action("Generation \n technology", self._generation)
        add_action("Storage \n technology", self._storage)
        add_action("Thermal demand", self._thermal)
        add_action("Electricity demand", self._electricity)
        add_action("Buy && Sell \n price", self._price)
        self.toolbar.addSeparator()
        add_action("Electricity CO\u2082 \n emissions", self._emissions)
        add_action("Thermal CO\u2082 \n emissions", self._thermal_emissions)
        self.toolbar.addSeparator()
        add_action("Previous system", self._previous_system)
        self.toolbar.addSeparator()
        add_action("Start optimization", lambda: self.run_optimization(None, None))


        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        spacer_action = QWidgetAction(self)
        spacer_action.setDefaultWidget(spacer)
        self.toolbar.addAction(spacer_action)


        logo_widget = QWidget()
        logo_layout = QHBoxLayout(logo_widget)
        logo_layout.setContentsMargins(0, 0, 10, 0)
        logo_layout.setSpacing(5)

        # EMERGE logo
        emerge_label = QLabel()
        emerge_pixmap = QPixmap(resource_path("images/Emerge_logo.png")).scaledToHeight(28, Qt.SmoothTransformation)
        emerge_label.setPixmap(emerge_pixmap)
        logo_layout.addWidget(emerge_label)

        # EU logo
        eu_label = QLabel()
        eu_pixmap = QPixmap(resource_path("images/EU_logo.png")).scaledToHeight(28, Qt.SmoothTransformation)
        eu_label.setPixmap(eu_pixmap)
        logo_layout.addWidget(eu_label)


        logo_action = QWidgetAction(self)
        logo_action.setDefaultWidget(logo_widget)
        self.toolbar.addAction(logo_action)

        self.toolbar.hide()

    def _show_initial_selection(self):
        self.toolbar.hide()


        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)


        self.main_layout.addStretch()
        

        title_label = QLabel('<span style="color:black;">GREEN</span><span style="color:green;">ADVISE</span>')
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setFont(QFont("Century Schoolbook", 22, QFont.Bold))
        title_label.setStyleSheet("color: black;")
        self.main_layout.addWidget(title_label, alignment=Qt.AlignCenter)
        

        self.selection_container = QWidget()
        layout = QVBoxLayout(self.selection_container)
        layout.setAlignment(Qt.AlignCenter)
        layout.setContentsMargins(20, 20, 20, 20)

        image_row = QHBoxLayout()
        image_row.setSpacing(60)
        image_row.setAlignment(Qt.AlignCenter)

        image_row.addWidget(self._create_image_button("images/euro.png", "Energy system\n optimization\n START", self._profit_clicked))

        layout.addLayout(image_row) 
        self.main_layout.addWidget(self.selection_container, alignment=Qt.AlignCenter)


        self.main_layout.addStretch()


        bottom_logo_widget = QWidget()
        bottom_logo_layout = QHBoxLayout(bottom_logo_widget)
        bottom_logo_layout.setContentsMargins(0, 0, 20, 20)
        bottom_logo_layout.setSpacing(10)
        bottom_logo_layout.setAlignment(Qt.AlignRight | Qt.AlignBottom)

        emerge_logo = QLabel()
        emerge_pixmap = QPixmap(resource_path("images/Emerge_logo.png")).scaledToHeight(50, Qt.SmoothTransformation)
        emerge_logo.setPixmap(emerge_pixmap)

        eu_logo = QLabel()
        eu_pixmap = QPixmap(resource_path("images/EU_logo.png")).scaledToHeight(50, Qt.SmoothTransformation)
        eu_logo.setPixmap(eu_pixmap)

        bottom_logo_layout.addWidget(emerge_logo)
        bottom_logo_layout.addWidget(eu_logo)

        self.main_layout.addWidget(bottom_logo_widget, alignment=Qt.AlignRight | Qt.AlignBottom)


    def _create_image_button(self, image_path, label_text, on_click):
        container = QWidget()
        container.setStyleSheet("""
            QWidget {
                border: 2px solid #555;
                border-radius: 100px;
                background-color: white;
            }
            QWidget:hover {
                border: 2px solid #000;
            }
        """)
        layout = QVBoxLayout(container)
        layout.setAlignment(Qt.AlignCenter)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        img_label = QLabel()
        img_label.setStyleSheet("background: transparent; border: none;")
        pixmap = QPixmap(resource_path(image_path))
        img_label.setPixmap(pixmap.scaled(150, 120, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        img_label.setAlignment(Qt.AlignCenter)

        container.setCursor(Qt.PointingHandCursor)
        container.mousePressEvent = lambda event: on_click()
        
        img_label.setCursor(Qt.PointingHandCursor)
        img_label.mousePressEvent = lambda event: on_click()
        
        text_label = QLabel(label_text)
        text_label.setAlignment(Qt.AlignCenter)
        text_label.setFont(QFont("Arial", 10, QFont.Bold))
        text_label.setStyleSheet("background: transparent; border: none;")
        text_label.setCursor(Qt.PointingHandCursor)
        text_label.mousePressEvent = lambda event: on_click()


        layout.addWidget(img_label)
        layout.addWidget(text_label)
        return container

    
    def _profit_clicked(self):
        self._clear_main_layout()


        self.main_container = QWidget()
        self.setCentralWidget(self.main_container)


        outer_layout = QVBoxLayout(self.main_container)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        self.workspace_manager = WorkspaceManager(self)
        self.workspace_manager.setup(self)

        self.map_widget = MapWidget(self.workspace_manager)
        self.map_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.text_analysis_workspace = OptimizationTextAnalysisManager(self)
        self.text_analysis_workspace.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        center_splitter = QSplitter(Qt.Vertical)
        center_splitter.setHandleWidth(2)
        center_splitter.setStyleSheet("QSplitter::handle { background: black; }")
        center_splitter.addWidget(self.map_widget)
        center_splitter.addWidget(self.text_analysis_workspace)
        center_splitter.setSizes([420, 520])

        self.emissions_workspace = EmissionsWorkspaceManager(self)
        self.emissions_workspace.setup_layout()
        self.emissions_workspace.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.financial_workspace = FinancialWorkspaceManager(self)
        self.financial_workspace.setup_layout()
        self.financial_workspace.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.output_workspace = OptimizationWorkspaceManager(self)
        self.output_workspace.setup_layout()
        self.output_workspace.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)


        right_container = QWidget()
        right_container.setMinimumWidth(420)


        bordered_frame = QWidget()
        bordered_frame.setObjectName("BorderedFrame")
        bordered_frame.setStyleSheet("""
            #BorderedFrame {
                border: 4px solid black;
                background-color: white;
            }
        """)


        export_button = QPushButton("Export to Excel")
        export_button.setFixedHeight(32)
        export_button.setStyleSheet("""
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
        export_button.clicked.connect(self._export_results_to_excel)


        frame_layout = QGridLayout()
        frame_layout.setContentsMargins(8, 8, 8, 8)
        frame_layout.setSpacing(0)

        frame_layout.addWidget(export_button, 0, 0, 1, 2)
        frame_layout.addItem(QSpacerItem(0, 10, QSizePolicy.Minimum, QSizePolicy.Fixed), 1, 0, 1, 2)
        left_results_container = QWidget()
        left_results_layout = QVBoxLayout(left_results_container)
        left_results_layout.setContentsMargins(0, 0, 0, 0)
        left_results_layout.setSpacing(0)
        left_results_layout.addWidget(self.financial_workspace, stretch=1)
        left_results_layout.addWidget(self.emissions_workspace, stretch=1)

        frame_layout.addWidget(left_results_container, 2, 0)
        frame_layout.addWidget(self.output_workspace, 2, 1)
        frame_layout.setRowStretch(2, 1)
        frame_layout.setColumnStretch(0, 1)
        frame_layout.setColumnStretch(1, 1)

        bordered_frame.setLayout(frame_layout)


        container_layout = QVBoxLayout()
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.addWidget(bordered_frame)
        right_container.setLayout(container_layout)


        main_splitter = QSplitter(Qt.Horizontal)
        main_splitter.setHandleWidth(2)
        main_splitter.setStyleSheet("QSplitter::handle { background: black; }")
        main_splitter.addWidget(self.workspace_manager)
        main_splitter.addWidget(center_splitter)
        main_splitter.addWidget(right_container)
        main_splitter.setSizes([260, 900, 620])


        outer_layout.addWidget(main_splitter)


        self.toolbar.show()
    def _capacity_clicked(self):
        print("Capacity button clicked (placeholder)")

    def run_optimization(self, selected_inputs=None, input_metadata=None):
        self.selected_inputs = selected_inputs
        self.input_metadata = input_metadata

        preparator = PrepareData(self.workspace_manager)
        all_inputs = preparator.run_input_selection_flow(self)

        try:
            self.selected_inputs = all_inputs["selected_inputs"]
            self.input_metadata = all_inputs["input_metadata"]

            print(self.selected_inputs)
        except Exception:
            pass

        if not self.selected_inputs:
            print("⚠️ Optimization cancelled or no inputs selected.")
            return

        try:

            if "stochastic" in self.selected_inputs:
                from OptimizationStochastic import OptimizationInputPreparator, OptimizationPopup
            else:
                from OptimizationDeterministic import OptimizationInputPreparator, OptimizationPopup


            preparator = OptimizationInputPreparator(self.selected_inputs)
            self.optimization_popup = OptimizationPopup(self, preparator)
            self.optimization_popup.exec_()

        except Exception as e:
            print(f"❌ Optimization failed: {e}")

    def _export_results_to_excel(self):
        try:
            tab_index = self.output_workspace.tabs.currentIndex()
            if tab_index < 0:
                QMessageBox.warning(self, "No Tab Selected", "Please select an optimization tab to export.")
                return

            selected_inputs = self. output_workspace.selected_inputs_list[tab_index]
            optimization_data = self.output_workspace.optimizations[tab_index]
            financial_data = self.financial_workspace.financial_data[tab_index]
            emissions_data = self.emissions_workspace.emission_data[tab_index]
            metadata = self.financial_workspace.metadata_list[tab_index]
            tab_name = self.output_workspace.tabs.tabText(tab_index).replace(" ", "_").lower()

            export_to_excel(self, optimization_data, financial_data, emissions_data,
                            metadata, selected_inputs, tab_name)

        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export:\n{str(e)}")

    def _get_coords(self):
        return self.map_widget.get_coordinates() if hasattr(self, "map_widget") else (None, None)

    def _generation(self): lat, lon = self._get_coords(); GenerationPopupHandler(self, self.toolbar, lat, lon, self.workspace_manager).show_popup()
    def _storage(self): StoragePopupHandler(self, self.toolbar, self.workspace_manager).show_popup()
    def _thermal(self): lat, lon = self._get_coords(); ThermalDemandPopupHandler(self, self.toolbar, lat, lon, self.workspace_manager).show_popup()
    def _electricity(self): ElectricityDemandPopupHandler(self, self.toolbar, self.workspace_manager).show_popup()
    def _price(self): PricePopupHandler(self, self.toolbar, self.workspace_manager).show_popup()
    def _emissions(self): EmissionsPopupHandler(self, self.toolbar, self.workspace_manager).show_popup()
    def _thermal_emissions(self): ThermalEmissionsPopupHandler(self, self.toolbar, self.workspace_manager).show_popup()
    def _previous_system(self): PreviousSystemPopupHandler(self, self.toolbar, self.workspace_manager).show_popup()

    def _clear_main_layout(self):
        while self.main_layout.count():
            widget = self.main_layout.takeAt(0).widget()
            if widget: widget.setParent(None)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.showMaximized()
    sys.exit(app.exec_())