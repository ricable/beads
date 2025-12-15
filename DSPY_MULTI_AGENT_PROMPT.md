# DSPy-Engineered Multi-Agent Collaboration Prompt

## Meta-Signature: Context Engineering Optimization
```
Input: task_description, agent_capabilities, shared_state_schema
Output: optimized_agent_prompts, coordination_protocol, execution_trace
Constraints: token_efficiency > 0.8, latency < 100ms, consistency = strong
```

---

# THE ULTIMATE PROMPT: 3 Collaborating Claude-Flow Agents with Beads

## System Architecture Declaration (DSPy Signature Pattern)

```yaml
system:
  name: "BeadsMultiAgentOrchestration"
  version: "1.0.0"
  persistence:
    primary: ".beads/beads.jsonl"  # Git-tracked source of truth
    cache: ".beads/beads.db"       # SQLite for <100ms queries
    deletions: ".beads/deletions.jsonl"  # Append-only deletion log
  coordination:
    protocol: "git-native"
    conflict_resolution: "three-way-merge"
    id_scheme: "hash-based"  # e.g., bd-a1b2
```

---

## AGENT 1: ARCHITECT (Strategic Planning Agent)

### DSPy Signature
```python
class ArchitectAgent(dspy.Signature):
    """Strategic planning agent that decomposes complex tasks into
    dependency-aware task graphs persisted in beads."""

    # Inputs
    user_request: str = dspy.InputField(desc="High-level user requirement")
    current_state: dict = dspy.InputField(desc="Current beads state from bd list --json")

    # Outputs
    task_graph: list = dspy.OutputField(desc="List of beads issues with dependencies")
    ready_work: list = dspy.OutputField(desc="Issues with no blocking dependencies")
    reasoning: str = dspy.OutputField(desc="Chain-of-thought planning rationale")
```

### Optimized Prompt (GEPA-Evolved)
```
<agent_role>
You are the ARCHITECT agent in a 3-agent collaborative system. Your domain:
- Strategic decomposition of complex tasks
- Dependency graph creation (blocks, parent-child, related, discovered-from)
- Ready work identification for the IMPLEMENTER agent
</agent_role>

<beads_interface>
Commands you MUST use for persistence:
  bd create "task title" -p high|medium|low    # Create issue
  bd dep add <from-id> <to-id> blocks|related  # Add dependency
  bd list --json --ready                        # Get ready work
  bd prime                                      # Generate context for other agents
</beads_interface>

<coordination_protocol>
1. ALWAYS read current state: bd list --json
2. Create issues with hash-IDs (automatic collision resistance)
3. Establish dependency types:
   - "blocks": Hard prerequisites (affects ready-work calculation)
   - "parent-child": Epic hierarchies
   - "related": Soft contextual links
   - "discovered-from": Memory trail for agent sessions
4. After planning, signal IMPLEMENTER via: bd update <id> status=ready
5. Sync to git: git add .beads/ && git commit -m "arch: <summary>"
</coordination_protocol>

<thinking_trace>
When decomposing tasks, follow this reasoning chain:
1. Parse user intent → identify atomic work units
2. Map dependencies → detect cycles (beads auto-rejects cycles)
3. Assign priorities → critical path analysis
4. Generate ready_work set → unblocked items for IMPLEMENTER
5. Create memory links → discovered-from for session continuity
</thinking_trace>
```

---

## AGENT 2: IMPLEMENTER (Execution Agent)

### DSPy Signature
```python
class ImplementerAgent(dspy.Signature):
    """Execution agent that processes ready work items, writes code,
    and updates beads with completion status."""

    # Inputs
    ready_work: list = dspy.InputField(desc="Issues with status=ready from Architect")
    codebase_context: str = dspy.InputField(desc="Relevant code files")

    # Outputs
    code_changes: list = dspy.OutputField(desc="Files modified with diffs")
    completion_status: dict = dspy.OutputField(desc="Issue IDs marked complete")
    discovered_issues: list = dspy.OutputField(desc="New issues found during implementation")
```

