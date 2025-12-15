#!/usr/bin/env node
/**
 * Multi-Agent Orchestrator
 *
 * Coordinates the 3 collaborating agents (ARCHITECT, IMPLEMENTER, REVIEWER)
 * using Beads as the shared state layer with git-native synchronization.
 *
 * DSPy-optimized workflow:
 * 1. ARCHITECT decomposes tasks → creates dependency graph
 * 2. IMPLEMENTER processes ready work → updates status
 * 3. REVIEWER validates & approves → syncs to git
 */

import { ArchitectAgent } from "../agents/architect.js";
import { ImplementerAgent } from "../agents/implementer.js";
import { ReviewerAgent } from "../agents/reviewer.js";
import { execSync } from "child_process";
import { existsSync, mkdirSync } from "fs";

// Ensure .beads directory exists
if (!existsSync(".beads")) {
  mkdirSync(".beads", { recursive: true });
}

class MultiAgentOrchestrator {
  constructor() {
    this.architect = new ArchitectAgent();
    this.implementer = new ImplementerAgent();
    this.reviewer = new ReviewerAgent();

    this.config = {
      maxIterations: 10,
      syncInterval: 5000, // ms
      coordinationMode: "sequential" // or "parallel"
    };
  }

  async run(userRequest) {
    console.log("╔════════════════════════════════════════════════════════════╗");
    console.log("║     BEADS MULTI-AGENT ORCHESTRATOR                        ║");
    console.log("║     Git-Native Collaboration with DSPy Optimization       ║");
    console.log("╚════════════════════════════════════════════════════════════╝\n");

    console.log(`📋 User Request: "${userRequest}"\n`);

    let iteration = 0;
    let complete = false;

    while (!complete && iteration < this.config.maxIterations) {
      iteration++;
      console.log(`\n${"═".repeat(60)}`);
      console.log(`ITERATION ${iteration}`);
      console.log(`${"═".repeat(60)}\n`);

      // Phase 1: ARCHITECT plans
      console.log("🏗️  PHASE 1: ARCHITECT (Planning)\n");
      const architectResult = await this.architect.execute(userRequest);

      console.log(`   Created ${architectResult.taskGraph.length} tasks`);
      console.log(`   Ready work: ${architectResult.readyWork.length} items\n`);

      if (architectResult.readyWork.length === 0 && iteration > 1) {
        console.log("   No more ready work - checking completion status...\n");
      }

      // Phase 2: IMPLEMENTER executes
      console.log("⚙️  PHASE 2: IMPLEMENTER (Execution)\n");
      const implementerResult = await this.implementer.execute();

      console.log(`   Processed: ${Object.keys(implementerResult.completionStatus).length} items`);
      console.log(`   Discovered: ${implementerResult.discoveredIssues.length} new issues\n`);

      // Phase 3: REVIEWER validates
      console.log("✅ PHASE 3: REVIEWER (Quality Assurance)\n");
      const reviewerResult = await this.reviewer.execute();

      const approved = reviewerResult.reviewResults.filter((r) => r.approved).length;
      const rejected = reviewerResult.reviewResults.filter((r) => !r.approved).length;

      console.log(`   Approved: ${approved}`);
      console.log(`   Rejected: ${rejected}`);
      console.log(`   Integrity: ${reviewerResult.integrityReport.valid ? "VALID" : "ISSUES FOUND"}\n`);

      // Check completion
      complete = this.checkCompletion();

      if (!complete) {
        // Only continue if there's more work or discoveries
        const hasMoreWork = this.implementer.getReadyWork().length > 0;
        const hasReviewQueue = this.reviewer.getReviewQueue().length > 0;

        if (!hasMoreWork && !hasReviewQueue && implementerResult.discoveredIssues.length === 0) {
          complete = true;
        }
      }
    }

    // Final sync to git
    console.log("\n📦 FINAL SYNC\n");
    this.syncToGit();

    // Generate final report
    return this.generateFinalReport();
  }

  checkCompletion() {
    const prime = this.architect.generatePrime();
    return prime.openIssues === 0;
  }

  syncToGit() {
    try {
      console.log("   Staging beads files...");
      execSync("git add .beads/", { encoding: "utf-8" });

      const status = execSync("git status --porcelain .beads/", { encoding: "utf-8" });
      if (status.trim()) {
        console.log("   Changes staged for commit");
      } else {
        console.log("   No changes to commit");
      }
    } catch (error) {
      console.log(`   Git sync warning: ${error.message}`);
    }
  }

  generateFinalReport() {
    const architectPrime = this.architect.generatePrime();
    const implementerReport = this.implementer.generateReport();
    const reviewerReport = this.reviewer.generateReport();

    const report = {
      orchestration: {
        status: "complete",
        timestamp: new Date().toISOString()
      },
      summary: {
        totalTasks: architectPrime.totalIssues,
        openTasks: architectPrime.openIssues,
        completionRate:
          architectPrime.totalIssues > 0
            ? ((architectPrime.totalIssues - architectPrime.openIssues) /
                architectPrime.totalIssues *
                100).toFixed(1) + "%"
            : "N/A"
      },
      agents: {
        architect: {
          tasksCreated: architectPrime.totalIssues,
          readyWorkGenerated: architectPrime.readyWork.length
        },
        implementer: implementerReport,
        reviewer: reviewerReport
      },
      integrity: reviewerReport.integrity
    };

    console.log("\n╔════════════════════════════════════════════════════════════╗");
    console.log("║                    FINAL REPORT                            ║");
    console.log("╚════════════════════════════════════════════════════════════╝\n");
    console.log(JSON.stringify(report, null, 2));

    return report;
  }
}

// CLI execution
const request = process.argv[2] || "Add user authentication with OAuth2 support";

const orchestrator = new MultiAgentOrchestrator();
orchestrator.run(request).then((report) => {
  console.log("\n✨ Orchestration complete!\n");
  process.exit(report.summary.openTasks === 0 ? 0 : 1);
});
