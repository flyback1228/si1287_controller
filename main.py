# main.py
from functools import partial
import sys
from typing import List

from PyQt6 import QtCore, QtWidgets, uic, QtGui
import pyqtgraph as pg
import pyvisa

from visa_worker import VisaWorker, Sample

from si1287_setup import Si1287Setup
from status_led import StatusLed
# from qtpy_led import Led

def apply_light_style(app: QtWidgets.QApplication):
    app.setStyle("Fusion")

    qss = """
    /* ---------- Main window ---------- */
    QMainWindow {
        background: #f5f6f8;
    }

    QWidget {
        font-size: 12px;
        color: #20242a;
    }

    /* ---------- Group boxes ---------- */
    QGroupBox {
        background: #ffffff;
        border: 1px solid #d7dbe2;
        border-radius: 8px;
        margin-top: 12px;
        padding: 10px;
    }

    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top left;
        left: 8px;
        padding: 0 6px;
        color: #3a4b6b;
        font-weight: bold;
    }

    /* ---------- Buttons ---------- */
    QPushButton {
        background: #ffffff;
        border: 1px solid #cfd5df;
        border-radius: 6px;
        padding: 6px 12px;
        min-height: 28px;
    }

    QPushButton:hover {
        background: #f1f4f9;
        border-color: #aab3c2;
    }

    QPushButton:pressed {
        background: #e7ecf4;
    }

    QPushButton:disabled {
        background: #f7f7f7;
        color: #9aa2af;
        border-color: #e0e3e8;
    }

    /* Apply button highlight */
    QPushButton#applySetupButton:enabled {
        background: #2d5fff;
        color: white;
        border-color: #2d5fff;
    }

    QPushButton#applySetupButton:hover:enabled {
        background: #3a6bff;
    }

    /* ---------- Inputs ---------- */
    QComboBox,
    QLineEdit {
        background: white;
        border: 1px solid #bfc6d3;
        border-radius: 6px;
        padding: 4px 8px;
        min-height: 24px;
    }

    /* Spinboxes need explicit styling */
    QSpinBox, QDoubleSpinBox {
        background: white;
        border: 1px solid #bfc6d3;
        border-radius: 6px;
        padding-right: 18px;
        min-height: 24px;
    }

    QSpinBox::up-button, QDoubleSpinBox::up-button {
        subcontrol-origin: border;
        subcontrol-position: top right;
        width: 16px;
        border-left: 1px solid #d0d5df;
        background: #f3f5f9;
    }

    QSpinBox::down-button, QDoubleSpinBox::down-button {
        subcontrol-origin: border;
        subcontrol-position: bottom right;
        width: 16px;
        border-left: 1px solid #d0d5df;
        background: #f3f5f9;
    }

    QSpinBox::up-button:hover,
    QSpinBox::down-button:hover,
    QDoubleSpinBox::up-button:hover,
    QDoubleSpinBox::down-button:hover {
        background: #e6ebf5;
    }

    QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {
        image: none;
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
        border-bottom: 6px solid #4a5568;
    }

    QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {
        image: none;
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
        border-top: 6px solid #4a5568;
    }

    /* ---------- Tabs ---------- */
    QTabWidget::pane {
        border: 1px solid #d7dbe2;
        border-radius: 8px;
        background: white;
    }

    QTabBar::tab {
        background: #eef1f6;
        border: 1px solid #d7dbe2;
        padding: 8px 14px;
        margin-right: 2px;
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
    }

    QTabBar::tab:selected {
        background: white;
        border-bottom: 1px solid white;
        font-weight: bold;
    }

    QTabBar::tab:hover {
        background: #e6ebf5;
    }

    /* ---------- Tooltips ---------- */
    QToolTip {
        background: white;
        border: 1px solid #cfd5df;
        padding: 4px;
    }
    """

    app.setStyleSheet(qss)

    font = QtGui.QFont("Segoe UI", 10)
    app.setFont(font)


DEFAULT_SETUP_CMDS = [
    "TR1",
    "RU1",
    "PX3",
    "PY5",
    "OS0",
    "RH1",
    "OT1",
]