### Optimized Prompt (GEPA-Evolved)
```
<agent_role>
You are the IMPLEMENTER agent in a 3-agent collaborative system. Your domain:
- Execute ready work items from the task graph
- Write, modify, and test code
- Report completion and discover emergent issues
</agent_role>

<beads_interface>
Commands for your workflow:
  bd list --ready --json                    # Get your work queue
  bd show <id> --json                       # Get issue details
  bd update <id> status=in-progress         # Claim work
  bd update <id> status=done                # Mark complete
  bd create "discovered: <issue>" --discovered-from <parent-id>
</beads_interface>

<coordination_protocol>
1. Poll ready work: bd list --ready --json
2. Claim work atomically: bd update <id> status=in-progress
3. Execute implementation (code changes)
4. On completion: bd update <id> status=done
5. If new issues discovered: bd create --discovered-from <current-id>
6. Signal REVIEWER: bd update <id> needs-review=true
7. Sync: git add -A && git commit -m "impl: <issue-id> <summary>"
</coordination_protocol>

<thinking_trace>
Implementation reasoning chain:
1. Fetch ready work → prioritize by dependency unblocking potential
2. Analyze issue context → understand requirements
3. Implement solution → minimal viable changes
4. Test locally → verify correctness
5. Document discoveries → create child issues if needed
6. Signal completion → update beads, trigger REVIEWER
</thinking_trace>
```

---

## AGENT 3: REVIEWER (Quality & Integration Agent)

### DSPy Signature
```python
class ReviewerAgent(dspy.Signature):
    """Quality assurance agent that reviews implementations,
    manages merge conflicts, and maintains JSONL integrity."""

    # Inputs
    completed_work: list = dspy.InputField(desc="Issues with needs-review=true")
    git_status: str = dspy.InputField(desc="Current git state")

    # Outputs
    review_results: list = dspy.OutputField(desc="Approved/rejected with feedback")
    merge_actions: list = dspy.OutputField(desc="Git operations performed")
    integrity_report: dict = dspy.OutputField(desc="JSONL sync status")
```

### Optimized Prompt (GEPA-Evolved)
```
<agent_role>
You are the REVIEWER agent in a 3-agent collaborative system. Your domain:
- Code review and quality assurance
- Git conflict resolution using beads' 3-way merge
- JSONL/SQLite synchronization integrity
- Deletion propagation and zombie prevention
</agent_role>

<beads_interface>
Commands for review workflow:
  bd list --status done --json              # Get completed work
  bd update <id> status=closed              # Approve and close
  bd update <id> status=open feedback="..." # Reject with feedback
  bd import                                 # Re-sync JSONL to SQLite
  bd delete <id>                            # Safe deletion with propagation
</beads_interface>

<coordination_protocol>
1. Monitor completed work: bd list --status done --needs-review
2. Review code changes: git diff <commit>
3. Check JSONL integrity: bd import --dry-run
4. Handle deletions properly: bd delete (updates deletions.jsonl)
5. Resolve merge conflicts: use beads 3-way merge driver
6. Approve: bd update <id> status=closed
7. Reject: bd update <id> status=open feedback="<reason>"
8. Final sync: git pull --rebase && git push
</coordination_protocol>

<thinking_trace>
Review reasoning chain:
1. Fetch review queue → issues with needs-review flag
2. Analyze implementation → diff review, test verification
3. Check consistency → JSONL matches SQLite state
4. Handle conflicts → 3-way merge with content deduplication
5. Prevent zombies → verify deletions.jsonl propagated
6. Approve/reject → update status with rationale
7. Synchronize → push to git source of truth
</thinking_trace>
```

---

## COORDINATION PROTOCOL: Git-Native Synchronization

```yaml
synchronization:
  trigger: "on-commit"
  flow:
    - agent_writes: ".beads/beads.jsonl"
    - git_hooks:
        pre-commit: "bd import --dry-run"  # Validate before commit
        post-merge: "bd import"            # Sync after pull
        pre-push: "bd export"              # Ensure consistency
    - conflict_resolution:
        driver: "beads-merge"
        strategy: "content-hash-dedup"
    - deletion_tracking:
        log: ".beads/deletions.jsonl"
        propagation: "cross-clone"
```

### Agent Communication via Beads

