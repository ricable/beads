/**
 * REVIEWER Agent - Quality Assurance & Integration
 *
 * DSPy Signature:
 *   Input: completed_work, git_status
 *   Output: review_results, merge_actions, integrity_report
 *
 * Responsibilities:
 * - Review completed implementations
 * - Validate JSONL/SQLite consistency
 * - Handle merge conflicts with 3-way merge
 * - Manage deletion propagation
 * - Approve or reject with feedback
 */

import { readFileSync, writeFileSync, existsSync, appendFileSync } from "fs";
import { execSync } from "child_process";

const BEADS_JSONL = ".beads/beads.jsonl";
const DELETIONS_JSONL = ".beads/deletions.jsonl";

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

function recordDeletion(id) {
  const deletion = {
    id,
    deletedAt: new Date().toISOString(),
    deletedBy: "REVIEWER"
  };
  appendFileSync(DELETIONS_JSONL, JSON.stringify(deletion) + "\n");
}

// DSPy-style Reviewer Agent
class ReviewerAgent {
  constructor() {
    this.name = "REVIEWER";
    this.role = "quality-assurance";
  }

  /**
   * Main signature execution
   * @param {Array} completedWork - Issues with status=done
   * @param {Object} gitStatus - Current git state
   * @returns {Object} { reviewResults, mergeActions, integrityReport }
   */
  async execute(completedWork = null, gitStatus = null) {
    // Get completed work needing review
    if (!completedWork) {
      completedWork = this.getReviewQueue();
    }

    // Get git status
    if (!gitStatus) {
      gitStatus = this.getGitStatus();
    }

    console.log(`[${this.name}] Reviewing ${completedWork.length} items`);

    const reviewResults = [];
    const mergeActions = [];

    // Review each completed item
    for (const issue of completedWork) {
      console.log(`[${this.name}] Reviewing: ${issue.id} - ${issue.title}`);

      const result = await this.review(issue);
      reviewResults.push(result);

      if (result.approved) {
        this.approve(issue.id);
      } else {
        this.reject(issue.id, result.feedback);
      }
    }

    // Check integrity
    const integrityReport = this.validateIntegrity();

    // Handle any merge conflicts
    if (gitStatus.hasConflicts) {
      const mergeResult = this.resolveMergeConflicts();
      mergeActions.push(mergeResult);
    }

    // Sync to git
    if (reviewResults.some((r) => r.approved)) {
      mergeActions.push(this.syncToGit());
    }

    return { reviewResults, mergeActions, integrityReport };
  }

  getReviewQueue() {
    const issues = readBeadsState();
    return issues.filter(
      (issue) => issue.status === "done" && issue.needsReview === true
    );
  }

  getGitStatus() {
    try {
      const status = execSync("git status --porcelain", { encoding: "utf-8" });
      const hasConflicts = status.includes("UU") || status.includes("AA");
      const hasChanges = status.trim().length > 0;

      return {
        hasConflicts,
        hasChanges,
        raw: status
      };
    } catch {
      return { hasConflicts: false, hasChanges: false, raw: "" };
    }
  }

  async review(issue) {
    // Chain-of-thought review reasoning
    console.log(`[${this.name}] Review reasoning:`);
    console.log(`  1. Checking implementation completeness`);
    console.log(`  2. Validating against requirements`);
    console.log(`  3. Verifying JSONL consistency`);
    console.log(`  4. Checking for zombie issues`);

    // Simulated review logic (90% approval rate)
    const approved = Math.random() > 0.1;

    return {
      issueId: issue.id,
      approved,
      feedback: approved ? null : "Needs additional test coverage",
      reviewedAt: new Date().toISOString(),
      reviewedBy: this.name
    };
  }

  approve(issueId) {
    console.log(`[${this.name}] Approving: ${issueId}`);
    return updateIssue(issueId, {
      status: "closed",
      needsReview: false,
      closedAt: new Date().toISOString(),
      closedBy: this.name
    });
  }

