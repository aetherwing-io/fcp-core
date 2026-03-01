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

    # --- Cell range support (spreadsheet domain) ---

    def test_merge_range_is_positional(self):
        """Cell ranges like A1:F1 must be positional, not key:value."""
        result = parse_op("merge A1:F1")
        assert isinstance(result, ParsedOp)
        assert result.verb == "merge"
        assert result.positionals == ["A1:F1"]
        assert result.params == {}

    def test_style_range_is_positional(self):
        result = parse_op("style A1:D10 bold")
        assert isinstance(result, ParsedOp)
        assert result.positionals == ["A1:D10", "bold"]
        assert result.params == {}

    def test_merge_range_with_param(self):
        result = parse_op("merge A1:F1 align:center")
        assert isinstance(result, ParsedOp)
        assert result.positionals == ["A1:F1"]
        assert result.params == {"align": "center"}

    def test_formula_is_positional(self):
        """Formulas like =SUM(D2:D4) must be positional, not key:value."""
        result = parse_op("set A1 =SUM(D2:D4)")
        assert isinstance(result, ParsedOp)
        assert result.positionals == ["A1", "=SUM(D2:D4)"]
        assert result.params == {}

    def test_formula_average_is_positional(self):
        result = parse_op("set B1 =AVERAGE(B2:B4)")
        assert isinstance(result, ParsedOp)
        assert result.positionals == ["B1", "=AVERAGE(B2:B4)"]

    def test_row_range_is_positional(self):
        result = parse_op("height 1:5 25")
        assert isinstance(result, ParsedOp)
        assert result.positionals == ["1:5", "25"]
        assert result.params == {}

    def test_cross_sheet_range_is_positional(self):
        result = parse_op("clear Sheet2!A1:B10")
        assert isinstance(result, ParsedOp)
        assert result.positionals == ["Sheet2!A1:B10"]

    def test_border_range_with_params(self):
        result = parse_op("border A1:F1 outline line:thin color:#000000")
        assert isinstance(result, ParsedOp)
        assert result.positionals == ["A1:F1", "outline"]
        assert result.params == {"line": "thin", "color": "#000000"}

    def test_filter_range(self):
        result = parse_op("filter A1:F10")
        assert isinstance(result, ParsedOp)
        assert result.positionals == ["A1:F10"]

    def test_formula_with_fmt_param(self):
        result = parse_op("set D2 =SUM(A2:C2) fmt:$#,##0")
        assert isinstance(result, ParsedOp)
        assert result.positionals == ["D2", "=SUM(A2:C2)"]
        assert result.params == {"fmt": "$#,##0"}

    # --- Quoted string colon handling ---

    def test_quoted_colon_is_positional(self):
        """Quoted strings with colons must NOT be split as key:value."""
        result = parse_op('set A11 "LTV:CAC"')
        assert isinstance(result, ParsedOp)
        assert result.positionals == ["A11", "LTV:CAC"]
        assert result.params == {}

    def test_quoted_string_with_key_value_param(self):
        result = parse_op('set A11 "LTV:CAC" fmt:$#,##0')
        assert isinstance(result, ParsedOp)
        assert result.positionals == ["A11", "LTV:CAC"]
        assert result.params == {"fmt": "$#,##0"}

    def test_quoted_no_colon_still_positional(self):
        result = parse_op('set A1 "Hello World"')
        assert isinstance(result, ParsedOp)
        assert result.positionals == ["A1", "Hello World"]

    # --- is_positional extension point ---

    def test_is_positional_callback(self):
        """Domain callback can force tokens as positional."""
        import re
        col_range_re = re.compile(r"^[A-Za-z]{1,3}:[A-Za-z]{1,3}$")

        result = parse_op(
            "width B:G 13",
            is_positional=lambda t: bool(col_range_re.match(t)),
        )
        assert isinstance(result, ParsedOp)
        assert result.positionals == ["B:G", "13"]
        assert result.params == {}

    def test_is_positional_does_not_affect_real_params(self):
        """is_positional callback should not intercept real key:value."""
        result = parse_op(
            "style A1 fill:#ff0000",
            is_positional=lambda t: False,
        )
        assert isinstance(result, ParsedOp)
        assert result.params == {"fill": "#ff0000"}

    def test_is_positional_none_default(self):
        """Without callback, column ranges are still treated as key:value."""
        result = parse_op("width B:G 13")
        assert isinstance(result, ParsedOp)
        # Without callback, B:G gets classified as key:value
        assert "B" in result.params
