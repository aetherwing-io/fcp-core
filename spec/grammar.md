# FCP Grammar Specification

**Version:** 0.1.0

## Overview

Every FCP operation is a single string that follows a common grammar. The fcp-core layer handles tokenization and structural classification (separating verbs, positionals, key:value params, and @selectors). Domains assign semantic meaning to the positional arguments.

This separation is the critical design boundary: **fcp-core classifies tokens to structure; domains assign meaning to positionals.**

## Tokenization

### Input

A single operation string, e.g.:

```
note Piano C4 at:1.1 dur:quarter vel:mf
add svc "Auth Service" theme:blue near:Gateway dir:right
```

### Rules

1. **Split on whitespace** (space, tab, newline).
2. **Quoted strings** are treated as a single token. Both double quotes (`"..."`) and single quotes (`'...'`) are supported.
3. **Escape sequences** within quotes: `\"` produces a literal `"`, `\\` produces `\`, `\n` produces a newline.
4. **Embedded quotes** in key:value tokens are supported: `label:"Auth Service"` produces the token `label:Auth Service`.
5. **Empty input** produces an empty token list.

### Output

An ordered list of string tokens with quotes stripped.

```
Input:  'note Piano "My Track" at:1.1'
Output: ["note", "Piano", "My Track", "at:1.1"]

Input:  'add svc AuthService theme:blue'
Output: ["add", "svc", "AuthService", "theme:blue"]

Input:  'label Gateway "API Gateway v2"'
Output: ["label", "Gateway", "API Gateway v2"]
```

## Token Classification

After tokenization, each token is classified into one of four types:

### 1. Verb

The **first token** (lowercased) is always the verb. It determines what operation to perform.

```
note Piano C4 at:1.1
^^^^
verb
```

Verbs are domain-specific. fcp-core does not maintain a verb whitelist; it simply extracts the first token as the verb.

### 2. Key:Value Parameter

A token containing `:` where:
- It does NOT start with `@` (that's a selector)
- The `:` is not in position 0 (bare `:` is not a key:value)
- It is not an arrow operator (`->`, `<->`, `--`)

The key is everything before the first `:`. The value is everything after.

```
at:1.1          key="at"      value="1.1"
dur:quarter     key="dur"     value="quarter"
theme:blue      key="theme"   value="blue"
style:solid     key="style"   value="solid"
as:./file.mid   key="as"      value="./file.mid"
```

Values may contain colons: `time-sig:3/4` is a valid key:value where key="time-sig", value="3/4".

### 3. Selector

A token starting with `@`. Selectors filter or target entities.

```
@track:Piano      type="track"     value="Piano"
@type:db          type="type"      value="db"
@range:1.1-4.4    type="range"     value="1.1-4.4"
@all              type="all"       value=""
@recent:5         type="recent"    value="5"
@not:pitch:C4     negated=true     type="pitch"  value="C4"
```

Structure: `@[not:]TYPE[:VALUE]`

- If the selector starts with `@not:`, it is negated, and the remaining string is parsed as `TYPE:VALUE`.
- If the token contains `:` after `@`, split on the first `:` to get type and value.
- If no `:` after `@`, the entire string after `@` is the type with an empty value.

### 4. Positional

Any token that is not a verb (first position), key:value, or selector. Positionals are domain-specific and their meaning depends on the verb.

```
note Piano C4 at:1.1 dur:quarter
     ^^^^^ ^^
     positional[0]  positional[1]

add svc AuthService theme:blue
    ^^^ ^^^^^^^^^^^
    positional[0]  positional[1]
```

### 5. Arrow (domain extension)

Arrow operators (`->`, `<->`, `--`) are used in diagram domains for connection syntax. They are classified as a distinct token type when present.

```
connect AuthService -> UserDB label:queries
                    ^^
                    arrow
```

Whether a domain uses arrows is domain-specific. fcp-core recognizes them as a category but does not require them.

## ParsedOp Output

After tokenization and classification, the result is a `ParsedOp` structure:

```
ParsedOp {
  verb: string            // lowercased first token
  positionals: string[]   // non-verb, non-param, non-selector tokens
  params: Map<string, string>  // key:value pairs
  selectors: Selector[]   // @-prefixed selector tokens
  arrows: string[]        // arrow operators (if present)
  raw: string             // original input string
}
```

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `verb` | `string` | The operation verb, lowercased |
| `positionals` | `string[]` | Ordered list of positional arguments |
| `params` | `Map<string, string>` | Key:value parameters |
| `selectors` | `Selector[]` | Parsed @-selectors |
| `arrows` | `string[]` | Arrow operators, if any |
| `raw` | `string` | Original input string for error reporting |

### Parse Error

If parsing fails (e.g., empty input, unterminated quote), a `ParseError` is returned instead:

```
ParseError {
  error: string   // human-readable error message
  raw: string     // original input string
}
```

## Semantic Assignment: Domain Responsibility

fcp-core produces a structurally classified `ParsedOp`. The domain layer assigns meaning to positionals.

### Example: Same grammar, different semantics

**drawio-studio:**
```
Input:  add svc AuthService theme:blue
Parsed: {
  verb: "add",
  positionals: ["svc", "AuthService"],
  params: { "theme": "blue" },
  selectors: [],
  raw: "add svc AuthService theme:blue"
}
Domain interprets: positionals[0] = node type, positionals[1] = label
```

**fcp-midi:**
```
Input:  note Piano C4 at:1.1 dur:quarter
Parsed: {
  verb: "note",
  positionals: ["Piano", "C4"],
  params: { "at": "1.1", "dur": "quarter" },
  selectors: [],
  raw: "note Piano C4 at:1.1 dur:quarter"
}
Domain interprets: positionals[0] = track name, positionals[1] = pitch
```

Both produce the same `ParsedOp` shape. The domain's verb handler decides what `positionals[0]` and `positionals[1]` mean.

### Example: Selectors across domains

**drawio-studio:**
```
Input:  style @type:db fill:#ff0000
Parsed: {
  verb: "style",
  positionals: [],
  params: { "fill": "#ff0000" },
  selectors: [{ type: "type", value: "db" }],
  raw: "style @type:db fill:#ff0000"
}
Domain interprets: @type:db = all shapes of type "db"
```

**fcp-midi:**
```
Input:  transpose @track:Piano @range:1.1-4.4 +5
Parsed: {
  verb: "transpose",
  positionals: ["+5"],
  params: {},
  selectors: [
    { type: "track", value: "Piano" },
    { type: "range", value: "1.1-4.4" }
  ],
  raw: "transpose @track:Piano @range:1.1-4.4 +5"
}
Domain interprets: @track = filter by track, @range = filter by position, +5 = semitones
```

## Grammar Summary (EBNF)

```ebnf
op         = verb { token } ;
verb       = WORD ;
token      = selector | key_value | arrow | positional ;
selector   = "@" [ "not:" ] TYPE [ ":" VALUE ] ;
key_value  = KEY ":" VALUE ;
arrow      = "->" | "<->" | "--" ;
positional = WORD ;

WORD       = quoted_string | unquoted_string ;
KEY        = unquoted_string ;       (* no @, no arrow *)
VALUE      = unquoted_string ;       (* may contain ":" *)
TYPE       = unquoted_string ;
```
