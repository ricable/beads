/**
 * IMPLEMENTER Agent - Execution
 *
 * DSPy Signature:
 *   Input: ready_work, codebase_context
 *   Output: code_changes, completion_status, discovered_issues
 *
 * Responsibilities:
 * - Process ready work items from task graph
 * - Execute code changes
 * - Update issue status in beads
 * - Discover and report emergent issues
 */

import { createHash } from "crypto";
import { readFileSync, writeFileSync, existsSync } from "fs";

const BEADS_JSONL = ".beads/beads.jsonl";

function generateId(title) {
  const hash = createHash("sha256")
    .update(title + Date.now())
    .digest("hex")
    .slice(0, 4);
  return `bd-${hash}`;
}

function readBeadsState() {
  if (!existsSync(BEADS_JSONL)) return [];
  const content = readFileSync(BEADS_JSONL, "utf-8");
  return content
    .trim()
    .split("\n")
    .filter(Boolean)
    .map((line) => JSON.parse(line));
}

function writeBeadsState(issues) {
  writeFileSync(
    BEADS_JSONL,
    issues.map((i) => JSON.stringify(i)).join("\n") + "\n"
  );
}

function updateIssue(id, updates) {
  const issues = readBeadsState();
  const updated = issues.map((issue) =>
    issue.id === id ? { ...issue, ...updates, updatedAt: new Date().toISOString() } : issue
  );
  writeBeadsState(updated);
  return updated.find((i) => i.id === id);
}

function appendIssue(issue) {
  const line = JSON.stringify(issue) + "\n";
  writeFileSync(BEADS_JSONL, line, { flag: "a" });
  return issue;
}

// DSPy-style Implementer Agent
class ImplementerAgent {
  constructor() {
    this.name = "IMPLEMENTER";
    this.role = "execution";
  }

  /**
   * Main signature execution
   * @param {Array} readyWork - Issues ready for implementation
   * @param {Object} codebaseContext - Relevant code files
   * @returns {Object} { codeChanges, completionStatus, discoveredIssues }
   */
  async execute(readyWork = null, codebaseContext = {}) {
    // Get ready work if not provided
    if (!readyWork) {
      readyWork = this.getReadyWork();
    }

    console.log(`[${this.name}] Processing ${readyWork.length} ready items`);

    const codeChanges = [];
    const completionStatus = {};
    const discoveredIssues = [];

    for (const issue of readyWork) {
      console.log(`[${this.name}] Working on: ${issue.id} - ${issue.title}`);

      // Claim the work
      this.claimWork(issue.id);

      // Execute implementation (simulated)
      const result = await this.implement(issue, codebaseContext);

      codeChanges.push(...result.changes);
      completionStatus[issue.id] = result.status;

      // Handle discovered issues
      if (result.discoveries.length > 0) {
        for (const discovery of result.discoveries) {
          const newIssue = this.createDiscoveredIssue(discovery, issue.id);
          discoveredIssues.push(newIssue);
        }
      }

      // Mark complete and request review
      if (result.status === "done") {
        this.completeWork(issue.id);
      }
    }

    return { codeChanges, completionStatus, discoveredIssues };
  }

  getReadyWork() {
    const issues = readBeadsState();
    return issues.filter((issue) => {
      if (issue.status !== "open") return false;
      if (!issue.dependencies || issue.dependencies.length === 0) return true;

      const blockingDeps = issue.dependencies.filter((d) => d.type === "blocks");
      return blockingDeps.every((dep) => {
        const blocker = issues.find((i) => i.id === dep.id);
        return blocker && (blocker.status === "done" || blocker.status === "closed");
      });
    });
  }

  claimWork(issueId) {
    console.log(`[${this.name}] Claiming: ${issueId}`);
    return updateIssue(issueId, {
      status: "in-progress",
      assignee: this.name
    });
  }

  async implement(issue, context) {
    // Chain-of-thought implementation reasoning
    console.log(`[${this.name}] Reasoning:`);
    console.log(`  1. Analyzing issue: ${issue.title}`);
    console.log(`  2. Identifying affected files`);
    console.log(`  3. Planning minimal changes`);
    console.log(`  4. Executing implementation`);

    // Simulated implementation result
    const changes = [
      {
        file: `src/${issue.type || "feature"}.js`,
        diff: `+ // Implementation for: ${issue.title}`,
        linesChanged: Math.floor(Math.random() * 50) + 10
      }
    ];

    // Sometimes discover new issues during implementation
    const discoveries = [];
    if (Math.random() > 0.7) {
      discoveries.push({
        title: `Discovered: Edge case in ${issue.title}`,
        priority: "medium",
        type: "bugfix"
      });
    }

    return {
      changes,
      status: "done",
      discoveries
    };
  }

  createDiscoveredIssue(discovery, parentId) {
    const issue = {
      id: generateId(discovery.title),
      title: discovery.title,
      status: "open",
      priority: discovery.priority,
      type: discovery.type,
      dependencies: [
        {
          id: parentId,
          type: "discovered-from"
        }
      ],
      createdAt: new Date().toISOString(),
      createdBy: this.name,
      meta: {
        discoveredDuring: parentId
      }
    };

    console.log(`[${this.name}] Created discovered issue: ${issue.id}`);
    return appendIssue(issue);
  }

  completeWork(issueId) {
    console.log(`[${this.name}] Completing: ${issueId}`);
    return updateIssue(issueId, {
      status: "done",
      needsReview: true,
      completedAt: new Date().toISOString()
    });
  }

  // Generate implementation report
  generateReport() {
    const state = readBeadsState();
    const myWork = state.filter((i) => i.assignee === this.name);

    return {
      claimed: myWork.filter((i) => i.status === "in-progress").length,
      completed: myWork.filter((i) => i.status === "done").length,
      discovered: state.filter((i) => i.createdBy === this.name).length
    };
  }
}

export { ImplementerAgent };

// CLI execution
if (process.argv[1].endsWith("implementer.js")) {
  const agent = new ImplementerAgent();

  agent.execute().then((result) => {
    console.log("\n=== IMPLEMENTER OUTPUT ===");
    console.log(JSON.stringify(result, null, 2));

    console.log("\n=== IMPLEMENTATION REPORT ===");
    console.log(JSON.stringify(agent.generateReport(), null, 2));
  });
}
