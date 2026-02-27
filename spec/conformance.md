# FCP Conformance Requirements

**Version:** 0.1.0

## Overview

This document defines what makes a valid FCP server. Requirements are classified as MUST (mandatory), SHOULD (strongly recommended), and MAY (optional extension).

## MUST Requirements

A conforming FCP server MUST implement all of the following.

### M1. Four MCP Tools

The server MUST expose exactly four MCP tools following the naming convention:

| Tool | Signature |
|------|-----------|
| `{domain}` | `(ops: string[])` returning text |
| `{domain}_query` | `(q: string)` returning text |
| `{domain}_session` | `(action: string)` returning text |
| `{domain}_help` | `()` returning text |

Where `{domain}` is a consistent short identifier (e.g., `midi`, `studio`, `slides`).

### M2. ParsedOp Grammar

Operation strings passed to the mutation tool MUST be parsed using the grammar defined in [grammar.md](grammar.md):

- Quote-aware tokenization (whitespace splitting, quoted string handling).
- Token classification into verb, key:value params, @selectors, arrows, and positionals.
- Output as a `ParsedOp` structure (or equivalent) with `verb`, `positionals`, `params`, `selectors`, and `raw` fields.
- Parse failures MUST return a `ParseError` (or equivalent) with an `error` message and the `raw` input.

### M3. Session Lifecycle

The session tool MUST support these commands:

| Command | Behavior |
|---------|----------|
| `new "Title" [params...]` | Create a fresh document |
| `open PATH` | Load from file |
| `save` | Save to current path |
| `save as:PATH` | Save to a new path |
| `checkpoint NAME` | Create a named checkpoint |
| `undo` | Undo the last operation |
| `undo to:NAME` | Undo to a named checkpoint |
| `redo` | Redo the last undone operation |

See [session.md](session.md) for full semantics.

### M4. Event Log with Cursor-Based Undo

The server MUST maintain an event log as defined in [events.md](events.md):

- Cursor-based model (not stack-based).
- `append()` truncates the redo tail.
- Named checkpoints with `checkpoint(name)`.
- `undo(count)` and `undoTo(name)` return events in reverse order.
- `redo(count)` returns events in forward order.
- `CheckpointEvent` sentinels are skipped during undo/redo counting.

### M5. Event Reversal and Replay

The server MUST implement:

- `reverseEvent(event, model)` -- apply the inverse of an event to the model.
- `replayEvent(event, model)` -- reapply a previously undone event.

Events MUST carry sufficient data (snapshots, before/after values) for both operations.

### M6. Read-Only Queries

The query tool MUST NOT modify state. It MUST support at minimum:

| Query | Description |
|-------|-------------|
| `map` | Overview of the current model |
| `stats` | Quantitative summary |
| `status` | Session status |

### M7. Domain-Specific Verbs

The mutation tool MUST dispatch parsed ops to domain-specific verb handlers. Unrecognized verbs MUST return an error (not silently ignored).

## SHOULD Requirements

A conforming FCP server SHOULD implement the following for optimal LLM interaction.

### S1. Reference Card in Tool Description

The `{domain}` mutation tool SHOULD embed a reference card in its MCP tool description. This reference card SHOULD include:

- All verb syntax with parameter lists.
- Domain vocabulary (entity types, value syntax).
- Selector reference.
- Response prefix legend.
- Key conventions.

This is critical for LLM usability: the description is loaded into context on connect and serves as the primary syntax reference.

### S2. Response Prefixes

Mutation results SHOULD use the prefix convention:

| Prefix | Meaning |
|--------|---------|
| `+` | Created |
| `~` | Connection/edge modified |
| `*` | Property modified |
| `-` | Deleted |
| `!` | Error or meta operation |
| `@` | Bulk/layout operation |

### S3. State Digest

The mutation tool SHOULD append a state digest as the final line of every response. The digest format is domain-specific but SHOULD be compact (one line) and machine-comparable.

### S4. Error Suggestions

Error responses SHOULD include a `try:` suggestion line when the server can infer what the user likely intended:

```
! Track "Drums" not found
  try: track add Drums instrument:standard-kit ch:10
```

