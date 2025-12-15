#!/usr/bin/env node
/**
 * Sync Agents State
 *
 * Synchronizes beads state between agents and git.
 * Handles:
 * - JSONL → SQLite import
 * - Conflict detection
 * - Deletion propagation
 */

import { readFileSync, existsSync } from "fs";
import { execSync } from "child_process";

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

function getGitStatus() {
  try {
    return execSync("git status --porcelain .beads/", { encoding: "utf-8" });
  } catch {
    return "";
  }
}

console.log("🔄 Syncing Agent States\n");

// Check git status
const gitStatus = getGitStatus();
if (gitStatus.includes("UU") || gitStatus.includes("AA")) {
  console.log("⚠️  Merge conflicts detected in .beads/");
  console.log("   Run: git mergetool .beads/beads.jsonl");
  process.exit(1);
}

// Load current state
const issues = readJsonl(BEADS_JSONL);
const deletions = readJsonl(DELETIONS_JSONL);

console.log(`📊 Current State:`);
console.log(`   • Issues: ${issues.length}`);
console.log(`   • Deletions tracked: ${deletions.length}`);

// Check for zombies (issues that should be deleted)
const deletedIds = new Set(deletions.map((d) => d.id));
const zombies = issues.filter((i) => deletedIds.has(i.id));

if (zombies.length > 0) {
  console.log(`\n⚠️  Zombie issues detected: ${zombies.length}`);
  zombies.forEach((z) => {
    console.log(`   • ${z.id}: ${z.title}`);
  });
  console.log("   These will be removed during next import.");
}

// Check integrity
const allIds = new Set(issues.map((i) => i.id));
let orphanedDeps = 0;

issues.forEach((issue) => {
  if (issue.dependencies) {
    issue.dependencies.forEach((dep) => {
      if (!allIds.has(dep.id) && !deletedIds.has(dep.id)) {
        orphanedDeps++;
      }
    });
  }
});

if (orphanedDeps > 0) {
  console.log(`\n⚠️  Orphaned dependencies: ${orphanedDeps}`);
}

// Status by agent
const byAgent = {};
issues.forEach((issue) => {
  const agent = issue.createdBy || "unknown";
  byAgent[agent] = (byAgent[agent] || 0) + 1;
});

console.log(`\n📤 Issues by Agent:`);
Object.entries(byAgent).forEach(([agent, count]) => {
  console.log(`   • ${agent}: ${count}`);
});

// Status breakdown
const byStatus = {};
issues.forEach((issue) => {
  byStatus[issue.status] = (byStatus[issue.status] || 0) + 1;
});

console.log(`\n📋 Issues by Status:`);
Object.entries(byStatus).forEach(([status, count]) => {
  console.log(`   • ${status}: ${count}`);
});

// Git changes
if (gitStatus.trim()) {
  console.log(`\n📁 Pending Git Changes:`);
  gitStatus
    .trim()
    .split("\n")
    .forEach((line) => {
      console.log(`   ${line}`);
    });
} else {
  console.log(`\n✅ No pending git changes in .beads/`);
}

console.log("\n✨ Sync check complete!");
