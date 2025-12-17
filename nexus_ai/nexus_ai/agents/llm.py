"""
NexusAI LLM Agent Implementation

Standard conversational agent with tool access and A2UI generation capabilities.
Supports multiple LLM providers through a unified interface.
"""

from __future__ import annotations

import json
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field

from nexus_ai.agents.base import (
    AgentConfig,
    AgentResult,
    BaseAgent,
    EventType,
)


class Message(BaseModel):
    """Chat message format"""
    role: str  # system, user, assistant, tool
    content: str
    name: str | None = None
    tool_call_id: str | None = None
    tool_calls: list[dict[str, Any]] | None = None


class ToolDefinition(BaseModel):
    """Tool schema for LLM function calling"""
    name: str
    description: str
    parameters: dict[str, Any] = Field(default_factory=dict)


class ToolResult(BaseModel):
    """Result from tool execution"""
    tool_call_id: str
    name: str
    result: Any
    error: str | None = None


@runtime_checkable
class LLMProvider(Protocol):
    """Protocol for LLM provider implementations"""

    async def complete(
        self,
        messages: list[Message],
        tools: list[ToolDefinition] | None = None,
        **kwargs: Any,
    ) -> Message:
        """Generate completion from messages"""
        ...


class MockLLMProvider:
    """
    Mock LLM provider for testing and development.
    Replace with actual provider (Anthropic, OpenAI, etc.) in production.
    """

    async def complete(
        self,
        messages: list[Message],
        tools: list[ToolDefinition] | None = None,
        **kwargs: Any,
    ) -> Message:
        # Extract the last user message
        user_msg = next(
            (m.content for m in reversed(messages) if m.role == "user"),
            "Hello"
        )

        # Simple mock response
        response_content = f"I understand you said: '{user_msg}'. How can I help you further?"

        return Message(role="assistant", content=response_content)


