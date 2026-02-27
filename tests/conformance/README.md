# FCP Conformance Test Fixtures

Language-agnostic JSON test fixtures that define the behavioral specification for any FCP (File Context Protocol) implementation. These tests are derived from two reference implementations:

- **fcp-drawio** (TypeScript) -- diagram editing MCP server
- **fcp-midi** (Python) -- MIDI composition MCP server

Any valid FCP implementation (TypeScript, Python, Go, Rust, etc.) must pass these tests.

## Fixture Files

| File | Tests | Description |
|------|-------|-------------|
| `tokenizer.json` | 43 | Tokenizer: input string to token array |
| `parse-op.json` | 42 + 3 error | Full parse pipeline: op string to ParsedOp |
| `event-log.json` | 34 | Event log: append, undo, redo, checkpoints |
| `session.json` | 22 + 4 error | Session command parsing: new, open, save, etc. |

## How to Use

### 1. Load the JSON fixture

```python
import json

with open("tests/conformance/tokenizer.json") as f:
    suite = json.load(f)
```

```typescript
import suite from "./tests/conformance/tokenizer.json";
```

```go
data, _ := os.ReadFile("tests/conformance/tokenizer.json")
var suite ConformanceSuite
json.Unmarshal(data, &suite)
```

### 2. Iterate tests and assert expected output

```python
for test in suite["tests"]:
    result = tokenize(test["input"])
    assert result == test["expected"], f"FAIL: {test['name']}"
```

```typescript
for (const test of suite.tests) {
  const result = tokenize(test.input);
  expect(result).toEqual(test.expected);
}
```

### 3. Handle error tests

Some fixtures include an `error_tests` array for inputs that should produce errors:

```python
for test in suite.get("error_tests", []):
    result = parse_op(test["input"])
    assert is_error(result), f"Expected error: {test['name']}"
```

## Fixture Format Conventions

### Common fields

- **`name`** -- Short, unique test name (use as test case label)
- **`description`** -- Optional longer explanation of what the test verifies
- **`input`** -- The string input to the function under test
- **`expected`** -- The expected output (structure varies by fixture)
- **`expected_error`** -- When `true`, the input should produce an error

### tokenizer.json

- `input`: raw op string
- `expected`: array of string tokens

### parse-op.json

- `input`: raw op string
- `expected`: object with `verb`, `positionals`, `params`, `selectors`, `raw`
- `expected_error`: boolean (in error_tests)

The `params` field is a JSON object (implementations may use Map/dict/HashMap). The `selectors` field is an array of raw `@`-prefixed strings (implementations may further parse these into structured objects).

### event-log.json

- `operations`: array of actions to execute sequentially
- `assertions`: expected state after all operations

Operations use `action` to specify the method:
- `{"action": "append", "event": {...}}` -- append an event
- `{"action": "undo", "count": N}` -- undo N steps
- `{"action": "redo", "count": N}` -- redo N steps
- `{"action": "undo_to", "name": "..."}` -- undo to named checkpoint
- `{"action": "checkpoint", "name": "..."}` -- create named checkpoint
- `{"action": "recent", "count": N}` -- query recent events

Assertions check:
- `cursor` -- expected cursor position
- `length` -- expected total event count
- `undo_returned` / `redo_returned` / `undo_to_returned` / `recent_returned` -- expected return values
- `undo_to_error` -- when `true`, the undo_to should fail (unknown checkpoint)

### session.json

- `input`: session command string
- `expected`: object with `command`, `args`, `params`
- `expected_error`: boolean (in error_tests)

## Design Principles

1. **Domain-agnostic** -- Tests use generic event objects `{type, id}` and avoid MIDI/diagram-specific behavior
2. **JSON-only** -- No test framework code; fixtures are pure data consumable by any language
3. **Thorough edge cases** -- Empty inputs, unicode, special characters, boundary conditions
4. **Both happy and error paths** -- Every fixture includes error_tests where applicable
5. **Derived from real implementations** -- Behavior is verified against fcp-drawio and fcp-midi codebases
