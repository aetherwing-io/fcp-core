# FCP Event Log Specification

**Version:** 0.1.0

## Overview

The event log is a linear, cursor-based record of all mutations applied to the domain model. It provides undo/redo functionality and named checkpoints. The event log is a core FCP component; every conforming server MUST implement it.

## Data Structure

```
EventLog {
  events: Event[]                 // ordered list of all events
  cursor: int                     // index past the last applied event
  checkpoints: Map<string, int>   // name -> cursor position at time of checkpoint
}
```

### Cursor Semantics

The cursor always points **one past** the last applied event:

```
events:  [e0, e1, e2, e3, e4]
cursor:                        ^  (cursor = 5, all events applied)

After undo(1):
events:  [e0, e1, e2, e3, e4]
cursor:                    ^      (cursor = 4, e4 is undone)

After redo(1):
events:  [e0, e1, e2, e3, e4]
cursor:                        ^  (cursor = 5, e4 is re-applied)
```

Events between `cursor` and `len(events)` are the "redo tail" -- undone events that can be replayed.

## Operations

### `append(event)`

Add a new event at the cursor position.

**Behavior:**
1. If `cursor < len(events)`, truncate the event list at `cursor` (the redo tail is lost).
2. Remove any checkpoints that reference positions beyond the new end.
3. Append the event.
4. Increment the cursor.

**Critical:** Appending a new mutation after an undo destroys the redo history. This is the standard cursor-based undo model (not stack-based). This matches the behavior of text editors, DAWs, and drawing tools.

```
Before: events=[e0,e1,e2,e3,e4], cursor=3  (e3,e4 in redo tail)
append(e5):
After:  events=[e0,e1,e2,e5],    cursor=4  (e3,e4 gone)
```

### `checkpoint(name)`

Create a named snapshot of the current cursor position.

**Behavior:**
1. Store `name -> cursor` in the checkpoints map.
2. Append a `CheckpointEvent` sentinel to the event list.

The `CheckpointEvent` is a special event type with no model effect. It exists so that checkpoints survive serialization and so that undo/redo operations can skip over them without counting them as real operations.

### `undo(count=1)`

Move the cursor backward by `count` real (non-checkpoint) events.