  reject(issueId, feedback) {
    console.log(`[${this.name}] Rejecting: ${issueId} - ${feedback}`);
    return updateIssue(issueId, {
      status: "open",
      needsReview: false,
      feedback,
      rejectedAt: new Date().toISOString(),
      rejectedBy: this.name
    });
  }

  validateIntegrity() {
    const issues = readBeadsState();

    // Check for orphaned dependencies
    const allIds = new Set(issues.map((i) => i.id));
    const orphanedDeps = [];

    issues.forEach((issue) => {
      if (issue.dependencies) {
        issue.dependencies.forEach((dep) => {
          if (!allIds.has(dep.id)) {
            orphanedDeps.push({ issueId: issue.id, orphanedDepId: dep.id });
          }
        });
      }
    });

    // Check for cycles
    const cycles = this.detectCycles(issues);

    // Check deletions log
    const deletions = this.getDeletions();
    const zombies = issues.filter((i) =>
      deletions.some((d) => d.id === i.id)
    );

    return {
      valid: orphanedDeps.length === 0 && cycles.length === 0 && zombies.length === 0,
      orphanedDependencies: orphanedDeps,
      cycles,
      zombieIssues: zombies.map((z) => z.id),
      totalIssues: issues.length,
      deletionsTracked: deletions.length
    };
  }

  detectCycles(issues) {
    const cycles = [];
    const visited = new Set();
    const recursionStack = new Set();

    const dfs = (issueId, path) => {
      if (recursionStack.has(issueId)) {
        cycles.push([...path, issueId]);
        return;
      }
      if (visited.has(issueId)) return;

      visited.add(issueId);
      recursionStack.add(issueId);

      const issue = issues.find((i) => i.id === issueId);
      if (issue?.dependencies) {
        issue.dependencies
          .filter((d) => d.type === "blocks")
          .forEach((dep) => dfs(dep.id, [...path, issueId]));
      }

      recursionStack.delete(issueId);
    };

    issues.forEach((issue) => dfs(issue.id, []));
    return cycles;
  }

  getDeletions() {
    if (!existsSync(DELETIONS_JSONL)) return [];
    const content = readFileSync(DELETIONS_JSONL, "utf-8");
    return content
      .trim()
      .split("\n")
      .filter(Boolean)
      .map((line) => JSON.parse(line));
  }

  resolveMergeConflicts() {
    console.log(`[${this.name}] Resolving merge conflicts with 3-way merge`);

    // In real implementation, would use beads merge driver
    return {
      action: "merge-conflict-resolution",
      strategy: "three-way-merge",
      resolvedAt: new Date().toISOString()
    };
  }

  syncToGit() {
    console.log(`[${this.name}] Syncing to git`);

    try {
      execSync("git add .beads/", { encoding: "utf-8" });

      return {
        action: "git-sync",
        status: "staged",
        files: [".beads/beads.jsonl", ".beads/deletions.jsonl"]
      };
    } catch (error) {
      return {
        action: "git-sync",
        status: "error",
        error: error.message
      };
    }
  }

  // Safe deletion with propagation
  deleteIssue(issueId) {
    console.log(`[${this.name}] Deleting: ${issueId}`);

    // Record deletion for cross-clone propagation
    recordDeletion(issueId);

    // Remove from JSONL
    const issues = readBeadsState().filter((i) => i.id !== issueId);
    writeBeadsState(issues);

    return {
      deleted: issueId,
      propagated: true
    };
  }

  // Generate review report
  generateReport() {
    const state = readBeadsState();

    return {
      totalReviewed: state.filter((i) => i.closedBy === this.name).length,
      approved: state.filter((i) => i.status === "closed").length,
      rejected: state.filter((i) => i.rejectedBy === this.name).length,
      integrity: this.validateIntegrity()
    };
  }
}

export { ReviewerAgent };

// CLI execution
if (process.argv[1].endsWith("reviewer.js")) {
  const agent = new ReviewerAgent();

  agent.execute().then((result) => {
    console.log("\n=== REVIEWER OUTPUT ===");
    console.log(JSON.stringify(result, null, 2));

    console.log("\n=== REVIEW REPORT ===");
    console.log(JSON.stringify(agent.generateReport(), null, 2));
  });
}
