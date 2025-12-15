/**
 * Claude-Flow Configuration for Multi-Agent Beads Orchestration
 *
 * DSPy-optimized configuration for 3 collaborating agents:
 * - ARCHITECT: Strategic planning and task decomposition
 * - IMPLEMENTER: Code execution and task completion
 * - REVIEWER: Quality assurance and git synchronization
 */

export default {
  name: "beads-multi-agent",
  version: "1.0.0",

  // Agent orchestration settings
  orchestration: {
    mode: "swarm",
    coordination: "git-native",
    maxConcurrentAgents: 3,
    communicationChannel: "beads-jsonl"
  },

  // Shared persistence layer (Beads)
  persistence: {
    type: "beads",
    paths: {
      jsonl: ".beads/beads.jsonl",
      deletions: ".beads/deletions.jsonl",
      sqliteCache: ".beads/beads.db"
    },
    sync: {
      mode: "git",
      autoCommit: false,
      conflictResolution: "three-way-merge"
    }
  },

  // Agent definitions
  agents: {
    architect: {
      name: "ARCHITECT",
      role: "strategic-planning",
      capabilities: [
        "task-decomposition",
        "dependency-graph-creation",
        "ready-work-identification",
        "epic-hierarchy-management"
      ],
      beadsCommands: [
        "create",
        "dep add",
        "list --json",
        "prime"
      ],
      outputSignature: {
        taskGraph: "list<Issue>",
        readyWork: "list<IssueId>",
        reasoning: "string"
      }
    },

    implementer: {
      name: "IMPLEMENTER",
      role: "execution",
      capabilities: [
        "code-writing",
        "task-execution",
        "issue-discovery",
        "status-updates"
      ],
      beadsCommands: [
        "list --ready",
        "show",
        "update",
        "create --discovered-from"
      ],
      outputSignature: {
        codeChanges: "list<FileDiff>",
        completionStatus: "dict<IssueId, Status>",
        discoveredIssues: "list<Issue>"
      }
    },

    reviewer: {
      name: "REVIEWER",
      role: "quality-assurance",
      capabilities: [
        "code-review",
        "merge-conflict-resolution",
        "jsonl-integrity-validation",
        "deletion-propagation"
      ],
      beadsCommands: [
        "list --status done",
        "update",
        "import",
        "delete"
      ],
      outputSignature: {
        reviewResults: "list<ReviewResult>",
        mergeActions: "list<GitOperation>",
        integrityReport: "dict"
      }
    }
  },

  // Memory and context settings
  memory: {
    type: "hybrid",
    backends: ["agentdb", "beads-discovered-from"],
    vectorSearch: {
      enabled: true,
      indexType: "hnsw"
    }
  },

  // Git integration hooks
  gitHooks: {
    preCommit: "node scripts/validate-jsonl.js",
    postMerge: "node scripts/sync-sqlite.js",
    prePush: "node scripts/check-consistency.js"
  },

  // Workflow definitions
  workflows: {
    featureDevelopment: {
      stages: ["plan", "implement", "review"],
      agentMapping: {
        plan: "architect",
        implement: "implementer",
        review: "reviewer"
      },
      transitions: {
        "plan -> implement": {
          trigger: "ready-work-available",
          beadsQuery: "bd list --ready --json | jq length > 0"
        },
        "implement -> review": {
          trigger: "needs-review-flag",
          beadsQuery: "bd list --needs-review --json | jq length > 0"
        },
        "review -> plan": {
          trigger: "rejected-with-feedback",
          beadsQuery: "bd list --status open --has-feedback --json | jq length > 0"
        }
      }
    }
  },

  // DSPy optimization metrics
  metrics: {
    taskCompletionRate: {
      formula: "completed_issues / total_issues",
      target: 0.95
    },
    dependencyAccuracy: {
      formula: "valid_dependencies / total_dependencies",
      target: 1.0
    },
    mergeConflictRate: {
      formula: "conflicts / total_merges",
      target: 0.0
    },
    queryLatencyP99: {
      formula: "percentile(query_times, 99)",
      target: 100  // milliseconds
    }
  }
};
