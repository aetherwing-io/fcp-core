import { describe, it, expect } from "vitest";
import { VerbRegistry, type VerbSpec } from "../src/verb-registry.js";

describe("VerbRegistry", () => {
  function createTestRegistry(): VerbRegistry {
    const reg = new VerbRegistry();
    reg.registerMany([
      { verb: "add", syntax: "add TYPE LABEL [key:value]", category: "create" },
      { verb: "remove", syntax: "remove SELECTOR", category: "modify" },
      { verb: "connect", syntax: "connect SRC -> TGT", category: "create", description: "Create an edge" },
      { verb: "style", syntax: "style REF [fill:#HEX]", category: "modify", params: ["fill", "stroke"] },
    ]);
    return reg;
  }

  describe("register/lookup", () => {
    it("registers and looks up a verb", () => {
      const reg = new VerbRegistry();
      const spec: VerbSpec = { verb: "add", syntax: "add TYPE LABEL", category: "create" };
      reg.register(spec);
      expect(reg.lookup("add")).toEqual(spec);
    });

    it("returns undefined for unknown verbs", () => {
      const reg = new VerbRegistry();
      expect(reg.lookup("nonexistent")).toBeUndefined();
    });

    it("registers many at once", () => {
      const reg = createTestRegistry();
      expect(reg.lookup("add")).toBeDefined();
      expect(reg.lookup("remove")).toBeDefined();
      expect(reg.lookup("connect")).toBeDefined();
      expect(reg.lookup("style")).toBeDefined();
    });
  });

  describe("verbs", () => {
    it("returns all registered specs", () => {
      const reg = createTestRegistry();
      expect(reg.verbs).toHaveLength(4);
      const verbs = reg.verbs.map((v) => v.verb);
      expect(verbs).toContain("add");
      expect(verbs).toContain("remove");
      expect(verbs).toContain("connect");
      expect(verbs).toContain("style");
    });
  });

  describe("generateReferenceCard", () => {
    it("groups verbs by category", () => {
      const reg = createTestRegistry();
      const card = reg.generateReferenceCard();
      expect(card).toContain("CREATE:");
      expect(card).toContain("MODIFY:");
      expect(card).toContain("  add TYPE LABEL [key:value]");
      expect(card).toContain("  connect SRC -> TGT");
      expect(card).toContain("  remove SELECTOR");
      expect(card).toContain("  style REF [fill:#HEX]");
    });

    it("appends additional sections", () => {
      const reg = createTestRegistry();
      const card = reg.generateReferenceCard({
        "Themes": "  blue  #dae8fc\n  red   #f8cecc",
      });
      expect(card).toContain("THEMES:");
      expect(card).toContain("  blue  #dae8fc");
    });

    it("returns empty string for empty registry", () => {
      const reg = new VerbRegistry();
      expect(reg.generateReferenceCard()).toBe("");
    });
  });
});