class LlmAgent(BaseAgent):
    """
    LLM-powered conversational agent.

    Features:
    - Multi-turn conversation with context management
    - Tool/function calling support
    - A2UI generation for rich responses
    - Thought trail separation for observability

    DSPy Signature:
        Input: message, conversation_history, tools
        Output: response, tool_calls, ui_output
    """

    def __init__(
        self,
        config: AgentConfig,
        provider: LLMProvider | None = None,
        tools: dict[str, Any] | None = None,
    ):
        super().__init__(config)
        self.provider = provider or MockLLMProvider()
        self.tools = tools or {}
        self._tool_definitions: list[ToolDefinition] = []

        # Register tools
        for name, tool in self.tools.items():
            self._register_tool(name, tool)

    def _register_tool(self, name: str, tool: Any) -> None:
        """Register a tool for function calling"""
        # Extract schema from tool (supports various formats)
        if hasattr(tool, "schema"):
            schema = tool.schema()
        elif isinstance(tool, dict):
            schema = tool
        else:
            schema = {
                "type": "object",
                "properties": {},
                "required": [],
            }

        self._tool_definitions.append(
            ToolDefinition(
                name=name,
                description=getattr(tool, "__doc__", f"Tool: {name}"),
                parameters=schema,
            )
        )

    def _build_messages(
        self,
        message: str,
        context: dict[str, Any],
    ) -> list[Message]:
        """Build message list for LLM call"""
        messages: list[Message] = []

        # System prompt
        system_prompt = self.config.system_prompt or self._default_system_prompt()
        messages.append(Message(role="system", content=system_prompt))

        # Include conversation history from context
        history = context.get("history", [])
        for event in history[-20:]:  # Last 20 events for context window management
            if event.get("event_type") == "user":
                messages.append(Message(role="user", content=str(event.get("content", ""))))
            elif event.get("event_type") == "agent":
                messages.append(Message(role="assistant", content=str(event.get("content", ""))))

        # Current message
        messages.append(Message(role="user", content=message))

        return messages

    def _default_system_prompt(self) -> str:
        """Generate default system prompt"""
        tool_names = [t.name for t in self._tool_definitions]

        prompt = f"""You are {self.config.name}, an intelligent AI assistant.

Your capabilities:
- Engage in helpful, accurate conversations
- Use available tools when appropriate: {tool_names or 'None'}
- Generate structured UI components when displaying data

Guidelines:
- Be concise but thorough
- Ask clarifying questions when needed
- Use tools to gather information before responding
- Format responses for clarity

When you need to display structured data, emit A2UI JSON components."""

        if self.config.description:
            prompt += f"\n\nSpecialization: {self.config.description}"

        return prompt

    async def _execute_tool(self, tool_name: str, arguments: dict[str, Any]) -> ToolResult:
        """Execute a tool and return result"""
        tool = self.tools.get(tool_name)

        if not tool:
            return ToolResult(
                tool_call_id=tool_name,
                name=tool_name,
                result=None,
                error=f"Tool '{tool_name}' not found",
            )

        try:
            if callable(tool):
                import asyncio
                if asyncio.iscoroutinefunction(tool):
                    result = await tool(**arguments)
                else:
                    result = tool(**arguments)
            else:
                result = f"Tool {tool_name} is not callable"

            self.emit_event(
                EventType.TOOL,
                {"tool": tool_name, "args": arguments, "result": result},
            )

            return ToolResult(
                tool_call_id=tool_name,
                name=tool_name,
                result=result,
            )
        except Exception as e:
            return ToolResult(
                tool_call_id=tool_name,
                name=tool_name,
                result=None,
                error=str(e),
            )

    def _extract_ui_output(self, content: str) -> tuple[str, dict[str, Any] | None]:
        """
        Extract A2UI JSON from response if present.
        Returns (cleaned_content, ui_output)
        """
        ui_output = None

        # Look for A2UI markers
        if "```a2ui" in content.lower() or "```json" in content:
            import re
            pattern = r"```(?:a2ui|json)\s*([\s\S]*?)```"
            matches = re.findall(pattern, content, re.IGNORECASE)

            for match in matches:
                try:
                    parsed = json.loads(match)
                    if isinstance(parsed, dict) and "component" in parsed:
                        ui_output = parsed
                        content = re.sub(pattern, "", content, flags=re.IGNORECASE)
                        break
                except json.JSONDecodeError:
                    continue

        return content.strip(), ui_output

    async def _execute_impl(
        self,
        message: str,
        context: dict[str, Any],
    ) -> AgentResult:
        """Execute LLM agent logic"""

        # Build messages
        messages = self._build_messages(message, context)

        # Think about the approach
        self.think(f"Processing user request: {message[:100]}...")
        self.think(f"Context keys available: {list(context.keys())}")

        # Call LLM
        tools = self._tool_definitions if self._tool_definitions else None
        response = await self.provider.complete(
            messages=messages,
            tools=tools,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
        )

        # Handle tool calls if present
        if response.tool_calls:
            self.think(f"LLM requested {len(response.tool_calls)} tool calls")

            tool_results = []
            for call in response.tool_calls:
                result = await self._execute_tool(
                    call.get("name", ""),
                    call.get("arguments", {}),
                )
                tool_results.append(result)

            # Add tool results to messages and re-call LLM
            for tr in tool_results:
                messages.append(
                    Message(
                        role="tool",
                        content=json.dumps(tr.result) if tr.result else tr.error or "",
                        tool_call_id=tr.tool_call_id,
                    )
                )

            response = await self.provider.complete(
                messages=messages,
                tools=tools,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )

        # Extract UI output if present
        content, ui_output = self._extract_ui_output(response.content)

        self.think(f"Generated response of {len(content)} chars")
        if ui_output:
            self.think(f"Emitted A2UI component: {ui_output.get('component', 'unknown')}")

        return AgentResult(
            success=True,
            output=content,
            ui_output=ui_output,
            events=list(self.state.history),
            metadata={
                "model": self.config.model,
                "thought_count": len(self.state.thought_trail),
            },
        )

    async def chat(self, message: str) -> str:
        """Convenience method for simple chat interactions"""
        result = await self.execute(message)
        return result.output or ""


# Specialized LLM agent variants
class CodeAgent(LlmAgent):
    """LLM agent specialized for code generation and analysis"""

    def _default_system_prompt(self) -> str:
        return """You are an expert software engineer AI assistant.

Your capabilities:
- Write clean, efficient, well-documented code
- Debug and fix code issues
- Explain code and suggest improvements
- Follow best practices and design patterns

When writing code:
- Use appropriate language features
- Include error handling
- Add helpful comments
- Consider edge cases

Format code in appropriate markdown code blocks."""


class AnalystAgent(LlmAgent):
    """LLM agent specialized for data analysis"""

    def _default_system_prompt(self) -> str:
        return """You are an expert data analyst AI assistant.

Your capabilities:
- Analyze datasets and extract insights
- Generate visualizations and charts
- Identify patterns and anomalies
- Provide statistical summaries

When presenting data:
- Use A2UI Table components for tabular data
- Use A2UI Chart components for visualizations
- Summarize key findings clearly
- Support conclusions with data"""
