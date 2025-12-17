# NexusAI

> Next-Generation Multi-Agent AI SDK with ADK Patterns, A2UI Protocol, and Context Engineering

NexusAI is a unified framework for building stateful, context-aware agents with generative UI capabilities. It synthesizes Google's Agent Development Kit (ADK) patterns, the Agent-to-User Interface (A2UI) protocol, and advanced context engineering.

## Features

- **Multi-Agent Orchestration**: Sequential, Parallel, Loop, and Coordinator patterns
- **Context Engineering**: Tiered storage (Working, Session, Memory, Artifacts)
- **A2UI Protocol**: Secure, declarative JSON-based UI generation
- **DSPy Integration**: Automatic prompt optimization
- **MCP Support**: Model Context Protocol for external tools
- **Full API**: REST and WebSocket interfaces

## Quick Start

```bash
# Install
pip install nexus-ai

# Initialize project
nexus init my-project
cd my-project

# Start API server
nexus serve

# Or run interactive chat
nexus chat
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER / CLIENT                            │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      INTERACTIONS API                            │
│               REST + WebSocket + Background Tasks                │
└─────────────────────────────────────────────────────────────────┘
                                │
          ┌─────────────────────┼─────────────────────┐
          ▼                     ▼                     ▼
┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
│   LLM AGENT     │   │ WORKFLOW AGENT  │   │ COORDINATOR     │
│  (Conversational)│   │ (Orchestration) │   │  (Routing)      │
└─────────────────┘   └─────────────────┘   └─────────────────┘
          │                     │                     │
          └─────────────────────┼─────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    CONTEXT ENGINEERING                           │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────────────┐   │
│  │ Working │  │ Session │  │ Memory  │  │    Artifacts    │   │
│  │ Context │  │  (Log)  │  │ (Vector)│  │    (Blobs)      │   │
│  └─────────┘  └─────────┘  └─────────┘  └─────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                        A2UI PROTOCOL                             │
│           Card | Table | Form | Chart | Code | Alert            │
└─────────────────────────────────────────────────────────────────┘
```

## Agent Patterns (ADK)

### Sequential Pipeline
```python
from nexus_ai import SequentialAgent, LlmAgent, AgentConfig

# Create pipeline stages
parser = LlmAgent(AgentConfig(name="Parser"))
analyzer = LlmAgent(AgentConfig(name="Analyzer"))
summarizer = LlmAgent(AgentConfig(name="Summarizer"))

# Create sequential workflow
pipeline = SequentialAgent(
    config=AgentConfig(name="Pipeline"),
    pipeline=[parser, analyzer, summarizer],
)

# Execute
result = await pipeline.execute("Analyze this document...")
```

### Parallel Fan-Out/Gather
```python
from nexus_ai import ParallelAgent, LlmAgent, AgentConfig

# Create parallel workers
reviewers = [
    LlmAgent(AgentConfig(name=f"Reviewer{i}"))
    for i in range(3)
]

synthesizer = LlmAgent(AgentConfig(name="Synthesizer"))

# Create parallel swarm
swarm = ParallelAgent(
    config=AgentConfig(name="ReviewSwarm"),
    workers=reviewers,
    synthesizer=synthesizer,
)

result = await swarm.execute("Review this code for quality")
```

### Loop/Iterative
```python
from nexus_ai import LoopAgent, LlmAgent, AgentConfig

generator = LlmAgent(AgentConfig(name="Generator"))
critic = LlmAgent(AgentConfig(name="Critic"))

# Iterative refinement loop
refiner = LoopAgent(
    config=AgentConfig(name="Refiner"),
    generator=generator,
    critic=critic,
    max_iterations=5,
)

result = await refiner.execute("Write a compelling headline")
```

### Coordinator/Dispatcher
```python
from nexus_ai import CoordinatorAgent, LlmAgent, AgentConfig

specialists = {
    "code": LlmAgent(AgentConfig(name="CodeExpert")),
    "docs": LlmAgent(AgentConfig(name="DocsExpert")),
    "review": LlmAgent(AgentConfig(name="ReviewExpert")),
}

coordinator = CoordinatorAgent(
    config=AgentConfig(name="Triage"),
    specialists=specialists,
)

result = await coordinator.execute("Help me write unit tests")
```

