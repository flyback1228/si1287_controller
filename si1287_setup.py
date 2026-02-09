# si1287_setup.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict
import json


@dataclass
class Si1287Setup:
    values: Dict[str, Any] = field(default_factory=dict)
    dirty: Dict[str, Any] = field(default_factory=dict)

    def set(self, cmd: str, value: Any) -> None:
        """Store value; mark as dirty only if changed."""
        if self.values.get(cmd) != value:
            self.values[cmd] = value
            self.dirty[cmd] = value

    def clear_dirty(self) -> None:
        self.dirty.clear()

    def get_dirty(self) -> Dict[str, Any]:
        return dict(self.dirty)

    def save_json(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.values, f, indent=2)

    def load_json(self, path: str) -> None:
        with open(path, "r", encoding="utf-8") as f:
            self.values = json.load(f)
        # mark everything dirty so Apply will push loaded settings
        self.dirty = dict(self.values)
