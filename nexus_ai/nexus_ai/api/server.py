"""
NexusAI REST & WebSocket API Server

Implements the Interactions API:
- POST /v1/interactions - Start new interaction
- GET /v1/interactions/{id} - Poll status
- WS /v1/stream - Real-time streaming
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from nexus_ai.agents.base import BaseAgent
from nexus_ai.protocol.interactions import InteractionsAPI, InteractionStatus


class NexusAPIConfig(BaseModel):
    """API configuration"""
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: list[str] = Field(default_factory=lambda: ["*"])
    api_key: str | None = None
    enable_docs: bool = True


class InteractionRequest(BaseModel):
    """Request body for creating an interaction"""
    message: str
    agent_id: str
    context: dict[str, Any] = Field(default_factory=dict)
    background: bool = False


class InteractionResponse(BaseModel):
    """Response from interaction endpoints"""
    id: str
    status: str
    result: Any = None
    ui_output: dict[str, Any] | None = None
    thoughts: list[str] = Field(default_factory=list)
    error: str | None = None


def create_app(
    config: NexusAPIConfig | None = None,
    interactions_api: InteractionsAPI | None = None,
) -> FastAPI:
    """
    Create FastAPI application for NexusAI.

    Args:
        config: API configuration
        interactions_api: InteractionsAPI instance (created if not provided)

    Returns:
        Configured FastAPI app
    """
    config = config or NexusAPIConfig()
    api = interactions_api or InteractionsAPI()

    app = FastAPI(
        title="NexusAI API",
        description="Multi-agent AI SDK with ADK patterns and A2UI protocol",
        version="1.0.0",
        docs_url="/docs" if config.enable_docs else None,
        redoc_url="/redoc" if config.enable_docs else None,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Store API instance in app state
    app.state.api = api
    app.state.config = config

    @app.get("/")
    async def root():
        """Health check and API info"""
        return {
            "name": "NexusAI",
            "version": "1.0.0",
            "status": "healthy",
            "agents": list(api._agents.keys()),
        }

    @app.get("/v1/agents")
    async def list_agents():
        """List registered agents"""
        agents = []
        for agent_id, agent in api._agents.items():
            agents.append({
                "id": agent_id,
                "name": agent.name if hasattr(agent, 'name') else agent_id,
                "status": agent.status.value if hasattr(agent, 'status') else "unknown",
            })
        return {"agents": agents}

    @app.post("/v1/agents/{agent_id}/register")
    async def register_agent(agent_id: str, config_data: dict[str, Any]):
        """
        Dynamically register an agent.

        This is a simplified endpoint - in production, agents would be
        configured via files or a management interface.
        """
        from nexus_ai.agents.llm import LlmAgent
        from nexus_ai.agents.base import AgentConfig

        agent_config = AgentConfig(
            name=config_data.get("name", agent_id),
            description=config_data.get("description", ""),
            model=config_data.get("model", "claude-3-5-sonnet-20241022"),
        )

        agent = LlmAgent(agent_config)
        api.register_agent(agent_id, agent)

        return {"message": f"Agent {agent_id} registered", "agent_id": agent_id}

    @app.post("/v1/interactions", response_model=InteractionResponse)
    async def create_interaction(request: InteractionRequest):
        """
        Start a new interaction with an agent.

        If background=true, returns immediately with status=pending.
        Poll GET /v1/interactions/{id} for completion.
        """
        try:
            interaction = await api.start_interaction(
                agent_id=request.agent_id,
                message=request.message,
                context=request.context,
                background=request.background,
            )

            return InteractionResponse(
                id=interaction.id,
                status=interaction.status.value,
                result=interaction.result,
                ui_output=interaction.ui_output,
                thoughts=interaction.thoughts,
                error=interaction.error,
            )
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/v1/interactions/{interaction_id}", response_model=InteractionResponse)
    async def get_interaction(interaction_id: str):
        """Get interaction status and result"""
        interaction = await api.get_interaction(interaction_id)

        if not interaction:
            raise HTTPException(status_code=404, detail="Interaction not found")

        return InteractionResponse(
            id=interaction.id,
            status=interaction.status.value,
            result=interaction.result,
            ui_output=interaction.ui_output,
            thoughts=interaction.thoughts,
            error=interaction.error,
        )

    @app.delete("/v1/interactions/{interaction_id}")
    async def cancel_interaction(interaction_id: str):
        """Cancel a running interaction"""
        success = await api.cancel_interaction(interaction_id)

        if not success:
            raise HTTPException(
                status_code=400,
                detail="Could not cancel interaction (not found or not running)"
            )

        return {"message": "Interaction cancelled", "id": interaction_id}

    @app.websocket("/v1/stream")
    async def websocket_stream(websocket: WebSocket):
        """
        WebSocket endpoint for real-time streaming.

        Protocol:
        1. Client connects
        2. Client sends: {"agent_id": "...", "message": "...", "context": {...}}
        3. Server streams: {"type": "token|thought|ui|control", "content": ...}
        4. Server sends: {"type": "control", "content": {"action": "complete"}}
        """
        await websocket.accept()

        try:
            # Receive request
            data = await websocket.receive_text()
            request = json.loads(data)

            agent_id = request.get("agent_id")
            message = request.get("message", "")
            context = request.get("context", {})

            if not agent_id:
                await websocket.send_json({
                    "type": "error",
                    "content": "agent_id is required"
                })
                return

            # Stream response
            async for chunk in api.stream_interaction(agent_id, message, context):
                await websocket.send_json({
                    "type": chunk.type,
                    "content": chunk.content,
                    "timestamp": chunk.timestamp.isoformat(),
                })

        except WebSocketDisconnect:
            pass
        except json.JSONDecodeError:
            await websocket.send_json({
                "type": "error",
                "content": "Invalid JSON"
            })
        except Exception as e:
            await websocket.send_json({
                "type": "error",
                "content": str(e)
            })
        finally:
            try:
                await websocket.close()
            except Exception:
                pass

    return app


def run_server(
    config: NexusAPIConfig | None = None,
    agents: dict[str, BaseAgent] | None = None,
):
    """
    Run the NexusAI API server.

    Args:
        config: Server configuration
        agents: Pre-registered agents
    """
    import uvicorn

    config = config or NexusAPIConfig()
    api = InteractionsAPI()

    # Register provided agents
    if agents:
        for agent_id, agent in agents.items():
            api.register_agent(agent_id, agent)

    app = create_app(config, api)

    uvicorn.run(
        app,
        host=config.host,
        port=config.port,
    )
