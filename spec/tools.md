# FCP Tool Contract

**Version:** 0.1.0

## The 4-Tool Architecture

Every FCP server exposes exactly four MCP tools. The tool names follow the pattern `{domain}`, `{domain}_query`, `{domain}_session`, and `{domain}_help`, where `{domain}` is a short identifier (e.g., `drawio`, `midi`).

## Tool 1: `{domain}(ops: string[])`

**Purpose:** Batch mutation operations.

**Parameter:** `ops` -- an array of operation strings. Each string follows the verb DSL grammar defined in [grammar.md](grammar.md).

**Behavior:**
1. Parse each op string into a `ParsedOp` using the grammar.
2. Dispatch each parsed op to the appropriate domain verb handler.
3. Record events in the event log for undo/redo.
4. Return formatted results for each op.

**Batching:** Operations are executed sequentially within a single call. This allows the LLM to send multiple related operations in one round-trip (e.g., creating 8 notes in a measure). If any operation in a batch fails, the server SHOULD roll back all preceding operations in that batch to maintain atomicity.

**Response format:** One line per operation result, using response prefix conventions (see below). The final line SHOULD be a state digest for drift detection.

### Example: fcp-drawio

```
drawio([
  "add svc AuthService theme:blue",
  "add db UserDB theme:green near:AuthService dir:right",
  "connect AuthService -> UserDB label:queries"
])

Response:
+svc AuthService @(200,200 140x60) blue
+db UserDB @(400,200 120x80) green
~AuthService->UserDB "queries" solid
digest: 3s 1e 0g
```

### Example: fcp-midi

```
midi([
  "note Piano C4 at:1.1 dur:quarter vel:mf",
  "note Piano E4 at:1.2 dur:quarter vel:mf",
  "note Piano G4 at:1.3 dur:quarter vel:mf"
])

Response:
+ Note C4 on Piano at 1.1 dur:480 vel:80
+ Note E4 on Piano at 1.2 dur:480 vel:80
+ Note G4 on Piano at 1.3 dur:480 vel:80
hash:abc123 tracks:1 notes:3
```

## Tool 2: `{domain}_query(q: string)`

**Purpose:** Read-only state inspection.

**Parameter:** `q` -- a query string. The query is NOT parsed using the verb DSL grammar; it uses a simpler dispatch on the first word.

**Behavior:** Read the current in-memory model and return formatted text. MUST NOT modify state.

**Required queries:**

| Query | Description |
|-------|-------------|
| `map` | Overview of the current model state |
| `stats` | Quantitative summary |
| `status` | Session status (file path, checkpoint count, etc.) |
| `describe REF` | Detailed information about a specific entity |
| `history N` | Last N events from the event log |

**Optional queries** (domain-specific):

| Domain | Query | Description |
|--------|-------|-------------|
| fcp-drawio | `list` | List all shapes |
| fcp-drawio | `list @type:db` | List shapes matching selector |
| fcp-drawio | `connections REF` | Show incoming/outgoing edges |
| fcp-drawio | `find TEXT` | Search shapes by label |
| fcp-drawio | `diff checkpoint:NAME` | Show changes since checkpoint |
| fcp-midi | `tracks` | List all tracks |
| fcp-midi | `events TRACK [M.B-M.B]` | Show events on a track |
| fcp-midi | `piano-roll TRACK M.B-M.B` | ASCII visualization |
| fcp-midi | `find PITCH` | Search notes by pitch |
| fcp-midi | `instruments [FILTER]` | List available instruments |

### Example

```
drawio_query("map")
Response:
map: 800x600 flow:TB | 3s 1e 0g
  AuthService(svc) @(200,200)
  UserDB(db) @(400,200)
  Gateway(api) @(300,50)

midi_query("map")
Response:
Song: My Song
  tempo:120 | 4/4 | C major | ppqn:480
  Tracks (2):
    1. Piano ch:1 acoustic-grand-piano (12 notes)
    2. Bass ch:2 acoustic-bass (8 notes)
```

## Tool 3: `{domain}_session(action: string)`

**Purpose:** Session lifecycle management.

**Parameter:** `action` -- a session action string, tokenized using the same quote-aware tokenizer as the verb DSL.

**Required actions:** See [session.md](session.md) for the full session lifecycle contract.

