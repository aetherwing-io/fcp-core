import { describe, it, expect } from "vitest";
import { parseOp, isParseError } from "../src/parsed-op.js";

describe("parseOp", () => {
  it("parses a simple verb with positionals", () => {
    const result = parseOp("add svc AuthService");
    expect(isParseError(result)).toBe(false);
    if (isParseError(result)) return;
    expect(result.verb).toBe("add");
    expect(result.positionals).toEqual(["svc", "AuthService"]);
    expect(result.params).toEqual({});
    expect(result.selectors).toEqual([]);
  });

  it("extracts key:value params", () => {
    const result = parseOp("add svc AuthService theme:blue near:Gateway");
    if (isParseError(result)) return;
    expect(result.verb).toBe("add");
    expect(result.positionals).toEqual(["svc", "AuthService"]);
    expect(result.params).toEqual({ theme: "blue", near: "Gateway" });
  });

  it("extracts selectors", () => {
    const result = parseOp("remove @type:db @recent:3");
    if (isParseError(result)) return;
    expect(result.verb).toBe("remove");
    expect(result.selectors).toEqual(["@type:db", "@recent:3"]);
    expect(result.positionals).toEqual([]);
  });

  it("handles mixed token types", () => {
    const result = parseOp("style @type:svc fill:#ff0000 bold");
    if (isParseError(result)) return;
    expect(result.verb).toBe("style");
    expect(result.selectors).toEqual(["@type:svc"]);
    expect(result.params).toEqual({ fill: "#ff0000" });
    expect(result.positionals).toEqual(["bold"]);
  });

  it("lowercases the verb", () => {
    const result = parseOp("ADD svc Test");
    if (isParseError(result)) return;
    expect(result.verb).toBe("add");
  });

  it("preserves original input as raw", () => {
    const result = parseOp("  add svc Test  ");
    if (isParseError(result)) return;
    expect(result.raw).toBe("add svc Test");
  });

  it("handles quoted positionals", () => {
    const result = parseOp('label Gateway "API Gateway v2"');
    if (isParseError(result)) return;
    expect(result.positionals).toEqual(["Gateway", "API Gateway v2"]);
  });

  it("returns error for empty input", () => {
    const result = parseOp("");
    expect(isParseError(result)).toBe(true);
    if (!isParseError(result)) return;
    expect(result.error).toBe("empty operation");
  });

  it("returns error for whitespace-only input", () => {
    const result = parseOp("   ");
    expect(isParseError(result)).toBe(true);
  });

  it("handles arrows as positionals", () => {
    const result = parseOp("connect A -> B");
    if (isParseError(result)) return;
    expect(result.positionals).toEqual(["A", "->", "B"]);
  });

  it("handles verb-only input", () => {
    const result = parseOp("undo");
    if (isParseError(result)) return;
    expect(result.verb).toBe("undo");
    expect(result.positionals).toEqual([]);
    expect(result.params).toEqual({});
    expect(result.selectors).toEqual([]);
  });
});

describe("isParseError", () => {
  it("returns true for errors", () => {
    expect(isParseError({ success: false, error: "test", raw: "" })).toBe(true);
  });

  it("returns false for valid ops", () => {
    const result = parseOp("add test");
    expect(isParseError(result)).toBe(false);
  });
});
