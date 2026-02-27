/**
 * Specification for a single verb in an FCP protocol.
 */
export interface VerbSpec {
  verb: string;
  syntax: string;
  category: string;
  params?: string[];
  description?: string;
}

/**
 * Registry of verb specifications. Provides lookup by verb name and
 * reference card generation grouped by category.
 */
export class VerbRegistry {
  private specs = new Map<string, VerbSpec>();
  private categories = new Map<string, VerbSpec[]>();

  /**
   * Register a single verb specification.
   */
  register(spec: VerbSpec): void {
    this.specs.set(spec.verb, spec);
    const list = this.categories.get(spec.category) ?? [];
    list.push(spec);
    this.categories.set(spec.category, list);
  }

  /**
   * Register multiple verb specifications at once.
   */
  registerMany(specs: VerbSpec[]): void {
    for (const spec of specs) {
      this.register(spec);
    }
  }

  /**
   * Look up a verb specification by name.
   */
  lookup(verb: string): VerbSpec | undefined {
    return this.specs.get(verb);
  }

  /**
   * Generate a reference card string grouped by category.
   * Optional `sections` adds extra static sections (e.g., domain-specific
   * reference material) appended after the verb listing.
   */
  generateReferenceCard(sections?: Record<string, string>): string {
    const lines: string[] = [];

    for (const [category, specs] of this.categories) {
      lines.push(`${category.toUpperCase()}:`);
      for (const spec of specs) {
        lines.push(`  ${spec.syntax}`);
      }
      lines.push("");
    }

    if (sections) {
      for (const [title, content] of Object.entries(sections)) {
        lines.push(`${title.toUpperCase()}:`);
        lines.push(content);
        lines.push("");
      }
    }

    // Remove trailing empty line
    while (lines.length > 0 && lines[lines.length - 1] === "") {
      lines.pop();
    }

    return lines.join("\n");
  }

  /**
   * All registered verb specifications.
   */
  get verbs(): VerbSpec[] {
    return [...this.specs.values()];
  }
}
