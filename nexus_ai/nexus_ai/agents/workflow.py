"""
NexusAI Workflow Agents

Implements ADK orchestration patterns:
- Sequential Pipeline: Linear hand-offs between agents
- Parallel Fan-Out/Gather: Concurrent execution with synthesis
- Loop/Iterative: Generator-Critic cycles for refinement
- Coordinator/Dispatcher: Central routing to specialist agents

These patterns enable complex multi-agent workflows with minimal boilerplate.
"""

from __future__ import annotations

import asyncio
from abc import abstractmethod
from enum import Enum
from typing import Any, Callable

from pydantic import BaseModel, Field

from nexus_ai.agents.base import (
    AgentConfig,
    AgentResult,
    AgentStatus,
    BaseAgent,
    EventType,
)


class WorkflowStatus(str, Enum):
    """Status of workflow execution"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"  # Some agents succeeded, some failed


class StepResult(BaseModel):
    """Result from a single workflow step"""
    agent_name: str
    success: bool
    output: Any = None
    error: str | None = None
    duration_ms: float = 0.0


class WorkflowResult(BaseModel):
    """Aggregate result from workflow execution"""
    status: WorkflowStatus
    steps: list[StepResult] = Field(default_factory=list)
    final_output: Any = None
    total_duration_ms: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkflowAgent(BaseAgent):
    """
    Base class for agents that orchestrate other agents.
    Manages sub-agent lifecycle and coordinates execution flow.
    """

    def __init__(
        self,
        config: AgentConfig,
        agents: list[BaseAgent] | None = None,
    ):
        super().__init__(config)
        self.agents: list[BaseAgent] = agents or []
        self._agent_map: dict[str, BaseAgent] = {}

        for agent in self.agents:
            self._agent_map[agent.name] = agent

    def add_agent(self, agent: BaseAgent) -> None:
        """Add an agent to the workflow"""
        self.agents.append(agent)
        self._agent_map[agent.name] = agent

    def get_agent(self, name: str) -> BaseAgent | None:
        """Get agent by name"""
        return self._agent_map.get(name)

    @abstractmethod
    async def _execute_workflow(
        self,
        message: str,
        context: dict[str, Any],
    ) -> WorkflowResult:
        """Implement specific workflow pattern"""
        pass

    async def _execute_impl(
        self,
        message: str,
        context: dict[str, Any],
    ) -> AgentResult:
        """Execute the workflow and convert to AgentResult"""
        workflow_result = await self._execute_workflow(message, context)

        return AgentResult(
            success=workflow_result.status == WorkflowStatus.COMPLETED,
            output=workflow_result.final_output,
            events=list(self.state.history),
            metadata={
                "workflow_status": workflow_result.status,
                "step_count": len(workflow_result.steps),
                "steps": [s.model_dump() for s in workflow_result.steps],
            },
            duration_ms=workflow_result.total_duration_ms,
        )


class SequentialAgent(WorkflowAgent):
    """
    Sequential Pipeline Pattern

    Executes agents in order, passing output from one to the next.
    Each agent receives the previous agent's output as input.

    Example use case: Parser -> Summarizer -> Translator

    DSPy Signature:
        Input: initial_message
        Output: final_output (after all stages)
    """

    def __init__(
        self,
        config: AgentConfig,
        pipeline: list[BaseAgent],
        transform_fn: Callable[[Any], str] | None = None,
    ):
        super().__init__(config, pipeline)
        self.transform_fn = transform_fn or (lambda x: str(x))

    async def _execute_workflow(
        self,
        message: str,
        context: dict[str, Any],
    ) -> WorkflowResult:
        import time
        start_time = time.time()

        steps: list[StepResult] = []
        current_input = message
        current_context = context.copy()

        self.think(f"Starting sequential pipeline with {len(self.agents)} stages")

        for i, agent in enumerate(self.agents):
            self.think(f"Stage {i + 1}/{len(self.agents)}: {agent.name}")

            self.emit_event(
                EventType.CONTROL,
                {"action": "stage_start", "stage": i + 1, "agent": agent.name},
            )

            step_start = time.time()
            result = await agent.execute(current_input, current_context)
            step_duration = (time.time() - step_start) * 1000

            step_result = StepResult(
                agent_name=agent.name,
                success=result.success,
                output=result.output,
                error=result.error,
                duration_ms=step_duration,
            )
            steps.append(step_result)

            if not result.success:
                self.think(f"Stage {agent.name} failed: {result.error}")
                return WorkflowResult(
                    status=WorkflowStatus.FAILED,
                    steps=steps,
                    final_output=None,
                    total_duration_ms=(time.time() - start_time) * 1000,
                    metadata={"failed_at_stage": i + 1},
                )

            # Transform output for next stage
            current_input = self.transform_fn(result.output)
            current_context["previous_output"] = result.output
            current_context["stage"] = i + 1

        self.think(f"Pipeline completed successfully in {len(steps)} stages")

        return WorkflowResult(
            status=WorkflowStatus.COMPLETED,
            steps=steps,
            final_output=steps[-1].output if steps else None,
            total_duration_ms=(time.time() - start_time) * 1000,
        )


class ParallelAgent(WorkflowAgent):
    """
    Parallel Fan-Out/Gather Pattern

    Executes multiple agents concurrently, then gathers results.
    Optionally includes a synthesis agent to combine outputs.

    Example use case: Code Review Swarm (multiple reviewers, one synthesizer)

    DSPy Signature:
        Input: message (broadcast to all agents)
        Output: aggregated_results or synthesized_output
    """

    def __init__(
        self,
        config: AgentConfig,
        workers: list[BaseAgent],
        synthesizer: BaseAgent | None = None,
        fail_fast: bool = False,
    ):
        super().__init__(config, workers)
        self.synthesizer = synthesizer
        self.fail_fast = fail_fast

    async def _execute_workflow(
        self,
        message: str,
        context: dict[str, Any],
    ) -> WorkflowResult:
        import time
        start_time = time.time()

        self.think(f"Starting parallel execution with {len(self.agents)} workers")

        # Fan-out: Execute all agents concurrently
        self.emit_event(
            EventType.CONTROL,
            {"action": "fan_out", "worker_count": len(self.agents)},
        )

        tasks = [
            agent.execute(message, context)
            for agent in self.agents
        ]

        if self.fail_fast:
            results = await asyncio.gather(*tasks, return_exceptions=True)
        else:
            results = await asyncio.gather(*tasks, return_exceptions=False)

        # Process results
        steps: list[StepResult] = []
        outputs: list[Any] = []
        failed_count = 0

        for agent, result in zip(self.agents, results):
            if isinstance(result, Exception):
                steps.append(StepResult(
                    agent_name=agent.name,
                    success=False,
                    error=str(result),
                ))
                failed_count += 1
            else:
                steps.append(StepResult(
                    agent_name=agent.name,
                    success=result.success,
                    output=result.output,
                    error=result.error,
                    duration_ms=result.duration_ms,
                ))
                if result.success:
                    outputs.append({
                        "agent": agent.name,
                        "output": result.output,
                    })
                else:
                    failed_count += 1

        self.think(f"Fan-out complete: {len(outputs)} succeeded, {failed_count} failed")

        # Gather: Synthesize results if synthesizer provided
        final_output: Any
        if self.synthesizer and outputs:
            self.emit_event(EventType.CONTROL, {"action": "synthesis_start"})

            synthesis_input = f"Synthesize these {len(outputs)} results:\n\n"
            for item in outputs:
                synthesis_input += f"### {item['agent']}:\n{item['output']}\n\n"

            synthesis_result = await self.synthesizer.execute(
                synthesis_input,
                {**context, "parallel_outputs": outputs},
            )

            steps.append(StepResult(
                agent_name=self.synthesizer.name,
                success=synthesis_result.success,
                output=synthesis_result.output,
                duration_ms=synthesis_result.duration_ms,
            ))

            final_output = synthesis_result.output
        else:
            final_output = outputs

        # Determine status
        if failed_count == 0:
            status = WorkflowStatus.COMPLETED
        elif failed_count == len(self.agents):
            status = WorkflowStatus.FAILED
        else:
            status = WorkflowStatus.PARTIAL

        return WorkflowResult(
            status=status,
            steps=steps,
            final_output=final_output,
            total_duration_ms=(time.time() - start_time) * 1000,
            metadata={
                "worker_count": len(self.agents),
                "success_count": len(self.agents) - failed_count,
                "failed_count": failed_count,
            },
        )


class LoopAgent(WorkflowAgent):
    """
    Loop/Iterative Pattern

    Generator-Critic cycle for quality assurance and refinement.
    Generator produces output, Critic evaluates, loop continues until satisfied.

    Example use case: Draft -> Critique -> Refine -> ... -> Final

    DSPy Signature:
        Input: initial_request
        Output: refined_output (after convergence)
    """

    def __init__(
        self,
        config: AgentConfig,
        generator: BaseAgent,
        critic: BaseAgent,
        max_iterations: int = 5,
        convergence_fn: Callable[[Any, Any], bool] | None = None,
    ):
        super().__init__(config, [generator, critic])
        self.generator = generator
        self.critic = critic
        self.max_iterations = max_iterations
        self.convergence_fn = convergence_fn or self._default_convergence

    def _default_convergence(self, critique: Any, iteration: int) -> bool:
        """Default convergence check: look for approval signals"""
        if iteration >= self.max_iterations:
            return True

        critique_str = str(critique).lower()
        approval_signals = ["approved", "looks good", "no changes needed", "accept"]
        return any(signal in critique_str for signal in approval_signals)

    async def _execute_workflow(
        self,
        message: str,
        context: dict[str, Any],
    ) -> WorkflowResult:
        import time
        start_time = time.time()

        steps: list[StepResult] = []
        current_input = message
        iteration = 0
        converged = False

        self.think(f"Starting iterative refinement (max {self.max_iterations} iterations)")

        while not converged and iteration < self.max_iterations:
            iteration += 1
            self.think(f"Iteration {iteration}/{self.max_iterations}")

            self.emit_event(
                EventType.CONTROL,
                {"action": "iteration_start", "iteration": iteration},
            )

            # Generate
            gen_context = {
                **context,
                "iteration": iteration,
                "previous_critique": steps[-1].output if steps and iteration > 1 else None,
            }

            gen_result = await self.generator.execute(current_input, gen_context)
            steps.append(StepResult(
                agent_name=f"{self.generator.name}_iter{iteration}",
                success=gen_result.success,
                output=gen_result.output,
                duration_ms=gen_result.duration_ms,
            ))

            if not gen_result.success:
                return WorkflowResult(
                    status=WorkflowStatus.FAILED,
                    steps=steps,
                    metadata={"failed_at": "generation", "iteration": iteration},
                    total_duration_ms=(time.time() - start_time) * 1000,
                )

            # Critique
            critique_input = f"Review this output and provide feedback:\n\n{gen_result.output}"
            crit_result = await self.critic.execute(
                critique_input,
                {**context, "iteration": iteration, "original_request": message},
            )

            steps.append(StepResult(
                agent_name=f"{self.critic.name}_iter{iteration}",
                success=crit_result.success,
                output=crit_result.output,
                duration_ms=crit_result.duration_ms,
            ))

            if not crit_result.success:
                return WorkflowResult(
                    status=WorkflowStatus.FAILED,
                    steps=steps,
                    metadata={"failed_at": "critique", "iteration": iteration},
                    total_duration_ms=(time.time() - start_time) * 1000,
                )

            # Check convergence
            converged = self.convergence_fn(crit_result.output, iteration)

            if not converged:
                # Prepare next iteration input with feedback
                current_input = f"""Original request: {message}

