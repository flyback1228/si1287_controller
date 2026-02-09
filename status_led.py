from PyQt6 import QtCore, QtWidgets, QtGui, uic  # add QtGui if not already

class StatusLed(QtWidgets.QWidget):
    """Simple round LED indicator for status bar."""
    def __init__(self, diameter: int = 12, parent=None):
        super().__init__(parent)
        self._d = diameter
        self._color = QtGui.QColor("#e74c3c")  # red (off)
        self.setFixedSize(diameter, diameter)

    def set_connected(self, connected: bool):
        self._color = QtGui.QColor("#2ecc71" if connected else "#e74c3c")
        self.update()

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)

        rect = QtCore.QRectF(0.5, 0.5, self._d - 1, self._d - 1)
        p.setPen(QtGui.QPen(QtGui.QColor("#555"), 1))
        p.setBrush(QtGui.QBrush(self._color))
        p.drawEllipse(rect)