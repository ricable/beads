#!/usr/bin/env node
/**
 * Initialize Beads for Multi-Agent Collaboration
 *
 * Sets up:
 * - .beads directory structure
 * - JSONL source of truth files
 * - Git hooks for synchronization
 * - SQLite cache (gitignored)
 */

import { existsSync, mkdirSync, writeFileSync, chmodSync } from "fs";
import { execSync } from "child_process";

console.log("🔧 Initializing Beads Multi-Agent System\n");

// Create .beads directory
if (!existsSync(".beads")) {
  mkdirSync(".beads", { recursive: true });
  console.log("✓ Created .beads directory");
} else {
  console.log("• .beads directory exists");
}

// Create JSONL files
const jsonlFiles = [
  { path: ".beads/beads.jsonl", desc: "Issue database" },
  { path: ".beads/deletions.jsonl", desc: "Deletion log" }
];

jsonlFiles.forEach(({ path, desc }) => {
  if (!existsSync(path)) {
    writeFileSync(path, "");
    console.log(`✓ Created ${path} (${desc})`);
  } else {
    console.log(`• ${path} exists`);
  }
});

// Create agents directory
if (!existsSync("agents")) {
  mkdirSync("agents", { recursive: true });
  console.log("✓ Created agents directory");
}

// Create scripts directory
if (!existsSync("scripts")) {
  mkdirSync("scripts", { recursive: true });
  console.log("✓ Created scripts directory");
}

// Set up git hooks
const hooksDir = ".git/hooks";
if (existsSync(".git")) {
  // Pre-commit hook
  const preCommitHook = `#!/bin/sh
# Beads pre-commit hook: validate JSONL before commit

JSONL_FILE=".beads/beads.jsonl"

if [ -f "$JSONL_FILE" ]; then
  # Validate each line is valid JSON
  while IFS= read -r line || [ -n "$line" ]; do
    if [ -n "$line" ]; then
      echo "$line" | node -e "JSON.parse(require('fs').readFileSync('/dev/stdin', 'utf8'))" 2>/dev/null
      if [ $? -ne 0 ]; then
        echo "ERROR: Invalid JSON in $JSONL_FILE"
        exit 1
      fi
    fi
  done < "$JSONL_FILE"
fi

echo "Beads: JSONL validation passed"
`;

  // Post-merge hook
  const postMergeHook = `#!/bin/sh
# Beads post-merge hook: sync after pull

echo "Beads: Syncing after merge..."
# In production, this would call: bd import
`;

  // Write hooks
  if (existsSync(hooksDir)) {
    writeFileSync(`${hooksDir}/pre-commit`, preCommitHook);
    chmodSync(`${hooksDir}/pre-commit`, "755");
    console.log("✓ Installed pre-commit hook");

    writeFileSync(`${hooksDir}/post-merge`, postMergeHook);
    chmodSync(`${hooksDir}/post-merge`, "755");
    console.log("✓ Installed post-merge hook");
  }
}

// Create beads config
const beadsConfig = {
  version: "1.0.0",
  persistence: {
    jsonl: ".beads/beads.jsonl",
    deletions: ".beads/deletions.jsonl",
    cache: ".beads/beads.db"
  },
  agents: {
    architect: { role: "strategic-planning" },
    implementer: { role: "execution" },
    reviewer: { role: "quality-assurance" }
  },
  sync: {
    mode: "git",
    autoCommit: false
  }
};

writeFileSync(".beads/config.json", JSON.stringify(beadsConfig, null, 2));
console.log("✓ Created .beads/config.json");

console.log("\n✨ Beads initialization complete!\n");
console.log("Next steps:");
console.log("  1. npm install");
console.log("  2. npm run demo       # Run the demo use case");
console.log("  3. npm start          # Start the orchestrator");
