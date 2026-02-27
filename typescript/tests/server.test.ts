import { describe, it, expect } from "vitest";
import { createFcpServer, type FcpDomainAdapter, type OpResult } from "../src/server.js";
import { EventLog } from "../src/event-log.js";
import type { ParsedOp } from "../src/parsed-op.js";
import type { VerbSpec } from "../src/verb-registry.js";

// A minimal test domain
interface TestModel {
  title: string;
  items: string[];
}

type TestEvent = { type: "add"; item: string } | { type: "remove"; item: string };

const testVerbs: VerbSpec[] = [
  { verb: "add", syntax: "add ITEM", category: "create", description: "Add an item" },
  { verb: "remove", syntax: "remove ITEM", category: "modify", description: "Remove an item" },
  { verb: "list", syntax: "list", category: "query", description: "List all items" },
];

const testAdapter: FcpDomainAdapter<TestModel, TestEvent> = {
  createEmpty(title) {
    return { title, items: [] };
  },
  serialize(model) {
    return JSON.stringify(model);
  },
  deserialize(data) {
    return JSON.parse(typeof data === "string" ? data : data.toString());
  },
  rebuildIndices() {},
  getDigest(model) {
    return `[${model.title}: ${model.items.length} items]`;
  },
  dispatchOp(op: ParsedOp, model: TestModel, log: EventLog<TestEvent>): OpResult {
    switch (op.verb) {
      case "add": {
        const item = op.positionals[0];
        if (!item) return { success: false, message: "add requires an item" };
        model.items.push(item);
        log.append({ type: "add", item });
        return { success: true, message: item, prefix: "+" };
      }
      case "remove": {
        const item = op.positionals[0];
        if (!item) return { success: false, message: "remove requires an item" };
        const idx = model.items.indexOf(item);
        if (idx === -1) return { success: false, message: `"${item}" not found` };
        model.items.splice(idx, 1);
        log.append({ type: "remove", item });
        return { success: true, message: item, prefix: "-" };
      }
      default:
        return { success: false, message: `unhandled verb "${op.verb}"` };
    }
  },
  dispatchQuery(query: string, model: TestModel) {
    if (query === "list") {
      return model.items.length === 0 ? "empty" : model.items.join(", ");
    }
    return `unknown query: ${query}`;
  },
  reverseEvent(event: TestEvent, model: TestModel) {
    if (event.type === "add") {
      const idx = model.items.indexOf(event.item);
      if (idx !== -1) model.items.splice(idx, 1);
    } else if (event.type === "remove") {
      model.items.push(event.item);
    }
  },
};

describe("createFcpServer", () => {
  it("creates an MCP server without errors", () => {
    const server = createFcpServer({
      domain: "test",
      adapter: testAdapter,
      verbs: testVerbs,
    });
    expect(server).toBeDefined();
  });

  it("creates a server with reference card sections", () => {
    const server = createFcpServer({
      domain: "test",
      adapter: testAdapter,
      verbs: testVerbs,
      referenceCard: {
        sections: { "Notes": "Some additional notes" },
      },
    });
    expect(server).toBeDefined();
  });
});
