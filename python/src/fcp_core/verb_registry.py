"""Structured verb registry — single source of truth for domain verbs.

Used by the reference card generator, tool description builder,
and for dispatch table validation.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class VerbSpec:
    """Specification for a single verb in an FCP protocol."""

    verb: str
    syntax: str
    category: str
    params: list[str] = field(default_factory=list)
    description: str = ""


class VerbRegistry:
    """Registry of verb specifications with reference card generation."""

    def __init__(self) -> None:
        self._verbs: list[VerbSpec] = []
        self._map: dict[str, VerbSpec] = {}

    def register(self, spec: VerbSpec) -> None:
        """Register a single verb specification."""
        self._verbs.append(spec)
        self._map[spec.verb] = spec

    def register_many(self, specs: list[VerbSpec]) -> None:
        """Register multiple verb specifications."""
        for spec in specs:
            self.register(spec)

    def lookup(self, verb: str) -> VerbSpec | None:
        """Look up a verb specification by name."""
        return self._map.get(verb)

    @property
    def verbs(self) -> list[VerbSpec]:
        """All registered verb specifications (insertion order)."""
        return list(self._verbs)

    def generate_reference_card(
        self,
        extra_sections: dict[str, str] | None = None,
    ) -> str:
        """Generate a formatted reference card from registered verbs.

        Verbs are grouped by category. Extra static sections are appended
        after the verb listings.
        """
        lines: list[str] = []

        # Group verbs by category, preserving insertion order
        seen_categories: list[str] = []
        for v in self._verbs:
            if v.category not in seen_categories:
                seen_categories.append(v.category)

        for cat in seen_categories:
            cat_verbs = [v for v in self._verbs if v.category == cat]
            if not cat_verbs:
                continue
            # Title-case the category name
            cat_title = cat.replace("_", " ").replace("-", " ").title()
            lines.append(f"### {cat_title}")
            for v in cat_verbs:
                lines.append(f"  {v.syntax}")
            lines.append("")

        if extra_sections:
            for title, content in extra_sections.items():
                lines.append(f"## {title}")
                lines.append(content)
                lines.append("")

        return "\n".join(lines)