| Action | Description |
|--------|-------------|
| `new "Title" [params...]` | Create a new empty model |
| `open ./path` | Load a model from file |
| `save` | Save to the current file path |
| `save as:./path` | Save to a new file path |
| `checkpoint NAME` | Create a named checkpoint |
| `undo` | Undo the last operation |
| `undo to:NAME` | Undo to a named checkpoint |
| `redo` | Redo the last undone operation |

**Domain extensions:** Domains MAY add custom session actions. For example, fcp-midi adds `load-soundfont PATH` to load custom instrument banks.

## Tool 4: `{domain}_help()`

**Purpose:** Self-documenting reference card.

**Parameters:** None.

**Behavior:** Return the complete reference card for the domain. This is the same content embedded in the `{domain}` tool description, optionally extended with any custom types or extensions defined during the current session.

**Why this exists:** LLM context windows get truncated during long conversations. When the LLM loses the tool description from its context, it can call `{domain}_help()` to recover the full reference card without starting a new session.

### Example

```
midi_help()
Response:
# MIDI FCP Reference Card

## Mutation Operations (via `midi` tool)

### Notes, Chords & Tracks
  note TRACK PITCH at:POS dur:DUR [vel:V] [ch:N]
  chord TRACK SYMBOL at:POS dur:DUR [vel:V] [ch:N]
  ...
```

## Response Format Conventions

### Prefix Characters

FCP servers use single-character prefixes on response lines to indicate the type of operation performed. This gives the LLM structured feedback without requiring JSON parsing.

| Prefix | Meaning | Used for |
|--------|---------|----------|
| `+` | Created | New entity added |
| `~` | Modified (connection/edge) | Edge/connection created or changed |
| `*` | Modified (property) | Property or style change |
| `-` | Deleted | Entity removed |
| `!` | Error / meta | Parse errors, group operations, meta changes |
| `@` | Bulk/layout | Layout changes, bulk position updates |

### Error Responses

Errors include a `!` prefix and optionally a suggestion line:

```
! Unknown verb "noot"
  try: note TRACK PITCH at:POS dur:DUR

! Track "Drums" not found
  try: track add Drums instrument:standard-kit ch:10
```

### State Digest

The mutation tool SHOULD append a state digest as the final line of every response. The digest is a compact summary that lets the LLM detect drift between its mental model and the actual state.

```
# fcp-drawio
digest: 5s 3e 1g

# fcp-midi
hash:abc123 tracks:3 notes:47
```

## Tool Description Requirements

### Embedding the Reference Card

The `{domain}` tool's MCP description MUST embed a complete (or near-complete) reference card. This is critical because:

1. The LLM sees tool descriptions on connect, before any interaction.
2. The description is the LLM's primary source of syntax knowledge.
3. Without it, the LLM must call `{domain}_help()` before every operation.

The description should include:
- All verb syntax with examples
- Entity/type vocabulary (node types, pitch syntax, etc.)
- Key:value parameter reference
- Selector syntax
- Response prefix legend
- Key conventions

### Example: Compact reference in description

```
Execute MIDI operations. Each op string follows: VERB TARGET [key:value ...]

NOTES, CHORDS & TRACKS:
  note TRACK PITCH at:POS dur:DUR [vel:V] [ch:N]
  chord TRACK SYMBOL at:POS dur:DUR [vel:V] [ch:N]
  track add|remove NAME [instrument:INST] [program:N] [ch:N]

SELECTORS:
  @track:NAME  @channel:N  @range:M.B-M.B  @pitch:PITCH
  ...

RESPONSE PREFIXES:
  +  note/chord added     ~  event modified
  *  track modified       -  event removed
  !  meta event           @  bulk operation
```

## Why Exactly Four Tools?

The 4-tool constraint is intentional and proven across domains:

1. **Context efficiency.** Each MCP tool adds its full description to the LLM's context. Four tools keep the token budget manageable while providing complete functionality.

2. **Clean separation.** Mutations, queries, lifecycle, and help serve fundamentally different purposes. Combining them into fewer tools would overload parameter interpretation. Splitting into more would fragment the interface.

3. **Discoverability.** An LLM connecting to a 4-tool server immediately understands the interaction model: "I mutate with `{domain}`, inspect with `{domain}_query`, manage lifecycle with `{domain}_session`, and recover syntax with `{domain}_help`."

4. **Batch efficiency.** The mutation tool accepts `ops: string[]`, so N operations require 1 tool call. If each verb were a separate tool (e.g., `midi_note`, `midi_chord`, `midi_tempo`), N operations would require N tool calls -- dramatically slower and more error-prone.
