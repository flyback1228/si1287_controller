from pathlib import Path

from PyQt6 import QtWidgets, uic


class StepSweepWindow(QtWidgets.QDialog):
    def __init__(self, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)
        ui_path = Path(__file__).resolve().parent / "step_sweep_window.ui"
        uic.loadUi(str(ui_path), self)
        self.closeButton.clicked.connect(self.hide)
        self.runButton_2.clicked.connect(self.hide)
        self._is_current_mode = False
        self.set_sweep_running(False)

    def load_from_values(self, values: dict[str, int | float]):
        self.offModeCombo.setCurrentIndex(int(values["off_mode"]))
        self.delaySpin.setValue(int(values["delay"]))
        self.numberOfSegmentSpin.setValue(int(values["segments"]))
        self.level1Spin.setValue(float(values["v1"]))
        self.level2Spin.setValue(float(values["v2"]))
        self.level3Spin.setValue(float(values["v3"]))
        self.level4Spin.setValue(float(values["v4"]))
        self.speedSweepTime1Spin.setValue(float(values["time"]))
        self.stepSpin.setValue(float(values["v_step"]))

    def values(self) -> dict[str, int | float]:
        return {
            "off_mode": self.offModeCombo.currentIndex(),
            "delay": self.delaySpin.value(),
            "segments": self.numberOfSegmentSpin.value(),
            "v1": self.level1Spin.value(),
            "v2": self.level2Spin.value(),
            "v3": self.level3Spin.value(),
            "v4": self.level4Spin.value(),
            "time": self.speedSweepTime1Spin.value(),
            "v_step": self.stepSpin.value(),
        }

    def set_polarization_mode(self, mode_index: int):
        self._is_current_mode = mode_index == 1
        if self._is_current_mode:
            self.labelVoltage.setText("Current Level")
            self.labelStep.setText("Current Step")
        else:
            self.labelVoltage.setText("Voltage Level")
            self.labelStep.setText("Voltage Step")

    def set_sweep_running(self, running: bool):
        self.groupBoxSetup.setEnabled(not running)
        self.groupBoxLevels.setEnabled(not running)
        self.groupBoxStep.setEnabled(not running)
        self.runButton.setEnabled(not running)
        self.closeButton.setEnabled(not running)
        self.runButton_2.setEnabled(running)