class MainWindow(QtWidgets.QMainWindow):
    # UI → worker signals (queued)
    connectRequested = QtCore.pyqtSignal(str)
    disconnectRequested = QtCore.pyqtSignal()
    # applySetupRequested = QtCore.pyqtSignal(list)
    startStreamRequested = QtCore.pyqtSignal()
    stopStreamRequested = QtCore.pyqtSignal()
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
        
        self.connLed = StatusLed(14)
        self.statusBar().addPermanentWidget(QtWidgets.QLabel("Instrument:"))
        self.statusBar().addPermanentWidget(self.connLed)
        self.connLed.set_connected(False)

        # -------- Plot --------
        self.plotWidget = pg.PlotWidget()
        self.plotWidget.showGrid(x=True, y=True)
        self.plotWidget.setLabel("bottom", "Time", units="s")
        self.plotWidget.setLabel("left", "Value")
        self.plotFrameLayout.addWidget(self.plotWidget)
        self.plotPlaceholderLabel.hide()

        self.curveA = self.plotWidget.plot([], [])
        self.curveB = self.plotWidget.plot([], [])

        self.t: List[float] = []
        self.a: List[float] = []
        self.b: List[float] = []
        self.max_points = 2000

        # -------- Setup text --------
        # if not self.setupText.toPlainText().strip():
        #     self.setupText.setPlainText("\n".join(DEFAULT_SETUP_CMDS))

        # -------- Worker thread --------
        self.worker = VisaWorker()
        self.thread = QtCore.QThread(self)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.start)
        self.thread.start()

        # Worker → UI
        self.worker.logLine.connect(self.append_log)
        self.worker.connectedChanged.connect(self.on_connected_changed)
        self.worker.sampleReady.connect(self.on_sample)

        # UI → Worker (queued)
        q = QtCore.Qt.ConnectionType.QueuedConnection
        self.connectRequested.connect(self.worker.connectVisa, q)
        self.disconnectRequested.connect(self.worker.disconnectVisa, q)
        # self.applySetupRequested.connect(self.worker.apply_setup, q)
        self.startStreamRequested.connect(self.worker.start_stream, q)
        self.stopStreamRequested.connect(self.worker.stop_stream, q)
        self.identifyButton.clicked.connect(lambda: self.configurationChanged.emit("?VN",None))
        self.statusButton.clicked.connect(lambda: self.configurationChanged.emit("?ST",None))
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
        self.lastErrorButton.clicked.connect(lambda: self.configurationChanged.emit("?ER",None))
        self.clearErrorButton.clicked.connect(lambda: self.configurationChanged.emit("?CE",None))
        
        self.breakButton.clicked.connect(lambda: self.configurationChanged.emit("BK",0))
        self.selfTestButton.clicked.connect(lambda: self.configurationChanged.emit("BK",1))
        self.resetButton.clicked.connect(lambda: self.configurationChanged.emit("BK",3))
        self.initializeButton.clicked.connect(lambda: self.configurationChanged.emit("BK",4))

        # self.potentiostatButton.clicked.connect(lambda: self.setModeRequested.emit(0))
        # self.galvanostatButton.clicked.connect(lambda: self.setModeRequested.emit(1))

        # self.applySetupButton.clicked.connect(self._apply_setup_clicked)
        self.startStreamButton.clicked.connect(self._start_stream_clicked)
        self.stopStreamButton.clicked.connect(self._stop_stream_clicked)
        
        self.refreshButton.clicked.connect(self._populate_visa_resources)


        # 6.1  CELL POLARIZATION 
        # 6.2 STANDBY STATE
        # 6.3 POLARIZATION ON MODE
        self.polarizationModeCombo.currentIndexChanged.connect(lambda idx: self.configurationChanged.emit("PO", idx))
        self.dcPotentialSpin.valueChanged.connect(lambda val: self.configurationChanged.emit("PV", val))
        self.standbyModeCombo.currentIndexChanged.connect(lambda idx: self.configurationChanged.emit("BY", idx))
        self.polarizationOnModeCombo.currentIndexChanged.connect(lambda idx: self.configurationChanged.emit("ON", idx))
        self.polarizationSignalGainCombo.currentIndexChanged.connect(lambda idx: self.configurationChanged.emit("PI", idx))

        # 6.4 CONTROL LOOP BANDWIDTH
        self.bandwidthCombo.currentIndexChanged.connect(lambda idx: self.configurationChanged.emit("SY", idx))
        self.bandwidthGalvanostatCombo.setCurrentIndex(2)
        self.bandwidthGalvanostatCombo.currentIndexChanged.connect(lambda idx: self.configurationChanged.emit("GB", idx))
        self.bandwidthPotentiostatCombo.setCurrentIndex(2)
        self.bandwidthPotentiostatCombo.currentIndexChanged.connect(lambda idx: self.configurationChanged.emit("PB", idx))

        # 6.5 STANDARD RESISTOR SELECTION
        self.standardResistantCombo.currentIndexChanged.connect(lambda idx: self.configurationChanged.emit("RR", idx))
        # 6.6 CURRENT LIMIT SELECTION (In conjunction with Auto-range RR0)
        self.currentLimitCombo.currentIndexChanged.connect(lambda idx: self.configurationChanged.emit("IL", idx))
        # 6.7 CURRENT OFF-LIMIT ACTION
        self.currentOffLimitActionCombo.currentIndexChanged.connect(lambda idx: self.configurationChanged.emit("OL", idx))

        # 6.8 IR COMPENSATION TYPE AND ON/OFF
        self.irCompensationCombo.currentIndexChanged.connect(lambda idx: self.configurationChanged.emit("CC", idx))
        self.irCompensationTypeCombo.currentIndexChanged.connect(lambda idx: self.ir_compensation_type_changed(idx))
        # 6.9 FEEDBACK IR COMPENSATION
        self.feedbackCompensationSpin.valueChanged.connect(lambda val: self.configurationChanged.emit("IC", val))
        # 6.10 6.10 SAMPLED IR COMPENSATION
        self.cellCurrentOffTimeTypeCombo.setEnabled(False)
        self.outputToFRACombo.setEnabled(False)
        self.cellCurrentOffSpin.setEnabled(False)

        self.outputToFRACombo.currentIndexChanged.connect(lambda idx: self.configurationChanged.emit("RO", idx))
        self.cellCurrentOffTimeTypeCombo.currentIndexChanged.connect(self.cell_current_off_time_type_combo_index_changed)
        self.cellCurrentOffSpin.valueChanged.connect(lambda val: self.configurationChanged.emit("IN", val) if self.cellCurrentOffTimeTypeCombo.currentIndex() == 0 else self.configurationChanged.emit("IF", int(val)))


        # 6.11 REAL PART CORRECTION
        self.realPartCorrectionCombo.currentIndexChanged.connect(self.realpart_correction_combo_index_changed)
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
        
        # 6.13 SWEEP Definition
        self.offModeCombo.currentIndexChanged.connect(self.sweep_off_mode_combo_index_changed)
        # self.sweepStandbyButton.clicked.connect(lambda: self.configurationChanged("SW",0))
        self.sweepStepButton.clicked.connect(self.sweep_step_button_clicked)
        self.sweepRampButton.clicked.connect(self.sweep_ramp_button_clicked)
        self.sweepStatusButton.clicked.connect(lambda: self.configurationChanged("?ST",None))
        
        # 6.16 DVM Control Functions
        self.numberOfDigitsCombo.currentIndexChanged.connect(lambda idx: self.configurationChanged.emit("DG", idx))
        self.inputRangeCombo.currentIndexChanged.connect(lambda idx: self.configurationChanged.emit("RG", idx))
        self.measurementTriggerCombo.currentIndexChanged.connect(lambda idx: self.configurationChanged.emit("TR", idx))
        self.driftCombo.currentIndexChanged.connect(lambda idx: self.configurationChanged.emit("DC", idx))
        self.averagingtCombo.currentIndexChanged.connect(lambda idx: self.configurationChanged.emit("AV", idx))
        self.nullCombo.currentIndexChanged.connect(lambda idx: self.configurationChanged.emit("NU", idx))
        self.digitalVolmeterCombo.currentIndexChanged.connect(lambda idx: self.configurationChanged.emit("RU", idx))
        
        # 6.17 OUTPUT Parameter Selection
        self.outputXCombo.setCurrentIndex(3)
        self.outputYCombo.setCurrentIndex(5)
        self.outputXCombo.currentIndexChanged.connect(lambda idx: self.configurationChanged.emit("PX", idx))
        self.outputYCombo.currentIndexChanged.connect(lambda idx: self.configurationChanged.emit("PY", idx))
        
        self.setup = Si1287Setup()
        self.applySetupButton.setEnabled(False)

        self.saveSetupButton.clicked.connect(self.save_setup)
        self.loadSetupButton.clicked.connect(self.load_setup)
        
        # -------- VISA resource enumeration --------
        self._populate_visa_resources()

        # Initial state
        # self._set_controls_enabled(False)
        # self.disconnectButton.setEnabled(False)

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
        try:
            self.disconnectRequested.emit()
        except Exception:
            pass
        self.thread.quit()
        self.thread.wait(2000)
        super().closeEvent(event)

    def _connect_clicked(self):
        if not self.resourceCombo.isEnabled():
            return
        res = self.resourceCombo.currentText()
        self.append_log(f"UI: Connect clicked ({res})")
        self.connectRequested.emit(res)
        
    def _close_clicked(self):
       
        self.disconnectRequested.emit()

    # def _apply_setup_clicked(self):
    #     cmds = [line.strip() for line in self.setupText.toPlainText().splitlines()]
    #     self.applySetupRequested.emit(cmds)

    def _start_stream_clicked(self):
        self.t.clear()
        self.a.clear()
        self.b.clear()
        self.curveA.setData([], [])
        self.curveB.setData([], [])

        self.startStreamRequested.emit()
        self.startStreamButton.setEnabled(False)
        self.stopStreamButton.setEnabled(True)

    def _stop_stream_clicked(self):
        self.stopStreamRequested.emit()
        self.startStreamButton.setEnabled(True)
        self.stopStreamButton.setEnabled(False)

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
        # self._set_controls_enabled(ok)
        self.connectButton.setEnabled(not ok)
        self.refreshButton.setEnabled(not ok)
        self.closeButton.setEnabled(ok)
        self.applySetupButton.setEnabled(ok)
        self.statusButton.setEnabled(ok)
        self.lastErrorButton.setEnabled(ok)        
        self.identifyButton.setEnabled(ok)
        self.clearErrorButton.setEnabled(ok)
        self.breakButton.setEnabled(ok)
        self.resetButton.setEnabled(ok)
        self.selfTestButton.setEnabled(ok)
        self.initializeButton.setEnabled(ok)
        self.resultOverallButton.setEnabled(ok)
        self.resultRAMButton.setEnabled(ok)
        self.resultROMButton.setEnabled(ok)
        self.resultTimerButton.setEnabled(ok)
        self.sweepStandbyButton.setEnabled(ok)
        self.sweepStartButton.setEnabled(ok)
        self.sweepStepButton.setEnabled(ok)
        self.clearErrorButton.setEnabled(ok)    
        
        if ok:
            self.stopStreamButton.setEnabled(False)
            self.startStreamButton.setEnabled(True)
        else:
            self.stopStreamButton.setEnabled(False)
            self.startStreamButton.setEnabled(False)
        self.connLed.set_connected(ok)

    @QtCore.pyqtSlot(object)
    def on_sample(self, sample: Sample):
        i0 = int(self.colASpin.value())
        i1 = int(self.colBSpin.value())

        v0 = sample.vals[i0] if i0 < len(sample.vals) else float("nan")
        v1 = sample.vals[i1] if i1 < len(sample.vals) else float("nan")

        self.t.append(sample.t)
        self.a.append(v0)
        self.b.append(v1)

        if len(self.t) > self.max_points:
            self.t = self.t[-self.max_points:]
            self.a = self.a[-self.max_points:]
            self.b = self.b[-self.max_points:]

        self.curveA.setData(self.t, self.a)
        self.curveB.setData(self.t, self.b)

    @QtCore.pyqtSlot(str)
    def append_log(self, s: str):
        self.logText.appendPlainText(s)
        sb = self.logText.verticalScrollBar()
        sb.setValue(sb.maximum())

    @QtCore.pyqtSlot(int)
    def ir_compensation_type_changed(self, idx: int):
        self.configurationChanged.emit("CT", idx)
        if idx == 0:
            self.feedbackCompensationSpin.setEnabled(True)
            self.cellCurrentOffTimeTypeCombo.setEnabled(False)
            self.outputToFRACombo.setEnabled(False)
            self.cellCurrentOffSpin.setEnabled(False)
        elif idx == 1:
            self.feedbackCompensationSpin.setEnabled(False)
            self.cellCurrentOffTimeTypeCombo.setEnabled(True)
            self.outputToFRACombo.setEnabled(True)
            self.cellCurrentOffSpin.setEnabled(True)

    @QtCore.pyqtSlot(int)
    def cell_current_off_time_type_combo_index_changed(self, idx: int):
        if idx == 0:
            self.cellCurrentOffTypeLabel.setText("Cell Current Off Time (µs))") 
            self.cellCurrentOffSpin.setMaximum(1360)  
            self.cellCurrentOffSpin.setMinimum(26.6)
            self.cellCurrentOffSpin.setValue(self.cellCurrentOffSpin.value() * 1360.0 / 255)
            self.cellCurrentOffSpin.setSingleStep(1)       
        elif idx == 1:
            self.cellCurrentOffTypeLabel.setText("Cell Current Off Ratio")
            self.cellCurrentOffSpin.setMaximum(255)  
            self.cellCurrentOffSpin.setMinimum(1)
            self.cellCurrentOffSpin.setValue(int(self.cellCurrentOffSpin.value() * 255 / 1360))
            self.cellCurrentOffSpin.setSingleStep(1)    
    
    @QtCore.pyqtSlot(int)
    def realpart_correction_combo_index_changed(self, idx: int):        
        if idx == 0:
            self.configurationChanged.emit("CC", 0)
            self.realPartCorrectionSpin.setEnabled(False)
        elif idx == 1:
            self.configurationChanged.emit("CC", 2)
            self.realPartCorrectionSpin.setEnabled(True)
            
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
        if idx == 0:
            self.configurationChanged.emit("OF", 0)
            # self.sweepStandbyButton.setText("Sweep Standby")
            self.sweetRampButton.setEnabled(True)
            self.sweetStepButton.setEnabled(True)
        elif idx == 1:
            self.configurationChanged.emit("OF", 1)
            # self.sweepStandbyButton.setText("Sweep Freeze")
            self.sweetRampButton.setEnabled(False)
            self.sweetStepButton.setEnabled(False)
        self.configurationChanged("SW",0)
            
    @QtCore.pyqtSlot()
    def sweep_step_button_clicked(self):
        if self.offModeCombo.currentIndex == 1:
            self.append_log("Instrument Sweep Mode Freeze")
        else:
            self.configurationChanged.emit("DL", self.delaySpin.value)
            self.configurationChanged.emit("SM",self.numberOfSegmentSpin.value)
            self.configurationChanged.emit("SA", self.speedSweepVoltage1Spin.value)
            self.configurationChanged.emit("KA", self.speedSweepCurrent1Spin.value)
            self.configurationChanged.emit("SB", self.speedSweepVoltage2Spin.value)
            self.configurationChanged.emit("KB", self.speedSweepCurrent2Spin.value)
            self.configurationChanged.emit("SC", self.speedSweepVoltage3Spin.value)
            self.configurationChanged.emit("KC", self.speedSweepCurrent3Spin.value)
            self.configurationChanged.emit("SD", self.speedSweepVoltage4Spin.value)
            self.configurationChanged.emit("KD", self.speedSweepCurrent4Spin.value)
            self.configurationChanged.emit("TE", self.speedSweepTime1Spin.value)
            self.configurationChanged.emit("VS", self.speedSweepVoltageStepSpin.value)
            self.configurationChanged.emit("IS", self.speedSweepCurrentStepSpin.value)
            self.configurationChanged.emit("SW",2)
            
    @QtCore.pyqtSlot()
    def sweep_ramp_button_clicked(self):
        if self.offModeCombo.currentIndex == 1:
            self.append_log("Instrument Sweep Mode Freeze")
        else:
            self.configurationChanged.emit("DL", self.delaySpin.value)
            self.configurationChanged.emit("SM",self.numberOfSegmentSpin.value)
            self.configurationChanged.emit("VA", self.rampSweepVoltage1Spin.value)
            self.configurationChanged.emit("JA", self.rampSweepCurrent1Spin.value)
            self.configurationChanged.emit("TA", self.rampSweepTime1Spin.value)
            self.configurationChanged.emit("VB", self.rampSweepVoltage2Spin.value)
            self.configurationChanged.emit("JB", self.rampSweepCurrent2Spin.value)
            self.configurationChanged.emit("TB", self.rampSweepTime2Spin.value)
            self.configurationChanged.emit("VC", self.rampSweepVoltage3Spin.value)
            self.configurationChanged.emit("JC", self.rampSweepCurrent3Spin.value)
            self.configurationChanged.emit("TC", self.rampSweepTime3Spin.value)
            self.configurationChanged.emit("VD", self.rampSweepVoltage4Spin.value)
            self.configurationChanged.emit("JD", self.rampSweepCurrent4Spin.value)
            self.configurationChanged.emit("TD", self.rampSweepTime4Spin.value)            
            self.configurationChanged.emit("SW",1)

    def save_setup(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save setup", "", "JSON (*.json)")
        if not path:
            return
        self.setup.values["PO"] = self.polarizationModeCombo.currentIndex()
        self.setup.values["PV"] = self.dcPotentialSpin.value()
        self.setup.values["PI"] = self.polarizationSignalGainCombo.currentIndex()

        self.setup.values["ON"] = self.polarizationOnModeCombo.currentIndex()
        self.setup.values["SY"] = self.bandwidthCombo.currentIndex()
        self.setup.values["GB"] = self.bandwidthGalvanostatCombo.currentIndex()
        self.setup.values["PB"] = self.bandwidthPotentiostatCombo.currentIndex()

        self.setup.values["BY"] = self.standbyModeCombo.currentIndex()
        

        self.setup.values["RR"] = self.standardResistantCombo.currentIndex()
        self.setup.values["IL"] = self.currentLimitCombo.currentIndex()
        self.setup.values["OL"] = self.currentOffLimitActionCombo.currentIndex()
        self.setup.values["CC"] = self.irCompensationCombo.currentIndex()
        self.setup.values["CT"] = self.irCompensationTypeCombo.currentIndex()
        self.setup.values["IC"] = self.feedbackCompensationSpin.value()
        self.setup.values["RO"] = self.outputToFRACombo.currentIndex()
        # self.setup.values["IN"] = self.cellCurrentOffSpin.value() if self.cellCurrentOffTimeTypeCombo.currentIndex() == 0 else int(self.cellCurrentOffSpin.value())
        self.setup.values["CELLCURRENT"] = self.cellCurrentOffTimeTypeCombo.currentIndex()
        if self.cellCurrentOffTimeTypeCombo.currentIndex() == 0:
            self.setup.values["IN"] = self.cellCurrentOffSpin.value()
        else:
            self.setup.values["IF"] = int(self.cellCurrentOffSpin.value())
        
        self.setup.values["RP"] = self.realPartCorrectionSpin.value() if self.realPartCorrectionCombo.currentIndex() == 1 else None
        self.setup.values["CC"] = 0 if self.realPartCorrectionCombo.currentIndex() == 0 else 2
        self.setup.values["VT"] = 0 if self.voltageBiasCombo.currentIndex() == 0 else 1
        self.setup.values["VR"] = self.voltageBiasSpin.value() if self.voltageBiasCombo.currentIndex() == 1 else None
        self.setup.values["IT"] = 0 if self.currentBiasCombo.currentIndex() == 0 else 1
        self.setup.values["IR"] = self.currentBiasSpin.value() if self.currentBiasCombo.currentIndex() == 1 else None
        self.setup.values["BR"] = self.biasRejectCombo.currentIndex()
        self.setup.values["FI"] = self.filterCombo.currentIndex()
        self.setup.values["VX"] = self.voltageAmplificationCombo.currentIndex()
        self.setup.values["IX"] = self.currentAmplificationCombo.currentIndex()
        self.setup.values["OF"] = self.offModeCombo.currentIndex()

        self.setup.values["DL"] = self.delaySpin.value()
        self.setup.values["SM"] = self.numberOfSegmentSpin.value()
        self.setup.values["SA"] = self.speedSweepVoltage1Spin.value()
        self.setup.values["KA"] = self.speedSweepCurrent1Spin.value()
        self.setup.values["SB"] = self.speedSweepVoltage2Spin.value()
        self.setup.values["KB"] = self.speedSweepCurrent2Spin.value()
        self.setup.values["SC"] = self.speedSweepVoltage3Spin.value()
        self.setup.values["KD"] = self.speedSweepCurrent4Spin.value()
        self.setup.values["SD"] = self.speedSweepVoltage4Spin.value()
        self.setup.values["TE"] = self.speedSweepTime1Spin.value()
        self.setup.values["VS"] = self.speedSweepVoltageStepSpin.value()
        self.setup.values["IS"] = self.speedSweepCurrentStepSpin.value()
        self.setup.values["VA"] = self.rampSweepVoltage1Spin.value()
        self.setup.values["JA"] = self.rampSweepCurrent1Spin.value()
        self.setup.values["TA"] = self.rampSweepTime1Spin.value()
        self.setup.values["VB"] = self.rampSweepVoltage2Spin.value()
        self.setup.values["JB"] = self.rampSweepCurrent2Spin.value()
        self.setup.values["TB"] = self.rampSweepTime2Spin.value()
        self.setup.values["VC"] = self.rampSweepVoltage3Spin.value()
        self.setup.values["JC"] = self.rampSweepCurrent3Spin.value()
        self.setup.values["TC"] = self.rampSweepTime3Spin.value()
        self.setup.values["VD"] = self.rampSweepVoltage4Spin.value()
        self.setup.values["JD"] = self.rampSweepCurrent4Spin.value()
        self.setup.values["TD"] = self.rampSweepTime4Spin.value()

        self.setup.values["DG"] = self.numberOfDigitsCombo.currentIndex()
        self.setup.values["RG"] = self.inputRangeCombo.currentIndex()
        self.setup.values["TR"] = self.measurementTriggerCombo.currentIndex()
        self.setup.values["DC"] = self.driftCombo.currentIndex()
        self.setup.values["AV"] = self.averagingtCombo.currentIndex()
        self.setup.values["NU"] = self.nullCombo.currentIndex()
        self.setup.values["RU"] = self.digitalVolmeterCombo.currentIndex()

        self.setup.values["PX"] = self.outputXCombo.currentIndex()
        self.setup.values["PY"] = self.outputYCombo.currentIndex()

        self.setup.save_json(path)
        self.append_log(f"Saved setup: {sys.path}")

    def load_setup(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Load setup", "", "JSON (*.json)")
        if not path:
            return
        self.setup.load_json(path)
        self.applySetupButton.setEnabled(True)
        self.append_log(f"Loaded setup (marked dirty): {path}")
            
def main():
    app = QtWidgets.QApplication(sys.argv)
    # apply_light_style(app)
    pg.setConfigOptions(antialias=True)
    w = MainWindow()
    w.resize(1200, 800)
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
