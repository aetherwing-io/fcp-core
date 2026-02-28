# FCP Domain Implementation Guide

**Version:** 0.1.0

## Overview

FCP is a translation layer, not a model framework. The core pipeline is:

```
MCP → op strings → fcp-core (parse, route, undo/redo) → verb handlers → native library → asset
```

The central architectural decision for any FCP server is: **choose the best native library for the target format, and use its types as your `Model`**. FCP provides the verb DSL and session lifecycle; the library provides format correctness.

The `FcpDomainAdapter<Model, Event>` interface is intentionally generic in its `Model` type parameter. It can be `hclwrite.File`, `mido.MidiFile`, a custom `DiagramModel`, or anything else. The right choice depends on what libraries exist for the target format.

## Implementation Tiers

| Tier | When | Pattern | Example |
|------|------|---------|---------|
| **1 — Library IS the model** | Mature library exists, its model matches the domain | verb handlers → library.API() → library.serialize() + thin index | Terraform + `hclwrite` (Go) |
| **2 — Library + thin layer** | Library exists but has gaps | verb handlers → thin conversion → library.API() + thin index + enrichment | MIDI + `mido` (Python) |
| **3 — No library exists** | Format has no programmatic SDK | verb handlers → minimal custom model → custom serializer | draw.io (TypeScript) |

### How to choose

1. Search for native libraries in the format's ecosystem language.
2. If a library provides a complete model AND a correct serializer, use Tier 1.
3. If a library handles file I/O but lacks higher-level concepts your DSL needs, use Tier 2 with a thin adaptation layer.
4. If no library exists, use Tier 3 — build the minimum custom model required.

## Naming Convention

FCP servers are named `fcp-{format}`. One server per format. The implementation language follows the best native library.

- `fcp-terraform` — Go (because `hclwrite` is Go)
- `fcp-midi` — Python (because `mido` is Python)
- `fcp-drawio` — TypeScript (no SDK; TypeScript for MCP ecosystem compatibility)

No language suffixes. When `fcp-terraform` is rewritten from TypeScript to Go, it is a new version of `fcp-terraform`, not a new project.

## The Thin Index Pattern

Regardless of tier, every FCP server needs O(1) label lookups. The thin index maps user-facing labels to library objects without duplicating them.

### Structure

A thin index contains:

1. **Label → library object pointer.** The index POINTS INTO the library's data structures; it does not copy or mirror them.
2. **Selector metadata.** Enough information to resolve `@type:`, `@track:`, and similar selectors without scanning.
3. **Connection graph.** Edge data for relationship queries.

### Example: BlockRef (Terraform, Tier 1)

```go
// BlockRef points into hclwrite.File — it does not duplicate block data
type BlockRef struct {
    Label    string           // user-facing label (e.g., "web_server")
    Type     string           // resource type (e.g., "aws_instance")
    Category string           // "resource", "data", "variable", "output", "module"
    Block    *hclwrite.Block  // pointer into hclwrite.File
    Tags     map[string]string
}

// Index maps labels to refs
type Index struct {
    Refs        map[string]*BlockRef          // label → ref
    ByType      map[string][]*BlockRef        // type → refs (for @type: selector)
    ByCategory  map[string][]*BlockRef        // category → refs (for @kind: selector)
    Connections map[string]map[string]string   // src → dst → label
}
```

### Example: NoteRef (MIDI, Tier 2)

```python
@dataclass
class NoteRef:
    label: str                  # auto-generated or user-assigned
    track_label: str            # which track this note belongs to
    note_on: mido.Message       # pointer into mido track message list
    note_off: mido.Message      # paired note-off message
    abs_tick: int               # absolute tick (converted from delta)
    pitch: int                  # MIDI note number (for @pitch: selector)
    velocity: int               # velocity (for @velocity: selector)
```

The key insight: `note_on` and `note_off` are pointers into the mido track's message list. The NoteRef enriches them with absolute timing and label information, but the messages themselves live in `mido.MidiFile`.

