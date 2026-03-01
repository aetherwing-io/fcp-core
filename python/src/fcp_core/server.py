"""FCP server factory — creates a fully wired MCP server for any domain.

Registers 4 tools: {domain}, {domain}_query, {domain}_session, {domain}_help.
Embeds the reference card in the main tool description.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, Protocol, TypeVar

from mcp.server.fastmcp import FastMCP
from mcp.types import TextContent

from fcp_core.event_log import EventLog
from fcp_core.formatter import format_result
from fcp_core.parsed_op import ParsedOp, ParseError, parse_op
from fcp_core.session import SessionDispatcher, SessionHooks
from fcp_core.verb_registry import VerbRegistry, VerbSpec

M = TypeVar("M")  # Model type
E = TypeVar("E")  # Event type


@dataclass
class OpResult:
    """Result of dispatching a single operation."""

    success: bool
    message: str
    prefix: str = ""


class FcpDomainAdapter(Protocol[M, E]):
    """Protocol that domain implementations must satisfy."""

    def create_empty(self, title: str, params: dict[str, str]) -> M:
        """Create a new empty model."""
        ...

    def serialize(self, model: M, path: str) -> None:
        """Serialize the model to a file."""
        ...

    def deserialize(self, path: str) -> M:
        """Deserialize a model from a file."""
        ...

    def rebuild_indices(self, model: M) -> None:
        """Rebuild any indices on the model."""
        ...

    def get_digest(self, model: M) -> str:
        """Return a human-readable digest of the model."""
        ...

    def dispatch_op(self, op: ParsedOp, model: M, log: EventLog[E]) -> OpResult:
        """Execute a parsed operation on the model."""
        ...

    def dispatch_query(self, query: str, model: M) -> str:
        """Execute a query against the model."""
        ...

    def reverse_event(self, event: E, model: M) -> None:
        """Reverse a single event (for undo)."""
        ...

    def replay_event(self, event: E, model: M) -> None:
        """Replay a single event (for redo)."""
        ...


class _AdapterSessionHooks(Generic[M, E]):
    """Bridges FcpDomainAdapter to SessionHooks protocol."""

    def __init__(self, adapter: FcpDomainAdapter[M, E]) -> None:
        self._adapter = adapter

    def on_new(self, params: dict[str, str]) -> M:
        title = params.pop("title", "Untitled")
        return self._adapter.create_empty(title, params)

    def on_open(self, path: str) -> M:
        return self._adapter.deserialize(path)

    def on_save(self, model: M, path: str) -> None:
        self._adapter.serialize(model, path)

    def on_rebuild_indices(self, model: M) -> None:
        self._adapter.rebuild_indices(model)

    def get_digest(self, model: M) -> str:
        return self._adapter.get_digest(model)


def _build_tool_description(
    domain: str,
    registry: VerbRegistry,
    extra_sections: dict[str, str] | None = None,
) -> str:
    """Build the inline tool description embedding the reference card."""
    lines: list[str] = []
    lines.append(
        f"Execute {domain} operations. Each op string follows: "
        f"VERB TARGET [key:value ...]\n"
        f"Call {domain}_help for the full reference card.\n"
    )

    # Group verbs by category
    seen_categories: list[str] = []
    for v in registry.verbs:
        if v.category not in seen_categories:
            seen_categories.append(v.category)

    for cat in seen_categories:
        cat_verbs = [v for v in registry.verbs if v.category == cat]
        if not cat_verbs:
            continue
        cat_title = cat.replace("_", " ").replace("-", " ").upper()
        lines.append(f"{cat_title}:")
        for v in cat_verbs:
            lines.append(f"  {v.syntax}")
        lines.append("")

    if extra_sections:
        for title, content in extra_sections.items():
            lines.append(f"{title.upper()}:")
            lines.append(content)
            lines.append("")

    return "\n".join(lines)


def create_fcp_server(
    domain: str,
    adapter: FcpDomainAdapter,
    verbs: list[VerbSpec],
    *,
    extra_sections: dict[str, str] | None = None,
    **kwargs,
) -> FastMCP:
    """Create a fully wired MCP server for the given domain.

    Registers 4 tools:
    - ``{domain}`` — execute operations (batch)
    - ``{domain}_query`` — query model state
    - ``{domain}_session`` — session lifecycle
    - ``{domain}_help`` — reference card

    Parameters
    ----------
    domain : str
        Domain name (e.g. "midi", "drawio"). Used as tool name prefix.
    adapter : FcpDomainAdapter
        Domain-specific adapter implementing the protocol.
    verbs : list[VerbSpec]
        Verb specifications for this domain.
    extra_sections : dict[str, str] | None
        Additional sections for the reference card.
    **kwargs
        Additional arguments passed to FastMCP constructor.

    Returns
    -------
    FastMCP
        Configured MCP server ready to run.
    """
    registry = VerbRegistry()
    registry.register_many(verbs)

    event_log: EventLog = EventLog()

    hooks = _AdapterSessionHooks(adapter)
    session = SessionDispatcher(
        hooks=hooks,
        event_log=event_log,
        reverse_event=adapter.reverse_event,
        replay_event=adapter.replay_event,
    )

    mcp = FastMCP(**kwargs)

    # Build tool description with embedded reference card
    tool_description = _build_tool_description(domain, registry, extra_sections)
    reference_card = registry.generate_reference_card(extra_sections)

    @mcp.tool(name=domain, description=tool_description)
    def execute_ops(ops: list[str]) -> TextContent:
        if session.model is None:
            return TextContent(type="text", text=format_result(False, "No model loaded. Use session 'new' or 'open' first."))
        results: list[str] = []
        for op_str in ops:
            parsed = parse_op(op_str)
            if isinstance(parsed, ParseError):
                results.append(format_result(False, parsed.error))
                continue
            result = adapter.dispatch_op(parsed, session.model, session.event_log)
            results.append(format_result(result.success, result.message, result.prefix))
        return TextContent(type="text", text="\n".join(results))

    @mcp.tool(name=f"{domain}_query")
    def execute_query(q: str) -> TextContent:
        f"""Query {domain} state."""
        if session.model is None:
            return TextContent(type="text", text=format_result(False, "No model loaded."))
        return TextContent(type="text", text=adapter.dispatch_query(q, session.model))

    @mcp.tool(name=f"{domain}_session")
    def execute_session(action: str) -> TextContent:
        f"""Session: 'new "Title"', 'open ./file', 'save', 'checkpoint v1', 'undo', 'redo'"""
        return TextContent(type="text", text=session.dispatch(action))

    @mcp.tool(name=f"{domain}_help")
    def get_help() -> str:
        f"""Returns the {domain} reference card with all syntax."""
        return reference_card

    return mcp
