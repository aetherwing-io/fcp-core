# File Context Protocol (FCP) Specification

**Version:** 0.1.0

## What is FCP?

FCP (File Context Protocol) is an application framework for building MCP (Model Context Protocol) servers that let LLMs interact with complex file formats through a verb-based DSL. Instead of asking an LLM to generate raw MIDI bytes or draw.io XML, FCP servers expose a small set of tools that accept human-readable operation strings and translate them into correct file manipulations.

FCP is to MCP what React is to the DOM -- the LLM thinks in domain operations, and FCP renders them into the target format (.mid, .drawio, .tf). It provides structure, conventions, and reusable patterns on top of a lower-level protocol.

## The Problem

LLMs are bad at producing complex binary and XML formats directly:

- **MIDI** is a binary protocol with delta-time encoding, running status, and channel/track interleaving. A single off-by-one in tick calculation corrupts the entire file.
- **draw.io** is nested XML with `mxGraphModel > root > mxCell[]` structures, absolute coordinate geometry, and style strings packed into semicolon-delimited attributes. One malformed style breaks rendering.
- **Other formats** (SVG, LaTeX TikZ, OpenAPI, Terraform HCL, etc.) share the same pattern: syntactically demanding, structurally fragile, and opaque to token-level prediction.

Asking an LLM to "write a MIDI file" or "generate a draw.io diagram" produces broken output. The LLM does not have reliable access to the format's invariants.

## The Solution

FCP servers absorb format complexity behind a verb-based DSL. The LLM operates in a domain it handles well -- structured natural language with key:value parameters -- and the server handles encoding, validation, geometry, and serialization.

The same architectural pattern applies regardless of domain:

```
# MIDI domain                          # Diagram domain
note Piano C4 at:1.1 dur:quarter       add svc AuthService theme:blue
chord Piano Cmaj at:2.1 dur:half       connect AuthService -> UserDB label:queries
tempo 140 at:5.1                        style @type:db fill:#ff0000
```

Both follow the same grammar: `VERB [positionals...] [key:value params...] [@selectors...]`

Both use the same 4-tool architecture. Both maintain an in-memory model with undo/redo. The domain changes; the structure does not.

## The 4-Tool Architecture

Every FCP server exposes exactly four MCP tools:

| Tool | Signature | Purpose |
|------|-----------|---------|
| `{domain}` | `(ops: string[])` | Batch mutation operations |
| `{domain}_query` | `(q: string)` | Read-only state inspection |
| `{domain}_session` | `(action: string)` | Lifecycle management (new, open, save, undo, redo) |
| `{domain}_help` | `()` | Self-documenting reference card |

Where `{domain}` is a short identifier like `midi` or `studio`.

**Why exactly four?** MCP tool descriptions are loaded into the LLM's context on connect. Each tool consumes context tokens. Four tools provide a clean separation of concerns (mutate / query / lifecycle / help) without fragmenting the interface into dozens of endpoints that bloat the context window. The mutation tool handles all write operations through a single `ops: string[]` parameter; the grammar handles dispatch internally.

## Relationship to MCP

MCP defines the transport protocol: how a client (LLM host) discovers tools, calls them, and receives results. FCP does not replace or modify MCP. Instead, FCP defines:

1. **How many tools** a server should expose (4)
2. **What each tool does** (mutate, query, session, help)
3. **How operations are parsed** (the verb DSL grammar)
4. **How state is managed** (session lifecycle, event log, undo/redo)
5. **How results are formatted** (response prefix conventions)

An FCP server is a valid MCP server. Any MCP client can connect to it without knowing about FCP. The FCP conventions ensure that LLMs can use the server effectively because the tool descriptions embed a complete reference card.

## Quick Example: Same Pattern, Different Domains

### Creating entities

```
# drawio-studio: add a service node
add svc AuthService theme:blue near:Gateway dir:right

# fcp-midi: add a note
note Piano C4 at:1.1 dur:quarter vel:mf
```

### Querying state

```
# drawio-studio
studio_query("map")           # spatial overview
studio_query("describe Auth") # shape details

# fcp-midi
midi_query("map")             # song overview
midi_query("describe Piano")  # track details
```

### Session lifecycle

```
# drawio-studio
studio_session('new "Architecture" type:architecture')
studio_session('save as:./arch.drawio')
studio_session('checkpoint v1')
studio_session('undo to:v1')

# fcp-midi
midi_session('new "My Song" tempo:120')
midi_session('save as:./song.mid')
midi_session('checkpoint v1')
midi_session('undo to:v1')
```

### Self-documentation

```
# Both return a reference card with full syntax
studio_help()
midi_help()
```

## Specification Documents

| Document | Contents |
|----------|----------|
| [grammar.md](grammar.md) | Verb DSL grammar: tokenization, token classification, ParsedOp output |
| [tools.md](tools.md) | The 4-tool contract: signatures, descriptions, response format |
| [session.md](session.md) | Session lifecycle: new, open, save, checkpoint, undo, redo |
| [events.md](events.md) | Event log: cursor-based undo model, checkpoints, reversal |
| [conformance.md](conformance.md) | MUST/SHOULD/MAY requirements for valid FCP servers |

## Proven Implementations

| Server | Domain | Language | Repository |
|--------|--------|----------|------------|
| drawio-studio | Diagrams (draw.io XML) | TypeScript | drawio-studio-mcp |
| fcp-midi | Music (MIDI binary) | Python | fcp-midi |