## Context Engineering

### Session Management
```python
from nexus_ai import Session

# Create or resume session
session = await Session.create(project_id="my-project")

# Append events
await session.append(SessionEventType.USER, "Hello!")
await session.append(SessionEventType.AGENT, "Hi there!")

# Get context for LLM
context = await session.get_context(max_tokens=10000)

# Resume later
session = await Session.load(project_id="my-project", session_id="abc123")
resume_context = await session.resume()
```

### Memory System
```python
from nexus_ai import Memory

memory = Memory(project_id="my-project")

# Store memories
await memory.remember("User prefers dark mode", category="preference")
await memory.store_fact("Project uses TypeScript")

# Recall relevant memories
results = await memory.recall("What are user preferences?")
prefs = await memory.get_preferences()
```

### Artifacts
```python
from nexus_ai.context import ArtifactStore

store = ArtifactStore()

# Store large files
artifact = await store.store_file("document.pdf")

# Load on demand
content = await artifact.load()
text = await artifact.load_text()
```

## A2UI Protocol

Agents generate secure UI components using declarative JSON:

```python
from nexus_ai import A2UIRenderer

renderer = A2UIRenderer()

# Create components
card = renderer.card(
    title="Task Complete",
    content="Your analysis is ready!",
)

table = renderer.table(
    columns=[{"key": "name", "header": "Name"}],
    data=[{"name": "Item 1"}],
)

code = renderer.code(
    code="print('Hello')",
    language="python",
)

# Render layout
layout = renderer.render_layout([card, table, code])
```

### Security
- Strict whitelist of allowed components
- No executable code (`eval`, `script`, etc.)
- Sanitized content
- Sandboxed rendering

## API Usage

### REST API
```bash
# Start server
nexus serve

# Create interaction
curl -X POST http://localhost:8000/v1/interactions \
  -H "Content-Type: application/json" \
  -d '{"agent_id": "default", "message": "Hello!"}'

# Poll status
curl http://localhost:8000/v1/interactions/{id}
```

### WebSocket Streaming
```javascript
const ws = new WebSocket('ws://localhost:8000/v1/stream');

ws.send(JSON.stringify({
  agent_id: 'default',
  message: 'Analyze this code...',
}));

ws.onmessage = (event) => {
  const chunk = JSON.parse(event.data);
  // chunk.type: 'token' | 'thought' | 'ui' | 'control'
  console.log(chunk.content);
};
```

## DSPy Integration

Automatic prompt optimization:

```python
from nexus_ai.optimization import (
    NexusSignature,
    LLMModule,
    PromptOptimizer,
    OptimizationConfig,
)

# Define signature
signature = NexusSignature(
    name="Summarize",
    inputs={"document": "Text to summarize"},
    outputs={"summary": "Concise summary"},
)

# Create module
module = LLMModule(signature)

# Optimize
optimizer = PromptOptimizer(OptimizationConfig(optimizer="mipro"))
optimized = await optimizer.optimize(
    module,
    train_data=[...],
    metric_fn=exact_match_metric,
)
```

## CLI Commands

```bash
nexus version          # Show version
nexus init [path]      # Initialize project
nexus serve            # Start API server
nexus chat             # Interactive chat
nexus demo <scenario>  # Run demos (workflow, parallel, loop, memory, a2ui)
nexus status           # Show project status
```

## Project Structure

```
my-project/
├── .nexus/
│   ├── sessions/     # Session persistence
│   ├── memory/       # Vector memory store
│   └── artifacts/    # Large file storage
├── agents/           # Custom agents
├── tools/            # Custom tools
└── nexus.json        # Project config
```

## Success Metrics

- **Adoption**: 500+ active developers (3 months)
- **Reliability**: 99.9% orchestration uptime
- **Efficiency**: 30% token reduction via Context Compaction
- **Velocity**: Deploy multi-agent "Hello World" in < 5 minutes

## Roadmap

| Phase | Features | Timeline |
|-------|----------|----------|
| 1. Foundation | BaseAgent, LlmAgent, Sequential, Sessions | Weeks 1-4 |
| 2. Patterns | Parallel, Loop, Memory, Compaction | Weeks 5-8 |
| 3. UI & Advanced | A2UI, Interactions API, DSPy | Weeks 9-12 |

## License

MIT
