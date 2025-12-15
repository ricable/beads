# Beads Multi-Agent Collaboration System

> **DSPy-Optimized 3-Agent Orchestration with Git-Native Persistence**

A demonstration of collaborative AI agents using Claude-Flow with Beads for distributed, git-native state management.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     USER REQUEST                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      ORCHESTRATOR                                │
│   Coordinates workflow: Plan → Implement → Review               │
└─────────────────────────────────────────────────────────────────┘
        │                    │                    │
        ▼                    ▼                    ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│   ARCHITECT   │   │  IMPLEMENTER  │   │   REVIEWER    │
│  (Planning)   │──▶│  (Execution)  │──▶│   (Quality)   │
│               │   │               │   │               │
│ • Decompose   │   │ • Execute     │   │ • Review      │
│ • Dependencies│   │ • Code        │   │ • Validate    │
│ • Ready work  │   │ • Discover    │   │ • Approve     │
└───────────────┘   └───────────────┘   └───────────────┘
        │                    │                    │
        └────────────────────┴────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         BEADS                                    │
│   .beads/beads.jsonl (git-tracked source of truth)              │
│   .beads/deletions.jsonl (cross-clone deletion log)             │
│   .beads/beads.db (local SQLite cache - gitignored)             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                          GIT                                     │
│   Single source of truth • Distributed collaboration            │
│   3-way merge • Conflict resolution • Version control           │
└─────────────────────────────────────────────────────────────────┘
```

## Quick Start

```bash
# Install dependencies
npm install

# Initialize beads
npm run setup:beads

# Run the demo
npm run demo

# Or start the orchestrator with a custom request
npm start "Add user authentication with OAuth2"
```

## Installation (Full Stack)

```bash
# Claude-Flow and ecosystem
npx claude-flow@alpha init --force
npx agentic-flow@alpha init
npx agentdb@alpha init
npx ruvvector@alpha init
npx @ruvector/postgres-cli@alpha init

# Initialize beads
npm run setup:beads
```

## The Three Agents

### 1. ARCHITECT (Strategic Planning)

**DSPy Signature:**
```python
Input: user_request, current_state
Output: task_graph, ready_work, reasoning
```

Responsibilities:
- Decompose complex tasks into atomic units
- Create dependency graphs (blocks, related, parent-child, discovered-from)
- Identify ready work for the IMPLEMENTER
- Generate context priming for token efficiency

### 2. IMPLEMENTER (Execution)

**DSPy Signature:**
```python
Input: ready_work, codebase_context
Output: code_changes, completion_status, discovered_issues
```

Responsibilities:
- Process ready work items from the queue
- Write and modify code
- Discover emergent issues during implementation
- Update beads with completion status

### 3. REVIEWER (Quality Assurance)

**DSPy Signature:**
```python
Input: completed_work, git_status
Output: review_results, merge_actions, integrity_report
```

Responsibilities:
- Review completed implementations
- Validate JSONL/SQLite consistency
- Handle merge conflicts with 3-way merge
- Manage deletion propagation (prevent zombies)
- Approve or reject with feedback

## Beads: Git-Native Persistence

### Dual Persistence Model

| Layer | File | Purpose |
|-------|------|---------|
| Source of Truth | `.beads/beads.jsonl` | Git-tracked, distributed |
| Local Cache | `.beads/beads.db` | SQLite, <100ms queries |
| Deletion Log | `.beads/deletions.jsonl` | Prevents zombie resurrection |

### Key Features

- **Hash-based IDs**: Collision-resistant (e.g., `bd-a1b2`)
- **Dependency Types**: `blocks`, `related`, `parent-child`, `discovered-from`
- **Ready Work Algorithm**: Identifies unblocked tasks
- **3-Way Merge**: Automatic conflict resolution
- **Deletion Propagation**: Cross-clone consistency

## DSPy Optimization Principles

This system applies DSPy context engineering:

1. **Signature-Based Declarations**: Explicit I/O contracts per agent
2. **Modular Composition**: Independent agents, shared state
3. **Chain-of-Thought Traces**: Reasoning captured in `<thinking_trace>`
4. **Multi-Objective Optimization**: Pareto metrics for quality/speed
5. **Context Efficiency**: `bd prime` for token-optimized context
6. **Reflection-Ready**: `discovered-from` links enable session memory

### Metrics

```javascript
metrics = {
  taskCompletionRate: completed / total,      // target: 0.95
  dependencyAccuracy: valid_deps / total,     // target: 1.0
  mergeConflictRate: conflicts / merges,      // target: 0.0
  queryLatencyP99: max(query_times)           // target: <100ms
}
```

## Commands

```bash
# Run demo use case
npm run demo

# Start orchestrator
npm start "<user request>"

# Run individual agents
npm run start:architect
npm run start:implementer
npm run start:reviewer

# Check status
npm run status

# Sync agents
npm run sync
```

## Project Structure

```
beads/
├── .beads/
│   ├── beads.jsonl         # Git-tracked source of truth
│   ├── deletions.jsonl     # Deletion propagation log
│   ├── beads.db            # Local SQLite cache (gitignored)
│   └── config.json         # Beads configuration
├── agents/
│   ├── architect.js        # Strategic planning agent
│   ├── implementer.js      # Execution agent
│   └── reviewer.js         # Quality assurance agent
├── scripts/
│   ├── orchestrator.js     # Multi-agent coordinator
│   ├── demo-usecase.js     # Demo script
│   ├── init-beads.js       # Initialization
│   ├── sync-agents.js      # State synchronization
│   └── status.js           # Status dashboard
├── claude-flow.config.js   # Claude-Flow configuration
├── DSPY_MULTI_AGENT_PROMPT.md  # The ultimate DSPy prompt
├── package.json
└── README.md
```

## References

- [Beads Documentation](https://deepwiki.com/steveyegge/beads)
- [Claude-Flow](https://github.com/ruvnet/claude-flow)
- [DSPy Framework](https://github.com/stanfordnlp/dspy)
- [DSPy GEPA Optimization](https://medium.com/firebird-technologies/context-engineering-improving-ai-coding-agents-using-dspy-gepa-df669c632766)

## License

MIT
