"""Tests for fcp_core.verb_registry."""

from fcp_core.verb_registry import VerbRegistry, VerbSpec


class TestVerbRegistry:
    def test_register_and_lookup(self):
        registry = VerbRegistry()
        spec = VerbSpec(verb="add", syntax="add TYPE LABEL", category="create")
        registry.register(spec)
        assert registry.lookup("add") is spec

    def test_lookup_missing(self):
        registry = VerbRegistry()
        assert registry.lookup("nonexistent") is None

    def test_register_many(self):
        registry = VerbRegistry()
        specs = [
            VerbSpec(verb="add", syntax="add TYPE LABEL", category="create"),
            VerbSpec(verb="remove", syntax="remove REF", category="edit"),
            VerbSpec(verb="connect", syntax="connect SRC -> TGT", category="create"),
        ]
        registry.register_many(specs)
        assert len(registry.verbs) == 3
        assert registry.lookup("add") is not None
        assert registry.lookup("remove") is not None
        assert registry.lookup("connect") is not None

    def test_verbs_property_returns_copy(self):
        registry = VerbRegistry()
        spec = VerbSpec(verb="add", syntax="add TYPE LABEL", category="create")
        registry.register(spec)
        verbs = registry.verbs
        verbs.append(VerbSpec(verb="fake", syntax="", category=""))
        assert len(registry.verbs) == 1  # original unmodified

    def test_verbs_preserve_order(self):
        registry = VerbRegistry()
        registry.register(VerbSpec(verb="c", syntax="c", category="x"))
        registry.register(VerbSpec(verb="a", syntax="a", category="x"))
        registry.register(VerbSpec(verb="b", syntax="b", category="x"))
        assert [v.verb for v in registry.verbs] == ["c", "a", "b"]


class TestReferenceCard:
    def test_groups_by_category(self):
        registry = VerbRegistry()
        registry.register_many([
            VerbSpec(verb="add", syntax="add TYPE LABEL", category="create"),
            VerbSpec(verb="remove", syntax="remove REF", category="edit"),
            VerbSpec(verb="connect", syntax="connect SRC -> TGT", category="create"),
        ])
        card = registry.generate_reference_card()
        assert "CREATE:" in card
        assert "EDIT:" in card
        assert "add TYPE LABEL" in card
        assert "remove REF" in card
        assert "connect SRC -> TGT" in card

    def test_extra_sections(self):
        registry = VerbRegistry()
        registry.register(VerbSpec(verb="add", syntax="add TYPE LABEL", category="create"))
        card = registry.generate_reference_card(extra_sections={
            "Selectors": "@type:TYPE  @group:NAME  @all",
        })
        assert "SELECTORS:" in card
        assert "@type:TYPE" in card

    def test_empty_registry(self):
        registry = VerbRegistry()
        card = registry.generate_reference_card()
        assert card == ""  # no categories, no content (trailing lines stripped)

    def test_category_order_preserved(self):
        registry = VerbRegistry()
        registry.register_many([
            VerbSpec(verb="z", syntax="z", category="zebra"),
            VerbSpec(verb="a", syntax="a", category="alpha"),
            VerbSpec(verb="m", syntax="m", category="zebra"),
        ])
        card = registry.generate_reference_card()
        zebra_pos = card.index("ZEBRA:")
        alpha_pos = card.index("ALPHA:")
        assert zebra_pos < alpha_pos  # zebra first (insertion order)
