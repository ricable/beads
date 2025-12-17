"""
NexusAI Interactions API

Implements the transport layer for agent interactions:
- REST API for starting interactions
- WebSocket for real-time streaming
- Background execution support
- Thought trail separation
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, AsyncIterator

from pydantic import BaseModel, Field


class InteractionStatus(str, Enum):
    """Status of an interaction"""
    PENDING = "pending"
    RUNNING = "running"
    STREAMING = "streaming"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StreamChunk(BaseModel):
    """A chunk in the streaming response"""
    type: str  # token, thought, ui, control, error
    content: Any
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)


class Interaction(BaseModel):
    """
    Represents a single interaction request/response cycle.

    Interactions support:
    - Synchronous execution
    - Background execution with polling
    - Real-time streaming via WebSocket
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str
    message: str
    context: dict[str, Any] = Field(default_factory=dict)
    status: InteractionStatus = InteractionStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    result: Any = None
    ui_output: dict[str, Any] | None = None
    thoughts: list[str] = Field(default_factory=list)
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_response(self) -> dict[str, Any]:
        """Convert to API response format"""
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "result": self.result,
            "ui_output": self.ui_output,
            "thoughts": self.thoughts,
            "error": self.error,
            "metadata": self.metadata,
        }


class InteractionsStore:
    """In-memory store for interactions"""

    def __init__(self):
        self._interactions: dict[str, Interaction] = {}
        self._lock = asyncio.Lock()

    async def create(
        self,
        agent_id: str,
        message: str,
        context: dict[str, Any] | None = None,
    ) -> Interaction:
        """Create a new interaction"""
        interaction = Interaction(
            agent_id=agent_id,
            message=message,
            context=context or {},
        )
        async with self._lock:
            self._interactions[interaction.id] = interaction
        return interaction

    async def get(self, interaction_id: str) -> Interaction | None:
        """Get interaction by ID"""
        return self._interactions.get(interaction_id)

    async def update(
        self,
        interaction_id: str,
        **updates: Any,
    ) -> Interaction | None:
        """Update interaction fields"""
        async with self._lock:
            if interaction_id not in self._interactions:
                return None
            interaction = self._interactions[interaction_id]
            for key, value in updates.items():
                if hasattr(interaction, key):
                    setattr(interaction, key, value)
            return interaction

    async def delete(self, interaction_id: str) -> bool:
        """Delete an interaction"""
        async with self._lock:
            if interaction_id in self._interactions:
                del self._interactions[interaction_id]
                return True
        return False

    async def list_by_agent(self, agent_id: str) -> list[Interaction]:
        """List interactions for an agent"""
        return [
            i for i in self._interactions.values()
            if i.agent_id == agent_id
        ]


