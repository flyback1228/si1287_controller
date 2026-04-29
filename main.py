# main.py
from functools import partial
from datetime import datetime
import json
import math
from pathlib import Path
import re
import sqlite3
import sys
from typing import List

from PyQt6 import QtCore, QtWidgets, uic, QtGui, QtCharts
import pyvisa

from visa_worker import VisaWorker, Sample

from ramp_sweep_window import RampSweepWindow
from si1287_setup import Si1287Setup
from step_sweep_window import StepSweepWindow
from status_led import StatusLed
# from qtpy_led import Led

def _theme_arrow_icon_paths():
    assets_dir = Path(__file__).resolve().parent / "assets"
    return (
        (assets_dir / "ubuntu_combo_down.svg").as_posix(),
        (assets_dir / "ubuntu_spin_up.svg").as_posix(),
        (assets_dir / "ubuntu_spin_down.svg").as_posix(),
    )

def apply_blue_style(app: QtWidgets.QApplication):
    app.setStyle("Fusion")

    combo_down_icon, spin_up_icon, spin_down_icon = _theme_arrow_icon_paths()
    qss = """
    QMainWindow {
        background: #f0f2f5;
    }

    QWidget {
        background: #f0f2f5;
        color: #1c1e21;
        font-size: 12px;
        selection-background-color: #dbe7ff;
        selection-color: #1c1e21;
    }

    QWidget#centralwidget {
        background: #f0f2f5;
    }

    QMenuBar {
        background: #ffffff;
        border-bottom: 1px solid #d8dde6;
        padding: 6px 10px;
    }

    QMenuBar::item {
        background: transparent;
        border-radius: 8px;
        padding: 6px 10px;
    }

    QMenuBar::item:selected {
        background: #eef3ff;
        color: #1877f2;
    }

    QMenu {
        background: #ffffff;
        border: 1px solid #d8dde6;
        border-radius: 10px;
        padding: 8px;
    }

    QMenu::item {
        border-radius: 8px;
        padding: 8px 26px 8px 12px;
    }

    QMenu::item:selected {
        background: #eef3ff;
        color: #1877f2;
    }

    QStatusBar {
        background: #ffffff;
        border-top: 1px solid #d8dde6;
        color: #606770;
    }

    QLabel {
        color: #1c1e21;
    }

    QGroupBox {
        background: #ffffff;
        border: 1px solid #d8dde6;
        border-radius: 12px;
        margin-top: 16px;
        padding: 14px;
    }

    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top left;
        left: 12px;
        padding: 0 8px;
        color: #65676b;
        font-weight: 600;
    }

    QPushButton {
        background: #e4e6eb;
        color: #050505;
        border: 1px solid #d8dde6;
        border-radius: 10px;
        padding: 8px 14px;
        min-height: 14px;
        font-weight: 600;
    }

    QPushButton:hover {
        background: #d8dadf;
        border-color: #cfd4dd;
    }

    QPushButton:pressed {
        background: #ccd0d5;
    }

    QPushButton:disabled {
        background: #f0f2f5;
        color: #bcc0c4;
        border-color: #e4e6eb;
    }

    QPushButton[fbRole="primary"] {
        background: #1877f2;
        color: white;
        border-color: #1877f2;
    }

    QPushButton[fbRole="primary"]:hover {
        background: #166fe5;
        border-color: #166fe5;
    }

    QPushButton[fbRole="primary"]:pressed {
        background: #1464d6;
        border-color: #1464d6;
    }

    QPushButton[fbRole="danger"] {
        background: #ffffff;
        color: #d93025;
        border-color: #f1b9b4;
    }

    QPushButton[fbRole="danger"]:hover {
        background: #fff1f0;
        border-color: #e59b94;
    }

    QComboBox,
    QLineEdit {
        background: #ffffff;
        border: 1px solid #bcc5d3;
        border-radius: 8px;
        padding: 6px 10px;
        min-height: 20px;
        color: #1c1e21;
    }

    QSpinBox, QDoubleSpinBox {
        background: #ffffff;
        border: 1px solid #bcc5d3;
        border-radius: 8px;
        padding-left: 10px;
        padding-right: 28px;
        min-height: 20px;
        color: #1c1e21;
    }

    QComboBox:hover,
    QLineEdit:hover,
    QSpinBox:hover,
    QDoubleSpinBox:hover {
        border-color: #8ea0b8;
        background: #ffffff;
    }

    QComboBox:focus,
    QLineEdit:focus,
    QSpinBox:focus,
    QDoubleSpinBox:focus {
        background: #ffffff;
        border: 1px solid #1877f2;
    }

    QComboBox {
        padding-right: 30px;
    }

    QComboBox::drop-down {
        subcontrol-origin: padding;
        subcontrol-position: top right;
        width: 24px;
        border: none;
        border-left: 1px solid #d8dde6;
        background: #f7f8fa;
        border-top-right-radius: 8px;
        border-bottom-right-radius: 8px;
    }

    QComboBox::drop-down:hover {
        background: #eef3ff;
    }

    QComboBox::down-arrow {
        image: url(__COMBO_DOWN_ICON__);
        width: 10px;
        height: 6px;
        margin-right: 7px;
    }

    QComboBox QAbstractItemView {
        background: #ffffff;
        color: #1c1e21;
        border: 1px solid #c7cfdb;
        border-radius: 8px;
        padding: 4px;
        selection-background-color: #eaf2ff;
        selection-color: #1c1e21;
        outline: 0;
    }

    QSpinBox::up-button, QDoubleSpinBox::up-button {
        subcontrol-origin: border;
        subcontrol-position: top right;
        width: 18px;
        border: none;
        border-left: 1px solid #d8dde6;
        background: #f7f8fa;
        border-top-right-radius: 8px;
    }

    QSpinBox::down-button, QDoubleSpinBox::down-button {
        subcontrol-origin: border;
        subcontrol-position: bottom right;
        width: 18px;
        border: none;
        border-left: 1px solid #d8dde6;
        background: #f7f8fa;
        border-bottom-right-radius: 8px;
    }

    QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
    QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {
        background: #eef3ff;
    }

    QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {
        image: url(__SPIN_UP_ICON__);
        width: 8px;
        height: 6px;
    }

    QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {
        image: url(__SPIN_DOWN_ICON__);
        width: 8px;
        height: 6px;
    }

    QComboBox:disabled,
    QLineEdit:disabled,
    QSpinBox:disabled,
    QDoubleSpinBox:disabled {
        background: #f5f6f7;
        color: #9aa1ac;
        border-color: #d9dee7;
    }

    QTabWidget::pane {
        border: 1px solid #d8dde6;
        border-radius: 12px;
        background: #ffffff;
        top: -1px;
    }

    QTabBar::tab {
        background: transparent;
        border: none;
        border-bottom: 3px solid transparent;
        color: #65676b;
        padding: 10px 16px;
        margin-right: 2px;
        font-weight: 600;
    }

    QTabBar::tab:selected {
        color: #1877f2;
        border-bottom-color: #1877f2;
    }

    QTabBar::tab:hover {
        background: #f2f4f7;
        border-top-left-radius: 10px;
        border-top-right-radius: 10px;
    }

    QFrame#plotFrame,
    QPlainTextEdit,
    QChartView {
        background: #ffffff;
        border: 1px solid #d8dde6;
        border-radius: 12px;
    }

    QPlainTextEdit {
        color: #1c1e21;
        padding: 8px;
        selection-background-color: #dbe7ff;
    }

    QScrollBar:vertical {
        background: transparent;
        width: 12px;
        margin: 6px 2px 6px 2px;
    }

    QScrollBar::handle:vertical {
        background: #c9ccd1;
        border-radius: 6px;
        min-height: 20px;
    }

    QScrollBar::handle:vertical:hover {
        background: #b4b8bf;
    }

    QScrollBar::add-line:vertical,
    QScrollBar::sub-line:vertical,
    QScrollBar::add-page:vertical,
    QScrollBar::sub-page:vertical {
        background: none;
        border: none;
        height: 0px;
    }

    QToolTip {
        background: #ffffff;
        color: #1c1e21;
        border: 1px solid #ccd0d5;
        border-radius: 8px;
        padding: 6px 8px;
    }
    """
    qss = (
        qss
        .replace("__COMBO_DOWN_ICON__", combo_down_icon)
        .replace("__SPIN_UP_ICON__", spin_up_icon)
        .replace("__SPIN_DOWN_ICON__", spin_down_icon)
    )

    app.setStyleSheet(qss)
    app.setFont(QtGui.QFont("Segoe UI", 10))

