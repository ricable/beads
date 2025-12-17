"""
NexusAI Context Processors

Transform and optimize context before LLM calls.
Implements context compaction strategies for token efficiency.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel


class ProcessedContext(BaseModel):
    """Result of context processing"""
    content: str
    original_tokens: int
    processed_tokens: int
    metadata: dict[str, Any] = {}


class ContextProcessor(ABC):
    """Base class for context processors"""

    @abstractmethod
    async def process(
        self,
        context: dict[str, Any],
        max_tokens: int | None = None,
    ) -> ProcessedContext:
        """
        Process context for LLM consumption.

        Args:
            context: Raw context dictionary
            max_tokens: Target token limit

        Returns:
            ProcessedContext with optimized content
        """
        pass


class CompactionProcessor(ContextProcessor):
    """
    Compacts context by removing redundant information.

    Strategies:
    - Remove duplicate messages
    - Truncate long tool outputs
    - Collapse sequential system messages
    """

    def __init__(
        self,
        dedup_window: int = 10,
        max_tool_output_chars: int = 2000,
        preserve_recent: int = 5,
    ):
        self.dedup_window = dedup_window
        self.max_tool_output_chars = max_tool_output_chars
        self.preserve_recent = preserve_recent

    async def process(
        self,
        context: dict[str, Any],
        max_tokens: int | None = None,
    ) -> ProcessedContext:
        history = context.get("history", [])
        original_tokens = self._estimate_tokens(history)

        # Process history
        processed_history = []
        seen_contents: set[str] = set()

        for i, event in enumerate(history):
            content = str(event.get("content", ""))

            # Always preserve recent events
            is_recent = i >= len(history) - self.preserve_recent

            # Dedup within window
            if not is_recent and i >= self.dedup_window:
                content_hash = hash(content[:200])
                if content_hash in seen_contents:
                    continue
                seen_contents.add(content_hash)

            # Truncate tool outputs
            if event.get("event_type") == "tool" and not is_recent:
                if len(content) > self.max_tool_output_chars:
                    content = content[:self.max_tool_output_chars] + "... [truncated]"
                    event = {**event, "content": content}

            processed_history.append(event)

        # Build output string
        output_parts = []

        # Add session info
        output_parts.append(f"Session: {context.get('session_id', 'unknown')}")
        output_parts.append(f"Project: {context.get('project_id', 'unknown')}")
        output_parts.append("")

        # Add variables if present
        variables = context.get("variables", {})
        if variables:
            output_parts.append("Session Variables:")
            for k, v in variables.items():
                output_parts.append(f"  {k}: {v}")
            output_parts.append("")

        # Add history
        output_parts.append("Conversation History:")
        for event in processed_history:
            event_type = event.get("event_type", "unknown")
            content = event.get("content", "")
            agent = event.get("agent_id", "")

            if event_type == "user":
                output_parts.append(f"USER: {content}")
            elif event_type == "agent":
                output_parts.append(f"AGENT ({agent}): {content}")
            elif event_type == "tool":
                output_parts.append(f"TOOL: {content[:500]}...")
            elif event_type == "thought":
                output_parts.append(f"THINKING: {content[:200]}...")

        output = "\n".join(output_parts)
        processed_tokens = self._estimate_tokens([{"content": output}])

        return ProcessedContext(
            content=output,
            original_tokens=original_tokens,
            processed_tokens=processed_tokens,
            metadata={
                "original_events": len(history),
                "processed_events": len(processed_history),
                "dedup_removed": len(history) - len(processed_history),
            },
        )

    def _estimate_tokens(self, items: list[dict[str, Any]]) -> int:
        """Rough token estimation (4 chars per token)"""
        total_chars = sum(len(str(item.get("content", ""))) for item in items)
        return total_chars // 4


class SummarizationProcessor(ContextProcessor):
    """
    Summarizes older context to save tokens.

    Uses a sliding window approach:
    - Recent events: kept verbatim
    - Older events: summarized into checkpoints
    """

    def __init__(
        self,
        recent_window: int = 20,
        summary_chunk_size: int = 50,
    ):
        self.recent_window = recent_window
        self.summary_chunk_size = summary_chunk_size

    async def process(
        self,
        context: dict[str, Any],
        max_tokens: int | None = None,
    ) -> ProcessedContext:
        history = context.get("history", [])
        original_tokens = self._estimate_tokens(history)

        if len(history) <= self.recent_window:
            # No summarization needed
            return ProcessedContext(
                content=self._format_history(history),
                original_tokens=original_tokens,
                processed_tokens=original_tokens,
            )

        # Split into old and recent
        old_events = history[:-self.recent_window]
        recent_events = history[-self.recent_window:]

        # Summarize old events in chunks
        summaries = []
        for i in range(0, len(old_events), self.summary_chunk_size):
            chunk = old_events[i:i + self.summary_chunk_size]
            summary = self._summarize_chunk(chunk)
            summaries.append(summary)

        # Build output
        output_parts = []

        if summaries:
            output_parts.append("=== Previous Context Summary ===")
            for i, summary in enumerate(summaries):
                output_parts.append(f"[Batch {i + 1}] {summary}")
            output_parts.append("")

        output_parts.append("=== Recent Conversation ===")
        output_parts.append(self._format_history(recent_events))

        output = "\n".join(output_parts)
        processed_tokens = len(output) // 4

        return ProcessedContext(
            content=output,
            original_tokens=original_tokens,
            processed_tokens=processed_tokens,
            metadata={
                "summarized_events": len(old_events),
                "recent_events": len(recent_events),
                "summary_chunks": len(summaries),
            },
        )

    def _summarize_chunk(self, events: list[dict[str, Any]]) -> str:
        """Create summary of event chunk"""
        # Simple extractive summary
        user_msgs = [e for e in events if e.get("event_type") == "user"]
        agent_msgs = [e for e in events if e.get("event_type") == "agent"]
        tool_calls = [e for e in events if e.get("event_type") == "tool"]

        parts = []
        if user_msgs:
            topics = [str(m.get("content", ""))[:50] for m in user_msgs[:3]]
            parts.append(f"User discussed: {'; '.join(topics)}")
        if agent_msgs:
            parts.append(f"Agent provided {len(agent_msgs)} responses")
        if tool_calls:
            tools = set(e.get("metadata", {}).get("tool", "unknown") for e in tool_calls)
            parts.append(f"Tools used: {', '.join(tools)}")

        return " | ".join(parts) if parts else "No significant events"

    def _format_history(self, events: list[dict[str, Any]]) -> str:
        """Format events as readable history"""
        lines = []
        for event in events:
            event_type = event.get("event_type", "unknown")
            content = str(event.get("content", ""))[:500]
            agent = event.get("agent_id", "")

            if event_type == "user":
                lines.append(f"USER: {content}")
            elif event_type == "agent":
                prefix = f"AGENT ({agent})" if agent else "AGENT"
                lines.append(f"{prefix}: {content}")
            elif event_type == "tool":
                lines.append(f"TOOL: {content[:200]}...")

        return "\n".join(lines)

    def _estimate_tokens(self, items: list[dict[str, Any]]) -> int:
        total_chars = sum(len(str(item.get("content", ""))) for item in items)
        return total_chars // 4


class PriorityProcessor(ContextProcessor):
    """
    Selects context based on relevance to current task.

    Prioritizes:
    - Recent user messages
    - Tool results relevant to current query
    - High-importance memories
    """

    def __init__(
        self,
        relevance_threshold: float = 0.5,
    ):
        self.relevance_threshold = relevance_threshold

    async def process(
        self,
        context: dict[str, Any],
        max_tokens: int | None = None,
    ) -> ProcessedContext:
        history = context.get("history", [])
        current_query = context.get("current_query", "")
        original_tokens = self._estimate_tokens(history)

        # Score events by relevance
        scored_events = []
        for i, event in enumerate(history):
            score = self._compute_relevance(event, current_query, i, len(history))
            if score >= self.relevance_threshold:
                scored_events.append((event, score))

        # Sort by score and position
        scored_events.sort(key=lambda x: x[1], reverse=True)

        # Select events within token budget
        selected = []
        token_count = 0
        target_tokens = max_tokens or 10000

        for event, score in scored_events:
            event_tokens = len(str(event.get("content", ""))) // 4
            if token_count + event_tokens <= target_tokens:
                selected.append(event)
                token_count += event_tokens

        # Sort selected back by timestamp
        selected.sort(key=lambda e: e.get("timestamp", ""))

        # Format output
        output = self._format_events(selected)

        return ProcessedContext(
            content=output,
            original_tokens=original_tokens,
            processed_tokens=token_count,
            metadata={
                "events_considered": len(history),
                "events_selected": len(selected),
                "relevance_threshold": self.relevance_threshold,
            },
        )

    def _compute_relevance(
        self,
        event: dict[str, Any],
        query: str,
        position: int,
        total: int,
    ) -> float:
        """Compute relevance score for an event"""
        score = 0.0

        # Recency bonus (0-0.3)
        recency = position / total if total > 0 else 1.0
        score += recency * 0.3

        # Type bonus
        event_type = event.get("event_type", "")
        type_scores = {
            "user": 0.3,
            "agent": 0.2,
            "tool": 0.25,
            "error": 0.15,
        }
        score += type_scores.get(event_type, 0.1)

        # Content relevance (simple keyword overlap)
        if query:
            content = str(event.get("content", "")).lower()
            query_words = set(query.lower().split())
            content_words = set(content.split())
            overlap = len(query_words & content_words)
            relevance = min(overlap / len(query_words), 1.0) if query_words else 0
            score += relevance * 0.4

        return min(score, 1.0)

    def _format_events(self, events: list[dict[str, Any]]) -> str:
        lines = []
        for event in events:
            event_type = event.get("event_type", "unknown")
            content = str(event.get("content", ""))
            lines.append(f"[{event_type.upper()}] {content}")
        return "\n".join(lines)

    def _estimate_tokens(self, items: list[dict[str, Any]]) -> int:
        total_chars = sum(len(str(item.get("content", ""))) for item in items)
        return total_chars // 4
