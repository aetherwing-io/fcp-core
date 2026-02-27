"""Tests for fcp_core.session."""

from dataclasses import dataclass, field

from fcp_core.event_log import EventLog
from fcp_core.session import SessionDispatcher


@dataclass
class MockModel:
    title: str = "Untitled"
    data: list[str] = field(default_factory=list)


@dataclass
class MockEvent:
    action: str = ""
    value: str = ""


class MockHooks:
    """Mock implementation of SessionHooks."""

    def __init__(self):
        self.last_new_params: dict[str, str] = {}
        self.last_save_path: str = ""
        self.rebuild_count: int = 0

    def on_new(self, params: dict[str, str]) -> MockModel:
        self.last_new_params = params
        return MockModel(title=params.get("title", "Untitled"))

    def on_open(self, path: str) -> MockModel:
        return MockModel(title=f"Opened from {path}")

    def on_save(self, model: MockModel, path: str) -> None:
        self.last_save_path = path

    def on_rebuild_indices(self, model: MockModel) -> None:
        self.rebuild_count += 1

    def get_digest(self, model: MockModel) -> str:
        return f"Model: {model.title}"


def _make_dispatcher():
    hooks = MockHooks()
    log: EventLog[MockEvent] = EventLog()

    def reverse_event(ev: MockEvent, model: MockModel) -> None:
        if ev.action == "add":
            model.data.remove(ev.value)

    def replay_event(ev: MockEvent, model: MockModel) -> None:
        if ev.action == "add":
            model.data.append(ev.value)

    dispatcher = SessionDispatcher(
        hooks=hooks,
        event_log=log,
        reverse_event=reverse_event,
        replay_event=replay_event,
    )
    return dispatcher, hooks


class TestSessionNew:
    def test_new_creates_model(self):
        d, hooks = _make_dispatcher()
        result = d.dispatch('new "My Project"')
        assert "+" in result
        assert "My Project" in result
        assert d.model is not None
        assert d.model.title == "My Project"

    def test_new_with_params(self):
        d, hooks = _make_dispatcher()
        result = d.dispatch('new "Test" tempo:120 key:C')
        assert "+" in result
        assert d.model is not None

    def test_new_resets_event_log(self):
        d, hooks = _make_dispatcher()
        d.dispatch('new "First"')
        d.event_log.append(MockEvent("add", "x"))
        assert d.event_log.cursor == 1
        d.dispatch('new "Second"')
        assert d.event_log.cursor == 0


class TestSessionOpen:
    def test_open_loads_model(self):
        d, hooks = _make_dispatcher()
        result = d.dispatch("open ./test.file")
        assert "+" in result
        assert d.model is not None
        assert "Opened from ./test.file" in d.model.title

    def test_open_missing_path(self):
        d, hooks = _make_dispatcher()
        result = d.dispatch("open")
        assert "!" in result

    def test_open_sets_file_path(self):
        d, hooks = _make_dispatcher()
        d.dispatch("open ./test.file")
        assert d.file_path == "./test.file"


class TestSessionSave:
    def test_save_with_as_path(self):
        d, hooks = _make_dispatcher()
        d.dispatch('new "Test"')
        result = d.dispatch("save as:./output.file")
        assert "+" in result
        assert hooks.last_save_path == "./output.file"

    def test_save_no_model(self):
        d, hooks = _make_dispatcher()
        result = d.dispatch("save as:./output.file")
        assert "!" in result

    def test_save_no_path(self):
        d, hooks = _make_dispatcher()
        d.dispatch('new "Test"')
        result = d.dispatch("save")
        assert "!" in result  # no path set

    def test_save_remembers_path(self):
        d, hooks = _make_dispatcher()
        d.dispatch('new "Test"')
        d.dispatch("save as:./output.file")
        result = d.dispatch("save")
        assert "+" in result
        assert hooks.last_save_path == "./output.file"


class TestSessionCheckpoint:
    def test_checkpoint(self):
        d, hooks = _make_dispatcher()
        d.dispatch('new "Test"')
        result = d.dispatch("checkpoint v1")
        assert "+" in result
        assert "v1" in result

    def test_checkpoint_missing_name(self):
        d, hooks = _make_dispatcher()
        result = d.dispatch("checkpoint")
        assert "!" in result


class TestSessionUndo:
    def test_undo(self):
        d, hooks = _make_dispatcher()
        d.dispatch('new "Test"')
        d.model.data.append("item1")
        d.event_log.append(MockEvent("add", "item1"))
        result = d.dispatch("undo")
        assert "+" in result
        assert "Undone 1 event" in result
        assert "item1" not in d.model.data

    def test_undo_no_model(self):
        d, hooks = _make_dispatcher()
        result = d.dispatch("undo")
        assert "!" in result

    def test_undo_nothing_to_undo(self):
        d, hooks = _make_dispatcher()
        d.dispatch('new "Test"')
        result = d.dispatch("undo")
        assert "!" in result
        assert "Nothing to undo" in result

    def test_undo_to_checkpoint(self):
        d, hooks = _make_dispatcher()
        d.dispatch('new "Test"')
        d.dispatch("checkpoint v1")
        d.model.data.append("a")
        d.event_log.append(MockEvent("add", "a"))
        d.model.data.append("b")
        d.event_log.append(MockEvent("add", "b"))
        result = d.dispatch("undo to:v1")
        assert "+" in result
        assert "Undone 2 event" in result
        assert d.model.data == []

    def test_undo_to_nonexistent_checkpoint(self):
        d, hooks = _make_dispatcher()
        d.dispatch('new "Test"')
        result = d.dispatch("undo to:nope")
        assert "!" in result

    def test_undo_rebuilds_indices(self):
        d, hooks = _make_dispatcher()
        d.dispatch('new "Test"')
        initial_count = hooks.rebuild_count
        d.model.data.append("item1")
        d.event_log.append(MockEvent("add", "item1"))
        d.dispatch("undo")
        assert hooks.rebuild_count > initial_count


class TestSessionRedo:
    def test_redo(self):
        d, hooks = _make_dispatcher()
        d.dispatch('new "Test"')
        d.model.data.append("item1")
        d.event_log.append(MockEvent("add", "item1"))
        d.dispatch("undo")
        result = d.dispatch("redo")
        assert "+" in result
        assert "Redone 1 event" in result
        assert "item1" in d.model.data

    def test_redo_no_model(self):
        d, hooks = _make_dispatcher()
        result = d.dispatch("redo")
        assert "!" in result

    def test_redo_nothing_to_redo(self):
        d, hooks = _make_dispatcher()
        d.dispatch('new "Test"')
        result = d.dispatch("redo")
        assert "!" in result


class TestSessionUnknown:
    def test_unknown_command(self):
        d, hooks = _make_dispatcher()
        result = d.dispatch("explode")
        assert "!" in result
        assert "Unknown" in result
