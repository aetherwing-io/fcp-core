import { describe, it, expect } from "vitest";
import { tokenize, isKeyValue, parseKeyValue, parseKeyValueWithMeta, isArrow, isSelector } from "../src/tokenizer.js";

describe("tokenize", () => {
  it("splits simple tokens", () => {
    expect(tokenize("add svc AuthService")).toEqual(["add", "svc", "AuthService"]);
  });

  it("handles quoted strings", () => {
    expect(tokenize('add svc "Auth Service" theme:blue')).toEqual([
      "add", "svc", "Auth Service", "theme:blue",
    ]);
  });

  it("handles escaped quotes inside quoted strings", () => {
    expect(tokenize('label A "say \\"hello\\""')).toEqual([
      "label", "A", 'say "hello"',
    ]);
  });

  it("handles empty input", () => {
    expect(tokenize("")).toEqual([]);
  });

  it("handles whitespace-only input", () => {
    expect(tokenize("   ")).toEqual([]);
  });

  it("handles multiple spaces between tokens", () => {
    expect(tokenize("add   svc   A")).toEqual(["add", "svc", "A"]);
  });

  it("converts literal \\n to newline in unquoted tokens", () => {
    expect(tokenize("add svc Container\\nRegistry")).toEqual([
      "add", "svc", "Container\nRegistry",
    ]);
  });

  it("converts literal \\n to newline in quoted strings", () => {
    expect(tokenize('add svc "Container\\nRegistry"')).toEqual([
      "add", "svc", "Container\nRegistry",
    ]);
  });

  it("handles embedded quoted values (key:\"value\") — preserves quotes in token", () => {
    expect(tokenize('label:"Line1\\nLine2"')).toEqual(['label:"Line1\nLine2"']);
  });

  it("parseKeyValue strips preserved quotes for backwards compat", () => {
    const { key, value } = parseKeyValue('label:"Line1\nLine2"');
    expect(key).toBe("label");
    expect(value).toBe("Line1\nLine2");
  });

  it("parseKeyValueWithMeta reports wasQuoted flag", () => {
    const result = parseKeyValueWithMeta('engine_version:"15"');
    expect(result.key).toBe("engine_version");
    expect(result.value).toBe("15");
    expect(result.wasQuoted).toBe(true);
  });

  it("parseKeyValueWithMeta reports wasQuoted=false for unquoted", () => {
    const result = parseKeyValueWithMeta("port:80");
    expect(result.key).toBe("port");
    expect(result.value).toBe("80");
    expect(result.wasQuoted).toBe(false);
  });

  it("converts multiple \\n sequences", () => {
    expect(tokenize("add svc A\\nB\\nC")).toEqual(["add", "svc", "A\nB\nC"]);
  });

  it("handles single token", () => {
    expect(tokenize("add")).toEqual(["add"]);
  });

  it("handles empty quoted string", () => {
    expect(tokenize('""')).toEqual([""]);
  });

  it("handles unclosed quote (takes rest as token)", () => {
    expect(tokenize('"hello world')).toEqual(["hello world"]);
  });

  it("handles escaped backslash in quotes", () => {
    expect(tokenize('"path\\\\dir"')).toEqual(["path\\dir"]);
  });

  it("handles key:value with colons in value", () => {
    expect(tokenize("url:http://example.com")).toEqual(["url:http://example.com"]);
  });
});

describe("isKeyValue", () => {
  it("returns true for key:value", () => {
    expect(isKeyValue("theme:blue")).toBe(true);
  });

  it("returns true for key:value with colons in value", () => {
    expect(isKeyValue("url:http://x")).toBe(true);
  });

  it("returns false for selectors", () => {
    expect(isKeyValue("@type:db")).toBe(false);
  });

  it("returns false for arrows", () => {
    expect(isKeyValue("->")).toBe(false);
  });

  it("returns false for plain words", () => {
    expect(isKeyValue("hello")).toBe(false);
  });

  it("returns false for trailing colon", () => {
    expect(isKeyValue("key:")).toBe(false);
  });

  it("returns false for leading colon", () => {
    expect(isKeyValue(":value")).toBe(false);
  });
});

describe("parseKeyValue", () => {
  it("parses simple key:value", () => {
    expect(parseKeyValue("theme:blue")).toEqual({ key: "theme", value: "blue" });
  });

  it("parses value with colons", () => {
    expect(parseKeyValue("url:http://x:8080")).toEqual({ key: "url", value: "http://x:8080" });
  });
});

describe("isArrow", () => {
  it("recognizes ->", () => {
    expect(isArrow("->")).toBe(true);
  });

  it("recognizes <->", () => {
    expect(isArrow("<->")).toBe(true);
  });

  it("recognizes --", () => {
    expect(isArrow("--")).toBe(true);
  });

  it("rejects other tokens", () => {
    expect(isArrow("=>")).toBe(false);
    expect(isArrow("add")).toBe(false);
  });
});

describe("isSelector", () => {
  it("recognizes @-prefixed tokens", () => {
    expect(isSelector("@type:db")).toBe(true);
    expect(isSelector("@all")).toBe(true);
    expect(isSelector("@recent:5")).toBe(true);
  });

  it("rejects non-@ tokens", () => {
    expect(isSelector("type:db")).toBe(false);
    expect(isSelector("add")).toBe(false);
  });
});
