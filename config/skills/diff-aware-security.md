---
name: Diff-Aware Security
description: Only scan changed files, modular pipeline, explicit denylist, prompt-injection limitations
version: 1.0.0
category: security
tags: [diff, pr-scan, modular]
source: #55 Claude Code Security Review
---

# Diff-Aware Security

## Description
Only scan changed files, modular pipeline, explicit denylist, prompt-injection limitations

## Source
#55 Claude Code Security Review

## Category
security

## Tags
diff, pr-scan, modular

## When to Use
Load this skill when the task involves diff.

## Key Patterns
- Follow the patterns described in the source
- Adapt to the current context
- Apply only what is new beyond baseline rules

## Integration
This skill auto-loads when the agent detects relevant context keywords.
