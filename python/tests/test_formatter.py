"""Tests for fcp_core.formatter."""

from fcp_core.formatter import format_result, suggest


class TestFormatResult:
    def test_success(self):
        assert format_result(True, "Created node") == "+ Created node"

    def test_failure(self):
        assert format_result(False, "Node not found") == "! Node not found"

    def test_custom_prefix(self):
        assert format_result(True, "Shape modified", prefix="*") == "* Shape modified"

    def test_custom_prefix_on_failure(self):
        assert format_result(False, "Error", prefix="~") == "~ Error"

    def test_empty_message(self):
        assert format_result(True, "") == "+ "

    def test_prefix_codes(self):
        # Verify all standard prefix conventions work
        assert format_result(True, "added", "+").startswith("+")
        assert format_result(True, "edge", "~").startswith("~")
        assert format_result(True, "modified", "*").startswith("*")
        assert format_result(True, "removed", "-").startswith("-")
        assert format_result(True, "group", "!").startswith("!")
        assert format_result(True, "layout", "@").startswith("@")


class TestSuggest:
    def test_exact_match(self):
        assert suggest("add", ["add", "remove", "connect"]) == "add"

    def test_close_match(self):
        assert suggest("ad", ["add", "remove", "connect"]) == "add"

    def test_no_match(self):
        assert suggest("xyz", ["add", "remove", "connect"]) is None

    def test_empty_candidates(self):
        assert suggest("add", []) is None

    def test_typo_correction(self):
        result = suggest("conect", ["add", "remove", "connect"])
        assert result == "connect"

    def test_case_sensitive_no_match(self):
        # difflib is case-sensitive — all-caps won't match lowercase
        result = suggest("CONNECT", ["connect", "remove", "resize"])
        assert result is None

    def test_partial_case_match(self):
        # Mixed case with enough overlap to match
        result = suggest("Connect", ["connect", "remove", "resize"])
        assert result == "connect"

    def test_best_of_multiple(self):
        result = suggest("remov", ["remove", "rename", "resize"])
        assert result == "remove"
