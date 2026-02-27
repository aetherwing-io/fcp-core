# FCP Session Lifecycle

**Version:** 0.1.0

## Overview

An FCP session encapsulates the lifecycle of a single document: creation, loading, modification, checkpointing, undo/redo, and saving. The session is the unit of state management.

## Session State

Every FCP server maintains the following session state:

```
Session {
  model: DomainModel       // The in-memory document (Song, Diagram, etc.)
  eventLog: EventLog       // Cursor-based event log for undo/redo
  filePath: string | null  // Path to the file on disk (null if unsaved)
}
```

Additional domain-specific state MAY be attached (e.g., a reference registry for O(1) label lookups, an instrument bank for MIDI).

## Required Session Commands

### `new`

Create a new empty document.

```
new "Title" [key:value params...]
```

**Behavior:**
1. Create a fresh domain model with the given title.
2. Reset the event log (empty, cursor at 0).
3. Clear the file path (new document is unsaved).
4. Apply any domain-specific initialization parameters.

**Domain parameters:**

| Domain | Parameters | Example |
|--------|-----------|---------|
| fcp-drawio | `type:architecture` | `new "System Design" type:architecture` |
| fcp-midi | `tempo:N`, `time-sig:N/D`, `key:K`, `ppqn:N` | `new "My Song" tempo:140 time-sig:3/4` |

**Response:** Confirmation with the created document's properties.

```
# fcp-drawio
new diagram "System Design" created

# fcp-midi
+ New song 'My Song' (tempo:140, 3/4, ppqn:480)
```

### `open`

Load an existing document from a file.

```
open PATH
```

**Behavior:**
1. Read the file at PATH.
2. Deserialize into the domain model.
3. Reset the event log (the loaded state becomes the new baseline).
4. Rebuild any derived indices (reference registry, etc.).
5. Set the file path for subsequent saves.

**Response:** Confirmation with loaded document summary.

```
# fcp-drawio
ok: opened "./arch.drawio" (2 pages, 5 shapes, 3 edges, 1 groups)

# fcp-midi
+ Opened './song.mid'
```

### `save`

Save the current document to disk.

```
save
save as:PATH
```

**Behavior:**
1. If `as:PATH` is provided, use that path (and update the stored file path).
2. Otherwise, use the stored file path.
3. If no file path is set, return an error with a suggestion.
4. Serialize the domain model to the file format.
5. Write to disk.

**Response:** Confirmation with the saved path.

```
# fcp-drawio
ok: saved ./arch.drawio (5 shapes, 3 edges, 1 groups)

# fcp-midi
+ Saved to './song.mid'
```

### `checkpoint`

Create a named checkpoint at the current event log position.

```
checkpoint NAME
```

**Behavior:**
1. Record the current event log cursor position under NAME.
2. Append a `CheckpointEvent` sentinel to the event log.
3. The checkpoint can be targeted by `undo to:NAME`.

See [events.md](events.md) for details on checkpoint mechanics.

**Response:** Confirmation.

```
checkpoint "v1" created
```

### `undo`

Undo one or more operations.

```
undo              # undo last operation
undo to:NAME      # undo back to a named checkpoint
```

**Behavior:**
1. Retrieve events to undo from the event log (see [events.md](events.md)).
2. For each event (in reverse order), apply the inverse operation to the domain model.
3. Rebuild any derived indices.

**Response:** Count of undone events.

```
undone 3 event(s) to checkpoint 'v1'
```

### `redo`

Redo previously undone operations.

```
redo
```

**Behavior:**
1. Retrieve events to redo from the event log.
2. For each event (in forward order), reapply the operation to the domain model.
3. Rebuild any derived indices.

**Response:** Count of redone events.

```
redone 1 event(s)
```

## Optional Session Commands

Domains MAY extend the session with additional commands. These follow the same tokenization rules as the required commands.

| Domain | Command | Purpose |
|--------|---------|---------|
| fcp-drawio | `export png path:./out.png` | Export to image format |
| fcp-midi | `load-soundfont PATH` | Load custom instrument bank |

## Domain Hooks

The session lifecycle provides hooks that domains implement to customize behavior:

### `onNew(title, params)`

Called when creating a new document. The domain constructs its model type with the appropriate defaults.

**fcp-drawio:** Creates a `Diagram` with a default page, layer, and empty shape/edge maps.

**fcp-midi:** Creates a `Song` with tempo, time signature, key signature, and PPQN from params.

### `onOpen(path) -> model`

Called when loading a file. The domain deserializes the file format into its model type.

**fcp-drawio:** Parses draw.io XML into a `Diagram` with pages, shapes, edges, and groups.

**fcp-midi:** Parses MIDI binary into a `Song` with tracks, notes, and tempo map.

### `onSave(model, path)`

Called when saving. The domain serializes its model to the file format.

**fcp-drawio:** Generates draw.io XML from the `Diagram` model.

**fcp-midi:** Generates MIDI binary from the `Song` model.

### `onRebuildIndices(model)`

Called after undo, redo, or open. The domain rebuilds any derived lookup structures.

**fcp-drawio:** Rebuilds the `ReferenceRegistry` (label-to-ID mapping for O(1) ref resolution).

**fcp-midi:** Rebuilds the `Registry` (track-name-to-ID mapping, note lookups).

### `reverseEvent(event, model)`

Called during undo to apply the inverse of an event to the model. See [events.md](events.md) for details.

### `replayEvent(event, model)`

Called during redo to reapply an event to the model. See [events.md](events.md) for details.

## Session Tokenization

Session action strings use the same quote-aware tokenizer as the verb DSL. The first token is the command, and remaining tokens are command arguments.

```
Input:  'new "My Song" tempo:120 time-sig:3/4'
Tokens: ["new", "My Song", "tempo:120", "time-sig:3/4"]
        ^^^^^^  ^^^^^^^^^  ^^^^^^^^^^^^^  ^^^^^^^^^^^^^^^
        command  positional  key:value      key:value
```

This reuse of the tokenizer is intentional -- it keeps the parsing infrastructure unified.
