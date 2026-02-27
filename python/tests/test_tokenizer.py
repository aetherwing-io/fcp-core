"""Tests for fcp_core.tokenizer."""

import pytest

from fcp_core.tokenizer import (
    is_arrow,
    is_key_value,
    is_selector,
    parse_key_value,
    tokenize,
)


class TestTokenize:
    def test_basic_splitting(self):
        assert tokenize("add svc AuthService") == ["add", "svc", "AuthService"]

    def test_double_quoted_string(self):
        assert tokenize('add svc "My Service" theme:blue') == [
            "add", "svc", "My Service", "theme:blue"
        ]

    def test_single_quoted_string(self):
        assert tokenize("add svc 'My Service' theme:blue") == [
            "add", "svc", "My Service", "theme:blue"
        ]

    def test_key_value_tokens(self):
        assert tokenize("style Node fill:#ff0000 bold") == [
            "style", "Node", "fill:#ff0000", "bold"
        ]

    def test_selector_tokens(self):
        assert tokenize("remove @type:db @all") == ["remove", "@type:db", "@all"]

    def test_arrows(self):
        assert tokenize("connect A -> B") == ["connect", "A", "->", "B"]

    def test_empty_string(self):
        assert tokenize("") == []

    def test_whitespace_only(self):
        assert tokenize("   ") == []

    def test_multiple_spaces(self):
        assert tokenize("add   svc   Name") == ["add", "svc", "Name"]

    def test_tabs(self):
        assert tokenize("add\tsvc\tName") == ["add", "svc", "Name"]

    def test_hash_not_comment(self):
        # # should NOT be treated as a comment character
        result = tokenize("style Node fill:#ff0000")
        assert "fill:#ff0000" in result

    def test_escaped_quote_in_string(self):
        # Single quotes inside double quotes don't need escaping
        result = tokenize('add svc "It\'s here"')
        assert result[2] == "It's here"

    def test_mixed_tokens(self):
        result = tokenize('connect "Auth Service" -> UserDB label:queries style:dashed')
        assert result == [
            "connect", "Auth Service", "->", "UserDB", "label:queries", "style:dashed"
        ]

    def test_unclosed_quote_raises(self):
        with pytest.raises(ValueError):
            tokenize('add svc "unclosed')


class TestIsKeyValue:
    def test_basic_key_value(self):
        assert is_key_value("theme:blue") is True

    def test_key_value_with_hash(self):
        assert is_key_value("fill:#ff0000") is True

    def test_selector_not_key_value(self):
        assert is_key_value("@track:Piano") is False

    def test_arrow_not_key_value(self):
        assert is_key_value("->") is False

    def test_plain_word(self):
        assert is_key_value("AuthService") is False

    def test_empty_value(self):
        assert is_key_value("key:") is True


class TestParseKeyValue:
    def test_basic(self):
        assert parse_key_value("theme:blue") == ("theme", "blue")

    def test_value_with_colon(self):
        # Only splits on first colon
        assert parse_key_value("fill:#ff0000") == ("fill", "#ff0000")

    def test_empty_value(self):
        assert parse_key_value("key:") == ("key", "")

    def test_multiple_colons(self):
        assert parse_key_value("a:b:c") == ("a", "b:c")


class TestIsSelector:
    def test_selector(self):
        assert is_selector("@track:Piano") is True

    def test_not_selector(self):
        assert is_selector("track:Piano") is False

    def test_at_all(self):
        assert is_selector("@all") is True


class TestIsArrow:
    def test_directed(self):
        assert is_arrow("->") is True

    def test_bidirectional(self):
        assert is_arrow("<->") is True

    def test_undirected(self):
        assert is_arrow("--") is True

    def test_not_arrow(self):
        assert is_arrow("connect") is False

    def test_partial_arrow(self):
        assert is_arrow("-") is False
