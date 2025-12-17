"""
NexusAI: Next-Generation Multi-Agent AI SDK

A unified framework for building stateful, context-aware agents
with generative UI capabilities.
"""

__version__ = "1.0.0"

from nexus_ai.agents.base import BaseAgent, AgentConfig, AgentState
from nexus_ai.agents.llm import LlmAgent
from nexus_ai.agents.workflow import (
    WorkflowAgent,
    SequentialAgent,
    ParallelAgent,
    LoopAgent,
    CoordinatorAgent,
)
from nexus_ai.context.session import Session, SessionConfig
from nexus_ai.context.memory import Memory, MemoryStore
from nexus_ai.protocol.a2ui import A2UIRenderer, UIComponent
from nexus_ai.protocol.interactions import InteractionsAPI

__all__ = [
    # Agents
    "BaseAgent",
    "AgentConfig",
    "AgentState",
    "LlmAgent",
    "WorkflowAgent",
    "SequentialAgent",
    "ParallelAgent",
    "LoopAgent",
    "CoordinatorAgent",
    # Context
    "Session",
    "SessionConfig",
    "Memory",
    "MemoryStore",
    # Protocol
    "A2UIRenderer",
    "UIComponent",
    "InteractionsAPI",
]