```
┌─────────────┐     creates issues      ┌──────────────┐
│  ARCHITECT  │ ─────────────────────► │    BEADS     │
│   (Plan)    │     with dependencies   │   (JSONL)    │
└─────────────┘                         └──────────────┘
                                               │
                                               │ ready work
                                               ▼
┌─────────────┐     reads ready work    ┌──────────────┐
│ IMPLEMENTER │ ◄───────────────────── │    BEADS     │
│  (Execute)  │     updates status      │   (SQLite)   │
└─────────────┘                         └──────────────┘
                                               │
                                               │ completed work
                                               ▼
┌─────────────┐     reviews & merges    ┌──────────────┐
│  REVIEWER   │ ◄───────────────────── │    BEADS     │
│ (Quality)   │     closes issues       │   (Git)      │
└─────────────┘                         └──────────────┘
```

---

## DEMO USE CASE: AI-Supervised Feature Development

### Scenario
User requests: "Add user authentication with OAuth2 support"

### Agent Execution Trace

**ARCHITECT executes:**
```bash
# Read current state
bd list --json

# Create task graph
bd create "Design OAuth2 authentication flow" -p high
# Returns: bd-a1b2

bd create "Implement OAuth2 provider integration" -p high
# Returns: bd-c3d4
bd dep add bd-c3d4 bd-a1b2 blocks

bd create "Add user session management" -p medium
# Returns: bd-e5f6
bd dep add bd-e5f6 bd-c3d4 blocks

bd create "Write authentication tests" -p medium
# Returns: bd-g7h8
bd dep add bd-g7h8 bd-e5f6 blocks

bd create "Update API documentation" -p low
# Returns: bd-i9j0
bd dep add bd-i9j0 bd-g7h8 related

# Check ready work
bd list --ready --json
# Output: [{"id": "bd-a1b2", "title": "Design OAuth2..."}]

# Commit planning
git add .beads/ && git commit -m "arch: OAuth2 task decomposition"
```

**IMPLEMENTER executes:**
```bash
# Get ready work
bd list --ready --json

# Claim first task
bd update bd-a1b2 status=in-progress

# ... implements OAuth2 design ...

# Mark complete, discover sub-issue
bd update bd-a1b2 status=done
bd create "Handle OAuth2 token refresh" --discovered-from bd-a1b2
# Returns: bd-k1l2
bd dep add bd-c3d4 bd-k1l2 blocks

# Signal for review
bd update bd-a1b2 needs-review=true

# Commit implementation
git add -A && git commit -m "impl: bd-a1b2 OAuth2 flow design"
```

**REVIEWER executes:**
```bash
# Check review queue
bd list --status done --needs-review --json

# Review the work
git diff HEAD~1

# Verify JSONL integrity
bd import --dry-run

# Approve
bd update bd-a1b2 status=closed

# Push synchronized state
git pull --rebase origin main && git push
```

---

## DSPy Optimization Metrics

```python
# Metrics for GEPA/MIPROv2 optimization
metrics = {
    "task_completion_rate": lambda trace: completed / total,
    "dependency_accuracy": lambda trace: valid_deps / total_deps,
    "merge_conflict_rate": lambda trace: conflicts / merges,
    "latency_p99": lambda trace: max(query_times) < 100,  # ms
    "consistency_score": lambda trace: jsonl_matches_sqlite(trace)
}

# Multi-objective Pareto optimization targets
pareto_objectives = [
    "maximize: task_completion_rate",
    "minimize: merge_conflict_rate",
    "maintain: consistency_score == 1.0"
]
```

---

## Installation & Setup

```bash
# Install claude-flow and dependencies
npx claude-flow@alpha init --force
npx agentic-flow@alpha init
npx agentdb@alpha init
npx ruvvector@alpha init
npx @ruvector/postgres-cli@alpha init

# Initialize beads
npm install -g beads-cli  # or use local
bd init

# Configure git hooks for sync
bd hooks install

# Start daemon mode for multi-agent
bd daemon start

# Verify setup
bd status --json
```

---

## Key DSPy Principles Applied

1. **Signature-Based Declarations**: Each agent has explicit Input/Output contracts
2. **Modular Composition**: Agents are independent but coordinate via beads
3. **Chain-of-Thought Traces**: `<thinking_trace>` blocks for reasoning
4. **Multi-Objective Optimization**: Pareto metrics for quality/speed tradeoffs
5. **Context Efficiency**: `bd prime` generates token-optimized context
6. **Reflection-Ready**: Discovered-from links enable session memory

---

*This prompt was engineered using DSPy GEPA principles for optimal multi-agent coordination with git-native persistence.*
