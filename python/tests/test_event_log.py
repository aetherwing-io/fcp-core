"""Tests for fcp_core.event_log."""

from dataclasses import dataclass

from fcp_core.event_log import CheckpointEvent, EventLog


@dataclass
class MockEvent:
    """Simple event for testing."""
    value: str


class TestEventLogAppend:
    def test_append_increments_cursor(self):
        log: EventLog[MockEvent] = EventLog()
        log.append(MockEvent("a"))
        assert log.cursor == 1

    def test_append_multiple(self):
        log: EventLog[MockEvent] = EventLog()
        log.append(MockEvent("a"))
        log.append(MockEvent("b"))
        log.append(MockEvent("c"))
        assert log.cursor == 3

    def test_len_matches_cursor(self):
        log: EventLog[MockEvent] = EventLog()
        log.append(MockEvent("a"))
        log.append(MockEvent("b"))
        assert len(log) == 2

    def test_append_truncates_redo_tail(self):
        log: EventLog[MockEvent] = EventLog()
        log.append(MockEvent("a"))
        log.append(MockEvent("b"))
        log.undo()  # cursor at 1
        log.append(MockEvent("c"))  # should truncate "b"
        assert log.cursor == 2
        # Redo should have nothing
        assert log.redo() == []


class TestEventLogUndo:
    def test_undo_single(self):
        log: EventLog[MockEvent] = EventLog()
        log.append(MockEvent("a"))
        log.append(MockEvent("b"))
        reversed_events = log.undo()
        assert len(reversed_events) == 1
        assert reversed_events[0].value == "b"
        assert log.cursor == 1

    def test_undo_multiple(self):
        log: EventLog[MockEvent] = EventLog()
        log.append(MockEvent("a"))
        log.append(MockEvent("b"))
        log.append(MockEvent("c"))
        reversed_events = log.undo(2)
        assert len(reversed_events) == 2
        assert reversed_events[0].value == "c"
        assert reversed_events[1].value == "b"
        assert log.cursor == 1

    def test_undo_on_empty_log(self):
        log: EventLog[MockEvent] = EventLog()
        assert log.undo() == []

    def test_undo_more_than_available(self):
        log: EventLog[MockEvent] = EventLog()
        log.append(MockEvent("a"))
        reversed_events = log.undo(5)
        assert len(reversed_events) == 1
        assert log.cursor == 0

    def test_undo_skips_checkpoints(self):
        log: EventLog[MockEvent] = EventLog()
        log.append(MockEvent("a"))
        log.checkpoint("v1")
        log.append(MockEvent("b"))
        reversed_events = log.undo()
        assert len(reversed_events) == 1
        assert reversed_events[0].value == "b"


class TestEventLogRedo:
    def test_redo_single(self):
        log: EventLog[MockEvent] = EventLog()
        log.append(MockEvent("a"))
        log.append(MockEvent("b"))
        log.undo()
        replayed = log.redo()
        assert len(replayed) == 1
        assert replayed[0].value == "b"
        assert log.cursor == 2

    def test_redo_on_nothing(self):
        log: EventLog[MockEvent] = EventLog()
        log.append(MockEvent("a"))
        assert log.redo() == []

    def test_redo_skips_checkpoints(self):
        log: EventLog[MockEvent] = EventLog()
        log.append(MockEvent("a"))
        log.checkpoint("v1")
        log.append(MockEvent("b"))
        log.undo(2)  # undo "b" and "a" (skipping checkpoint)
        replayed = log.redo(2)
        assert len(replayed) == 2
        assert replayed[0].value == "a"
        assert replayed[1].value == "b"


class TestEventLogCheckpoint:
    def test_checkpoint_creates_sentinel(self):
        log: EventLog[MockEvent] = EventLog()
        log.append(MockEvent("a"))
        log.checkpoint("v1")
        # Cursor advanced by one for the checkpoint sentinel
        assert log.cursor == 2

    def test_undo_to_checkpoint(self):
        log: EventLog[MockEvent] = EventLog()
        log.append(MockEvent("a"))
        log.checkpoint("v1")
        log.append(MockEvent("b"))
        log.append(MockEvent("c"))
        reversed_events = log.undo_to("v1")
        assert reversed_events is not None
        assert len(reversed_events) == 2
        assert reversed_events[0].value == "c"
        assert reversed_events[1].value == "b"

    def test_undo_to_nonexistent_checkpoint(self):
        log: EventLog[MockEvent] = EventLog()
        log.append(MockEvent("a"))
        result = log.undo_to("nope")
        assert result is None

    def test_checkpoint_invalidated_by_new_append(self):
        log: EventLog[MockEvent] = EventLog()
        log.append(MockEvent("a"))
        log.checkpoint("v1")
        log.append(MockEvent("b"))
        # Undo past checkpoint
        log.undo(2)  # undo "b", skip checkpoint, undo -> cursor should be at 0
        # Append new event, which should truncate the redo tail including checkpoint
        log.append(MockEvent("c"))
        # v1 checkpoint should be gone
        result = log.undo_to("v1")
        assert result is None


class TestEventLogRecent:
    def test_recent(self):
        log: EventLog[MockEvent] = EventLog()
        log.append(MockEvent("a"))
        log.append(MockEvent("b"))
        log.append(MockEvent("c"))
        recent = log.recent(2)
        assert len(recent) == 2
        assert recent[0].value == "b"
        assert recent[1].value == "c"

    def test_recent_skips_checkpoints(self):
        log: EventLog[MockEvent] = EventLog()
        log.append(MockEvent("a"))
        log.checkpoint("v1")
        log.append(MockEvent("b"))
        recent = log.recent(5)
        assert len(recent) == 2
        assert recent[0].value == "a"
        assert recent[1].value == "b"

    def test_recent_on_empty(self):
        log: EventLog[MockEvent] = EventLog()
        assert log.recent() == []

    def test_recent_respects_cursor(self):
        log: EventLog[MockEvent] = EventLog()
        log.append(MockEvent("a"))
        log.append(MockEvent("b"))
        log.append(MockEvent("c"))
        log.undo()  # cursor at 2
        recent = log.recent(5)
        assert len(recent) == 2
        assert recent[0].value == "a"
        assert recent[1].value == "b"