def create_app_icon() -> QtGui.QIcon:
    icon = QtGui.QIcon()
    for size in (16, 24, 32, 48, 64, 128):
        pix = QtGui.QPixmap(size, size)
        pix.fill(QtCore.Qt.GlobalColor.transparent)

        p = QtGui.QPainter(pix)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)

        # Rounded tile aligned with the Facebook-inspired accent color.
        rect = QtCore.QRectF(1, 1, size - 2, size - 2)
        p.setPen(QtCore.Qt.PenStyle.NoPen)
        p.setBrush(QtGui.QColor("#1877f2"))
        p.drawRoundedRect(rect, size * 0.22, size * 0.22)

        # White trace line to suggest measurement/plot behavior.
        pen = QtGui.QPen(QtGui.QColor("white"), max(1.6, size * 0.09))
        pen.setCapStyle(QtCore.Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(QtCore.Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        path = QtGui.QPainterPath()
        path.moveTo(size * 0.18, size * 0.62)
        path.lineTo(size * 0.36, size * 0.62)
        path.lineTo(size * 0.48, size * 0.30)
        path.lineTo(size * 0.62, size * 0.72)
        path.lineTo(size * 0.82, size * 0.72)
        p.drawPath(path)
        p.end()

        icon.addPixmap(pix)
    return icon


class MainWindow(QtWidgets.QMainWindow):
    # UI â†’ worker signals (queued)
    connectRequested = QtCore.pyqtSignal(str)
    disconnectRequested = QtCore.pyqtSignal()
    # applySetupRequested = QtCore.pyqtSignal(list)
    startStreamRequested = QtCore.pyqtSignal(int,int)
    stopStreamRequested = QtCore.pyqtSignal()
    startPolarizationRequested = QtCore.pyqtSignal()
    stopPolarizationRequested = QtCore.pyqtSignal()
    # identifyRequested = QtCore.pyqtSignal()
    # statusRequested = QtCore.pyqtSignal()
    # lastErrorRequested = QtCore.pyqtSignal()
    # clearErrorRequested = QtCore.pyqtSignal()
    # setModeRequested = QtCore.pyqtSignal(int)
    # breakSelfTestRequested = QtCore.pyqtSignal(int)

    configurationChanged = QtCore.pyqtSignal(str, object)

    def __init__(self):
        super().__init__()
        uic.loadUi("si1287_main.ui", self)
        # Favor chart area over log area in the bottom section.
        self.verticalLayout.setStretch(2, 3)
        self.verticalLayout.setStretch(3, 1)
        self.setWindowIcon(create_app_icon())
        self._build_menu_bar()
        
        self.connLed = StatusLed(14)
        self.statusBar().addPermanentWidget(QtWidgets.QLabel("Instrument Connection:"))
        self.statusBar().addPermanentWidget(self.connLed)
        self.connLed.set_connected(False)
        
        self.polarizationLed = StatusLed(14)
        self.statusBar().addPermanentWidget(QtWidgets.QLabel("Polarization:"))
        self.statusBar().addPermanentWidget(self.polarizationLed)
        self.polarizationLed.set_connected(False)

        self.errorLed = StatusLed(14)
        self.statusBar().addPermanentWidget(QtWidgets.QLabel("Instrument Error:"))
        self.statusBar().addPermanentWidget(self.errorLed)
        self.errorLed.set_connected(False)

        self.sweepLed = StatusLed(14)
        self.sweepStatusLabel = QtWidgets.QLabel("Idle")
        self.statusBar().addPermanentWidget(QtWidgets.QLabel("Sweep:"))
        self.statusBar().addPermanentWidget(self.sweepLed)
        self.statusBar().addPermanentWidget(self.sweepStatusLabel)
        self.sweepLed.set_connected(False)
        self._apply_facebook_widget_roles()

        # -------- Plot --------
        self.chart = QtCharts.QChart()
        self.chart.legend().setVisible(True)
        self.chart.setBackgroundVisible(False)
        self.chart.setMargins(QtCore.QMargins(16, 16, 16, 16))

        self.seriesA = QtCharts.QLineSeries()
        self.seriesA.setName("A")
        self.seriesA.setColor(QtGui.QColor("#1877f2"))

        self.seriesB = QtCharts.QLineSeries()
        self.seriesB.setName("B")
        self.seriesB.setColor(QtGui.QColor("#42b72a"))

        self.chart.addSeries(self.seriesA)
        self.chart.addSeries(self.seriesB)

        self.axisX = QtCharts.QValueAxis()
        self.axisX.setTitleText("Time (s)")
        self.axisX.setLabelFormat("%.2f")
        self.axisX.setRange(0.0, 1.0)

        self.axisYLeft = QtCharts.QValueAxis()
        self.axisYLeft.setTitleText("A")
        self.axisYLeft.setLabelFormat("%.3g")
        self.axisYLeft.setRange(-1.0, 1.0)

        self.axisYRight = QtCharts.QValueAxis()
        self.axisYRight.setTitleText("B")
        self.axisYRight.setLabelFormat("%.3g")
        self.axisYRight.setRange(-1.0, 1.0)

        self.chart.addAxis(self.axisX, QtCore.Qt.AlignmentFlag.AlignBottom)
        self.chart.addAxis(self.axisYLeft, QtCore.Qt.AlignmentFlag.AlignLeft)
        self.chart.addAxis(self.axisYRight, QtCore.Qt.AlignmentFlag.AlignRight)
        self.seriesA.attachAxis(self.axisX)
        self.seriesA.attachAxis(self.axisYLeft)
        self.seriesB.attachAxis(self.axisX)
        self.seriesB.attachAxis(self.axisYRight)

        self.plotWidget = QtCharts.QChartView(self.chart)
        self.plotWidget.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        self.plotFrameLayout.addWidget(self.plotWidget)
        self.plotPlaceholderLabel.hide()
        self._apply_chart_theme()

        self.t: List[float] = []
        self.a: List[float] = []
        self.b: List[float] = []
        self.max_points = 2000
        self._is_connected = False
        self._polarization_on = False
        self._db_conn: sqlite3.Connection | None = None
        self._db_cursor: sqlite3.Cursor | None = None
        self._db_path = "si1287_data.db"
        self._db_table_name = ""
        self._saving_to_db = False
        self._updating_compensation_checks = False
        self._sweep_defaults_path = Path(__file__).resolve().parent / "sweep_defaults.json"

        # -------- Setup text --------
        # if not self.setupText.toPlainText().strip():
        #     self.setupText.setPlainText("\n".join(DEFAULT_SETUP_CMDS))

        # -------- Worker thread --------
        self.worker = VisaWorker()
        self.thread = QtCore.QThread(self)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.start)
        self.thread.start()

        # Worker â†’ UI
        self.worker.logLine.connect(self.append_log)
        self.worker.connectedChanged.connect(self.on_connected_changed)
        self.worker.sampleReady.connect(self.on_sample)
        self.worker.errorStatusChanged.connect(self.on_error_status_changed)

        # UI â†’ Worker (queued)
        q = QtCore.Qt.ConnectionType.QueuedConnection
        self.connectRequested.connect(self.worker.connectVisa, q)
        self.disconnectRequested.connect(self.worker.disconnectVisa, q)
        self.startStreamRequested.connect(self.worker.start_stream, q)
        self.stopStreamRequested.connect(self.worker.stop_stream, q)
        self.startPolarizationRequested.connect(self.worker.start_polarization, q)
        self.stopPolarizationRequested.connect(self.worker.stop_polarization, q)
        self.actionIdentify.triggered.connect(lambda: self.configurationChanged.emit("?VN", None))
        self.actionInstrumentStatus.triggered.connect(lambda: self.configurationChanged.emit("?ST", None))
        # self.lastErrorRequested.connect(self.worker.last_error, q)
        # self.clearErrorRequested.connect(self.worker.clear_error, q)
        # self.setModeRequested.connect(self.worker.set_mode, q)
        # self.breakSelfTestRequested.connect(self.worker.break_self_test,q)
        
        self.configurationChanged.connect(self.worker.handle_si1287_configuration,q)

        
        

        # -------- Buttons --------
        self.connectButton.clicked.connect(self._connect_clicked)
        self.closeButton.clicked.connect(self._close_clicked )

        # self.identifyButton.clicked.connect(lambda: self.identifyRequested.emit())
        # self.statusButton.clicked.connect(lambda: self.statusRequested.emit())
        self.actionLastError.triggered.connect(lambda: self.configurationChanged.emit("?ER", None))
        self.actionClearError.triggered.connect(lambda: self.configurationChanged.emit("?CE", None))
        
        self.actionBreak.triggered.connect(lambda: self.configurationChanged.emit("BK", 0))
        self.actionSelfTest.triggered.connect(lambda: self.configurationChanged.emit("BK", 1))
        self.actionReset.triggered.connect(lambda: self.configurationChanged.emit("BK", 3))
        self.actionInitialize.triggered.connect(lambda: self.configurationChanged.emit("BK", 4))

        # self.potentiostatButton.clicked.connect(lambda: self.setModeRequested.emit(0))
        # self.galvanostatButton.clicked.connect(lambda: self.setModeRequested.emit(1))

        self.applySetupButton.clicked.connect(self._apply_setup_clicked)
        self.startStreamButton.clicked.connect(self._start_stream_clicked)
        self.stopStreamButton.clicked.connect(self._stop_stream_clicked)
        self.startSaveToDbButton.clicked.connect(self._start_save_to_db_clicked)
        self.stopSaveToDbButton.clicked.connect(self._stop_save_to_db_clicked)
        self.exportPlotButton.clicked.connect(self.export_plot)
        
        self.refreshButton.clicked.connect(self._populate_visa_resources)

        self.polarzation_mode = -1
        self.standby_mode = -1
        # 6.1  CELL POLARIZATION 
        # 6.2 STANDBY STATE
        # 6.3 POLARIZATION ON MODE
        # self.polarizationModeCombo.currentIndexChanged.connect(lambda idx: self.configurationChanged.emit("PO", idx))
        self.polarizationModeCombo.currentIndexChanged.connect(self.polarization_mode_combo_index_changed)
        self.dcPotentialSpin.valueChanged.connect(self.dc_potential_spin_value_changed)
        self.standbyModeCombo.currentIndexChanged.connect(self.standby_mode_combo_index_changed)
        self.polarizationOnModeCombo.currentIndexChanged.connect(lambda idx: self.configurationChanged.emit("ON", idx))
        self.polarizationSignalGainCombo.setCurrentIndex(1)
        self.polarizationSignalGainCombo.currentIndexChanged.connect(lambda idx: self.configurationChanged.emit("PI", idx))

        self.worker.polarizationChanged.connect(self.on_polarization_changed)
        self.startPolarizationButton.clicked.connect(self._start_polarization_clicked)
        self.stopPolarizationButton.clicked.connect(self._stop_polarization_clicked)

        # 6.4 CONTROL LOOP BANDWIDTH
        self.bandwidthCombo.currentIndexChanged.connect(self.bandwidth_combo_index_changed)
        self.bandwidthGalvanostatCombo.setCurrentIndex(2)
        self.bandwidthGalvanostatCombo.currentIndexChanged.connect(lambda idx: self.configurationChanged.emit("GB", idx))
        self.bandwidthPotentiostatCombo.setCurrentIndex(2)
        self.bandwidthPotentiostatCombo.currentIndexChanged.connect(lambda idx: self.configurationChanged.emit("PB", idx))

        # 6.5 STANDARD RESISTOR SELECTION
        self.standardResistantCombo.currentIndexChanged.connect(lambda idx: self.configurationChanged.emit("RR", idx))
        # 6.6 CURRENT LIMIT SELECTION (In conjunction with Auto-range RR0)
        self.currentLimitCombo.setCurrentIndex(6)
        self.currentLimitCombo.currentIndexChanged.connect(lambda idx: self.configurationChanged.emit("IL", idx))
        # 6.7 CURRENT OFF-LIMIT ACTION
        self.currentOffLimitActionCombo.currentIndexChanged.connect(lambda idx: self.configurationChanged.emit("OL", idx))

        # 6.8 IR COMPENSATION TYPE AND ON/OFF
        self.compensationCombo.currentIndexChanged.connect(self.compensation_combo_index_changed)
        self.irCompensationCheckBox.toggled.connect(self.ir_compensation_checkbox_toggled)
        self.realPartCorrectionCheckBox.toggled.connect(self.realpart_correction_checkbox_toggled)
        self.irCompensationTypeCombo.currentIndexChanged.connect(lambda idx: self.ir_compensation_type_changed(idx))
        # 6.9 FEEDBACK IR COMPENSATION
        self.feedbackCompensationSpin.valueChanged.connect(lambda val: self.configurationChanged.emit("IC", val))
        # 6.10 6.10 SAMPLED IR COMPENSATION
        self.cellCurrentOffTimeTypeCombo.setEnabled(False)
        self.outputToFRACombo.setEnabled(False)
        self.cellCurrentOffTimeSpin.setEnabled(False)
        self.cellCurrentOffRatioSpin.setEnabled(False)

        self.outputToFRACombo.currentIndexChanged.connect(lambda idx: self.configurationChanged.emit("RO", idx))
        self.cellCurrentOffTimeTypeCombo.currentIndexChanged.connect(self.cell_current_off_time_type_combo_index_changed)
        self.cellCurrentOffTimeSpin.valueChanged.connect(lambda val: self.configurationChanged.emit("IN", val) )
        self.cellCurrentOffRatioSpin.valueChanged.connect(lambda val: self.configurationChanged.emit("IF", int(val)))

        # 6.11 REAL PART CORRECTION
        self.realPartCorrectionSpin.valueChanged.connect(lambda val: self.configurationChanged.emit("RP", val))

        # 6.12 Output conditioning facilities
        self.voltageBiasSpin.setEnabled(False)
        self.currentBiasSpin.setEnabled(False)
        self.voltageBiasCombo.currentIndexChanged.connect(self.voltage_bias_combo_index_changed)
        self.voltageBiasSpin.valueChanged.connect(lambda val: self.configurationChanged.emit("VR", val))
        self.currentBiasCombo.currentIndexChanged.connect(self.current_bias_combo_index_changed)
        self.currentBiasSpin.valueChanged.connect(lambda val: self.configurationChanged.emit("IR", val))

        self.biasRejectCombo.currentIndexChanged.connect(lambda idx: self.configurationChanged.emit("BR", idx))
        self.filterCombo.currentIndexChanged.connect(lambda idx: self.configurationChanged.emit("FI", idx))
        self.voltageAmplificationCombo.currentIndexChanged.connect(lambda idx: self.configurationChanged.emit("VX", idx))
        self.currentAmplificationCombo.currentIndexChanged.connect(lambda idx: self.configurationChanged.emit("IX", idx))
        
        # 6.16 DVM Control Functions
        self.numberOfDigitsCombo.currentIndexChanged.connect(lambda idx: self.configurationChanged.emit("DG", idx))
        self.inputRangeCombo.currentIndexChanged.connect(lambda idx: self.configurationChanged.emit("RG", idx))
        self.measurementTriggerCombo.setCurrentIndex(1)
        self.measurementTriggerCombo.currentIndexChanged.connect(lambda idx: self.configurationChanged.emit("TR", idx))
        self.driftCombo.currentIndexChanged.connect(lambda idx: self.configurationChanged.emit("DC", idx))
        self.averagingtCombo.currentIndexChanged.connect(lambda idx: self.configurationChanged.emit("AV", idx))
        self.nullCombo.currentIndexChanged.connect(lambda idx: self.configurationChanged.emit("NU", idx))
        self.digitalVolmeterCombo.setCurrentIndex(1)
        self.digitalVolmeterCombo.currentIndexChanged.connect(lambda idx: self.configurationChanged.emit("RU", idx))
        
        # 6.17 OUTPUT Parameter Selection
        
        self.outputXCombo.setCurrentIndex(3)
        self.outputYCombo.setCurrentIndex(5)
        self.outputXCombo.currentIndexChanged.connect(lambda idx: self.configurationChanged.emit("PX", idx))
        self.outputYCombo.currentIndexChanged.connect(lambda idx: self.configurationChanged.emit("PY", idx))
        self.outputXCombo.currentIndexChanged.connect(self._update_plot_series_names)
        self.outputYCombo.currentIndexChanged.connect(self._update_plot_series_names)
     
        self.displayLeftCombo.setCurrentIndex(3)
        self.displayRightCombo.setCurrentIndex(5)
        self.displayLeftCombo.currentIndexChanged.connect(lambda idx: self.configurationChanged.emit("UL", idx))
        self.displayRightCombo.currentIndexChanged.connect(lambda idx: self.configurationChanged.emit("UR", idx))

        self.setup = Si1287Setup()
        self.applySetupButton.setEnabled(False)

        self.saveSetupButton.clicked.connect(self.save_setup)
        self.loadSetupButton.clicked.connect(self.load_setup)
        
        # -------- VISA resource enumeration --------
        self._populate_visa_resources()
        self._update_plot_series_names()
        self._update_polarization_value_label(self.polarizationModeCombo.currentIndex())
        self.compensationCombo.currentIndexChanged.emit(0)

        # Initial state
        # self._set_controls_enabled(False)
        # self.disconnectButton.setEnabled(False)
        self.stopSaveToDbButton.setEnabled(False)
        self._step_sweep_values = {
            "off_mode": 0,
            "delay": 0,
            "segments": 2,
            "v1": 0.0,
            "v2": 0.0,
            "v3": 0.0,
            "v4": 0.0,
            "time": 0.0,
            "v_step": 0.0,
        }
        self._ramp_sweep_values = {
            "off_mode": 0,
            "delay": 0,
            "segments": 2,
            "filter": 0,
            "v1": 0.0,
            "v2": 0.0,
            "v3": 0.0,
            "v4": 0.0,
            "t1": 0.0,
            "t2": 0.0,
            "t3": 0.0,
            "t4": 0.0,
        }
        self._sweep_running = False
        self._active_sweep_type: str | None = None
        self._sweep_status_timer = QtCore.QTimer(self)
        self._sweep_status_timer.setInterval(2000)
        self._sweep_status_timer.timeout.connect(self._poll_sweep_status)
        self._load_sweep_defaults()
        self.stepSweepDialog = StepSweepWindow(self)
        self.stepSweepDialog.runButton.clicked.connect(self._start_step_sweep_from_dialog)
        self.stepSweepDialog.runButton_2.clicked.connect(self.stop_sweep_action_clicked)
        self.stepSweepDialog.valuesSaved.connect(self._save_step_sweep_values)
        self.stepSweepDialog.load_from_values(self._step_sweep_values)
        self.stepSweepDialog.set_polarization_mode(self.polarizationModeCombo.currentIndex())
        self.rampSweepDialog = RampSweepWindow(self)
        self.rampSweepDialog.startRampSweep.clicked.connect(self._start_ramp_sweep_from_dialog)
        self.rampSweepDialog.runRampSweep.clicked.connect(self.stop_sweep_action_clicked)
        self.rampSweepDialog.valuesSaved.connect(self._save_ramp_sweep_values)
        self.rampSweepDialog.load_from_values(self._ramp_sweep_values)
        self.rampSweepDialog.set_polarization_mode(self.polarizationModeCombo.currentIndex())
        self._set_sweep_dialogs_running(False)

    # ---------------- VISA enumeration ----------------
    def _populate_visa_resources(self):
        self.resourceCombo.clear()
        try:
            rm = pyvisa.ResourceManager()
            resources = rm.list_resources()
            rm.close()

            if not resources:
                self.resourceCombo.addItem("No VISA resources found")
                self.resourceCombo.setEnabled(False)
                return

            self.resourceCombo.addItems(resources)
            self.resourceCombo.setEnabled(True)

            # Prefer GPIB instruments
            for i, r in enumerate(resources):
                if r.startswith("GPIB"):
                    self.resourceCombo.setCurrentIndex(i)
                    break

            self.append_log(f"VISA resources found: {resources}")

        except Exception as e:
            self.resourceCombo.addItem("VISA not available")
            self.resourceCombo.setEnabled(False)
            self.append_log(f"VISA scan failed: {e}")

    # ---------------- UI handlers ----------------
    def closeEvent(self, event):
        if not self._allow_disconnect_or_exit():
            event.ignore()
            return

        self._persist_sweep_defaults()
        self._stop_db_session()
        try:
            self.disconnectRequested.emit()
        except Exception:
            pass
        try:
            if self.thread.isRunning():
                QtCore.QMetaObject.invokeMethod(
                    self.worker,
                    "shutdown",
                    QtCore.Qt.ConnectionType.BlockingQueuedConnection,
                )
        except Exception:
            pass
        self.thread.quit()
        self.thread.wait(2000)
        super().closeEvent(event)

    def _allow_disconnect_or_exit(self) -> bool:
        if not self._polarization_on:
            return True

        msg = "Stop polarization before disconnecting or exiting the program."
        self.append_log(msg)
        QtWidgets.QMessageBox.warning(self, "Polarization Active", msg)
        return False

    def _connect_clicked(self):
        if not self.resourceCombo.isEnabled():
            return
        res = self.resourceCombo.currentText()
        self.append_log(f"UI: Connect clicked ({res})")
        self.connectRequested.emit(res)
        
    def _close_clicked(self):
        if not self._allow_disconnect_or_exit():
            return
        self.disconnectRequested.emit()

    def _apply_setup_clicked(self):
        if not self._is_connected:
            self.append_log("Connect to the instrument before applying setup.")
            return

        compensation_on = self.compensationCombo.currentIndex() == 1
        ir_on = compensation_on and self.irCompensationCheckBox.isChecked()
        rp_on = compensation_on and self.realPartCorrectionCheckBox.isChecked()
        fixed_type_c = self.bandwidthCombo.currentIndex() == 1
        sampled_ir = ir_on and self.irCompensationTypeCombo.currentIndex() == 1
        time_mode = self.cellCurrentOffTimeTypeCombo.currentIndex() == 0

        commands: list[tuple[str, object]] = [
            ("SY", self.bandwidthCombo.currentIndex()),
            ("RR", self.standardResistantCombo.currentIndex()),
            ("IL", self.currentLimitCombo.currentIndex()),
            ("OL", self.currentOffLimitActionCombo.currentIndex()),
            ("CC", 1 if ir_on else 2 if rp_on else 0),
            ("VT", self.voltageBiasCombo.currentIndex()),
            ("IT", self.currentBiasCombo.currentIndex()),
            ("BR", self.biasRejectCombo.currentIndex()),
            ("FI", self.filterCombo.currentIndex()),
            ("VX", self.voltageAmplificationCombo.currentIndex()),
            ("IX", self.currentAmplificationCombo.currentIndex()),
            ("DG", self.numberOfDigitsCombo.currentIndex()),
            ("RG", self.inputRangeCombo.currentIndex()),
            ("TR", self.measurementTriggerCombo.currentIndex()),
            ("DC", self.driftCombo.currentIndex()),
            ("AV", self.averagingtCombo.currentIndex()),
            ("NU", self.nullCombo.currentIndex()),
            ("RU", self.digitalVolmeterCombo.currentIndex()),
            ("PX", self.outputXCombo.currentIndex()),
            ("PY", self.outputYCombo.currentIndex()),
            ("UL", self.displayLeftCombo.currentIndex()),
            ("UR", self.displayRightCombo.currentIndex()),
        ]

        if not fixed_type_c:
            commands.append(("GB", self.bandwidthGalvanostatCombo.currentIndex()))
            commands.append(("PB", self.bandwidthPotentiostatCombo.currentIndex()))

        if ir_on:
            commands.append(("CT", self.irCompensationTypeCombo.currentIndex()))
            if sampled_ir:
                commands.append(("RO", self.outputToFRACombo.currentIndex()))
                if time_mode:
                    commands.append(("IN", self.cellCurrentOffTimeSpin.value()))
                else:
                    commands.append(("IF", int(self.cellCurrentOffRatioSpin.value())))
            else:
                commands.append(("IC", self.feedbackCompensationSpin.value()))

        if self.voltageBiasCombo.currentIndex() == 1:
            commands.append(("VR", self.voltageBiasSpin.value()))
        if self.currentBiasCombo.currentIndex() == 1:
            commands.append(("IR", self.currentBiasSpin.value()))
        if rp_on:
            commands.append(("RP", self.realPartCorrectionSpin.value()))

        for cmd, value in commands:
            self.configurationChanged.emit(cmd, value)

        self.applySetupButton.setEnabled(False)
        self.append_log(f"Applied setup to instrument ({len(commands)} commands).")

    def _start_stream_clicked(self):
        if not self._is_connected:
            self.append_log("Connect to the instrument before starting stream.")
            return

        self.t.clear()
        self.a.clear()
        self.b.clear()
        self.seriesA.clear()
        self.seriesB.clear()
        self.axisX.setRange(0.0, 1.0)
        self.axisYLeft.setRange(-1.0, 1.0)
        self.axisYRight.setRange(-1.0, 1.0)

        # Ensure the SI1287 is actively measuring and routing the selected
        # outputs before GP1 asks it to stream readings.
        self.configurationChanged.emit("TR", self.measurementTriggerCombo.currentIndex())
        self.configurationChanged.emit("RU", self.digitalVolmeterCombo.currentIndex())
        # self.configurationChanged.emit("PX", self.outputXCombo.currentIndex())
        # self.configurationChanged.emit("PY", self.outputYCombo.currentIndex())
        self.startStreamRequested.emit(self.outputXCombo.currentIndex(), self.outputYCombo.currentIndex())
        self.startStreamButton.setEnabled(False)
        self.stopStreamButton.setEnabled(True)

    def _stop_stream_clicked(self):
        self.stopStreamRequested.emit()
        self.startStreamButton.setEnabled(True)
        self.stopStreamButton.setEnabled(False)

    def _sanitize_db_identifier(self, value: str) -> str:
        cleaned = re.sub(r"[^0-9A-Za-z_]+", "_", value.strip())
        cleaned = re.sub(r"_+", "_", cleaned).strip("_")
        if not cleaned:
            cleaned = "value"
        if cleaned[0].isdigit():
            cleaned = f"v_{cleaned}"
        return cleaned.lower()

    def _build_db_table_name(self) -> str:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        label1 = self._sanitize_db_identifier(self.seriesA.name())
        label2 = self._sanitize_db_identifier(self.seriesB.name())
        return f"run_{stamp}_{label1}_{label2}_pol"

    def _load_sweep_defaults(self):
        try:
            if not self._sweep_defaults_path.exists():
                return
            data = json.loads(self._sweep_defaults_path.read_text(encoding="utf-8"))
        except Exception as e:
            self.append_log(f"Failed to load sweep defaults: {e}")
            return

        step_values = data.get("step")
        if isinstance(step_values, dict):
            self._step_sweep_values.update(step_values)
        ramp_values = data.get("ramp")
        if isinstance(ramp_values, dict):
            self._ramp_sweep_values.update(ramp_values)

    def _persist_sweep_defaults(self):
        data = {
            "step": self._step_sweep_values,
            "ramp": self._ramp_sweep_values,
        }
        try:
            self._sweep_defaults_path.write_text(
                json.dumps(data, indent=2),
                encoding="utf-8",
            )
        except Exception as e:
            self.append_log(f"Failed to save sweep defaults: {e}")

    def _save_step_sweep_values(self, values: dict[str, int | float]):
        self._step_sweep_values = dict(values)
        self._persist_sweep_defaults()

    def _save_ramp_sweep_values(self, values: dict[str, int | float]):
        self._ramp_sweep_values = dict(values)
        self._persist_sweep_defaults()

    def _stop_db_session(self):
        if self._db_conn is not None:
            try:
                self._db_conn.commit()
            except Exception:
                pass
            try:
                self._db_conn.close()
            except Exception:
                pass
        self._db_conn = None
        self._db_cursor = None
        self._db_table_name = ""
        self._saving_to_db = False
        self.startSaveToDbButton.setEnabled(True)
        self.stopSaveToDbButton.setEnabled(False)

    def _start_save_to_db_clicked(self):
        # if not self._polarization_on:
        #     self.append_log("Turn polarization on before saving data to the database.")
        #     return

        if self._saving_to_db:
            self.append_log(f"Already saving data to table: {self._db_table_name}")
            return

        table_name = self._build_db_table_name()
        try:
            conn = sqlite3.connect(self._db_path)
            cursor = conn.cursor()
            cursor.execute(
                f"""
                CREATE TABLE IF NOT EXISTS "{table_name}" (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    current_time TEXT NOT NULL,
                    value1 REAL,
                    value2 REAL
                )
                """
            )
            conn.commit()
        except Exception as e:
            self.append_log(f"Failed to start database save: {e}")
            try:
                conn.close()
            except Exception:
                pass
            return

        self._db_conn = conn
        self._db_cursor = cursor
        self._db_table_name = table_name
        self._saving_to_db = True
        self.startSaveToDbButton.setEnabled(False)
        self.stopSaveToDbButton.setEnabled(True)
        self.append_log(
            f"Saving stream data to {self._db_path} table {table_name!r}."
        )

    def _stop_save_to_db_clicked(self):
        if not self._saving_to_db:
            self.append_log("Database saving is not active.")
            return
        table_name = self._db_table_name
        self._stop_db_session()
        self.append_log(f"Stopped saving stream data for table {table_name!r}.")

    def _start_polarization_clicked(self):
        if not self._is_connected:
            self.append_log("Connect to the instrument before starting polarization.")
            return

        if self.polarizationModeCombo.currentIndex() < 0:
            self.append_log("Select Cell Polarization Mode before starting polarization.")
            return

        if self.standbyModeCombo.currentIndex() < 0:
            self.append_log("Select Standby Mode before starting polarization.")
            return

        # Re-send the active polarization setup so PW1 is evaluated against
        # the current UI state every time the user starts polarization.
        self.configurationChanged.emit("PO", self.polarizationModeCombo.currentIndex())
        self.configurationChanged.emit("BY", self.standbyModeCombo.currentIndex())
        self.configurationChanged.emit("ON", self.polarizationOnModeCombo.currentIndex())
        self.configurationChanged.emit("PI", self.polarizationSignalGainCombo.currentIndex())
        if self.polarizationModeCombo.currentIndex()==0:  # Potentiostatic
            self.configurationChanged.emit("PV", self.dcPotentialSpin.value())
        else:  # Galvanostatic
            self.configurationChanged.emit("PC", self.dcPotentialSpin.value())
        self.startPolarizationRequested.emit()

    def _stop_polarization_clicked(self):
        if not self._is_connected:
            self.append_log("Connect to the instrument before stopping polarization.")
            return
        self.stopPolarizationRequested.emit()

    # def _set_controls_enabled(self, enabled: bool):
    #     # for w in [
    #     #     self.identifyButton, self.statusButton, self.lastErrorButton, self.clearErrorButton,
    #     #     self.potentiostatButton, self.galvanostatButton,
    #     #     self.applySetupButton, self.setupText,
    #     #     self.colASpin, self.colBSpin,
    #     #     self.startStreamButton, self.stopStreamButton,
    #     #     # self.disconnectButton,
    #     # ]:
    #     #     w.setEnabled(enabled)
    #     self.connectButton.setEnabled(not enabled)
    #     self.resourceCombo.setEnabled(not enabled)

    @QtCore.pyqtSlot(bool)
    def on_connected_changed(self, ok: bool):
        self._is_connected = ok
        if not ok:
            self._polarization_on = False
            if self._saving_to_db:
                table_name = self._db_table_name
                self._stop_db_session()
                self.append_log(
                    f"Stopped saving because instrument disconnected from table {table_name!r}."
                )
        # self._set_controls_enabled(ok)
        self.connectButton.setEnabled(not ok)
        self.refreshButton.setEnabled(not ok)
        self.closeButton.setEnabled(ok and not self._polarization_on)
        self.applySetupButton.setEnabled(ok)
        self.actionInstrumentStatus.setEnabled(ok)
        self.actionLastError.setEnabled(ok)
        self.actionIdentify.setEnabled(ok)
        self.actionClearError.setEnabled(ok)
        self.actionBreak.setEnabled(ok)
        self.actionReset.setEnabled(ok)
        self.actionSelfTest.setEnabled(ok)
        self.actionInitialize.setEnabled(ok)
        self.actionResultOverall.setEnabled(ok)
        self.actionResultRAM.setEnabled(ok)
        self.actionResultROM.setEnabled(ok)
        self.actionResultTimer.setEnabled(ok)
        if ok:
            self.stopStreamButton.setEnabled(False)
            self.startStreamButton.setEnabled(True)
            self.startSaveToDbButton.setEnabled(not self._saving_to_db)
            self.stopSaveToDbButton.setEnabled(self._saving_to_db)
        else:
            self.stopStreamButton.setEnabled(False)
            self.startStreamButton.setEnabled(False)
            self.startSaveToDbButton.setEnabled(False)
            self.stopSaveToDbButton.setEnabled(False)
        self.connLed.set_connected(ok)

    @QtCore.pyqtSlot(bool)
    def on_polarization_changed(self, ok: bool):
        self._polarization_on = ok
        self.polarizationLed.set_connected(ok)
        self.closeButton.setEnabled(self._is_connected and not ok)
        if not ok and self._saving_to_db:
            table_name = self._db_table_name
            self._stop_db_session()
            self.append_log(
                f"Stopped saving because polarization turned off for table {table_name!r}."
            )

    @QtCore.pyqtSlot(bool)
    def on_error_status_changed(self, ok: bool):
        self.errorLed.set_connected(ok)
        
        
    
           

    @QtCore.pyqtSlot(object)
    def on_sample(self, sample: Sample):
        v0 = sample.vals[0] if len(sample.vals) > 0 else float("nan")
        v1 = sample.vals[1] if len(sample.vals) > 1 else float("nan")

        if self._saving_to_db and self._db_cursor is not None and self._db_conn is not None:
            current_time = datetime.now().isoformat(timespec="seconds")
            try:
                self._db_cursor.execute(
                    f'INSERT INTO "{self._db_table_name}" (current_time, value1, value2) VALUES (?, ?, ?)',
                    (current_time, v0, v1),
                )
                self._db_conn.commit()
            except Exception as e:
                self.append_log(f"Database insert failed: {e}")
                self._stop_db_session()

        self.t.append(sample.t)
        self.a.append(v0)
        self.b.append(v1)

        if len(self.t) > self.max_points:
            self.t = self.t[-self.max_points:]
            self.a = self.a[-self.max_points:]
            self.b = self.b[-self.max_points:]

        points_a = [
            QtCore.QPointF(x, y)
            for x, y in zip(self.t, self.a)
            if math.isfinite(y)
        ]
        points_b = [
            QtCore.QPointF(x, y)
            for x, y in zip(self.t, self.b)
            if math.isfinite(y)
        ]
        self.seriesA.replace(points_a)
        self.seriesB.replace(points_b)

        if self.t:
            xmin = self.t[0]
            xmax = self.t[-1]
            if xmax <= xmin:
                xmax = xmin + 1.0
            self.axisX.setRange(xmin, xmax)

        y_values_a = [y for y in self.a if math.isfinite(y)]
        if y_values_a:
            ymin_a = min(y_values_a)
            ymax_a = max(y_values_a)
            if ymax_a <= ymin_a:
                ymax_a = ymin_a + 1.0
            pad_a = (ymax_a - ymin_a) * 0.1
            self.axisYLeft.setRange(ymin_a - pad_a, ymax_a + pad_a)

        y_values_b = [y for y in self.b if math.isfinite(y)]
        if y_values_b:
            ymin_b = min(y_values_b)
            ymax_b = max(y_values_b)
            if ymax_b <= ymin_b:
                ymax_b = ymin_b + 1.0
            pad_b = (ymax_b - ymin_b) * 0.1
            self.axisYRight.setRange(ymin_b - pad_b, ymax_b + pad_b)

    @QtCore.pyqtSlot()
    def _update_plot_series_names(self):
        left_name = self.outputXCombo.currentText() or "X"
        right_name = self.outputYCombo.currentText() or "Y"
        self.seriesA.setName(left_name)
        self.seriesB.setName(right_name)
        self.axisYLeft.setTitleText(left_name)
        self.axisYRight.setTitleText(right_name)

    @QtCore.pyqtSlot(str)
    def append_log(self, s: str):
        stamp = datetime.now().strftime("%H:%M:%S")
        self.logText.appendPlainText(f"[{stamp}] {s}")
        sb = self.logText.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _update_polarization_value_label(self, idx: int):
        if idx == 1:
            self.polarizationValueLabel.setText("D.C. Current")
        else:
            self.polarizationValueLabel.setText("D.C. Potential")
    
    @QtCore.pyqtSlot(int)
    def polarization_mode_combo_index_changed(self, idx: int):
        self.polarzation_mode = idx
        self._update_polarization_value_label(idx)
        self.stepSweepDialog.set_polarization_mode(idx)
        self.rampSweepDialog.set_polarization_mode(idx)
        self.configurationChanged.emit("PO", idx)
        
    @QtCore.pyqtSlot(int)
    def standby_mode_combo_index_changed(self, idx: int):
        self.standby_mode = idx
        self.configurationChanged.emit("BY", idx)
        
    @QtCore.pyqtSlot(float)
    def dc_potential_spin_value_changed(self, value: float):
        if(self.polarzation_mode < 0):
            self.append_log("Set Cell Polarization Mode before setting DC Potential")
            return
        if(self.standby_mode < 0):
            self.append_log("Set Standby Mode before setting DC Potential")
            return
        if(self.polarzation_mode==0):
            self.configurationChanged.emit("PV", value)
        else:
            self.configurationChanged.emit("PC", value)
        
    @QtCore.pyqtSlot(int)
    def bandwidth_combo_index_changed(self, idx:int):
        if idx == 0:
            self.configurationChanged.emit("SY",0)
            self.bandwidthGalvanostatCombo.setEnabled(True)
            self.bandwidthPotentiostatCombo.setEnabled(True)
        elif idx == 1:
            self.bandwidthGalvanostatCombo.setCurrentIndex(2)
            self.bandwidthGalvanostatCombo.setEnabled(False)
            self.bandwidthPotentiostatCombo.setCurrentIndex(2)
            self.bandwidthPotentiostatCombo.setEnabled(False)            
            self.configurationChanged.emit("SY",1)
            

    @QtCore.pyqtSlot(int)
    def ir_compensation_type_changed(self, idx: int):
        self.configurationChanged.emit("CT", idx)
        
        if idx == 0:
            self.feedbackCompensationSpin.setEnabled(True)
            self.feedbackCompensationSpin.valueChanged.emit(self.feedbackCompensationSpin.value())  # Trigger update with current value  
            self.cellCurrentOffTimeTypeCombo.setEnabled(False)
            self.outputToFRACombo.setEnabled(False)
            self.cellCurrentOffTimeSpin.setEnabled(False)
            self.cellCurrentOffRatioSpin.setEnabled(False)
            
        elif idx == 1:
            self.feedbackCompensationSpin.setEnabled(False)
            self.cellCurrentOffTimeTypeCombo.setEnabled(True)
            self.cellCurrentOffTimeTypeCombo.currentIndexChanged.emit(self.cellCurrentOffTimeTypeCombo.currentIndex())  # Trigger update with current index
            self.outputToFRACombo.setEnabled(True)


    @QtCore.pyqtSlot(int)
    def cell_current_off_time_type_combo_index_changed(self, idx: int):
        if idx == 0:
            self.cellCurrentOffTimeSpin.setEnabled(True)
            self.cellCurrentOffTimeSpin.valueChanged.emit(self.cellCurrentOffTimeSpin.value())  # Trigger update with current value 
            self.cellCurrentOffRatioSpin.setEnabled(False)
        elif idx == 1:
            self.cellCurrentOffTimeSpin.setEnabled(False)
            self.cellCurrentOffRatioSpin.setEnabled(True)
            self.cellCurrentOffRatioSpin.valueChanged.emit(self.cellCurrentOffRatioSpin.value())  # Trigger update with current value

    @QtCore.pyqtSlot(int)
    def compensation_combo_index_changed(self, idx: int):
        enabled = idx != 0
        self.irCompensationCheckBox.setEnabled(enabled)
        self.realPartCorrectionCheckBox.setEnabled(enabled)
        if not enabled:
            self.configurationChanged.emit("CC", 0)
            return
        self.ir_compensation_checkbox_toggled(self.irCompensationCheckBox.isChecked())
        self.realpart_correction_checkbox_toggled(self.realPartCorrectionCheckBox.isChecked())
            
    @QtCore.pyqtSlot(bool)
    def ir_compensation_checkbox_toggled(self, checked: bool):
        self.irCompensationTypeCombo.setEnabled(checked)
        if not checked:
            self.feedbackCompensationSpin.setEnabled(False)
            self.cellCurrentOffTimeTypeCombo.setEnabled(False)
            self.outputToFRACombo.setEnabled(False)
            self.cellCurrentOffTimeSpin.setEnabled(False)
            self.cellCurrentOffRatioSpin.setEnabled(False)
            return
        if checked:            
            self.configurationChanged.emit("CC", 1)
            self.ir_compensation_type_changed(self.irCompensationTypeCombo.currentIndex())

    @QtCore.pyqtSlot(bool)
    def realpart_correction_checkbox_toggled(self, checked: bool):
        self.realPartCorrectionSpin.setEnabled(checked)
        if checked:
            self.configurationChanged.emit("CC", 2)
            self.configurationChanged.emit("RP", self.realPartCorrectionSpin.value())
           
    @QtCore.pyqtSlot(int)
    def voltage_bias_combo_index_changed(self,idx:int):
        if idx == 0:
            self.configurationChanged.emit("VT", 0)
            self.voltageBiasSpin.setEnabled(False)
        elif idx == 1:
            self.configurationChanged.emit("VT", 1)
            self.voltageBiasSpin.setEnabled(True)
            
    @QtCore.pyqtSlot(int)
    def current_bias_combo_index_changed(self,idx:int):
        if idx == 0:
            self.configurationChanged.emit("IT", 0)
            self.currentBiasSpin.setEnabled(False)
        elif idx == 1:
            self.configurationChanged.emit("IT", 1)
            self.currentBiasSpin.setEnabled(True)
            
    @QtCore.pyqtSlot(int)
    def sweep_off_mode_combo_index_changed(self,idx:int):
        if idx in (0, 1):
            self.configurationChanged.emit("OF", idx)
        self.configurationChanged.emit("SW", 0)
            
    @QtCore.pyqtSlot()
    def sweep_step_button_clicked(self):
        self._start_step_sweep_from_dialog()
            
    @QtCore.pyqtSlot()
    def sweep_ramp_button_clicked(self):
        self._start_ramp_sweep_from_dialog()

    @QtCore.pyqtSlot()
    def sweep_step_action_clicked(self):
        if not self._ensure_polarization_mode_selected_for_sweep():
            return
        if not self._ensure_sweep_window_allowed("step"):
            return
        self._sync_step_sweep_dialog_from_main()
        self.stepSweepDialog.show()
        self.stepSweepDialog.raise_()
        self.stepSweepDialog.activateWindow()

    @QtCore.pyqtSlot()
    def sweep_ramp_action_clicked(self):
        if not self._ensure_polarization_mode_selected_for_sweep():
            return
        if not self._ensure_sweep_window_allowed("ramp"):
            return
        self._sync_ramp_sweep_dialog_from_main()
        self.rampSweepDialog.show()
        self.rampSweepDialog.raise_()
        self.rampSweepDialog.activateWindow()
    

    @QtCore.pyqtSlot()
    def sweep_status_action_clicked(self):
        self.configurationChanged.emit("?ST", None)

    @QtCore.pyqtSlot()
    def _poll_sweep_status(self):
        if self._sweep_running and self._is_connected:
            self.configurationChanged.emit("?ST", None)
    
    @QtCore.pyqtSlot()
    def stop_sweep_action_clicked(self):
        self.configurationChanged.emit("SW", 0)
        self._active_sweep_type = None
        self._set_sweep_dialogs_running(False)
        self.append_log("Sweep stopped.")

    def _sync_step_sweep_dialog_from_main(self):
        self.stepSweepDialog.load_from_values(self._step_sweep_values)
        self.stepSweepDialog.set_polarization_mode(self.polarizationModeCombo.currentIndex())
        self.stepSweepDialog.set_sweep_running(self._sweep_running)

    def _sync_ramp_sweep_dialog_from_main(self):
        self.rampSweepDialog.load_from_values(self._ramp_sweep_values)
        self.rampSweepDialog.set_polarization_mode(self.polarizationModeCombo.currentIndex())
        self.rampSweepDialog.set_sweep_running(self._sweep_running)

    def _set_sweep_dialogs_running(self, running: bool):
        self._sweep_running = running
        self.stepSweepDialog.set_sweep_running(running)
        self.rampSweepDialog.set_sweep_running(running)
        self.tab.setEnabled(not running)
        if running and self._is_connected:
            self._sweep_status_timer.start()
        else:
            self._sweep_status_timer.stop()
        self.sweepLed.set_connected(running)
        if running and self._active_sweep_type == "step":
            self.sweepStatusLabel.setText("Step Running")
        elif running and self._active_sweep_type == "ramp":
            self.sweepStatusLabel.setText("Ramp Running")
        else:
            self.sweepStatusLabel.setText("Idle")

    def _ensure_polarization_mode_selected_for_sweep(self) -> bool:
        if self.polarizationModeCombo.currentIndex() >= 0:
            return True

        msg = "Select polarization mode before opening the sweep window."
        self.append_log(msg)
        QtWidgets.QMessageBox.warning(self, "Polarization Mode Required", msg)
        return False

    def _ensure_sweep_window_allowed(self, requested_type: str) -> bool:
        if not self._sweep_running:
            return True
        if self._active_sweep_type == requested_type:
            return True

        active_name = "Step Sweep" if self._active_sweep_type == "step" else "Ramp Sweep"
        requested_name = "Step Sweep" if requested_type == "step" else "Ramp Sweep"
        msg = f"{active_name} is running. Stop it before opening {requested_name}."
        self.append_log(msg)
        QtWidgets.QMessageBox.warning(self, "Sweep Active", msg)
        return False

    def _start_step_sweep_from_dialog(self):
        dlg = self.stepSweepDialog
        values = dlg.values()
        self._step_sweep_values = values
        if self._sweep_running and self._active_sweep_type == "ramp":
            self._ensure_sweep_window_allowed("step")
            return
        if values["off_mode"] == 1:
            self.append_log("Instrument Sweep Mode Freeze")
            return

        self.configurationChanged.emit("OF", values["off_mode"])
        self.configurationChanged.emit("DL", values["delay"])
        self.configurationChanged.emit("SM", values["segments"])
        if self.polarzation_mode == 1:
            self.configurationChanged.emit("KA", values["v1"])
            self.configurationChanged.emit("KB", values["v2"])
            self.configurationChanged.emit("KC", values["v3"])
            self.configurationChanged.emit("KD", values["v4"])
            self.configurationChanged.emit("IS", values["v_step"])
        else:
            self.configurationChanged.emit("SA", values["v1"])
            self.configurationChanged.emit("SB", values["v2"])
            self.configurationChanged.emit("SC", values["v3"])
            self.configurationChanged.emit("SD", values["v4"])
            self.configurationChanged.emit("VS", values["v_step"])
        self.configurationChanged.emit("TE", values["time"])
        self.configurationChanged.emit("SW", 2)
        self._active_sweep_type = "step"
        self._set_sweep_dialogs_running(True)
        self.append_log("Step sweep started from Step Sweep window.")

    def _start_ramp_sweep_from_dialog(self):
        dlg = self.rampSweepDialog
        values = dlg.values()
        self._ramp_sweep_values = values
        if self._sweep_running and self._active_sweep_type == "step":
            self._ensure_sweep_window_allowed("ramp")
            return
        if values["off_mode"] == 1:
            self.append_log("Instrument Sweep Mode Freeze")
            return

        self.configurationChanged.emit("OF", values["off_mode"])
        self.configurationChanged.emit("DL", values["delay"])
        self.configurationChanged.emit("SM", values["segments"])
        self.configurationChanged.emit("FI", values["filter"])
        if self.polarzation_mode == 1:
            self.configurationChanged.emit("JA", values["v1"])
            self.configurationChanged.emit("JB", values["v2"])
            self.configurationChanged.emit("JC", values["v3"])
            self.configurationChanged.emit("JD", values["v4"])
        else:
            self.configurationChanged.emit("VA", values["v1"])
            self.configurationChanged.emit("VB", values["v2"])
            self.configurationChanged.emit("VC", values["v3"])
            self.configurationChanged.emit("VD", values["v4"])
        self.configurationChanged.emit("TA", values["t1"])
        self.configurationChanged.emit("TB", values["t2"])
        self.configurationChanged.emit("TC", values["t3"])
        self.configurationChanged.emit("TD", values["t4"])
        self.configurationChanged.emit("SW", 1)
        self._active_sweep_type = "ramp"
        self._set_sweep_dialogs_running(True)
        self.append_log("Ramp sweep started from Ramp Sweep window.")

    def save_setup(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save setup", "", "JSON (*.json)")
        if not path:
            return
        values: dict[str, object] = {}

        values["PO"] = self.polarizationModeCombo.currentIndex()
        values["BY"] = self.standbyModeCombo.currentIndex()
        values["ON"] = self.polarizationOnModeCombo.currentIndex()
        values["PI"] = self.polarizationSignalGainCombo.currentIndex()
        if self.polarizationModeCombo.currentIndex() == 1:
            values["PC"] = self.dcPotentialSpin.value()
        else:
            values["PV"] = self.dcPotentialSpin.value()

        values["SY"] = self.bandwidthCombo.currentIndex()
        values["GB"] = self.bandwidthGalvanostatCombo.currentIndex()
        values["PB"] = self.bandwidthPotentiostatCombo.currentIndex()

        values["RR"] = self.standardResistantCombo.currentIndex()
        values["IL"] = self.currentLimitCombo.currentIndex()
        values["OL"] = self.currentOffLimitActionCombo.currentIndex()

        values["COMPENSATION"] = self.compensationCombo.currentIndex()
        values["IR_COMPENSATION_ENABLED"] = self.irCompensationCheckBox.isChecked()
        values["REAL_PART_CORRECTION_ENABLED"] = self.realPartCorrectionCheckBox.isChecked()
        values["CT"] = self.irCompensationTypeCombo.currentIndex()
        values["IC"] = self.feedbackCompensationSpin.value()
        values["RO"] = self.outputToFRACombo.currentIndex()
        values["CELLCURRENT"] = self.cellCurrentOffTimeTypeCombo.currentIndex()
        values["IN"] = self.cellCurrentOffTimeSpin.value()
        values["IF"] = int(self.cellCurrentOffRatioSpin.value())
        values["RP"] = self.realPartCorrectionSpin.value() if self.realPartCorrectionCheckBox.isChecked() else None

        values["VT"] = 0 if self.voltageBiasCombo.currentIndex() == 0 else 1
        values["VR"] = self.voltageBiasSpin.value() if self.voltageBiasCombo.currentIndex() == 1 else None
        values["IT"] = 0 if self.currentBiasCombo.currentIndex() == 0 else 1
        values["IR"] = self.currentBiasSpin.value() if self.currentBiasCombo.currentIndex() == 1 else None
        values["BR"] = self.biasRejectCombo.currentIndex()
        values["FI"] = self.filterCombo.currentIndex()
        values["VX"] = self.voltageAmplificationCombo.currentIndex()
        values["IX"] = self.currentAmplificationCombo.currentIndex()

        values["DG"] = self.numberOfDigitsCombo.currentIndex()
        values["RG"] = self.inputRangeCombo.currentIndex()
        values["TR"] = self.measurementTriggerCombo.currentIndex()
        values["DC"] = self.driftCombo.currentIndex()
        values["AV"] = self.averagingtCombo.currentIndex()
        values["NU"] = self.nullCombo.currentIndex()
        values["RU"] = self.digitalVolmeterCombo.currentIndex()
        values["PX"] = self.outputXCombo.currentIndex()
        values["PY"] = self.outputYCombo.currentIndex()
        values["UL"] = self.displayLeftCombo.currentIndex()
        values["UR"] = self.displayRightCombo.currentIndex()

        self.setup.values = values

        self.setup.save_json(path)
        self.append_log(f"Saved setup: {sys.path}")

    def load_setup(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Load setup", "", "JSON (*.json)")
        if not path:
            return
        self.setup.load_json(path)
        values = self.setup.values

        widget_blockers = [
            QtCore.QSignalBlocker(self.polarizationModeCombo),
            QtCore.QSignalBlocker(self.standbyModeCombo),
            QtCore.QSignalBlocker(self.polarizationOnModeCombo),
            QtCore.QSignalBlocker(self.polarizationSignalGainCombo),
            QtCore.QSignalBlocker(self.dcPotentialSpin),
            QtCore.QSignalBlocker(self.bandwidthCombo),
            QtCore.QSignalBlocker(self.bandwidthGalvanostatCombo),
            QtCore.QSignalBlocker(self.bandwidthPotentiostatCombo),
            QtCore.QSignalBlocker(self.standardResistantCombo),
            QtCore.QSignalBlocker(self.currentLimitCombo),
            QtCore.QSignalBlocker(self.currentOffLimitActionCombo),
            QtCore.QSignalBlocker(self.compensationCombo),
            QtCore.QSignalBlocker(self.irCompensationCheckBox),
            QtCore.QSignalBlocker(self.realPartCorrectionCheckBox),
            QtCore.QSignalBlocker(self.irCompensationTypeCombo),
            QtCore.QSignalBlocker(self.feedbackCompensationSpin),
            QtCore.QSignalBlocker(self.outputToFRACombo),
            QtCore.QSignalBlocker(self.cellCurrentOffTimeTypeCombo),
            QtCore.QSignalBlocker(self.cellCurrentOffTimeSpin),
            QtCore.QSignalBlocker(self.cellCurrentOffRatioSpin),
            QtCore.QSignalBlocker(self.realPartCorrectionSpin),
            QtCore.QSignalBlocker(self.voltageBiasCombo),
            QtCore.QSignalBlocker(self.voltageBiasSpin),
            QtCore.QSignalBlocker(self.currentBiasCombo),
            QtCore.QSignalBlocker(self.currentBiasSpin),
            QtCore.QSignalBlocker(self.biasRejectCombo),
            QtCore.QSignalBlocker(self.filterCombo),
            QtCore.QSignalBlocker(self.voltageAmplificationCombo),
            QtCore.QSignalBlocker(self.currentAmplificationCombo),
            QtCore.QSignalBlocker(self.numberOfDigitsCombo),
            QtCore.QSignalBlocker(self.inputRangeCombo),
            QtCore.QSignalBlocker(self.measurementTriggerCombo),
            QtCore.QSignalBlocker(self.driftCombo),
            QtCore.QSignalBlocker(self.averagingtCombo),
            QtCore.QSignalBlocker(self.nullCombo),
            QtCore.QSignalBlocker(self.digitalVolmeterCombo),
            QtCore.QSignalBlocker(self.outputXCombo),
            QtCore.QSignalBlocker(self.outputYCombo),
            QtCore.QSignalBlocker(self.displayLeftCombo),
            QtCore.QSignalBlocker(self.displayRightCombo),
        ]

        self.polarizationModeCombo.setCurrentIndex(values.get("PO", self.polarizationModeCombo.currentIndex()))
        self.standbyModeCombo.setCurrentIndex(values.get("BY", self.standbyModeCombo.currentIndex()))
        self.polarizationOnModeCombo.setCurrentIndex(values.get("ON", self.polarizationOnModeCombo.currentIndex()))
        self.polarizationSignalGainCombo.setCurrentIndex(values.get("PI", self.polarizationSignalGainCombo.currentIndex()))
        pol_mode = self.polarizationModeCombo.currentIndex()
        self.dcPotentialSpin.setValue(values.get("PC" if pol_mode == 1 else "PV", self.dcPotentialSpin.value()))

        self.bandwidthCombo.setCurrentIndex(values.get("SY", self.bandwidthCombo.currentIndex()))
        self.bandwidthGalvanostatCombo.setCurrentIndex(values.get("GB", self.bandwidthGalvanostatCombo.currentIndex()))
        self.bandwidthPotentiostatCombo.setCurrentIndex(values.get("PB", self.bandwidthPotentiostatCombo.currentIndex()))
        self.standardResistantCombo.setCurrentIndex(values.get("RR", self.standardResistantCombo.currentIndex()))
        self.currentLimitCombo.setCurrentIndex(values.get("IL", self.currentLimitCombo.currentIndex()))
        self.currentOffLimitActionCombo.setCurrentIndex(values.get("OL", self.currentOffLimitActionCombo.currentIndex()))

        compensation_enabled = values.get("COMPENSATION", 0)
        self.compensationCombo.setCurrentIndex(compensation_enabled)
        self.irCompensationCheckBox.setChecked(compensation_enabled == 1 and values.get("IR_COMPENSATION_ENABLED", False))
        self.realPartCorrectionCheckBox.setChecked(compensation_enabled == 1 and values.get("REAL_PART_CORRECTION_ENABLED", False))
        self.irCompensationTypeCombo.setCurrentIndex(values.get("CT", self.irCompensationTypeCombo.currentIndex()))
        self.feedbackCompensationSpin.setValue(values.get("IC", self.feedbackCompensationSpin.value()))
        self.outputToFRACombo.setCurrentIndex(values.get("RO", self.outputToFRACombo.currentIndex()))
        self.cellCurrentOffTimeTypeCombo.setCurrentIndex(values.get("CELLCURRENT", self.cellCurrentOffTimeTypeCombo.currentIndex()))
        self.cellCurrentOffTimeSpin.setValue(values.get("IN", self.cellCurrentOffTimeSpin.value()))
        self.cellCurrentOffRatioSpin.setValue(int(values.get("IF", self.cellCurrentOffRatioSpin.value())))
        rp_value = values.get("RP")
        if rp_value is not None:
            self.realPartCorrectionSpin.setValue(rp_value)

        self.voltageBiasCombo.setCurrentIndex(values.get("VT", self.voltageBiasCombo.currentIndex()))
        if values.get("VR") is not None:
            self.voltageBiasSpin.setValue(values["VR"])
        self.currentBiasCombo.setCurrentIndex(values.get("IT", self.currentBiasCombo.currentIndex()))
        if values.get("IR") is not None:
            self.currentBiasSpin.setValue(values["IR"])
        self.biasRejectCombo.setCurrentIndex(values.get("BR", self.biasRejectCombo.currentIndex()))
        self.filterCombo.setCurrentIndex(values.get("FI", self.filterCombo.currentIndex()))
        self.voltageAmplificationCombo.setCurrentIndex(values.get("VX", self.voltageAmplificationCombo.currentIndex()))
        self.currentAmplificationCombo.setCurrentIndex(values.get("IX", self.currentAmplificationCombo.currentIndex()))

        self.numberOfDigitsCombo.setCurrentIndex(values.get("DG", self.numberOfDigitsCombo.currentIndex()))
        self.inputRangeCombo.setCurrentIndex(values.get("RG", self.inputRangeCombo.currentIndex()))
        self.measurementTriggerCombo.setCurrentIndex(values.get("TR", self.measurementTriggerCombo.currentIndex()))
        self.driftCombo.setCurrentIndex(values.get("DC", self.driftCombo.currentIndex()))
        self.averagingtCombo.setCurrentIndex(values.get("AV", self.averagingtCombo.currentIndex()))
        self.nullCombo.setCurrentIndex(values.get("NU", self.nullCombo.currentIndex()))
        self.digitalVolmeterCombo.setCurrentIndex(values.get("RU", self.digitalVolmeterCombo.currentIndex()))
        self.outputXCombo.setCurrentIndex(values.get("PX", self.outputXCombo.currentIndex()))
        self.outputYCombo.setCurrentIndex(values.get("PY", self.outputYCombo.currentIndex()))
        self.displayLeftCombo.setCurrentIndex(values.get("UL", self.displayLeftCombo.currentIndex()))
        self.displayRightCombo.setCurrentIndex(values.get("UR", self.displayRightCombo.currentIndex()))

        del widget_blockers

        self.polarzation_mode = self.polarizationModeCombo.currentIndex()
        self.standby_mode = self.standbyModeCombo.currentIndex()
        self._update_polarization_value_label(self.polarizationModeCombo.currentIndex())
        self.bandwidth_combo_index_changed(self.bandwidthCombo.currentIndex())
        self._update_compensation_controls()
        self.voltage_bias_combo_index_changed(self.voltageBiasCombo.currentIndex())
        self.current_bias_combo_index_changed(self.currentBiasCombo.currentIndex())
        self._update_plot_series_names()
        self.applySetupButton.setEnabled(True)
        self._apply_setup_clicked()
        self.append_log(f"Loaded setup (marked dirty): {path}")

    def export_plot(self):
        path, selected_filter = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Export Plot",
            "plot.png",
            "PNG Image (*.png);;JPEG Image (*.jpg *.jpeg);;Bitmap Image (*.bmp)",
        )
        if not path:
            return

        if "." not in QtCore.QFileInfo(path).fileName():
            if "JPEG" in selected_filter:
                path += ".jpg"
            elif "Bitmap" in selected_filter:
                path += ".bmp"
            else:
                path += ".png"

        pixmap = self.plotWidget.grab()
        if pixmap.isNull():
            self.append_log("Export plot failed: no chart image available.")
            return

        ok = pixmap.save(path)
        if ok:
            self.append_log(f"Plot exported: {path}")
        else:
            self.append_log(f"Export plot failed: {path}")

    def _build_menu_bar(self):
        menubar = self.menuBar()
        test_menu = menubar.addMenu("Quick Test")
        break_menu = menubar.addMenu("Break && Self-Test")
        result_menu = menubar.addMenu("Self-Test Result")
        sweep_menu = menubar.addMenu("Sweep")

        self.actionInstrumentStatus = test_menu.addAction("Instrument Status")
        self.actionIdentify = test_menu.addAction("Identify")
        self.actionLastError = test_menu.addAction("Last Error")
        self.actionClearError = test_menu.addAction("Clear Error")

        self.actionBreak = break_menu.addAction("Break")
        self.actionSelfTest = break_menu.addAction("Self-Test")
        self.actionReset = break_menu.addAction("Reset")
        self.actionInitialize = break_menu.addAction("Initialize")

        self.actionResultOverall = result_menu.addAction("Overall")
        self.actionResultRAM = result_menu.addAction("RAM")
        self.actionResultROM = result_menu.addAction("ROM")
        self.actionResultTimer = result_menu.addAction("Timer")
        

        sweep_menu.addAction("Ramp Sweep", self.sweep_ramp_action_clicked)
        sweep_menu.addAction("Step Sweep", self.sweep_step_action_clicked)
        sweep_menu.addSeparator()
        sweep_menu.addAction("Stop Sweep", self.stop_sweep_action_clicked)
        sweep_menu.addSeparator()
        sweep_menu.addAction("Sweep Status", self.sweep_status_action_clicked)  

        for action in (
            self.actionInstrumentStatus,
            self.actionIdentify,
            self.actionLastError,
            self.actionClearError,
            self.actionBreak,
            self.actionSelfTest,
            self.actionReset,
            self.actionInitialize,
            self.actionResultOverall,
            self.actionResultRAM,
            self.actionResultROM,
            self.actionResultTimer,
        ):
            action.setEnabled(False)

    def _apply_facebook_widget_roles(self):
        for button in (
            self.connectButton,
            self.startStreamButton,
            self.startSaveToDbButton,
            self.exportPlotButton,
            self.startPolarizationButton,
        ):
            button.setProperty("fbRole", "primary")

        for button in (
            self.closeButton,
            self.stopStreamButton,
            self.stopSaveToDbButton,
            self.stopPolarizationButton,
        ):
            button.setProperty("fbRole", "danger")

        for widget in (
            self.connectButton,
            self.startStreamButton,
            self.startSaveToDbButton,
            self.exportPlotButton,
            self.startPolarizationButton,
            self.closeButton,
            self.stopStreamButton,
            self.stopSaveToDbButton,
            self.stopPolarizationButton,
        ):
            widget.style().unpolish(widget)
            widget.style().polish(widget)

    def _apply_chart_theme(self):
        self.chart.setTitleBrush(QtGui.QBrush(QtGui.QColor("#1c1e21")))
        self.chart.setBackgroundBrush(QtGui.QBrush(QtGui.QColor("#ffffff")))
        self.chart.setPlotAreaBackgroundVisible(True)
        self.chart.setPlotAreaBackgroundBrush(QtGui.QBrush(QtGui.QColor("#ffffff")))

        legend = self.chart.legend()
        legend.setLabelColor(QtGui.QColor("#606770"))
        legend.setBrush(QtGui.QBrush(QtCore.Qt.GlobalColor.transparent))

        grid_pen = QtGui.QPen(QtGui.QColor("#e4e6eb"))
        grid_pen.setWidth(1)
        axis_pen = QtGui.QPen(QtGui.QColor("#ccd0d5"))
        axis_pen.setWidth(1)
        label_brush = QtGui.QBrush(QtGui.QColor("#606770"))
        title_brush = QtGui.QBrush(QtGui.QColor("#1c1e21"))

        for axis in (self.axisX, self.axisYLeft, self.axisYRight):
            axis.setGridLinePen(grid_pen)
            axis.setLinePen(axis_pen)
            axis.setLabelsBrush(label_brush)
            axis.setTitleBrush(title_brush)

        self.plotWidget.setBackgroundBrush(QtGui.QBrush(QtGui.QColor("#ffffff")))
            
def main():
    app = QtWidgets.QApplication(sys.argv)
    apply_blue_style(app)
    w = MainWindow()
    w.showMaximized()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

