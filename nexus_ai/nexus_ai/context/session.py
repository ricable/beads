"""
NexusAI Session Management

Implements durable, project-scoped session storage with:
- Append-only event log
- State persistence (SQLite/JSONL)
- Resume functionality
- Configurable retention policies
"""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, AsyncIterator

from pydantic import BaseModel, Field


class SessionEventType(str, Enum):
    """Types of session events"""
    USER = "user"
    AGENT = "agent"
    TOOL = "tool"
    CONTROL = "control"
    SYSTEM = "system"
    CHECKPOINT = "checkpoint"


class SessionEvent(BaseModel):
    """
    Immutable event in the session log.
    Sessions are append-only for auditability and replay.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    event_type: SessionEventType
    agent_id: str | None = None
    content: Any
    metadata: dict[str, Any] = Field(default_factory=dict)
    token_count: int = 0

    class Config:
        frozen = True

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type.value,
            "agent_id": self.agent_id,
            "content": self.content,
            "metadata": self.metadata,
            "token_count": self.token_count,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SessionEvent:
        """Create from dictionary"""
        return cls(
            id=data["id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            event_type=SessionEventType(data["event_type"]),
            agent_id=data.get("agent_id"),
            content=data["content"],
            metadata=data.get("metadata", {}),
            token_count=data.get("token_count", 0),
        )


class RetentionPolicy(BaseModel):
    """Configuration for event retention"""
    max_events: int | None = 1000
    max_age_hours: int | None = 168  # 1 week
    compact_after_events: int = 100
    keep_checkpoints: bool = True


class SessionConfig(BaseModel):
    """Session configuration"""
    project_id: str
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    storage_path: Path = Field(default_factory=lambda: Path(".nexus/sessions"))
    retention: RetentionPolicy = Field(default_factory=RetentionPolicy)
    auto_checkpoint: bool = True
    checkpoint_interval: int = 50  # Events between checkpoints


class SessionState(BaseModel):
    """Serializable session state for persistence"""
    session_id: str
    project_id: str
    created_at: datetime
    updated_at: datetime
    variables: dict[str, Any] = Field(default_factory=dict)
    agent_states: dict[str, dict[str, Any]] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    event_count: int = 0
    total_tokens: int = 0


class Session:
    """
    Durable session manager implementing the Context Engineering tiered model.

    Tiers:
    - Working Context: Ephemeral, recomputed for each LLM call
    - Session: Durable, append-only event log (this class)
    - Memory: Long-term vector-searchable store (see memory.py)
    - Artifacts: Large blobs loaded on-demand (see artifacts.py)

    Features:
    - Project-scoped persistence
    - Resume functionality
    - Token counting and compaction
    - Retention policies
    """

    def __init__(self, config: SessionConfig):
        self.config = config
        self._events: list[SessionEvent] = []
        self._state = SessionState(
            session_id=config.session_id,
            project_id=config.project_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        self._lock = asyncio.Lock()
        self._initialized = False

    @property
    def session_id(self) -> str:
        return self.config.session_id

    @property
    def project_id(self) -> str:
        return self.config.project_id

    @property
    def events(self) -> list[SessionEvent]:
        return self._events.copy()

    @property
    def event_count(self) -> int:
        return len(self._events)

    @property
    def total_tokens(self) -> int:
        return sum(e.token_count for e in self._events)

    async def initialize(self) -> None:
        """Initialize session storage"""
        if self._initialized:
            return

        # Ensure storage directory exists
        storage_dir = self.config.storage_path / self.config.project_id
        storage_dir.mkdir(parents=True, exist_ok=True)

        # Try to load existing session
        session_file = storage_dir / f"{self.config.session_id}.jsonl"
        state_file = storage_dir / f"{self.config.session_id}.state.json"

        if session_file.exists():
            await self._load_events(session_file)

        if state_file.exists():
            await self._load_state(state_file)

        self._initialized = True

    async def _load_events(self, path: Path) -> None:
        """Load events from JSONL file"""
        async with self._lock:
            with open(path, "r") as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        self._events.append(SessionEvent.from_dict(data))

    async def _load_state(self, path: Path) -> None:
        """Load state from JSON file"""
        with open(path, "r") as f:
            data = json.load(f)
            self._state = SessionState(**data)

    async def _save_event(self, event: SessionEvent) -> None:
        """Append event to JSONL file"""
        storage_dir = self.config.storage_path / self.config.project_id
        session_file = storage_dir / f"{self.config.session_id}.jsonl"

        with open(session_file, "a") as f:
            f.write(json.dumps(event.to_dict()) + "\n")

    async def _save_state(self) -> None:
        """Save state to JSON file"""
        storage_dir = self.config.storage_path / self.config.project_id
        state_file = storage_dir / f"{self.config.session_id}.state.json"

        self._state.updated_at = datetime.utcnow()
        self._state.event_count = len(self._events)
        self._state.total_tokens = self.total_tokens

        with open(state_file, "w") as f:
            json.dump(self._state.model_dump(mode="json"), f, indent=2, default=str)

    async def append(
        self,
        event_type: SessionEventType,
        content: Any,
        agent_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        token_count: int = 0,
    ) -> SessionEvent:
        """
        Append an event to the session log.

        Args:
            event_type: Type of event
            content: Event content (any JSON-serializable value)
            agent_id: Optional agent that generated the event
            metadata: Additional metadata
            token_count: Estimated token count for context management

        Returns:
            The created SessionEvent
        """
        await self.initialize()

        event = SessionEvent(
            event_type=event_type,
            agent_id=agent_id,
            content=content,
            metadata=metadata or {},
            token_count=token_count,
        )

        async with self._lock:
            self._events.append(event)
            await self._save_event(event)

            # Auto-checkpoint if configured
            if (
                self.config.auto_checkpoint
                and len(self._events) % self.config.checkpoint_interval == 0
            ):
                await self._create_checkpoint()

            # Apply retention policy
            await self._apply_retention()

        return event

    async def _create_checkpoint(self) -> None:
        """Create a checkpoint event with summary"""
        # Summarize recent events
        recent_events = self._events[-self.config.checkpoint_interval:]
        summary = {
            "event_count": len(recent_events),
            "event_types": list(set(e.event_type.value for e in recent_events)),
            "agents": list(set(e.agent_id for e in recent_events if e.agent_id)),
            "token_sum": sum(e.token_count for e in recent_events),
        }

        checkpoint = SessionEvent(
            event_type=SessionEventType.CHECKPOINT,
            content=summary,
            metadata={"checkpoint_index": len(self._events)},
        )

        self._events.append(checkpoint)
        await self._save_event(checkpoint)
        await self._save_state()

    async def _apply_retention(self) -> None:
        """Apply retention policy to events"""
        policy = self.config.retention

        # Check max events
        if policy.max_events and len(self._events) > policy.max_events:
            # Keep checkpoints and recent events
            checkpoints = [e for e in self._events if e.event_type == SessionEventType.CHECKPOINT]
            recent = self._events[-policy.max_events:]

            if policy.keep_checkpoints:
                self._events = list(set(checkpoints + recent))
            else:
                self._events = recent

        # Check max age
        if policy.max_age_hours:
            cutoff = datetime.utcnow() - timedelta(hours=policy.max_age_hours)
            self._events = [
                e for e in self._events
                if e.timestamp > cutoff
                or (policy.keep_checkpoints and e.event_type == SessionEventType.CHECKPOINT)
            ]

    def get_variable(self, key: str, default: Any = None) -> Any:
        """Get a session variable"""
        return self._state.variables.get(key, default)

    def set_variable(self, key: str, value: Any) -> None:
        """Set a session variable"""
        self._state.variables[key] = value

    def save_agent_state(self, agent_id: str, state: dict[str, Any]) -> None:
        """Save agent state for resume"""
        self._state.agent_states[agent_id] = state

    def get_agent_state(self, agent_id: str) -> dict[str, Any] | None:
        """Get saved agent state"""
        return self._state.agent_states.get(agent_id)

    async def get_context(
        self,
        max_tokens: int | None = None,
        include_types: list[SessionEventType] | None = None,
    ) -> dict[str, Any]:
        """
        Build working context for LLM call.

        Args:
            max_tokens: Maximum tokens to include
            include_types: Event types to include (default: all)

        Returns:
            Context dictionary with history and variables
        """
        await self.initialize()

        events = self._events
        if include_types:
            events = [e for e in events if e.event_type in include_types]

        # Respect token limit
        if max_tokens:
            selected_events = []
            total = 0
            for event in reversed(events):
                if total + event.token_count <= max_tokens:
                    selected_events.insert(0, event)
                    total += event.token_count
                else:
                    break
            events = selected_events

        return {
            "session_id": self.session_id,
            "project_id": self.project_id,
            "history": [e.to_dict() for e in events],
            "variables": self._state.variables.copy(),
            "agent_states": self._state.agent_states.copy(),
            "metadata": self._state.metadata.copy(),
        }

    async def iter_events(
        self,
        event_type: SessionEventType | None = None,
        agent_id: str | None = None,
    ) -> AsyncIterator[SessionEvent]:
        """Iterate over events with optional filtering"""
        await self.initialize()

        for event in self._events:
            if event_type and event.event_type != event_type:
                continue
            if agent_id and event.agent_id != agent_id:
                continue
            yield event

    async def resume(self) -> dict[str, Any]:
        """
        Resume session from last checkpoint.

        Returns:
            Context for resuming agents
        """
        await self.initialize()

        # Find last checkpoint
        checkpoints = [
            e for e in self._events
            if e.event_type == SessionEventType.CHECKPOINT
        ]

        resume_context = await self.get_context()
        resume_context["resumed_from_checkpoint"] = bool(checkpoints)

        if checkpoints:
            last_checkpoint = checkpoints[-1]
            resume_context["checkpoint"] = last_checkpoint.to_dict()

        return resume_context

    async def close(self) -> None:
        """Close session and save final state"""
        await self._save_state()

    @classmethod
    async def create(
        cls,
        project_id: str,
        session_id: str | None = None,
        storage_path: Path | str | None = None,
    ) -> Session:
        """Factory method to create and initialize a session"""
        config = SessionConfig(
            project_id=project_id,
            session_id=session_id or str(uuid.uuid4()),
            storage_path=Path(storage_path) if storage_path else Path(".nexus/sessions"),
        )
        session = cls(config)
        await session.initialize()
        return session

    @classmethod
    async def load(
        cls,
        project_id: str,
        session_id: str,
        storage_path: Path | str | None = None,
    ) -> Session:
        """Load an existing session"""
        return await cls.create(project_id, session_id, storage_path)