## Undo/Redo Strategy

### Tier 1 and Tier 2: Byte Snapshots

When the library IS the model, undo/redo works by snapshotting the library's serialized state:

```go
// Terraform: snapshot is just file.Bytes()
type TerraformEvent struct {
    OpSummary string
    Before    []byte  // hclFile.Bytes() before the operation
    After     []byte  // hclFile.Bytes() after the operation
}

func (a *Adapter) ReverseEvent(event TerraformEvent, file *hclwrite.File) {
    // Replace file contents with the before-snapshot
    *file = *hclwrite.ParseConfig(event.Before, "", hcl.Pos{})
}
```

```python
# MIDI: snapshot is MidiFile saved to bytes buffer
class MidiEvent:
    op_summary: str
    before: bytes  # midi_file.save() to BytesIO
    after: bytes

def reverse_event(self, event: MidiEvent, model: MidiModel) -> None:
    buf = BytesIO(event.before)
    model.midi_file = mido.MidiFile(file=buf)
    model.rebuild_index()
```

This approach is simple, correct, and handles all edge cases — the library's own serializer guarantees round-trip fidelity.

### Tier 3: Event Sourcing

When the model is custom, undo/redo uses event sourcing with before/after snapshots per entity:

```typescript
// draw.io: events capture entity-level changes
type DiagramEvent =
  | { type: "add"; entity: Shape }
  | { type: "remove"; entity: Shape }
  | { type: "modify"; id: string; before: Partial<Shape>; after: Partial<Shape> }
  | { type: "connect"; edge: Edge }
  | { type: "disconnect"; edge: Edge };
```

This is the correct pattern when there is no library serializer to snapshot.

## Anti-Pattern: The Parallel Model

**Do not build a model that mirrors the library, then write adapter code to translate between them.**

The `fcp-terraform` TypeScript implementation is the canonical example of this anti-pattern:

```
                    WRONG (Parallel Model)
┌─────────────────────────────────────────────────┐
│  Op strings                                      │
│      ↓                                           │
│  TerraformConfig (custom model)                  │
│    ├── Map<string, TfBlock>                      │
│    ├── Map<string, TfVariable>                   │
│    └── Map<string, TfOutput>                     │
│      ↓                                           │
│  Custom HCL serializer (renderBlock, renderValue)│
│      ↓                                           │
│  .tf file                                        │
└─────────────────────────────────────────────────┘
```

The custom serializer had bugs: list values rendered unquoted, nested blocks serialized incorrectly, HCL expressions not handled. Every format edge case required new serializer code — code that `hclwrite` already handles correctly.

```
                    RIGHT (Library IS the Model)
┌─────────────────────────────────────────────────┐
│  Op strings                                      │
│      ↓                                           │
│  hclwrite.File (library model)                   │
│      ↓                                           │
│  file.Bytes() (library serializer)               │
│      ↓                                           │
│  .tf file                                        │
└─────────────────────────────────────────────────┘
```

With `hclwrite.File` as the model, `serialize()` is literally `file.Bytes()`. No custom serializer. No serializer bugs. The library's battle-tested implementation handles quoting, expressions, nested blocks, and every other HCL edge case.

### How to detect the anti-pattern

- You have a custom model class AND the library has its own model class, and they represent the same things.
- You are writing serialization code for a format that the library already serializes.
- Bug reports involve your serializer producing incorrect output for edge cases the library handles correctly.
- You have adapter/conversion functions that translate between your model and the library's model.

## Case Studies

### Terraform — Tier 1: Library IS the Model

**Library:** `hclwrite` (Go, part of the official HashiCorp HCL toolkit)

**Why Tier 1:** `hclwrite.File` is a complete, mutable AST for HCL. It handles all serialization edge cases: attribute quoting, expression syntax, nested blocks, comments. The model matches the domain 1:1.

**Architecture:**

