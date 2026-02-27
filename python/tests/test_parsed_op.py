"""Tests for fcp_core.parsed_op."""

from fcp_core.parsed_op import ParseError, ParsedOp, parse_op


class TestParseOp:
    def test_basic_verb_and_positionals(self):
        result = parse_op("add svc AuthService")
        assert isinstance(result, ParsedOp)
        assert result.verb == "add"
        assert result.positionals == ["svc", "AuthService"]
        assert result.params == {}
        assert result.selectors == []

    def test_verb_is_lowercased(self):
        result = parse_op("ADD svc AuthService")
        assert isinstance(result, ParsedOp)
        assert result.verb == "add"

    def test_key_value_params(self):
        result = parse_op("style Node fill:#ff0000 bold")
        assert isinstance(result, ParsedOp)
        assert result.verb == "style"
        assert result.params == {"fill": "#ff0000"}
        assert result.positionals == ["Node", "bold"]

    def test_selectors(self):
        result = parse_op("remove @type:db @all")
        assert isinstance(result, ParsedOp)
        assert result.verb == "remove"
        assert result.selectors == ["@type:db", "@all"]
        assert result.positionals == []

    def test_mixed_tokens(self):
        result = parse_op('connect "Auth Service" -> UserDB label:queries')
        assert isinstance(result, ParsedOp)
        assert result.verb == "connect"
        assert result.positionals == ["Auth Service", "->", "UserDB"]
        assert result.params == {"label": "queries"}

    def test_all_token_types(self):
        result = parse_op("move @track:Piano @range:1.1-4.4 to:5.1")
        assert isinstance(result, ParsedOp)
        assert result.verb == "move"
        assert result.selectors == ["@track:Piano", "@range:1.1-4.4"]
        assert result.params == {"to": "5.1"}
        assert result.positionals == []

    def test_raw_preserved(self):
        raw = "add svc AuthService theme:blue"
        result = parse_op(raw)
        assert isinstance(result, ParsedOp)
        assert result.raw == raw

    def test_empty_string_error(self):
        result = parse_op("")
        assert isinstance(result, ParseError)
        assert result.success is False
        assert "Empty" in result.error

    def test_whitespace_only_error(self):
        result = parse_op("   ")
        assert isinstance(result, ParseError)
        assert result.success is False

    def test_single_verb(self):
        result = parse_op("undo")
        assert isinstance(result, ParsedOp)
        assert result.verb == "undo"
        assert result.positionals == []
        assert result.params == {}
        assert result.selectors == []

    def test_unclosed_quote_error(self):
        result = parse_op('add svc "unclosed')
        assert isinstance(result, ParseError)
        assert "Tokenization failed" in result.error

    def test_multiple_params(self):
        result = parse_op("note Piano C4 at:1.1 dur:quarter vel:80")
        assert isinstance(result, ParsedOp)
        assert result.verb == "note"
        assert result.positionals == ["Piano", "C4"]
        assert result.params == {"at": "1.1", "dur": "quarter", "vel": "80"}

    def test_negated_selector(self):
        result = parse_op("remove @track:Piano @not:pitch:C4")
        assert isinstance(result, ParsedOp)
        assert "@not:pitch:C4" in result.selectors

    def test_positional_order_preserved(self):
        result = parse_op("chord Piano Cmaj at:1.1")
        assert isinstance(result, ParsedOp)
        assert result.positionals == ["Piano", "Cmaj"]

    def test_no_domain_interpretation(self):
        """parse_op should NOT interpret positionals — that's domain responsibility."""
        result = parse_op("note Piano C4 at:1.1 dur:quarter")
        assert isinstance(result, ParsedOp)
        # Positionals are just strings, not interpreted as track/pitch
        assert result.positionals == ["Piano", "C4"]