**Behavior:**
1. Starting from `cursor - 1`, walk backward through events.
2. Skip `CheckpointEvent` sentinels (they don't count toward `count`).
3. For each non-checkpoint event encountered, add it to the result list and decrement `count`.
4. Stop when `count` reaches 0 or cursor reaches 0.
5. Update the cursor to the new position.
6. Return the events in reverse chronological order (most recent first).

The caller (session handler) is responsible for applying `reverseEvent()` for each returned event.

### `undoTo(name)`

Move the cursor backward to a named checkpoint.

**Behavior:**
1. Look up the checkpoint position for `name`.
2. If not found, raise an error.
3. If the checkpoint position is at or beyond the current cursor, return null (can't undo forward).
4. Collect all non-checkpoint events between the current cursor and the checkpoint position.
5. Move the cursor to the checkpoint position.
6. Return the collected events in reverse chronological order.

### `redo(count=1)`

Move the cursor forward by `count` real events.

**Behavior:**
1. Starting from `cursor`, walk forward through events.
2. Skip `CheckpointEvent` sentinels.
3. For each non-checkpoint event, add it to the result list and decrement `count`.
4. Stop when `count` reaches 0 or cursor reaches `len(events)`.
5. Update the cursor.
6. Return events in chronological order (oldest first).

### `recent(count)`

Return the last `count` non-checkpoint events up to the cursor, in chronological order. This is a read-only query for the `history N` query command.

## Event Types

Events are domain-specific discriminated unions. Each event has a `type` string field that identifies it.

### fcp-drawio events

```
shape_created    { shape }
shape_modified   { id, before, after }
shape_deleted    { shape }
edge_created     { edge }
edge_modified    { id, before, after }
edge_deleted     { edge }
group_created    { group }
group_modified   { id, before, after }
group_dissolved  { group }
page_added       { page }
page_removed     { page }
layer_created    { layer, pageId }
layer_modified   { pageId, layerId, before, after }
flow_direction_changed { pageId, before, after }
title_changed    { before, after }
checkpoint       { name, eventIndex }
```

### fcp-midi events

```
note_added       { trackId, noteId, noteSnapshot }
note_removed     { trackId, noteId, noteSnapshot }
note_modified    { trackId, noteId, fieldName, oldValue, newValue }
track_added      { trackId, trackSnapshot }
track_removed    { trackId, trackSnapshot }
track_renamed    { trackId, oldName, newName }
cc_added         { trackId, ccId, ccSnapshot }
pitch_bend_added { trackId, pbId, pbSnapshot }
tempo_changed    { oldBpm, newBpm, absoluteTick }
time_signature_changed { oldNum, oldDenom, newNum, newDenom, absoluteTick }
key_signature_changed  { oldKey, oldMode, newKey, newMode, absoluteTick }
marker_added     { text, absoluteTick }
checkpoint       { name }
```

### Common patterns

Both domains follow the same patterns:

1. **Snapshot events** store a full copy of the created/deleted entity. This allows perfect reversal without querying the model.
2. **Modified events** store before/after state (either as partial snapshots or as field-level diffs).
3. **CheckpointEvent** is a sentinel with no model effect.

## Event Reversal

Domains MUST implement a `reverseEvent(event, model)` function that applies the inverse of an event to the model.

### Reversal rules

| Event pattern | Reversal |
|--------------|----------|
| Entity added | Remove the entity |
| Entity removed | Re-insert from snapshot |
| Property modified | Restore old value |
| Checkpoint | No-op (skip) |

### Example: fcp-midi reversal

```python
def reverse_event(ev, song):
    if isinstance(ev, NoteAdded):
        song.remove_note(ev.track_id, ev.note_id)
    elif isinstance(ev, NoteRemoved):
        # Re-insert from snapshot
        track = song.tracks[ev.track_id]
        track.notes[ev.note_snapshot.id] = ev.note_snapshot
    elif isinstance(ev, NoteModified):
        note = find_note(song, ev.note_id)
        setattr(note, ev.field_name, ev.old_value)
    elif isinstance(ev, TrackAdded):
        song.remove_track(ev.track_id)
    elif isinstance(ev, TrackRemoved):
        song.tracks[ev.track_id] = ev.track_snapshot
    ...
```

### Example: fcp-drawio reversal

```typescript
function reverseEvent(event: DiagramEvent, model: DiagramModel): void {
  switch (event.type) {
    case "shape_created":
      model.removeShapeById(event.shape.id);
      break;
    case "shape_deleted":
      model.restoreShape(event.shape);
      break;
    case "shape_modified":
      model.applyPartial(event.id, event.before);
      break;
    ...
  }
}
```

## Event Replay

Domains MUST implement a `replayEvent(event, model)` function that reapplies a previously undone event during redo.

### Replay rules

| Event pattern | Replay |
|--------------|--------|
| Entity added | Re-insert from snapshot |
| Entity removed | Remove the entity |
| Property modified | Apply new value |
| Checkpoint | No-op (skip) |

Replay is the logical mirror of reversal.

## Batch Atomicity

When the mutation tool processes a batch of operations (multiple ops in a single `{domain}(ops)` call), the server SHOULD create an internal checkpoint before the batch and roll back to it if any operation fails. This ensures that a partially-failed batch does not leave the model in an inconsistent state.

```python
# Pattern from fcp-midi
def execute_ops(self, ops):
    batch_cp = f"__batch_{id(ops)}"
    self.event_log.checkpoint(batch_cp)

    results = []
    for op in ops:
        result = self.execute_single_op(op)
        results.append(result)
        if result.startswith("!"):  # error
            # Roll back entire batch
            self.event_log.undo_to(batch_cp)
            for ev in reversed_events:
                reverse_event(ev, self.model)
            break

    return results
```

## State Digest

After mutations, the server SHOULD compute a state digest -- a compact fingerprint of the model state. This serves two purposes:

1. **Drift detection:** The LLM can compare digests between calls to verify its mental model matches reality.
2. **Debugging:** Unexpected digest changes indicate unintended side effects.

Digest format is domain-specific:

```
# fcp-drawio
digest: 5s 3e 1g                    # shapes, edges, groups

# fcp-midi
hash:abc123 tracks:3 notes:47       # content hash, track/note counts
```
