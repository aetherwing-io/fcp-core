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

  // --- Cell range support (spreadsheet domain) ---

  it("treats cell range A1:F1 as positional, not key:value", () => {
    const result = parseOp("merge A1:F1");
    if (isParseError(result)) return;
    expect(result.verb).toBe("merge");
    expect(result.positionals).toEqual(["A1:F1"]);
    expect(result.params).toEqual({});
  });

  it("treats cell range with params correctly", () => {
    const result = parseOp("merge A1:F1 align:center");
    if (isParseError(result)) return;
    expect(result.positionals).toEqual(["A1:F1"]);
    expect(result.params).toEqual({ align: "center" });
  });

  it("treats style range as positional", () => {
    const result = parseOp("style A1:D10 bold");
    if (isParseError(result)) return;
    expect(result.positionals).toEqual(["A1:D10", "bold"]);
    expect(result.params).toEqual({});
  });

  it("treats formula as positional", () => {
    const result = parseOp("set A1 =SUM(D2:D4)");
    if (isParseError(result)) return;
    expect(result.positionals).toEqual(["A1", "=SUM(D2:D4)"]);
    expect(result.params).toEqual({});
  });

  it("treats formula with fmt param correctly", () => {
    const result = parseOp("set D2 =SUM(A2:C2) fmt:$#,##0");
    if (isParseError(result)) return;
    expect(result.positionals).toEqual(["D2", "=SUM(A2:C2)"]);
    expect(result.params).toEqual({ "fmt": "$#,##0" });
  });

  it("treats row range as positional", () => {
    const result = parseOp("height 1:5 25");
    if (isParseError(result)) return;
    expect(result.positionals).toEqual(["1:5", "25"]);
    expect(result.params).toEqual({});
  });

  it("treats cross-sheet range as positional", () => {
    const result = parseOp("clear Sheet2!A1:B10");
    if (isParseError(result)) return;
    expect(result.positionals).toEqual(["Sheet2!A1:B10"]);
  });

  it("treats border range with params correctly", () => {
    const result = parseOp("border A1:F1 outline line:thin color:#000000");
    if (isParseError(result)) return;
    expect(result.positionals).toEqual(["A1:F1", "outline"]);
    expect(result.params).toEqual({ line: "thin", color: "#000000" });
  });

  // --- Quoted string colon handling ---

  it("treats quoted colon string as positional, not key:value", () => {
    const result = parseOp('set A11 "LTV:CAC"');
    if (isParseError(result)) return;
    expect(result.positionals).toEqual(["A11", "LTV:CAC"]);
    expect(result.params).toEqual({});
  });

  it("handles quoted string with key:value param", () => {
    const result = parseOp('set A11 "LTV:CAC" fmt:$#,##0');
    if (isParseError(result)) return;
    expect(result.positionals).toEqual(["A11", "LTV:CAC"]);
    expect(result.params).toEqual({ "fmt": "$#,##0" });
  });

  it("handles quoted string without colon", () => {
    const result = parseOp('set A1 "Hello World"');
    if (isParseError(result)) return;
    expect(result.positionals).toEqual(["A1", "Hello World"]);
  });

  // --- isPositional extension point ---

  it("uses isPositional callback to force column range as positional", () => {
    const colRangeRe = /^[A-Za-z]{1,3}:[A-Za-z]{1,3}$/;
    const result = parseOp("width B:G 13", (token) => colRangeRe.test(token));
    if (isParseError(result)) return;
    expect(result.positionals).toEqual(["B:G", "13"]);
    expect(result.params).toEqual({});
  });

  it("isPositional callback does not intercept real params", () => {
    const result = parseOp("style A1 fill:#ff0000", () => false);
    if (isParseError(result)) return;
    expect(result.params).toEqual({ fill: "#ff0000" });
  });

  it("without isPositional, column ranges are key:value", () => {
    const result = parseOp("width B:G 13");
    if (isParseError(result)) return;
    expect(result.params).toHaveProperty("B");
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