### S5. Batch Atomicity

When processing multiple ops in a single call, the server SHOULD roll back the entire batch if any operation fails, using an internal checkpoint.

### S6. Index Rebuild After Undo/Redo

After undo or redo operations, the server SHOULD rebuild any derived indices (reference registries, lookup caches) to maintain consistency.

### S7. `describe` and `history` Queries

The query tool SHOULD support:

| Query | Description |
|-------|-------------|
| `describe REF` | Detailed information about a specific entity |
| `history N` | Last N events from the event log |

## MAY Requirements

A conforming FCP server MAY implement the following optional extensions.

### O1. Custom Session Commands

Domains MAY extend the session tool with additional commands (e.g., `export`, `load-soundfont`). Custom commands MUST follow the same tokenization rules as required commands.

### O2. Domain-Specific Selectors

Domains MAY define additional selector types beyond the common set. Common selectors include:

| Selector | Description |
|----------|-------------|
| `@all` | All entities |
| `@recent` | Last created/modified entity |
| `@recent:N` | Last N entities |

Domain-specific examples:

| Domain | Selector | Description |
|--------|----------|-------------|
| fcp-drawio | `@type:db` | Shapes of type "db" |
| fcp-drawio | `@group:Backend` | Shapes in group "Backend" |
| fcp-drawio | `@connected:Auth` | Shapes connected to "Auth" |
| fcp-midi | `@track:Piano` | Notes on track "Piano" |
| fcp-midi | `@range:1.1-4.4` | Notes in position range |
| fcp-midi | `@pitch:C4` | Notes matching pitch |
| fcp-midi | `@velocity:80-127` | Notes in velocity range |
| fcp-midi | `@not:pitch:C4` | Negated selector |

### O3. Arrow Operators

Domains MAY use arrow operators (`->`, `<->`, `--`) for connection syntax. Arrow recognition is built into the tokenizer but is not required for all domains.

### O4. Custom Entity Types

Domains MAY support user-defined entity types via a `define` verb or equivalent mechanism. The help tool SHOULD reflect custom types when they exist.

### O5. Domain-Specific Query Commands

Domains MAY add query commands beyond the required set (e.g., `piano-roll`, `connections`, `find`).

### O6. Verb Registry

Domains MAY maintain a structured verb registry that serves as a single source of truth for verb syntax, categories, and parameters. The reference card generator can read from this registry to stay in sync.

## Conformance Validation

### Test Fixture Format

Conformance can be validated using JSON test fixtures:

```json
{
  "suite": "grammar",
  "tests": [
    {
      "name": "basic verb with params",
      "input": "note Piano C4 at:1.1 dur:quarter",
      "expected": {
        "verb": "note",
        "positionals": ["Piano", "C4"],
        "params": { "at": "1.1", "dur": "quarter" },
        "selectors": []
      }
    },
    {
      "name": "selector with negation",
      "input": "remove @track:Piano @not:pitch:C4",
      "expected": {
        "verb": "remove",
        "positionals": [],
        "params": {},
        "selectors": [
          { "type": "track", "value": "Piano", "negated": false },
          { "type": "pitch", "value": "C4", "negated": true }
        ]
      }
    }
  ]
}
```

### Fixture Suites

| Suite | Tests | Coverage |
|-------|-------|----------|
| `grammar/tokenizer` | Whitespace splitting, quote handling, escapes | M2 |
| `grammar/classifier` | Key:value, selector, arrow, positional detection | M2 |
| `grammar/parsed-op` | Full op parsing to ParsedOp | M2 |
| `session/lifecycle` | new, open, save, checkpoint, undo, redo | M3 |
| `events/cursor` | Append, truncate, cursor movement | M4 |
| `events/checkpoint` | Named checkpoints, undoTo | M4 |

### Running Conformance Tests

A conformance test runner takes a JSON fixture file and a server adapter, then verifies that the server produces the expected output for each test case. The adapter translates between the fixture format and the server's internal API.

Both TypeScript and Python implementations of fcp-core SHOULD ship with a conformance test runner and the complete fixture suite.
