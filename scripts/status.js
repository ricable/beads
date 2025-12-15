#!/usr/bin/env node
/**
 * Beads Status Dashboard
 *
 * Display current state of the multi-agent system.
 */

import { readFileSync, existsSync } from "fs";

const BEADS_JSONL = ".beads/beads.jsonl";
const DELETIONS_JSONL = ".beads/deletions.jsonl";

function readJsonl(path) {
  if (!existsSync(path)) return [];
  const content = readFileSync(path, "utf-8");
  return content
    .trim()
    .split("\n")
    .filter(Boolean)
    .map((line) => JSON.parse(line));
}

const issues = readJsonl(BEADS_JSONL);
const deletions = readJsonl(DELETIONS_JSONL);

console.log("╔════════════════════════════════════════════════════════════╗");
console.log("║              BEADS MULTI-AGENT STATUS                      ║");
console.log("╚════════════════════════════════════════════════════════════╝\n");

// Overview
console.log("📊 OVERVIEW");
console.log(`   Total Issues: ${issues.length}`);
console.log(`   Deletions Tracked: ${deletions.length}`);

// By Status
const statusCounts = {};
issues.forEach((i) => {
  statusCounts[i.status] = (statusCounts[i.status] || 0) + 1;
});

console.log("\n📋 BY STATUS");
const statusIcons = {
  open: "⚪",
  "in-progress": "🔵",
  done: "🟢",
  closed: "✅"
};
Object.entries(statusCounts).forEach(([status, count]) => {
  console.log(`   ${statusIcons[status] || "⚪"} ${status}: ${count}`);
});

// By Priority
const priorityCounts = {};
issues.forEach((i) => {
  priorityCounts[i.priority] = (priorityCounts[i.priority] || 0) + 1;
});

console.log("\n🎯 BY PRIORITY");
const priorityIcons = { high: "🔴", medium: "🟡", low: "🟢" };
Object.entries(priorityCounts).forEach(([priority, count]) => {
  console.log(`   ${priorityIcons[priority] || "⚪"} ${priority}: ${count}`);
});

// By Agent
const agentCounts = {};
issues.forEach((i) => {
  const agent = i.createdBy || "unknown";
  agentCounts[agent] = (agentCounts[agent] || 0) + 1;
});

console.log("\n🤖 BY AGENT");
Object.entries(agentCounts).forEach(([agent, count]) => {
  console.log(`   ${agent}: ${count}`);
});

// Ready Work
const readyWork = issues.filter((issue) => {
  if (issue.status !== "open") return false;
  if (!issue.dependencies || issue.dependencies.length === 0) return true;
  const blockingDeps = issue.dependencies.filter((d) => d.type === "blocks");
  return blockingDeps.every((dep) => {
    const blocker = issues.find((i) => i.id === dep.id);
    return blocker && (blocker.status === "done" || blocker.status === "closed");
  });
});

console.log("\n🚀 READY WORK");
if (readyWork.length === 0) {
  console.log("   (none)");
} else {
  readyWork.forEach((issue) => {
    console.log(`   ${issue.id}: ${issue.title}`);
  });
}

// Review Queue
const reviewQueue = issues.filter(
  (i) => i.status === "done" && i.needsReview
);

console.log("\n🔍 REVIEW QUEUE");
if (reviewQueue.length === 0) {
  console.log("   (none)");
} else {
  reviewQueue.forEach((issue) => {
    console.log(`   ${issue.id}: ${issue.title}`);
  });
}

// Recent Activity
console.log("\n📅 RECENT ISSUES");
const recent = [...issues]
  .sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt))
  .slice(0, 5);

if (recent.length === 0) {
  console.log("   (none)");
} else {
  recent.forEach((issue) => {
    const date = new Date(issue.createdAt).toLocaleString();
    console.log(`   ${issue.id}: ${issue.title} (${date})`);
  });
}

console.log("\n" + "─".repeat(60));
