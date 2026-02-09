# visa_worker.py
import time
from dataclasses import dataclass
from typing import List, Optional

import pyvisa
from pyvisa import errors
from PyQt6 import QtCore


@dataclass
class Sample:
    t: float
    vals: List[float]
    raw: str


class VisaWorker(QtCore.QObject):
    # UI signals
    logLine = QtCore.pyqtSignal(str)
    connectedChanged = QtCore.pyqtSignal(bool)
    sampleReady = QtCore.pyqtSignal(object)  # Sample

    def __init__(self):
        super().__init__()
        self._rm: Optional[pyvisa.ResourceManager] = None
        self._inst = None

        self._streaming = False
        self._t0 = 0.0

        self._timer: Optional[QtCore.QTimer] = None

    def _log(self, s: str):
        self.logLine.emit(s)

    # ---- Thread bootstrap: start a timer so queued slots always work ----
    @QtCore.pyqtSlot()
    def start(self):
        """Called once when the worker thread starts."""
        self._timer = QtCore.QTimer()
        self._timer.setInterval(20)  # ms
        self._timer.timeout.connect(self._tick)
        self._timer.start()
        self._log("Worker started (timer running).")

    def _tick(self):
        """Polling loop (runs in worker thread via QTimer)."""
        if not self._streaming or self._inst is None:
            return

        try:
            # short timeout so we never block the thread
            old_to = self._inst.timeout
            self._inst.timeout = 300  # ms
            try:
                raw = self._inst.read()
            finally:
                self._inst.timeout = old_to

            if not raw:
                return

            # Log raw return string from instrument
            self._log(f"<< {raw!r}")

            line = raw.strip()
            if not line:
                return

            parts = [p.strip() for p in line.split(",") if p.strip()]
            try:
                vals = [float(p) for p in parts]
            except ValueError:
                # still keep raw in log; just don't emit Sample
                return

            t = time.time() - self._t0
            self.sampleReady.emit(Sample(t=t, vals=vals, raw=line))

        except errors.VisaIOError as e:
            if e.error_code == errors.StatusCode.error_timeout:
                return
            self._log(f"VISA read error: {e}")
            self._streaming = False
        except Exception as e:
            self._log(f"Stream exception: {e}")
            self._streaming = False

    # ---- VISA helpers ----
    def _ensure_connected(self):
        if self._inst is None:
            raise RuntimeError("Not connected")

    def _write(self, cmd: str):
        self._ensure_connected()
        cmd = cmd.strip()
        if not cmd:
            return
        self._inst.write(cmd)
        self._log(f">> {cmd}")

    def _query(self, cmd: str, timeout_ms: int = 5000) -> str:
        self._ensure_connected()
        old_to = self._inst.timeout
        self._inst.timeout = timeout_ms
        try:
            self._inst.write(cmd)
            self._log(f">> {cmd}")
            resp = self._inst.read()
            self._log(f"<< {resp!r}")
            return resp
        finally:
            self._inst.timeout = old_to

    # ---- Public slots called by UI (queued to worker thread) ----
    @QtCore.pyqtSlot(str)
    def connectVisa(self, resource: str):
        try:
            resource = resource.strip()
            self._log(f"Connecting to {resource} ...")

            self._rm = pyvisa.ResourceManager()
            inst = self._rm.open_resource(resource)

            # SI1287: EOI only write; LF read termination
            inst.write_termination = None
            inst.read_termination = "\n"
            inst.timeout = 3000

            self._inst = inst
            self.connectedChanged.emit(True)
            self._log(f"Connected: {resource}")

            # quick sanity queries
            self._query("?VN", timeout_ms=5000)
            self._query("?ER", timeout_ms=5000)

        except Exception as e:
            self._log(f"Connect failed: {e}")
            self._cleanup()
            self.connectedChanged.emit(False)

    @QtCore.pyqtSlot()
    def disconnectVisa(self):
        self._log("Disconnect requested...")
        self._streaming = False

        try:
            if self._inst is not None:
                try:
                    self._inst.write("GP0")
                    self._log(">> GP0")
                except Exception:
                    pass
        except Exception:
            pass

        self._cleanup()
        self.connectedChanged.emit(False)
        self._log("Disconnected.")

    def _cleanup(self):
        try:
            if self._inst is not None:
                try:
                    self._inst.close()
                except Exception:
                    pass
        finally:
            self._inst = None

        try:
            if self._rm is not None:
                try:
                    self._rm.close()
                except Exception:
                    pass
        finally:
            self._rm = None
            
    @QtCore.pyqtSlot(str,object)
    def send_command(self, cmd, value):
        if value is None:
            try:
                self._query(cmd,timeout_ms=5000)
            except Exception as e:
                self._log(f"Query Command {cmd} Failed: {e}")
        else:
            self._write(f"{cmd}{value}")

    # @QtCore.pyqtSlot()
    # def identify(self):
    #     try:
    #         self._query("?VN", timeout_ms=5000)
    #     except Exception as e:
    #         self._log(f"Identify failed: {e}")

    # @QtCore.pyqtSlot()
    # def status(self):
    #     try:
    #         self._query("?ST", timeout_ms=5000)
    #     except Exception as e:
    #         self._log(f"Status failed: {e}")

    # @QtCore.pyqtSlot()
    # def last_error(self):
    #     try:
    #         self._query("?ER", timeout_ms=5000)
    #     except Exception as e:
    #         self._log(f"Last error failed: {e}")

    # @QtCore.pyqtSlot()
    # def clear_error(self):
    #     try:
    #         self._write("CE")
    #         time.sleep(0.05)
    #         self._query("?ER", timeout_ms=5000)
    #     except Exception as e:
    #         self._log(f"Clear error failed: {e}")
            
    @QtCore.pyqtSlot(int)
    def break_self_test(self,value: int):
        try:
            self._write(f"BK{value}")
            time.sleep(1)
            self._query("?ER", timeout_ms=5000)
        except Exception as e:
            self._log(f"Clear error failed: {e}")

    # @QtCore.pyqtSlot(int)
    # def set_mode(self, mode: int):
    #     try:
    #         # 0 -> PO0, 1 -> PO1
    #         self._write("PO0" if mode == 0 else "PO1")
    #         time.sleep(0.05)
    #         self._query("?ER", timeout_ms=5000)
    #     except Exception as e:
    #         self._log(f"Set mode failed: {e}")

    # @QtCore.pyqtSlot(list)
    # def apply_setup(self, cmds: list):
    #     try:
    #         self._ensure_connected()
    #         for c in cmds:
    #             c = str(c).strip()
    #             if not c:
    #                 continue
    #             self._write(c)
    #             time.sleep(0.05)
    #         self._query("?ER", timeout_ms=5000)
    #     except Exception as e:
    #         self._log(f"Apply setup failed: {e}")

    @QtCore.pyqtSlot()
    def start_stream(self):
        try:
            self._ensure_connected()
            self._t0 = time.time()
            self._streaming = True
            self._write("GP1")
        except Exception as e:
            self._log(f"Start stream failed: {e}")
            self._streaming = False

    @QtCore.pyqtSlot()
    def stop_stream(self):
        try:
            self._streaming = False
            if self._inst is not None:
                self._write("GP0")
        except Exception as e:
            self._log(f"Stop stream failed: {e}")



__all__ = ["VisaWorker", "Sample"]