Previous output: {gen_result.output}

Feedback: {crit_result.output}

Please revise the output based on the feedback."""

        self.think(f"Converged after {iteration} iterations")

        # Get the last generated output
        gen_steps = [s for s in steps if "generator" in s.agent_name.lower() or self.generator.name in s.agent_name]
        final_output = gen_steps[-1].output if gen_steps else None

        return WorkflowResult(
            status=WorkflowStatus.COMPLETED,
            steps=steps,
            final_output=final_output,
            total_duration_ms=(time.time() - start_time) * 1000,
            metadata={
                "iterations": iteration,
                "converged": converged,
            },
        )


class CoordinatorAgent(WorkflowAgent):
    """
    Coordinator/Dispatcher Pattern

    Central agent analyzes intent and routes to specialist agents.
    Supports dynamic routing based on content analysis.

    Example use case: Triage Agent routing to specialists

    DSPy Signature:
        Input: user_message
        Output: specialist_output (from selected agent)
    """

    def __init__(
        self,
        config: AgentConfig,
        specialists: dict[str, BaseAgent],
        router: BaseAgent | None = None,
        default_specialist: str | None = None,
    ):
        specialist_list = list(specialists.values())
        super().__init__(config, specialist_list)
        self.specialists = specialists
        self.router = router
        self.default_specialist = default_specialist or list(specialists.keys())[0]

    async def _route_request(
        self,
        message: str,
        context: dict[str, Any],
    ) -> str:
        """Determine which specialist should handle the request"""
        if self.router:
            # Use router agent to determine specialist
            specialist_names = list(self.specialists.keys())
            routing_prompt = f"""Analyze this request and determine which specialist should handle it.

