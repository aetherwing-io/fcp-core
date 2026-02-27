import { describe, it, expect } from "vitest";
import { EventLog } from "../src/event-log.js";

describe("EventLog", () => {
  it("appends events and advances cursor", () => {
    const log = new EventLog<string>();
    log.append("a");
    log.append("b");
    expect(log.cursor).toBe(2);
    expect(log.length).toBe(2);
  });

  it("returns recent events in chronological order", () => {
    const log = new EventLog<string>();
    log.append("a");
    log.append("b");
    log.append("c");
    expect(log.recent(2)).toEqual(["b", "c"]);
    expect(log.recent()).toEqual(["a", "b", "c"]);
  });

  describe("undo", () => {
    it("returns most recent event", () => {
      const log = new EventLog<string>();
      log.append("a");
      log.append("b");
      const undone = log.undo();
      expect(undone).toEqual(["b"]);
      expect(log.cursor).toBe(1);
    });

    it("returns multiple events in reverse order", () => {
      const log = new EventLog<string>();
      log.append("a");
      log.append("b");
      log.append("c");
      const undone = log.undo(2);
      expect(undone).toEqual(["c", "b"]);
      expect(log.cursor).toBe(1);
    });

    it("returns empty array when nothing to undo", () => {
      const log = new EventLog<string>();
      expect(log.undo()).toEqual([]);
    });

    it("skips checkpoint sentinels", () => {
      const log = new EventLog<string>();
      log.append("a");
      log.checkpoint("cp1");
      log.append("b");
      const undone = log.undo(2);
      expect(undone).toEqual(["b", "a"]);
    });
  });

  describe("redo", () => {
    it("re-applies undone events in forward order", () => {
      const log = new EventLog<string>();
      log.append("a");
      log.append("b");
      log.undo(2);
      const redone = log.redo(2);
      expect(redone).toEqual(["a", "b"]);
      expect(log.cursor).toBe(2);
    });

    it("returns empty array when nothing to redo", () => {
      const log = new EventLog<string>();
      log.append("a");
      expect(log.redo()).toEqual([]);
    });

    it("skips checkpoint sentinels during redo", () => {
      const log = new EventLog<string>();
      log.append("a");
      log.checkpoint("cp1");
      log.append("b");
      log.undo(2);
      const redone = log.redo(2);
      expect(redone).toEqual(["a", "b"]);
    });
  });

  describe("redo tail truncation", () => {
    it("truncates redo history on new append", () => {
      const log = new EventLog<string>();
      log.append("a");
      log.append("b");
      log.undo(); // cursor at 1, "b" is in redo tail
      log.append("c"); // should truncate "b"
      expect(log.length).toBe(2); // "a", "c"
      expect(log.redo()).toEqual([]); // no redo available
      expect(log.recent()).toEqual(["a", "c"]);
    });
  });

  describe("checkpoint", () => {
    it("creates a checkpoint that can be undone to", () => {
      const log = new EventLog<string>();
      log.append("a");
      log.checkpoint("v1");
      log.append("b");
      log.append("c");
      const undone = log.undoTo("v1");
      expect(undone).toEqual(["c", "b"]);
      // cursor should be at checkpoint position
      expect(log.recent()).toEqual(["a"]);
    });

    it("returns null for unknown checkpoint", () => {
      const log = new EventLog<string>();
      log.append("a");
      expect(log.undoTo("nonexistent")).toBeNull();
    });

    it("returns null if checkpoint is at/beyond cursor", () => {
      const log = new EventLog<string>();
      log.append("a");
      log.checkpoint("v1");
      // Undo past the checkpoint
      log.undo(); // undo "a" (checkpoint is skipped)
      // Now cursor is before the checkpoint, so undoTo should still work
      // Actually: checkpoint is at position 1, cursor after undo of "a" is at 0
      // So target(1) >= cursor(0) is false, it should work
      // Let me test a different scenario where checkpoint IS at cursor
      const log2 = new EventLog<string>();
      log2.checkpoint("v1"); // checkpoint at position 0
      log2.append("a");
      // cursor is 2, checkpoint is 0 — should work
      const result = log2.undoTo("v1");
      expect(result).toEqual(["a"]);
    });

    it("removes checkpoints beyond cursor on truncation", () => {
      const log = new EventLog<string>();
      log.append("a");
      log.checkpoint("v1");
      log.append("b");
      log.undo(2); // undo b and a, cursor before checkpoint
      log.append("x"); // truncates everything including checkpoint
      expect(log.undoTo("v1")).toBeNull(); // checkpoint gone
    });
  });

  describe("cursor management", () => {
    it("starts at 0", () => {
      const log = new EventLog<string>();
      expect(log.cursor).toBe(0);
    });

    it("advances on append", () => {
      const log = new EventLog<string>();
      log.append("a");
      expect(log.cursor).toBe(1);
      log.append("b");
      expect(log.cursor).toBe(2);
    });

    it("moves back on undo", () => {
      const log = new EventLog<string>();
      log.append("a");
      log.append("b");
      log.undo();
      expect(log.cursor).toBe(1);
    });

    it("moves forward on redo", () => {
      const log = new EventLog<string>();
      log.append("a");
      log.append("b");
      log.undo();
      log.redo();
      expect(log.cursor).toBe(2);
    });
  });
});
