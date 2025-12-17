"""
NexusAI Command Line Interface

Provides commands for:
- Running agents
- Starting the API server
- Managing sessions
- Demo workflows
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax
from rich.live import Live
from rich.spinner import Spinner

app = typer.Typer(
    name="nexus",
    help="NexusAI - Multi-Agent AI SDK",
    add_completion=False,
)

console = Console()


@app.command()
def version():
    """Show version information"""
    from nexus_ai import __version__
    console.print(f"NexusAI v{__version__}")


@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", help="Host to bind to"),
    port: int = typer.Option(8000, help="Port to bind to"),
    reload: bool = typer.Option(False, help="Enable auto-reload"),
):
    """Start the NexusAI API server"""
    from nexus_ai.api.server import run_server, NexusAPIConfig

    console.print(Panel.fit(
        f"[bold green]Starting NexusAI Server[/]\n"
        f"Host: {host}\n"
        f"Port: {port}\n"
        f"Docs: http://{host}:{port}/docs",
        title="NexusAI",
    ))

    config = NexusAPIConfig(host=host, port=port)
    run_server(config)


@app.command()
def chat(
    agent: str = typer.Option("default", help="Agent name to chat with"),
    model: str = typer.Option("claude-3-5-sonnet-20241022", help="Model to use"),
):
    """Interactive chat with an agent"""
    from nexus_ai.agents.llm import LlmAgent
    from nexus_ai.agents.base import AgentConfig

    console.print(Panel.fit(
        f"[bold]Chat with NexusAI Agent[/]\n"
        f"Agent: {agent}\n"
        f"Model: {model}\n"
        f"Type 'exit' or 'quit' to end",
        title="NexusAI Chat",
    ))

    config = AgentConfig(name=agent, model=model)
    llm_agent = LlmAgent(config)

    async def chat_loop():
        while True:
            try:
                user_input = console.input("\n[bold blue]You:[/] ")

                if user_input.lower() in ("exit", "quit"):
                    console.print("[dim]Goodbye![/]")
                    break

                with console.status("[bold green]Thinking..."):
                    result = await llm_agent.execute(user_input)

                console.print(f"\n[bold green]Agent:[/] {result.output}")

                if result.ui_output:
                    console.print("\n[dim]UI Output:[/]")
                    console.print_json(json.dumps(result.ui_output))

            except KeyboardInterrupt:
                console.print("\n[dim]Interrupted[/]")
                break

    asyncio.run(chat_loop())


@app.command()
def demo(
    scenario: str = typer.Argument("workflow", help="Demo scenario to run"),
):
    """Run a demo scenario"""
    scenarios = {
        "workflow": demo_workflow,
        "parallel": demo_parallel,
        "loop": demo_loop,
        "memory": demo_memory,
        "a2ui": demo_a2ui,
    }

    if scenario not in scenarios:
        console.print(f"[red]Unknown scenario: {scenario}[/]")
        console.print(f"Available: {', '.join(scenarios.keys())}")
        raise typer.Exit(1)

    asyncio.run(scenarios[scenario]())


async def demo_workflow():
    """Demo: Sequential Workflow"""
    from nexus_ai.agents.llm import LlmAgent
    from nexus_ai.agents.workflow import SequentialAgent
    from nexus_ai.agents.base import AgentConfig

    console.print(Panel.fit(
        "[bold]Sequential Workflow Demo[/]\n"
        "Parser -> Analyzer -> Summarizer",
        title="NexusAI Demo",
    ))

    # Create agents
    parser = LlmAgent(AgentConfig(name="Parser", description="Parse and structure input"))
    analyzer = LlmAgent(AgentConfig(name="Analyzer", description="Analyze content"))
    summarizer = LlmAgent(AgentConfig(name="Summarizer", description="Create summary"))

    # Create pipeline
    pipeline = SequentialAgent(
        config=AgentConfig(name="Pipeline"),
        pipeline=[parser, analyzer, summarizer],
    )

    # Execute
    with console.status("[bold green]Running pipeline..."):
        result = await pipeline.execute("Analyze the impact of AI on software development")

    console.print("\n[bold]Pipeline Result:[/]")
    console.print(f"Status: {'Success' if result.success else 'Failed'}")
    console.print(f"Output: {result.output[:500]}...")

    # Show steps
    steps = result.metadata.get("steps", [])
    if steps:
        table = Table(title="Pipeline Steps")
        table.add_column("Agent")
        table.add_column("Status")
        table.add_column("Duration (ms)")

        for step in steps:
            table.add_row(
                step["agent_name"],
                "✓" if step["success"] else "✗",
                f"{step['duration_ms']:.1f}",
            )

        console.print(table)


async def demo_parallel():
    """Demo: Parallel Execution"""
    from nexus_ai.agents.llm import LlmAgent
    from nexus_ai.agents.workflow import ParallelAgent
    from nexus_ai.agents.base import AgentConfig

    console.print(Panel.fit(
        "[bold]Parallel Execution Demo[/]\n"
        "3 reviewers working concurrently",
        title="NexusAI Demo",
    ))

    # Create parallel reviewers
    reviewers = [
        LlmAgent(AgentConfig(name=f"Reviewer{i+1}", description=f"Review aspect {i+1}"))
        for i in range(3)
    ]

    synthesizer = LlmAgent(AgentConfig(name="Synthesizer", description="Combine reviews"))

    # Create parallel agent
    parallel = ParallelAgent(
        config=AgentConfig(name="ReviewSwarm"),
        workers=reviewers,
        synthesizer=synthesizer,
    )

    # Execute
    with console.status("[bold green]Running parallel review..."):
        result = await parallel.execute("Review this code for quality, security, and performance")

    console.print("\n[bold]Parallel Result:[/]")
    console.print(f"Status: {'Success' if result.success else 'Failed'}")

    metadata = result.metadata
    console.print(f"Workers: {metadata.get('worker_count', 0)}")
    console.print(f"Succeeded: {metadata.get('success_count', 0)}")
    console.print(f"Failed: {metadata.get('failed_count', 0)}")


async def demo_loop():
    """Demo: Iterative Refinement"""
    from nexus_ai.agents.llm import LlmAgent
    from nexus_ai.agents.workflow import LoopAgent
    from nexus_ai.agents.base import AgentConfig

    console.print(Panel.fit(
        "[bold]Iterative Loop Demo[/]\n"
        "Generator -> Critic -> Refine (until satisfied)",
        title="NexusAI Demo",
    ))

    generator = LlmAgent(AgentConfig(name="Generator", description="Generate content"))
    critic = LlmAgent(AgentConfig(name="Critic", description="Critique and suggest improvements"))

    loop_agent = LoopAgent(
        config=AgentConfig(name="RefineLoop"),
        generator=generator,
        critic=critic,
        max_iterations=3,
    )

    with console.status("[bold green]Running refinement loop..."):
        result = await loop_agent.execute("Write a haiku about programming")

    console.print("\n[bold]Loop Result:[/]")
    console.print(f"Iterations: {result.metadata.get('iterations', 0)}")
    console.print(f"Converged: {result.metadata.get('converged', False)}")
    console.print(f"\nFinal Output:\n{result.output}")


async def demo_memory():
    """Demo: Memory System"""
    from nexus_ai.context.memory import Memory

    console.print(Panel.fit(
        "[bold]Memory System Demo[/]\n"
        "Store and recall information",
        title="NexusAI Demo",
    ))

    memory = Memory(project_id="demo")

    # Store some memories
    console.print("\n[dim]Storing memories...[/]")

    await memory.remember(
        "User prefers dark mode themes",
        category="preference",
        importance=0.9,
    )
    await memory.remember(
        "Project uses TypeScript and React",
        category="fact",
        importance=0.8,
    )
    await memory.remember(
        "Previous task was implementing authentication",
        category="observation",
        importance=0.6,
    )

    # Recall
    console.print("\n[bold]Recall: 'What tech stack is used?'[/]")
    results = await memory.recall("What tech stack is used?", limit=3)
    for r in results:
        console.print(f"  - {r}")

    console.print("\n[bold]Recall: 'User preferences'[/]")
    prefs = await memory.get_preferences()
    console.print(f"  Preferences: {prefs}")


async def demo_a2ui():
    """Demo: A2UI Rendering"""
    from nexus_ai.protocol.a2ui import A2UIRenderer

    console.print(Panel.fit(
        "[bold]A2UI Rendering Demo[/]\n"
        "Generate secure UI components",
        title="NexusAI Demo",
    ))

    renderer = A2UIRenderer()

    # Create components
    card = renderer.card(
        title="Task Summary",
        content="Your workflow completed successfully!",
        subtitle="5 agents processed",
        footer="Duration: 2.3s",
    )

    table = renderer.table(
        columns=[
            {"key": "agent", "header": "Agent"},
            {"key": "status", "header": "Status"},
            {"key": "time", "header": "Time (ms)"},
        ],
        data=[
            {"agent": "Parser", "status": "Complete", "time": "120"},
            {"agent": "Analyzer", "status": "Complete", "time": "450"},
            {"agent": "Summarizer", "status": "Complete", "time": "380"},
        ],
        title="Agent Performance",
    )

    code = renderer.code(
        code='async def hello():\n    return "Hello, NexusAI!"',
        language="python",
        title="Generated Code",
    )

    # Render layout
    layout = renderer.render_layout([card, table, code])

    console.print("\n[bold]Generated A2UI JSON:[/]")
    syntax = Syntax(json.dumps(layout, indent=2), "json", theme="monokai")
    console.print(syntax)


@app.command()
def init(
    path: Path = typer.Argument(Path("."), help="Project path"),
):
    """Initialize a new NexusAI project"""
    console.print(f"[bold]Initializing NexusAI project in {path}[/]")

    # Create directories
    dirs = [
        path / ".nexus" / "sessions",
        path / ".nexus" / "memory",
        path / ".nexus" / "artifacts",
        path / "agents",
        path / "tools",
    ]

    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
        console.print(f"  Created: {d}")

    # Create config file
    config = {
        "version": "1.0.0",
        "project_name": path.name,
        "agents": {},
        "default_model": "claude-3-5-sonnet-20241022",
    }

    config_path = path / "nexus.json"
    config_path.write_text(json.dumps(config, indent=2))
    console.print(f"  Created: {config_path}")

    console.print("\n[green]Project initialized successfully![/]")
    console.print("Next steps:")
    console.print("  1. Edit nexus.json to configure agents")
    console.print("  2. Run 'nexus serve' to start the API")
    console.print("  3. Run 'nexus demo workflow' to see a demo")


@app.command()
def status():
    """Show NexusAI status"""
    console.print(Panel.fit(
        "[bold]NexusAI Status[/]",
        title="Status",
    ))

    # Check for project
    config_path = Path("nexus.json")
    if config_path.exists():
        config = json.loads(config_path.read_text())
        console.print(f"Project: {config.get('project_name', 'Unknown')}")
        console.print(f"Version: {config.get('version', 'Unknown')}")
    else:
        console.print("[yellow]No project found. Run 'nexus init' to create one.[/]")


def main():
    """Main entry point"""
    app()


if __name__ == "__main__":
    main()
