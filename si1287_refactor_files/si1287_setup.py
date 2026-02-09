# si1287_setup.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict
import json


@dataclass
class Si1287Setup:
    """Tracks SI1287 configuration values and which ones have changed (dirty).

    - values: the last known/loaded value for each command (e.g., "PO" -> 0)
    - dirty: only the commands that have been modified since last Apply
    """

    values: Dict[str, Any] = field(default_factory=dict)
    dirty: Dict[str, Any] = field(default_factory=dict)

    def set(self, cmd: str, value: Any) -> None:
        # Normalize command
        cmd = str(cmd).strip()
        if not cmd:
            return

        if self.values.get(cmd) != value:
            self.values[cmd] = value
            self.dirty[cmd] = value

    def clear_dirty(self) -> None:
        self.dirty.clear()

    def get_dirty_commands(self) -> Dict[str, Any]:
        return dict(self.dirty)

    def save(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.values, f, indent=2, sort_keys=True)

    def load(self, path: str) -> None:
        with open(path, "r", encoding="utf-8") as f:
            self.values = json.load(f)
        # After loading, consider everything dirty until applied.
        self.dirty = dict(self.values)
