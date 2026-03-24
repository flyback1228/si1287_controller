from pathlib import Path

from PyQt6 import QtWidgets, uic


class RampSweepWindow(QtWidgets.QDialog):
    def __init__(self, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)
        ui_path = Path(__file__).resolve().parent / "ramp_sweep_window.ui"
        uic.loadUi(str(ui_path), self)
        self.closeButton.clicked.connect(self.hide)
        self.runRampSweep.clicked.connect(self.hide)
        self._is_current_mode = False
        self.set_sweep_running(False)

    def load_from_values(self, values: dict[str, int | float]):
        self.offModeCombo.setCurrentIndex(int(values["off_mode"]))
        self.delaySpin.setValue(int(values["delay"]))
        self.numberOfSegmentSpin.setValue(int(values["segments"]))
        self.filterCombo.setCurrentIndex(int(values["filter"]))
        self.rampSweepVoltage1Spin.setValue(float(values["v1"]))
        self.rampSweepVoltage2Spin.setValue(float(values["v2"]))
        self.rampSweepVoltage3Spin.setValue(float(values["v3"]))
        self.rampSweepVoltage4Spin.setValue(float(values["v4"]))
        self.rampSweepTime1Spin.setValue(float(values["t1"]))
        self.rampSweepTime2Spin.setValue(float(values["t2"]))
        self.rampSweepTime3Spin.setValue(float(values["t3"]))
        self.rampSweepTime4Spin.setValue(float(values["t4"]))

    def values(self) -> dict[str, int | float]:
        return {
            "off_mode": self.offModeCombo.currentIndex(),
            "delay": self.delaySpin.value(),
            "segments": self.numberOfSegmentSpin.value(),
            "filter": self.filterCombo.currentIndex(),
            "v1": self.rampSweepVoltage1Spin.value(),
            "v2": self.rampSweepVoltage2Spin.value(),
            "v3": self.rampSweepVoltage3Spin.value(),
            "v4": self.rampSweepVoltage4Spin.value(),
            "t1": self.rampSweepTime1Spin.value(),
            "t2": self.rampSweepTime2Spin.value(),
            "t3": self.rampSweepTime3Spin.value(),
            "t4": self.rampSweepTime4Spin.value(),
        }

    def set_polarization_mode(self, mode_index: int):
        self._is_current_mode = mode_index == 1
        if self._is_current_mode:
            self.labelVoltage.setText("Current Level")
        else:
            self.labelVoltage.setText("Voltage Level")

    def set_sweep_running(self, running: bool):
        self.groupBoxSetup.setEnabled(not running)
        self.groupBoxLevels.setEnabled(not running)
        self.startRampSweep.setEnabled(not running)
        self.closeButton.setEnabled(not running)
        self.runRampSweep.setEnabled(running)
