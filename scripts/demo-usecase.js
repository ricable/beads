#!/usr/bin/env node
/**
 * Demo Use Case: AI-Supervised Feature Development
 *
 * This demo showcases the 3-agent collaboration system building
 * a feature from scratch using beads for persistent state.
 *
 * Based on: https://deepwiki.com/steveyegge/beads
 */

import { ArchitectAgent } from "../agents/architect.js";
import { ImplementerAgent } from "../agents/implementer.js";
import { ReviewerAgent } from "../agents/reviewer.js";
import { readFileSync, writeFileSync, existsSync, mkdirSync } from "fs";

const BEADS_JSONL = ".beads/beads.jsonl";

// Reset beads state for demo
function resetBeadsState() {
  if (!existsSync(".beads")) {
    mkdirSync(".beads", { recursive: true });
  }
  writeFileSync(BEADS_JSONL, "");
  writeFileSync(".beads/deletions.jsonl", "");
}

// Pretty print beads state
function printBeadsState(title) {
  console.log(`\n${"─".repeat(60)}`);
  console.log(`📊 BEADS STATE: ${title}`);
  console.log(`${"─".repeat(60)}`);

  if (!existsSync(BEADS_JSONL)) {
    console.log("  (empty)\n");
    return;
  }

  const content = readFileSync(BEADS_JSONL, "utf-8");
  const issues = content
    .trim()
    .split("\n")
    .filter(Boolean)
    .map((line) => JSON.parse(line));

  if (issues.length === 0) {
    console.log("  (empty)\n");
    return;
  }

  issues.forEach((issue) => {
    const statusIcon = {
      open: "⚪",
      "in-progress": "🔵",
      done: "🟢",
      closed: "✅"
    }[issue.status] || "⚪";

    const priorityIcon = {
      high: "🔴",
      medium: "🟡",
      low: "🟢"
    }[issue.priority] || "⚪";

    console.log(`  ${statusIcon} ${issue.id} [${priorityIcon}] ${issue.title}`);

    if (issue.dependencies?.length > 0) {
      console.log(
        `     └─ deps: ${issue.dependencies.map((d) => `${d.id}(${d.type})`).join(", ")}`
      );
    }
  });
  console.log();
}

// Simulate git operations
function simulateGitCommit(message) {
  console.log(`\n📦 GIT: ${message}`);
  console.log(`   $ git add .beads/`);
  console.log(`   $ git commit -m "${message}"`);
}