Available specialists: {specialist_names}

Request: {message}

Respond with ONLY the specialist name, nothing else."""

            result = await self.router.execute(routing_prompt, context)
            if result.success and result.output:
                chosen = result.output.strip().lower()
                # Find matching specialist (fuzzy match)
                for name in specialist_names:
                    if name.lower() in chosen or chosen in name.lower():
                        return name

        return self.default_specialist

    async def _execute_workflow(
        self,
        message: str,
        context: dict[str, Any],
    ) -> WorkflowResult:
        import time
        start_time = time.time()

        steps: list[StepResult] = []

        # Route to specialist
        self.think("Analyzing request to determine specialist...")
        specialist_name = await self._route_request(message, context)
        self.think(f"Routing to specialist: {specialist_name}")

        self.emit_event(
            EventType.CONTROL,
            {"action": "route", "specialist": specialist_name},
        )

        specialist = self.specialists.get(specialist_name)
        if not specialist:
            return WorkflowResult(
                status=WorkflowStatus.FAILED,
                steps=steps,
                metadata={"error": f"Specialist '{specialist_name}' not found"},
                total_duration_ms=(time.time() - start_time) * 1000,
            )

        # Execute specialist
        result = await specialist.execute(
            message,
            {**context, "routed_by": self.name, "specialist": specialist_name},
        )

        steps.append(StepResult(
            agent_name=specialist_name,
            success=result.success,
            output=result.output,
            error=result.error,
            duration_ms=result.duration_ms,
        ))

        return WorkflowResult(
            status=WorkflowStatus.COMPLETED if result.success else WorkflowStatus.FAILED,
            steps=steps,
            final_output=result.output,
            total_duration_ms=(time.time() - start_time) * 1000,
            metadata={
                "specialist": specialist_name,
                "ui_output": result.ui_output,
            },
        )
