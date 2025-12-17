"""
NexusAI Base Agent Implementation

Provides the foundational agent primitives following Google ADK patterns.
Agents are stateful, event-driven, and support context engineering.
"""

from __future__ import annotations

import asyncio
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any, Callable, TypeVar, Generic

from pydantic import BaseModel, Field


class EventType(str, Enum):
    """Types of events in the agent system"""
    USER = "user"
    AGENT = "agent"
    TOOL = "tool"
    CONTROL = "control"
    THOUGHT = "thought"
    UI = "ui"
    ERROR = "error"


class AgentStatus(str, Enum):
    """Agent execution status"""
    IDLE = "idle"
    RUNNING = "running"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentEvent(BaseModel):
    """
    Immutable event record for agent interactions.
    All agent activity is logged as events for observability and replay.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    event_type: EventType
    agent_id: str
    content: Any
    metadata: dict[str, Any] = Field(default_factory=dict)
    parent_id: str | None = None

    class Config:
        frozen = True


class AgentConfig(BaseModel):
    """Configuration for agent initialization"""
    name: str
    description: str = ""
    model: str = "claude-3-5-sonnet-20241022"
    temperature: float = 0.7
    max_tokens: int = 4096
    system_prompt: str | None = None
    tools: list[str] = Field(default_factory=list)
    timeout_seconds: float = 300.0
    retry_attempts: int = 3

    # Context settings
    max_context_tokens: int = 100000
    context_compaction_threshold: float = 0.8

    # A2UI settings
    enable_genui: bool = True
    allowed_ui_components: list[str] = Field(
        default_factory=lambda: ["Card", "Table", "Form", "Chart", "Code"]
    )


class AgentState(BaseModel):
    """
    Mutable state container for agent execution.
    Supports serialization for session persistence.
    """
    agent_id: str
    status: AgentStatus = AgentStatus.IDLE
    current_task: str | None = None
    variables: dict[str, Any] = Field(default_factory=dict)
    history: list[AgentEvent] = Field(default_factory=list)
    thought_trail: list[str] = Field(default_factory=list)
    ui_state: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def add_event(self, event: AgentEvent) -> None:
        """Append event to history and update timestamp"""
        self.history.append(event)
        self.updated_at = datetime.utcnow()

    def add_thought(self, thought: str) -> None:
        """Add to thought trail (separate from final response)"""
        self.thought_trail.append(thought)
        self.updated_at = datetime.utcnow()

    def get_variable(self, key: str, default: Any = None) -> Any:
        """Get state variable with optional default"""
        return self.variables.get(key, default)

    def set_variable(self, key: str, value: Any) -> None:
        """Set state variable"""
        self.variables[key] = value
        self.updated_at = datetime.utcnow()


T = TypeVar("T")


class AgentResult(BaseModel, Generic[T]):
    """Result container for agent execution"""
    success: bool
    output: T | None = None
    events: list[AgentEvent] = Field(default_factory=list)
    ui_output: dict[str, Any] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    duration_ms: float = 0.0


class BaseAgent(ABC):
    """
    Abstract base class for all NexusAI agents.

    Implements the core agent lifecycle:
    1. Initialize with config
    2. Process input through execute()
    3. Emit events and update state
    4. Return structured result

    DSPy Signature:
        Input: message, context, state
        Output: result, events, ui_output
    """

    def __init__(self, config: AgentConfig):
        self.config = config
        self.agent_id = f"{config.name}-{uuid.uuid4().hex[:8]}"
        self.state = AgentState(agent_id=self.agent_id)
        self._hooks: dict[str, list[Callable]] = {
            "pre_execute": [],
            "post_execute": [],
            "on_event": [],
            "on_error": [],
        }

    @property
    def name(self) -> str:
        return self.config.name

    @property
    def status(self) -> AgentStatus:
        return self.state.status

    def register_hook(self, event: str, callback: Callable) -> None:
        """Register lifecycle hook"""
        if event in self._hooks:
            self._hooks[event].append(callback)

    async def _run_hooks(self, event: str, *args: Any, **kwargs: Any) -> None:
        """Execute registered hooks"""
        for hook in self._hooks.get(event, []):
            if asyncio.iscoroutinefunction(hook):
                await hook(*args, **kwargs)
            else:
                hook(*args, **kwargs)

    def emit_event(
        self,
        event_type: EventType,
        content: Any,
        metadata: dict[str, Any] | None = None,
        parent_id: str | None = None,
    ) -> AgentEvent:
        """Create and record an event"""
        event = AgentEvent(
            event_type=event_type,
            agent_id=self.agent_id,
            content=content,
            metadata=metadata or {},
            parent_id=parent_id,
        )
        self.state.add_event(event)
        asyncio.create_task(self._run_hooks("on_event", event))
        return event

    def think(self, thought: str) -> None:
        """
        Record internal reasoning (Chain-of-Thought).
        Thoughts are separate from final output for observability.
        """
        self.state.add_thought(thought)
        self.emit_event(EventType.THOUGHT, thought)

    async def execute(
        self,
        message: str,
        context: dict[str, Any] | None = None,
    ) -> AgentResult:
        """
        Main execution entry point.

        Args:
            message: User input or task description
            context: Additional context (session data, artifacts, etc.)

        Returns:
            AgentResult with output, events, and optional UI
        """
        import time
        start_time = time.time()

        self.state.status = AgentStatus.RUNNING
        self.state.current_task = message

        try:
            # Pre-execution hooks
            await self._run_hooks("pre_execute", message, context)

            # Record input event
            self.emit_event(EventType.USER, message, {"context_keys": list((context or {}).keys())})

            # Core execution (implemented by subclasses)
            result = await self._execute_impl(message, context or {})

            # Record output event
            self.emit_event(
                EventType.AGENT,
                result.output,
                {"success": result.success, "has_ui": result.ui_output is not None},
            )

            self.state.status = AgentStatus.COMPLETED

            # Post-execution hooks
            await self._run_hooks("post_execute", result)

            result.duration_ms = (time.time() - start_time) * 1000
            return result

        except Exception as e:
            self.state.status = AgentStatus.FAILED
            self.state.error = str(e)

            error_event = self.emit_event(EventType.ERROR, str(e))
            await self._run_hooks("on_error", e)

            return AgentResult(
                success=False,
                error=str(e),
                events=[error_event],
                duration_ms=(time.time() - start_time) * 1000,
            )

    @abstractmethod
    async def _execute_impl(
        self,
        message: str,
        context: dict[str, Any],
    ) -> AgentResult:
        """
        Implementation-specific execution logic.
        Override in subclasses.
        """
        pass

    def get_state_snapshot(self) -> dict[str, Any]:
        """Export current state for persistence"""
        return self.state.model_dump()

    def restore_state(self, snapshot: dict[str, Any]) -> None:
        """Restore state from snapshot"""
        self.state = AgentState(**snapshot)

    def reset(self) -> None:
        """Reset agent to initial state"""
        self.state = AgentState(agent_id=self.agent_id)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name} status={self.status}>"
