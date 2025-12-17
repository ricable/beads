"""
NexusAI Memory System

Long-term, vector-searchable knowledge store for:
- User preferences
- Historical facts
- Learned patterns
- Cross-session knowledge

Implements semantic search for efficient context retrieval.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
from pydantic import BaseModel, Field


class MemoryEntry(BaseModel):
    """A single memory entry with embedding support"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    content: str
    embedding: list[float] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    category: str = "general"
    importance: float = 0.5  # 0-1, higher = more important
    created_at: datetime = Field(default_factory=datetime.utcnow)
    accessed_at: datetime = Field(default_factory=datetime.utcnow)
    access_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "embedding": self.embedding,
            "metadata": self.metadata,
            "category": self.category,
            "importance": self.importance,
            "created_at": self.created_at.isoformat(),
            "accessed_at": self.accessed_at.isoformat(),
            "access_count": self.access_count,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MemoryEntry:
        return cls(
            id=data["id"],
            content=data["content"],
            embedding=data.get("embedding"),
            metadata=data.get("metadata", {}),
            category=data.get("category", "general"),
            importance=data.get("importance", 0.5),
            created_at=datetime.fromisoformat(data["created_at"]),
            accessed_at=datetime.fromisoformat(data["accessed_at"]),
            access_count=data.get("access_count", 0),
        )


class MemorySearchResult(BaseModel):
    """Result from memory search"""
    entry: MemoryEntry
    score: float
    relevance_explanation: str | None = None