async function runDemo() {
  console.log("╔════════════════════════════════════════════════════════════╗");
  console.log("║        BEADS MULTI-AGENT COLLABORATION DEMO                ║");
  console.log("║                                                            ║");
  console.log("║  3 Agents • Git-Native • DSPy-Optimized                    ║");
  console.log("╚════════════════════════════════════════════════════════════╝\n");

  // Initialize
  resetBeadsState();
  const architect = new ArchitectAgent();
  const implementer = new ImplementerAgent();
  const reviewer = new ReviewerAgent();

  const userRequest = "Build a REST API with user authentication";

  console.log(`\n🎯 USER REQUEST: "${userRequest}"\n`);

  // ═══════════════════════════════════════════════════════════════
  // STEP 1: ARCHITECT creates task graph
  // ═══════════════════════════════════════════════════════════════
  console.log("\n╭────────────────────────────────────────────────────────────╮");
  console.log("│  STEP 1: ARCHITECT - Strategic Planning                   │");
  console.log("╰────────────────────────────────────────────────────────────╯");

  console.log("\n🧠 Chain-of-Thought Reasoning:");
  console.log("   1. Parse user intent → REST API + authentication");
  console.log("   2. Identify atomic tasks → design, implement, test, docs");
  console.log("   3. Map dependencies → sequential with parallel opportunities");
  console.log("   4. Generate ready work → design task unblocked");

  const architectResult = await architect.execute(userRequest);

  printBeadsState("After ARCHITECT Planning");

  console.log("📤 ARCHITECT Output:");
  console.log(`   • Tasks created: ${architectResult.taskGraph.length}`);
  console.log(`   • Ready work: ${architectResult.readyWork.length} item(s)`);
  console.log(
    `   • Ready: ${architectResult.readyWork.map((i) => i.id).join(", ") || "none"}`
  );

  simulateGitCommit("arch: REST API task decomposition");

  // ═══════════════════════════════════════════════════════════════
  // STEP 2: IMPLEMENTER processes ready work
  // ═══════════════════════════════════════════════════════════════
  console.log("\n╭────────────────────────────────────────────────────────────╮");
  console.log("│  STEP 2: IMPLEMENTER - Execution                          │");
  console.log("╰────────────────────────────────────────────────────────────╯");

  console.log("\n⚙️  Processing ready work queue...");

  const implementerResult = await implementer.execute();

  printBeadsState("After IMPLEMENTER Execution");

  console.log("📤 IMPLEMENTER Output:");
  console.log(`   • Items processed: ${Object.keys(implementerResult.completionStatus).length}`);
  console.log(`   • Discoveries: ${implementerResult.discoveredIssues.length}`);

  if (implementerResult.discoveredIssues.length > 0) {
    console.log("   • Discovered issues:");
    implementerResult.discoveredIssues.forEach((issue) => {
      console.log(`     └─ ${issue.id}: ${issue.title}`);
    });
  }

  simulateGitCommit("impl: completed design phase");

  // ═══════════════════════════════════════════════════════════════
  // STEP 3: REVIEWER validates and approves
  // ═══════════════════════════════════════════════════════════════
  console.log("\n╭────────────────────────────────────────────────────────────╮");
  console.log("│  STEP 3: REVIEWER - Quality Assurance                     │");
  console.log("╰────────────────────────────────────────────────────────────╯");

  console.log("\n🔍 Review reasoning:");
  console.log("   1. Check implementation completeness");
  console.log("   2. Validate JSONL consistency");
  console.log("   3. Verify no zombie issues");
  console.log("   4. Approve or reject with feedback");

  const reviewerResult = await reviewer.execute();

  printBeadsState("After REVIEWER Validation");

  console.log("📤 REVIEWER Output:");
  console.log(`   • Reviewed: ${reviewerResult.reviewResults.length}`);
  console.log(`   • Approved: ${reviewerResult.reviewResults.filter((r) => r.approved).length}`);
  console.log(`   • Rejected: ${reviewerResult.reviewResults.filter((r) => !r.approved).length}`);
  console.log(`   • Integrity: ${reviewerResult.integrityReport.valid ? "✅ VALID" : "❌ ISSUES"}`);

  simulateGitCommit("review: approved design phase");

  // ═══════════════════════════════════════════════════════════════
  // ITERATION 2: Continue with unblocked work
  // ═══════════════════════════════════════════════════════════════
  console.log("\n╭────────────────────────────────────────────────────────────╮");
  console.log("│  ITERATION 2: Processing Unblocked Tasks                  │");
  console.log("╰────────────────────────────────────────────────────────────╯");

  // Get newly unblocked work
  const readyWork = implementer.getReadyWork();
  console.log(`\n🔓 Newly unblocked: ${readyWork.length} task(s)`);

  if (readyWork.length > 0) {
    console.log("\n⚙️  IMPLEMENTER processing unblocked tasks...");
    await implementer.execute();

    printBeadsState("After Iteration 2 Implementation");

    console.log("\n🔍 REVIEWER validating iteration 2...");
    await reviewer.execute();

    printBeadsState("After Iteration 2 Review");
  }

  // ═══════════════════════════════════════════════════════════════
  // FINAL SUMMARY
  // ═══════════════════════════════════════════════════════════════
  console.log("\n╔════════════════════════════════════════════════════════════╗");
  console.log("║                    DEMO COMPLETE                           ║");
  console.log("╚════════════════════════════════════════════════════════════╝\n");

  const prime = architect.generatePrime();
  const implReport = implementer.generateReport();
  const revReport = reviewer.generateReport();

  console.log("📊 FINAL METRICS:");
  console.log(`   • Total tasks: ${prime.totalIssues}`);
  console.log(`   • Open: ${prime.openIssues}`);
  console.log(`   • Completed: ${implReport.completed}`);
  console.log(`   • Reviewed: ${revReport.totalReviewed}`);
  console.log(`   • Discovered during work: ${implReport.discovered}`);

  console.log("\n🔗 DEPENDENCY GRAPH:");
  prime.dependencyGraph.forEach((node) => {
    if (node.deps.length > 0) {
      console.log(`   ${node.id} ← [${node.deps.join(", ")}]`);
    } else {
      console.log(`   ${node.id} (root)`);
    }
  });

  console.log("\n📁 FILES SYNCHRONIZED:");
  console.log("   • .beads/beads.jsonl (git-tracked source of truth)");
  console.log("   • .beads/deletions.jsonl (cross-clone deletion log)");
  console.log("   • .beads/beads.db (local SQLite cache - gitignored)");

  console.log("\n✨ Demo showcases:");
  console.log("   ✓ 3-agent collaboration (ARCHITECT → IMPLEMENTER → REVIEWER)");
  console.log("   ✓ Git-native persistence with JSONL source of truth");
  console.log("   ✓ Dependency-aware task graph");
  console.log("   ✓ Issue discovery during implementation");
  console.log("   ✓ Hash-based IDs for collision resistance");
  console.log("   ✓ DSPy-optimized chain-of-thought reasoning\n");
}

runDemo().catch(console.error);
