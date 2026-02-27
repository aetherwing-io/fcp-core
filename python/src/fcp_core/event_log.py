"""Generic event log with undo/redo and named checkpoints.

The log is cursor-based: ``cursor`` always points one past the last
*applied* event. Appending a new event when cursor < len truncates
the redo tail.

Generic over event type T — domains supply their own event dataclasses.
Checkpoint sentinels are stored inline so the log is self-describing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass
class CheckpointEvent:
    """Sentinel stored in the log so checkpoints survive serialisation."""

    _is_checkpoint: bool = field(default=True, init=False, repr=False)
    name: str = ""


class EventLog(Generic[T]):
    """Linear event log with cursor-based undo/redo and named checkpoints."""

    def __init__(self) -> None:
        self._events: list[T | CheckpointEvent] = []
        self._cursor: int = 0
        self._checkpoints: dict[str, int] = {}

    @property
    def cursor(self) -> int:
        """Current cursor position (one past last applied event)."""
        return self._cursor

    def __len__(self) -> int:
        """Total number of events (including checkpoints) up to cursor."""
        return self._cursor

    def append(self, event: T) -> None:
        """Add *event* at cursor position, truncating any redo tail."""
        if self._cursor < len(self._events):
            self._events = self._events[: self._cursor]
            self._checkpoints = {
                name: pos
                for name, pos in self._checkpoints.items()
                if pos <= self._cursor
            }
        self._events.append(event)
        self._cursor += 1

    def checkpoint(self, name: str) -> None:
        """Record the current cursor position under *name* and append a
        checkpoint sentinel."""
        self._checkpoints[name] = self._cursor
        # Append checkpoint sentinel — bypass the public append to avoid
        # type-checking issues (CheckpointEvent is not T)
        if self._cursor < len(self._events):
            self._events = self._events[: self._cursor]
            self._checkpoints = {
                n: p
                for n, p in self._checkpoints.items()
                if p <= self._cursor
            }
        self._events.append(CheckpointEvent(name=name))  # type: ignore[arg-type]
        self._cursor += 1

    def undo(self, count: int = 1) -> list[T]:
        """Move cursor back by *count* applied events (skipping checkpoints).

        Returns the events that should be reversed, most-recent-first.
        """
        reversed_events: list[T] = []
        remaining = count
        while remaining > 0 and self._cursor > 0:
            self._cursor -= 1
            ev = self._events[self._cursor]
            if isinstance(ev, CheckpointEvent):
                continue
            reversed_events.append(ev)  # type: ignore[arg-type]
            remaining -= 1
        return reversed_events

    def undo_to(self, name: str) -> list[T] | None:
        """Undo back to the named checkpoint.

        Returns events most-recent-first, or None if checkpoint not found.
        The cursor lands at the checkpoint position.
        """
        target = self._checkpoints.get(name)
        if target is None:
            return None
        reversed_events: list[T] = []
        while self._cursor > target:
            self._cursor -= 1
            ev = self._events[self._cursor]
            if not isinstance(ev, CheckpointEvent):
                reversed_events.append(ev)  # type: ignore[arg-type]
        return reversed_events

    def redo(self, count: int = 1) -> list[T]:
        """Replay up to *count* events forward from cursor (skipping
        checkpoint sentinels). Returns events in forward order."""
        replayed: list[T] = []
        remaining = count
        while remaining > 0 and self._cursor < len(self._events):
            ev = self._events[self._cursor]
            self._cursor += 1
            if isinstance(ev, CheckpointEvent):
                continue
            replayed.append(ev)  # type: ignore[arg-type]
            remaining -= 1
        return replayed

    def recent(self, count: int = 5) -> list[T]:
        """Return the last *count* non-checkpoint events up to the cursor,
        in chronological (oldest-first) order."""
        result: list[T] = []
        idx = self._cursor - 1
        while len(result) < count and idx >= 0:
            ev = self._events[idx]
            if not isinstance(ev, CheckpointEvent):
                result.append(ev)  # type: ignore[arg-type]
            idx -= 1
        result.reverse()
        return result
