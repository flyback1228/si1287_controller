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
    polarizationChanged = QtCore.pyqtSignal(bool)
    errorStatusChanged = QtCore.pyqtSignal(bool)
    
    
    
    def __init__(self):
        super().__init__()
        self._rm: Optional[pyvisa.ResourceManager] = None
        self._inst = None

        self._streaming = False
        self._t0 = 0.0
        
        self._polarization = False


        self._timer: Optional[QtCore.QTimer] = None

    def _log(self, s: str):
        self.logLine.emit(s)

    # ---- Thread bootstrap: start a timer so queued slots always work ----
    @QtCore.pyqtSlot()
    def start(self):
        """Called once when the worker thread starts."""
        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(20)  # ms
        self._timer.timeout.connect(self._tick)
        self._timer.start()
        self._log("Worker started (timer running).")

    @QtCore.pyqtSlot()
    def shutdown(self):
        self._streaming = False
        if self._timer is not None:
            self._timer.stop()
            self._timer.deleteLater()
            self._timer = None
        self._cleanup()

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
        try:
            self._ensure_connected()
        except Exception:
            self._log("Write failed: Not connected")
            return
        cmd = cmd.strip()
        if not cmd:
            return
        self._inst.write(cmd)
        self._log(f">> {cmd}")

    def _query(self, cmd: str, timeout_ms: int = 5000) -> str:
        try:
            self._ensure_connected()
        except Exception:
            self._log("Query failed: Not connected")
            return ""
        old_to = self._inst.timeout
        self._inst.timeout = timeout_ms
        try:
            self._inst.write(cmd)
            self._log(f">> {cmd}")
            resp = self._inst.read()
            self._log(f"<< {resp!r}")
            if cmd.strip().upper() == "?ER":
                self._emit_error_status(resp)
            return resp
        finally:
            self._inst.timeout = old_to

    def _emit_error_status(self, resp: str):
        txt = (resp or "").strip()
        try:
            # SI1287 ?ER is expected to return an integer status code.
            code = int(txt.split(",")[0].strip())
            self.errorStatusChanged.emit(code == 0)
        except Exception:
            self._log(f"Unable to parse ?ER response: {resp!r}")
            self.errorStatusChanged.emit(False)

    def _parse_status_code(self, resp: str) -> Optional[int]:
        txt = (resp or "").strip()
        if not txt:
            return None
        try:
            return int(txt.split(",")[0].strip())
        except Exception:
            return None

    def _query_with_retry(
        self, cmd: str, timeout_ms: int = 5000, attempts: int = 3, delay_s: float = 0.2
    ) -> str:
        last_error = None
        for i in range(attempts):
            try:
                return self._query(cmd, timeout_ms=timeout_ms)
            except Exception as e:
                last_error = e
                if i < attempts - 1:
                    self._log(
                        f"{cmd} query failed ({i + 1}/{attempts}), retrying..."
                    )
                    time.sleep(delay_s)
        raise last_error

    def _write_and_check_error(
        self, cmd: str, delay_s: float = 0.05, timeout_ms: int = 2000
    ) -> Optional[int]:
        self._write(cmd)
        if delay_s > 0:
            time.sleep(delay_s)
        r = self._query("?ER", timeout_ms=timeout_ms)
        code = self._parse_status_code(r)
        if code not in (None, 0):
            self._log(f"Command {cmd!r} rejected by instrument (?ER={r.strip()!r}).")
        return code

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
            try:
                self._query_with_retry("?VN", timeout_ms=5000, attempts=3, delay_s=0.2)
                self._query_with_retry("?ER", timeout_ms=5000, attempts=3, delay_s=0.2)
            except Exception as e:
                # Keep the transport connection state as connected.
                # Some instruments respond slowly right after opening a VISA session.
                self._log(f"Connected, but startup query failed: {e}")

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
        self.errorStatusChanged.emit(False)
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
    def handle_si1287_configuration(self,str,obj):
        if obj is None:
            try:
                self._query(str,timeout_ms=5000)
            except Exception as e:
                self._log(f"Query Command {str} Failed: {e}")
        else:
            try:
                self._write(f"{str}{obj}")
            except Exception as e:
                self._log(f"Write Command {str}{obj} Failed: {e}")

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
            self._streaming = False

            # Put the SI1287 into a known-good measurement state before graph output.
            setup_cmds = ["CE", "DG0", "RG0", "TR1", "DC0", "AV0", "NU0", "RU1", "PX3", "PY5"]
            for cmd in setup_cmds:
                code = self._write_and_check_error(cmd)
                if code not in (None, 0):
                    self._log(f"Start stream aborted during setup command {cmd!r}.")
                    return

            code = self._write_and_check_error("GP0", delay_s=0.1)
            if code not in (None, 0):
                self._log("Start stream aborted while resetting graph output.")
                return

            code = self._write_and_check_error("GP1", delay_s=0.1)
            if code not in (None, 0):
                self._log("Start stream aborted when enabling graph output.")
                return

            self._streaming = True
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

    @QtCore.pyqtSlot()
    def start_polarization(self):
        try:
            if self._inst is not None:
                self._write("PW1")
                time.sleep(1)
                r = self._query("?ER", timeout_ms=5000)
                code = self._parse_status_code(r)
                if code == 0:
                    self._polarization = True
                    self.polarizationChanged.emit(True)
                else:
                    # If the SI1287 reports an error after PW1, force the output
                    # back off so a rejected start cannot leave polarization on.
                    try:
                        self._write("PW0")
                        time.sleep(0.2)
                        rollback = self._query("?ER", timeout_ms=5000)
                        self._log(
                            f"Rollback after failed PW1 returned ?ER={rollback.strip()!r}."
                        )
                    except Exception as rollback_error:
                        self._log(
                            f"Rollback after failed PW1 also failed: {rollback_error}"
                        )
                    self._polarization = False
                    self.polarizationChanged.emit(False)
                    self._log(
                        f"Start polarization rejected by instrument (?ER={r.strip()!r})."
                    )
        except Exception as e:
            self._log(f"Start polarization failed: {e}")
            
    @QtCore.pyqtSlot()
    def stop_polarization(self):
        try:
            if self._inst is not None:
                self._write("PW0")                
                time.sleep(1)
                r = self._query("?ER", timeout_ms=5000)
                code = self._parse_status_code(r)
                if code == 0:
                    self._polarization = False
                    self.polarizationChanged.emit(False)
                else:
                    self._log(
                        f"Stop polarization rejected by instrument (?ER={r.strip()!r})."
                    )
        except Exception as e:
            self._log(f"Stop polarization failed: {e}")    
                   

__all__ = ["VisaWorker", "Sample"]
