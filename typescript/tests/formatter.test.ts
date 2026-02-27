import { describe, it, expect } from "vitest";
import { formatResult, suggest } from "../src/formatter.js";

describe("formatResult", () => {
  it("formats success with prefix", () => {
    expect(formatResult(true, "svc AuthService", "+")).toBe("+ svc AuthService");
  });

  it("formats success without prefix", () => {
    expect(formatResult(true, "done")).toBe("done");
  });

  it("formats error", () => {
    expect(formatResult(false, "something broke")).toBe("ERROR: something broke");
  });

  it("formats error ignoring prefix", () => {
    expect(formatResult(false, "bad input", "+")).toBe("ERROR: bad input");
  });

  it("handles standard prefix conventions", () => {
    expect(formatResult(true, "AuthService", "+")).toBe("+ AuthService"); // created
    expect(formatResult(true, "edge A->B", "~")).toBe("~ edge A->B");   // modified
    expect(formatResult(true, "styled A", "*")).toBe("* styled A");     // changed
    expect(formatResult(true, "A", "-")).toBe("- A");                    // removed
    expect(formatResult(true, "group Backend", "!")).toBe("! group Backend"); // meta
    expect(formatResult(true, "layout", "@")).toBe("@ layout");          // bulk
  });
});

describe("suggest", () => {
  const candidates = ["add", "remove", "connect", "style", "label", "badge"];

  it("suggests exact match", () => {
    expect(suggest("add", candidates)).toBe("add");
  });

  it("suggests for single-char typo", () => {
    expect(suggest("ad", candidates)).toBe("add");
  });

  it("suggests for transposition", () => {
    expect(suggest("styel", candidates)).toBe("style");
  });

  it("suggests for substitution", () => {
    expect(suggest("labek", candidates)).toBe("label");
  });

  it("returns null for distant strings", () => {
    expect(suggest("zzzzzzz", candidates)).toBeNull();
  });

  it("returns null for empty candidates", () => {
    expect(suggest("test", [])).toBeNull();
  });

  it("picks closest when multiple are close", () => {
    expect(suggest("bade", candidates)).toBe("badge");
  });
});
