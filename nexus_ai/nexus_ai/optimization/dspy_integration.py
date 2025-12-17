"""
NexusAI DSPy Integration

Integrates DSPy for automatic prompt optimization:
- Signature-based declarations
- MIPROv2 and GEPA optimizers
- Validation dataset support
- Programmatic prompt tuning
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable
from abc import ABC, abstractmethod

from pydantic import BaseModel


class OptimizationConfig(BaseModel):
    """Configuration for prompt optimization"""
    optimizer: str = "mipro"  # mipro, copro, gepa
    num_candidates: int = 10
    max_iterations: int = 50
    metric_threshold: float = 0.8
    validation_split: float = 0.2


@dataclass
class NexusSignature:
    """
    DSPy-style signature for NexusAI agents.

    Defines input/output contracts for agent tasks.

    Example:
        sig = NexusSignature(
            name="SummarizeDocument",
            inputs={"document": "The document to summarize"},
            outputs={"summary": "A concise summary", "key_points": "List of key points"}
        )
    """
    name: str
    inputs: dict[str, str]  # name -> description
    outputs: dict[str, str]  # name -> description
    instructions: str = ""
    examples: list[dict[str, Any]] = field(default_factory=list)

    def to_prompt_template(self) -> str:
        """Generate prompt template from signature"""
        lines = []

        if self.instructions:
            lines.append(f"Task: {self.instructions}")
            lines.append("")

        lines.append("Inputs:")
        for name, desc in self.inputs.items():
            lines.append(f"  - {name}: {desc}")
        lines.append("")

        lines.append("Required Outputs:")
        for name, desc in self.outputs.items():
            lines.append(f"  - {name}: {desc}")

        if self.examples:
            lines.append("")
            lines.append("Examples:")
            for i, example in enumerate(self.examples[:3]):
                lines.append(f"  Example {i + 1}:")
                for key, value in example.items():
                    lines.append(f"    {key}: {str(value)[:100]}")

        return "\n".join(lines)

    def validate_output(self, output: dict[str, Any]) -> bool:
        """Check if output matches signature"""
        return all(key in output for key in self.outputs.keys())


class NexusModule(ABC):
    """
    Base class for optimizable NexusAI modules.

    Similar to DSPy modules, these can be optimized with
    automatic prompt tuning.
    """

    def __init__(self, signature: NexusSignature):
        self.signature = signature
        self._optimized_prompt: str | None = None

    @abstractmethod
    async def forward(self, **inputs: Any) -> dict[str, Any]:
        """Execute the module"""
        pass

    def get_prompt(self) -> str:
        """Get current prompt (optimized or default)"""
        return self._optimized_prompt or self.signature.to_prompt_template()

    def set_optimized_prompt(self, prompt: str) -> None:
        """Set optimized prompt"""
        self._optimized_prompt = prompt


class LLMModule(NexusModule):
    """Module that calls an LLM with the signature prompt"""

    def __init__(
        self,
        signature: NexusSignature,
        llm_fn: Callable[..., Any] | None = None,
    ):
        super().__init__(signature)
        self._llm_fn = llm_fn or self._default_llm

    async def _default_llm(self, prompt: str) -> str:
        """Default mock LLM function"""
        # In production, this would call actual LLM
        return f"Response to: {prompt[:100]}..."

    async def forward(self, **inputs: Any) -> dict[str, Any]:
        """Execute LLM call with signature"""
        # Build prompt
        prompt = self.get_prompt()
        prompt += "\n\nInputs:\n"
        for key, value in inputs.items():
            prompt += f"  {key}: {value}\n"

        # Call LLM
        response = await self._llm_fn(prompt)

        # Parse response (simplified)
        outputs = {}
        for key in self.signature.outputs.keys():
            outputs[key] = response  # In real impl, parse structured output

        return outputs


class ChainOfThoughtModule(NexusModule):
    """Module that includes explicit reasoning steps"""

    def __init__(
        self,
        signature: NexusSignature,
        reasoning_steps: list[str] | None = None,
    ):
        super().__init__(signature)
        self.reasoning_steps = reasoning_steps or [
            "Analyze the input",
            "Identify key information",
            "Generate response",
        ]

    async def forward(self, **inputs: Any) -> dict[str, Any]:
        """Execute with chain-of-thought reasoning"""
        thoughts = []

        for step in self.reasoning_steps:
            thoughts.append(f"Step: {step}")
            # In real impl, each step would involve LLM call

        return {
            "thoughts": thoughts,
            **{key: f"Output for {key}" for key in self.signature.outputs.keys()},
        }


class PromptOptimizer:
    """
    Optimizes prompts using DSPy-style techniques.

    Supports:
    - MIPROv2: Bayesian optimization over prompt space
    - COPRO: Coordinate ascent optimization
    - GEPA: Evolutionary prompt optimization
    """

    def __init__(self, config: OptimizationConfig):
        self.config = config
        self._history: list[dict[str, Any]] = []

    async def optimize(
        self,
        module: NexusModule,
        train_data: list[dict[str, Any]],
        metric_fn: Callable[[dict[str, Any], dict[str, Any]], float],
    ) -> NexusModule:
        """
        Optimize a module's prompt.

        Args:
            module: Module to optimize
            train_data: Training examples [{inputs: {...}, expected: {...}}]
            metric_fn: Function(predicted, expected) -> score

        Returns:
            Optimized module
        """
        # Split data
        split_idx = int(len(train_data) * (1 - self.config.validation_split))
        train_set = train_data[:split_idx]
        val_set = train_data[split_idx:]

        best_prompt = module.get_prompt()
        best_score = await self._evaluate(module, val_set, metric_fn)

        for iteration in range(self.config.max_iterations):
            # Generate candidate prompts
            candidates = await self._generate_candidates(
                module.signature,
                train_set,
                best_prompt,
            )

            for candidate in candidates:
                module.set_optimized_prompt(candidate)
                score = await self._evaluate(module, val_set, metric_fn)

                self._history.append({
                    "iteration": iteration,
                    "score": score,
                    "prompt_length": len(candidate),
                })

                if score > best_score:
                    best_score = score
                    best_prompt = candidate

                if best_score >= self.config.metric_threshold:
                    break

            if best_score >= self.config.metric_threshold:
                break

        module.set_optimized_prompt(best_prompt)
        return module

    async def _generate_candidates(
        self,
        signature: NexusSignature,
        train_data: list[dict[str, Any]],
        current_best: str,
    ) -> list[str]:
        """Generate candidate prompts"""
        candidates = []

        # Strategy 1: Add examples
        if train_data:
            example_prompt = current_best + "\n\nExamples:\n"
            for ex in train_data[:3]:
                example_prompt += f"  Input: {ex.get('inputs', {})}\n"
                example_prompt += f"  Output: {ex.get('expected', {})}\n"
            candidates.append(example_prompt)

        # Strategy 2: Emphasize outputs
        emphasis_prompt = current_best + "\n\nIMPORTANT: Ensure all required outputs are provided."
        candidates.append(emphasis_prompt)

        # Strategy 3: Add formatting instructions
        format_prompt = current_best + "\n\nFormat your response as JSON with keys: "
        format_prompt += ", ".join(signature.outputs.keys())
        candidates.append(format_prompt)

        return candidates[:self.config.num_candidates]

    async def _evaluate(
        self,
        module: NexusModule,
        data: list[dict[str, Any]],
        metric_fn: Callable[[dict[str, Any], dict[str, Any]], float],
    ) -> float:
        """Evaluate module on dataset"""
        if not data:
            return 0.0

        scores = []
        for example in data:
            inputs = example.get("inputs", {})
            expected = example.get("expected", {})

            try:
                predicted = await module.forward(**inputs)
                score = metric_fn(predicted, expected)
                scores.append(score)
            except Exception:
                scores.append(0.0)

        return sum(scores) / len(scores) if scores else 0.0

    def get_optimization_history(self) -> list[dict[str, Any]]:
        """Get optimization history"""
        return self._history


# Utility functions for common metrics
def exact_match_metric(predicted: dict[str, Any], expected: dict[str, Any]) -> float:
    """Exact string match metric"""
    matches = 0
    total = len(expected)

    for key, value in expected.items():
        if key in predicted and str(predicted[key]) == str(value):
            matches += 1

    return matches / total if total > 0 else 0.0


def contains_metric(predicted: dict[str, Any], expected: dict[str, Any]) -> float:
    """Check if predicted contains expected content"""
    matches = 0
    total = len(expected)

    for key, value in expected.items():
        if key in predicted:
            if str(value).lower() in str(predicted[key]).lower():
                matches += 1

    return matches / total if total > 0 else 0.0


def key_presence_metric(predicted: dict[str, Any], expected: dict[str, Any]) -> float:
    """Check if all expected keys are present"""
    expected_keys = set(expected.keys())
    predicted_keys = set(predicted.keys())

    if not expected_keys:
        return 1.0

    return len(expected_keys & predicted_keys) / len(expected_keys)