| Component | Implementation |
|-----------|---------------|
| Model type (`M`) | `*hclwrite.File` |
| Verb handlers | Call `hclwrite` API: `Body().AppendNewBlock()`, `Body().SetAttributeValue()` |
| Serializer | `file.Bytes()` |
| Thin index | `map[string]*BlockRef` — label → block pointer |
| Undo/redo | Byte snapshots via `file.Bytes()` / `hclwrite.ParseConfig()` |
| Language | Go |

**What FCP adds:** Verb DSL (`add resource`, `connect`, `set`, `remove`), label-based addressing, session lifecycle, 4-tool MCP interface.

### MIDI — Tier 2: Library + Thin Layer

**Library:** `mido` (Python)

**Why Tier 2:** `mido` handles MIDI file I/O and message-level operations, but it lacks several concepts the FCP verb DSL needs:

- **Absolute ↔ delta tick conversion.** MIDI stores delta times; the DSL uses absolute positions like `at:1.1` (measure.beat).
- **Note pairing.** MIDI has separate NoteOn/NoteOff messages; the DSL has a unified `note` concept with duration.
- **Track metadata.** Labels, instrument names, channel assignments.
- **Note index.** O(1) lookup for selectors like `@pitch:C4`, `@velocity:80-127`.
- **Chord expansion.** The DSL supports `chord Piano Cmaj7` which expands to multiple notes.

**Architecture:**

| Component | Implementation |
|-----------|---------------|
| Model type (`M`) | `MidiModel` (thin wrapper around `mido.MidiFile`) |
| Source of truth | `mido.MidiFile` — all note data lives in mido's message lists |
| Thin layer | ~700 LOC: tick conversion, note pairing, track metadata, index, chord expansion |
| Serializer | `mido.MidiFile.save()` |
| Thin index | `NoteRef` objects pointing into mido message lists |
| Undo/redo | Byte snapshots via `mido.MidiFile.save()` to buffer |
| Language | Python |

**Contrast:** A parallel model approach would build a `Song` with `Track` and `Note` classes that duplicate mido's data, then convert back to mido for serialization. That approach produced ~1,767 LOC of model code. The thin layer approach achieves the same functionality in ~700 LOC by enriching mido's objects rather than replacing them.

### draw.io — Tier 3: No Library Exists

**Library:** None (no TypeScript SDK for draw.io/mxGraph)

**Why Tier 3:** There is no programmatic library for creating/editing draw.io files. The format is XML with `mxGraphModel > root > mxCell[]` structures, absolute coordinate geometry, and semicolon-delimited style strings.

**Architecture:**

| Component | Implementation |
|-----------|---------------|
| Model type (`M`) | `DiagramModel` (custom semantic model) |
| Verb handlers | Manipulate `DiagramModel` entity graph |
| Serializer | Custom XML serializer (mxGraphModel generation) |
| Layout | ELK graph layout engine |
| Undo/redo | Event sourcing on `DiagramModel` |
| Language | TypeScript |

**This IS the correct pattern for Tier 3.** When no library exists, you must build the model and serializer. The anti-pattern only applies when a library exists and you build a parallel model instead of using it.

## What FCP Adds

Regardless of tier, FCP provides the same infrastructure:

| Capability | Description |
|------------|-------------|
| Verb DSL | `VERB [positionals...] [key:value params...] [@selectors...]` grammar, parsed by fcp-core |
| Session lifecycle | `new`, `open`, `save`, `checkpoint`, `undo`, `redo` — managed by fcp-core |
| Thin index | O(1) label lookups for verb dispatch and selector resolution |
| LLM reasoning layer | Domain operations the LLM can reason about, instead of raw format bytes |
| 4-tool MCP interface | `{domain}`, `{domain}_query`, `{domain}_session`, `{domain}_help` |
| Event log | Cursor-based undo/redo with named checkpoints |
| Reference card | Self-documenting help tool generated from verb registry |
| Batch operations | Multiple ops per call with atomic rollback |

The domain chooses the library. FCP provides everything else.