class EmbeddingProvider:
    """
    Abstract embedding provider.
    Replace with actual implementation (OpenAI, Cohere, local model, etc.)
    """

    def __init__(self, dimension: int = 384):
        self.dimension = dimension

    async def embed(self, text: str) -> list[float]:
        """Generate embedding for text"""
        # Mock implementation - returns deterministic pseudo-embedding
        # based on text hash for testing consistency
        import hashlib
        hash_bytes = hashlib.sha256(text.encode()).digest()

        # Create reproducible embedding from hash
        np.random.seed(int.from_bytes(hash_bytes[:4], 'big'))
        embedding = np.random.randn(self.dimension).astype(float)
        # Normalize
        embedding = embedding / np.linalg.norm(embedding)
        return embedding.tolist()

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts"""
        return [await self.embed(text) for text in texts]


class MemoryStore:
    """
    Vector-searchable memory storage.

    Features:
    - Semantic search via cosine similarity
    - Category-based filtering
    - Importance-weighted retrieval
    - Automatic embedding generation
    """

    def __init__(
        self,
        storage_path: Path | str = ".nexus/memory",
        embedding_provider: EmbeddingProvider | None = None,
    ):
        self.storage_path = Path(storage_path)
        self.embedding_provider = embedding_provider or EmbeddingProvider()
        self._memories: dict[str, MemoryEntry] = {}
        self._lock = asyncio.Lock()
        self._initialized = False

    async def initialize(self) -> None:
        """Load existing memories from storage"""
        if self._initialized:
            return

        self.storage_path.mkdir(parents=True, exist_ok=True)
        memory_file = self.storage_path / "memories.jsonl"

        if memory_file.exists():
            async with self._lock:
                with open(memory_file, "r") as f:
                    for line in f:
                        if line.strip():
                            data = json.loads(line)
                            entry = MemoryEntry.from_dict(data)
                            self._memories[entry.id] = entry

        self._initialized = True

    async def _save_memory(self, entry: MemoryEntry) -> None:
        """Append memory to storage"""
        memory_file = self.storage_path / "memories.jsonl"
        with open(memory_file, "a") as f:
            f.write(json.dumps(entry.to_dict()) + "\n")

    async def _rewrite_storage(self) -> None:
        """Rewrite entire memory file (for deletions/updates)"""
        memory_file = self.storage_path / "memories.jsonl"
        with open(memory_file, "w") as f:
            for entry in self._memories.values():
                f.write(json.dumps(entry.to_dict()) + "\n")

    async def store(
        self,
        content: str,
        category: str = "general",
        importance: float = 0.5,
        metadata: dict[str, Any] | None = None,
        generate_embedding: bool = True,
    ) -> MemoryEntry:
        """
        Store a new memory entry.

        Args:
            content: The memory content
            category: Category for filtering
            importance: Importance score (0-1)
            metadata: Additional metadata
            generate_embedding: Whether to generate embedding

        Returns:
            The created MemoryEntry
        """
        await self.initialize()

        embedding = None
        if generate_embedding:
            embedding = await self.embedding_provider.embed(content)

        entry = MemoryEntry(
            content=content,
            embedding=embedding,
            category=category,
            importance=importance,
            metadata=metadata or {},
        )

        async with self._lock:
            self._memories[entry.id] = entry
            await self._save_memory(entry)

        return entry

    async def search(
        self,
        query: str,
        limit: int = 5,
        category: str | None = None,
        min_importance: float = 0.0,
        min_score: float = 0.5,
    ) -> list[MemorySearchResult]:
        """
        Search memories using semantic similarity.

        Args:
            query: Search query
            limit: Maximum results to return
            category: Optional category filter
            min_importance: Minimum importance threshold
            min_score: Minimum similarity score threshold

        Returns:
            List of MemorySearchResult sorted by relevance
        """
        await self.initialize()

        if not self._memories:
            return []

        # Generate query embedding
        query_embedding = await self.embedding_provider.embed(query)
        query_vec = np.array(query_embedding)

        results: list[MemorySearchResult] = []

        for entry in self._memories.values():
            # Apply filters
            if category and entry.category != category:
                continue
            if entry.importance < min_importance:
                continue
            if not entry.embedding:
                continue

            # Compute cosine similarity
            entry_vec = np.array(entry.embedding)
            similarity = float(np.dot(query_vec, entry_vec))

            # Weight by importance
            weighted_score = similarity * (0.7 + 0.3 * entry.importance)

            if weighted_score >= min_score:
                results.append(MemorySearchResult(
                    entry=entry,
                    score=weighted_score,
                ))

        # Sort by score descending
        results.sort(key=lambda x: x.score, reverse=True)

        # Update access metadata for returned results
        for result in results[:limit]:
            entry = self._memories[result.entry.id]
            entry.accessed_at = datetime.utcnow()
            entry.access_count += 1

        return results[:limit]

    async def get(self, memory_id: str) -> MemoryEntry | None:
        """Get a memory by ID"""
        await self.initialize()
        return self._memories.get(memory_id)

    async def delete(self, memory_id: str) -> bool:
        """Delete a memory by ID"""
        await self.initialize()

        async with self._lock:
            if memory_id in self._memories:
                del self._memories[memory_id]
                await self._rewrite_storage()
                return True
        return False

    async def list_categories(self) -> list[str]:
        """List all memory categories"""
        await self.initialize()
        return list(set(e.category for e in self._memories.values()))

    async def get_by_category(
        self,
        category: str,
        limit: int | None = None,
    ) -> list[MemoryEntry]:
        """Get memories by category"""
        await self.initialize()

        entries = [
            e for e in self._memories.values()
            if e.category == category
        ]
        entries.sort(key=lambda x: x.importance, reverse=True)

        if limit:
            entries = entries[:limit]
        return entries

    async def compact(self, keep_top_n: int = 1000) -> int:
        """
        Compact memory by removing least important/accessed entries.

        Returns:
            Number of entries removed
        """
        await self.initialize()

        if len(self._memories) <= keep_top_n:
            return 0

        # Score entries by importance and recency
        scored: list[tuple[str, float]] = []
        now = datetime.utcnow()

        for entry in self._memories.values():
            age_days = (now - entry.accessed_at).days
            recency_score = max(0, 1 - age_days / 365)  # Decay over a year
            access_score = min(1, entry.access_count / 100)
            total_score = (
                entry.importance * 0.4 +
                recency_score * 0.3 +
                access_score * 0.3
            )
            scored.append((entry.id, total_score))

        # Sort and keep top N
        scored.sort(key=lambda x: x[1], reverse=True)
        keep_ids = set(id for id, _ in scored[:keep_top_n])
        remove_count = len(self._memories) - len(keep_ids)

        async with self._lock:
            self._memories = {
                id: entry
                for id, entry in self._memories.items()
                if id in keep_ids
            }
            await self._rewrite_storage()

        return remove_count

    @property
    def size(self) -> int:
        """Number of memories stored"""
        return len(self._memories)


class Memory:
    """
    High-level memory interface for agents.

    Provides convenient methods for:
    - Storing observations and facts
    - Retrieving relevant context
    - Managing user preferences
    """

    def __init__(
        self,
        project_id: str,
        storage_path: Path | str = ".nexus/memory",
    ):
        self.project_id = project_id
        self.store = MemoryStore(
            storage_path=Path(storage_path) / project_id
        )

    async def remember(
        self,
        content: str,
        category: str = "observation",
        importance: float = 0.5,
        metadata: dict[str, Any] | None = None,
    ) -> MemoryEntry:
        """Store something to remember"""
        return await self.store.store(
            content=content,
            category=category,
            importance=importance,
            metadata=metadata,
        )

    async def recall(
        self,
        query: str,
        limit: int = 5,
        category: str | None = None,
    ) -> list[str]:
        """Recall relevant memories as strings"""
        results = await self.store.search(
            query=query,
            limit=limit,
            category=category,
        )
        return [r.entry.content for r in results]

    async def get_preferences(self) -> dict[str, Any]:
        """Get stored user preferences"""
        entries = await self.store.get_by_category("preference")
        prefs = {}
        for entry in entries:
            prefs.update(entry.metadata)
        return prefs

    async def set_preference(self, key: str, value: Any) -> None:
        """Store a user preference"""
        await self.store.store(
            content=f"User preference: {key} = {value}",
            category="preference",
            importance=0.8,
            metadata={key: value},
        )

    async def get_facts(self, topic: str, limit: int = 10) -> list[str]:
        """Get facts related to a topic"""
        results = await self.store.search(
            query=topic,
            limit=limit,
            category="fact",
        )
        return [r.entry.content for r in results]

    async def store_fact(
        self,
        fact: str,
        importance: float = 0.6,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Store a fact for future retrieval"""
        await self.store.store(
            content=fact,
            category="fact",
            importance=importance,
            metadata=metadata,
        )