class InteractionsAPI:
    """
    Main API interface for agent interactions.

    Provides:
    - Synchronous execution
    - Background execution
    - Streaming execution
    """

    def __init__(self):
        self.store = InteractionsStore()
        self._agents: dict[str, Any] = {}  # agent_id -> agent instance
        self._stream_queues: dict[str, asyncio.Queue] = {}

    def register_agent(self, agent_id: str, agent: Any) -> None:
        """Register an agent for interactions"""
        self._agents[agent_id] = agent

    def unregister_agent(self, agent_id: str) -> None:
        """Unregister an agent"""
        self._agents.pop(agent_id, None)

    async def start_interaction(
        self,
        agent_id: str,
        message: str,
        context: dict[str, Any] | None = None,
        background: bool = False,
    ) -> Interaction:
        """
        Start a new interaction.

        Args:
            agent_id: Target agent ID
            message: User message
            context: Additional context
            background: If True, execute in background

        Returns:
            Interaction object
        """
        if agent_id not in self._agents:
            raise ValueError(f"Agent not found: {agent_id}")

        interaction = await self.store.create(agent_id, message, context)

        if background:
            # Start background execution
            asyncio.create_task(self._execute_background(interaction))
        else:
            # Execute synchronously
            await self._execute(interaction)

        return interaction

    async def _execute(self, interaction: Interaction) -> None:
        """Execute interaction synchronously"""
        agent = self._agents.get(interaction.agent_id)
        if not agent:
            await self.store.update(
                interaction.id,
                status=InteractionStatus.FAILED,
                error="Agent not found",
            )
            return

        await self.store.update(
            interaction.id,
            status=InteractionStatus.RUNNING,
            started_at=datetime.utcnow(),
        )

        try:
            result = await agent.execute(interaction.message, interaction.context)

            await self.store.update(
                interaction.id,
                status=InteractionStatus.COMPLETED,
                completed_at=datetime.utcnow(),
                result=result.output,
                ui_output=result.ui_output,
                thoughts=agent.state.thought_trail if hasattr(agent, 'state') else [],
            )
        except Exception as e:
            await self.store.update(
                interaction.id,
                status=InteractionStatus.FAILED,
                completed_at=datetime.utcnow(),
                error=str(e),
            )

    async def _execute_background(self, interaction: Interaction) -> None:
        """Execute interaction in background"""
        await self._execute(interaction)

    async def get_interaction(self, interaction_id: str) -> Interaction | None:
        """Get interaction status"""
        return await self.store.get(interaction_id)

    async def cancel_interaction(self, interaction_id: str) -> bool:
        """Cancel a running interaction"""
        interaction = await self.store.get(interaction_id)
        if not interaction:
            return False

        if interaction.status == InteractionStatus.RUNNING:
            await self.store.update(
                interaction_id,
                status=InteractionStatus.CANCELLED,
                completed_at=datetime.utcnow(),
            )
            return True
        return False

    async def stream_interaction(
        self,
        agent_id: str,
        message: str,
        context: dict[str, Any] | None = None,
    ) -> AsyncIterator[StreamChunk]:
        """
        Stream interaction results in real-time.

        Yields:
            StreamChunk objects as they become available
        """
        if agent_id not in self._agents:
            yield StreamChunk(type="error", content="Agent not found")
            return

        interaction = await self.store.create(agent_id, message, context)

        # Create stream queue
        queue: asyncio.Queue[StreamChunk | None] = asyncio.Queue()
        self._stream_queues[interaction.id] = queue

        # Start execution in background
        asyncio.create_task(self._execute_streaming(interaction, queue))

        # Yield chunks as they arrive
        try:
            while True:
                chunk = await queue.get()
                if chunk is None:
                    break
                yield chunk
        finally:
            self._stream_queues.pop(interaction.id, None)

    async def _execute_streaming(
        self,
        interaction: Interaction,
        queue: asyncio.Queue,
    ) -> None:
        """Execute with streaming output"""
        agent = self._agents.get(interaction.agent_id)
        if not agent:
            await queue.put(StreamChunk(type="error", content="Agent not found"))
            await queue.put(None)
            return

        await self.store.update(
            interaction.id,
            status=InteractionStatus.STREAMING,
            started_at=datetime.utcnow(),
        )

        # Emit start chunk
        await queue.put(StreamChunk(
            type="control",
            content={"action": "start", "interaction_id": interaction.id},
        ))

        try:
            # Hook into agent's thought process
            if hasattr(agent, '_hooks'):
                async def thought_hook(thought: str):
                    await queue.put(StreamChunk(type="thought", content=thought))

                async def event_hook(event: Any):
                    if hasattr(event, 'event_type'):
                        await queue.put(StreamChunk(
                            type="event",
                            content={"type": event.event_type, "content": event.content},
                        ))

                agent.register_hook("on_event", event_hook)

            # Execute agent
            result = await agent.execute(interaction.message, interaction.context)

            # Emit result
            if result.output:
                # Simulate token streaming (in real impl, would come from LLM)
                for word in str(result.output).split():
                    await queue.put(StreamChunk(type="token", content=word + " "))
                    await asyncio.sleep(0.01)  # Simulate streaming delay

            # Emit UI if present
            if result.ui_output:
                await queue.put(StreamChunk(type="ui", content=result.ui_output))

            await self.store.update(
                interaction.id,
                status=InteractionStatus.COMPLETED,
                completed_at=datetime.utcnow(),
                result=result.output,
                ui_output=result.ui_output,
            )

            # Emit completion
            await queue.put(StreamChunk(
                type="control",
                content={"action": "complete", "success": True},
            ))

        except Exception as e:
            await self.store.update(
                interaction.id,
                status=InteractionStatus.FAILED,
                completed_at=datetime.utcnow(),
                error=str(e),
            )

            await queue.put(StreamChunk(type="error", content=str(e)))
            await queue.put(StreamChunk(
                type="control",
                content={"action": "complete", "success": False},
            ))

        finally:
            await queue.put(None)  # Signal end of stream
