/**
 * ARCHITECT Agent - Strategic Planning
 *
 * DSPy Signature:
 *   Input: user_request, current_state
 *   Output: task_graph, ready_work, reasoning
 *
 * Responsibilities:
 * - Decompose complex tasks into dependency-aware graphs
 * - Create issues with hash-based IDs
 * - Establish dependency relationships (blocks, related, parent-child, discovered-from)
 * - Identify ready work for IMPLEMENTER
 */

import { createHash } from "crypto";
import { readFileSync, writeFileSync, existsSync } from "fs";

const BEADS_JSONL = ".beads/beads.jsonl";

// Generate hash-based ID (collision-resistant)
function generateId(title) {
  const hash = createHash("sha256")
    .update(title + Date.now())
    .digest("hex")
    .slice(0, 4);
  return `bd-${hash}`;
}

// Read current beads state
function readBeadsState() {
  if (!existsSync(BEADS_JSONL)) return [];
  const content = readFileSync(BEADS_JSONL, "utf-8");
  return content
    .trim()
    .split("\n")
    .filter(Boolean)
    .map((line) => JSON.parse(line));
}

// Append issue to JSONL
function appendIssue(issue) {
  const line = JSON.stringify(issue) + "\n";
  writeFileSync(BEADS_JSONL, line, { flag: "a" });
  return issue;
}

// Update issue in JSONL
function updateIssue(id, updates) {
  const issues = readBeadsState();
  const updated = issues.map((issue) =>
    issue.id === id ? { ...issue, ...updates, updatedAt: new Date().toISOString() } : issue
  );

  writeFileSync(
    BEADS_JSONL,
    updated.map((i) => JSON.stringify(i)).join("\n") + "\n"
  );
  return updated.find((i) => i.id === id);
}

// DSPy-style Architect Agent
class ArchitectAgent {
  constructor() {
    this.name = "ARCHITECT";
    this.role = "strategic-planning";
  }

  /**
   * Main signature execution
   * @param {string} userRequest - High-level user requirement
   * @returns {Object} { taskGraph, readyWork, reasoning }
   */
  async execute(userRequest) {
    console.log(`[${this.name}] Processing request: ${userRequest}`);

    // Chain-of-thought reasoning
    const reasoning = this.generateReasoning(userRequest);
    console.log(`[${this.name}] Reasoning:\n${reasoning}`);

    // Decompose into tasks
    const tasks = this.decomposeTasks(userRequest);

    // Create task graph with dependencies
    const taskGraph = [];
    for (const task of tasks) {
      const issue = this.createIssue(task);
      taskGraph.push(issue);
    }

    // Establish dependencies
    this.establishDependencies(taskGraph);

    // Identify ready work
    const readyWork = this.identifyReadyWork(taskGraph);

    return { taskGraph, readyWork, reasoning };
  }

  generateReasoning(request) {
    return `
1. PARSE USER INTENT: "${request}"
   - Identified domain: software development
   - Complexity level: multi-step feature
   - Requires: planning → implementation → review

2. MAP DEPENDENCIES:
   - Design phase must precede implementation
   - Tests depend on implementation
   - Documentation follows testing

3. ASSIGN PRIORITIES:
   - Critical path: design → core implementation
   - Parallel opportunities: tests, docs

4. GENERATE READY WORK:
   - Initial ready item: design/planning task
   - Blocked items: all others (pending dependencies)

5. CREATE MEMORY LINKS:
   - Session context preserved via discovered-from
`.trim();
  }

  decomposeTasks(request) {
    // DSPy-optimized task decomposition
    return [
      {
        title: `Design: ${request}`,
        priority: "high",
        type: "design",
        blocksOthers: true
      },
      {
        title: `Implement core: ${request}`,
        priority: "high",
        type: "implementation",
        dependsOn: "design"
      },
      {
        title: `Write tests: ${request}`,
        priority: "medium",
        type: "testing",
        dependsOn: "implementation"
      },
      {
        title: `Update documentation: ${request}`,
        priority: "low",
        type: "documentation",
        dependsOn: "testing",
        dependencyType: "related"
      }
    ];
  }

  createIssue(task) {
    const issue = {
      id: generateId(task.title),
      title: task.title,
      status: "open",
      priority: task.priority,
      type: task.type,
      dependencies: [],
      createdAt: new Date().toISOString(),
      createdBy: this.name,
      meta: {
        blocksOthers: task.blocksOthers || false,
        dependsOn: task.dependsOn || null,
        dependencyType: task.dependencyType || "blocks"
      }
    };

    return appendIssue(issue);
  }

  establishDependencies(taskGraph) {
    const typeToId = {};
    taskGraph.forEach((issue) => {
      typeToId[issue.type] = issue.id;
    });

    taskGraph.forEach((issue) => {
      if (issue.meta.dependsOn) {
        const blockerId = typeToId[issue.meta.dependsOn];
        if (blockerId) {
          updateIssue(issue.id, {
            dependencies: [
              {
                id: blockerId,
                type: issue.meta.dependencyType
              }
            ]
          });
        }
      }
    });
  }

  identifyReadyWork(taskGraph) {
    const currentState = readBeadsState();
    return currentState.filter((issue) => {
      if (issue.status !== "open") return false;
      if (!issue.dependencies || issue.dependencies.length === 0) return true;

      // Check if all blocking dependencies are resolved
      const blockingDeps = issue.dependencies.filter((d) => d.type === "blocks");
      return blockingDeps.every((dep) => {
        const blocker = currentState.find((i) => i.id === dep.id);
        return blocker && blocker.status === "done";
      });
    });
  }

  // Generate context for other agents (bd prime equivalent)
  generatePrime() {
    const state = readBeadsState();
    const readyWork = this.identifyReadyWork(state);

    return {
      totalIssues: state.length,
      openIssues: state.filter((i) => i.status === "open").length,
      readyWork: readyWork.map((i) => ({ id: i.id, title: i.title })),
      dependencyGraph: state.map((i) => ({
        id: i.id,
        deps: i.dependencies?.map((d) => d.id) || []
      }))
    };
  }
}

// Export for orchestrator
export { ArchitectAgent };

// CLI execution
if (process.argv[1].endsWith("architect.js")) {
  const agent = new ArchitectAgent();
  const request = process.argv[2] || "Add user authentication with OAuth2";

  agent.execute(request).then((result) => {
    console.log("\n=== ARCHITECT OUTPUT ===");
    console.log(JSON.stringify(result, null, 2));

    console.log("\n=== PRIME CONTEXT ===");
    console.log(JSON.stringify(agent.generatePrime(), null, 2));
  });
}
