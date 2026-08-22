"""
Skill Authoring - create skills through conversation (CowAgent pattern).
User describes what they want, agent generates a SKILL.md.
"""

import json
import re
from datetime import datetime


class SkillAuthoring:
    """Create custom skills through natural language conversation."""

    def __init__(self, model_router=None, registry=None):
        self.model = model_router
        self.registry = registry

    async def create_skill(self, description: str,
                            context: str = "") -> dict:
        """Generate a SKILL.md from a natural language description."""
        if self.model:
            content = await self._generate_with_llm(description, context)
        else:
            content = self._generate_fallback(description)

        parsed = self._parse_skill_metadata(content)
        skill_id = parsed.get("id") or self._slugify(description)

        if self.registry:
            self.registry.install_skill(skill_id, content, {
                "name": parsed.get("name", description[:50]),
                "description": description,
                "category": parsed.get("category", "custom"),
                "tags": parsed.get("tags", []),
                "source": "conversational",
                "version": "1.0.0",
            })

        return {
            "skill_id": skill_id,
            "content": content,
            "parsed": parsed,
            "message": f"Skill '{skill_id}' created and installed.",
        }

    async def _generate_with_llm(self, description: str,
                                  context: str) -> str:
        system = ("You are a skill authoring agent. Generate a SKILL.md "
                  "file based on the user's description. Include frontmatter "
                  "with name, description, version, category, tags. "
                  "Include sections: Description, When to Use, Key Patterns, "
                  "Integration, Examples.")
        prompt = f"""
Create a SKILL.md for the following:

Description: {description}
Context: {context}

Generate a complete SKILL.md with:
1. Frontmatter (name, description, version, category, tags, source)
2. Description section
3. When to Use section
4. Key Patterns section (3-5 patterns)
5. Integration section (how it connects to agents)
6. Examples section

The skill should be specific, actionable, and follow the Agent Skills spec.
"""
        return await self.model.complete(
            system=system,
            messages=[{"role": "user", "content": prompt}]
        )

    def _generate_fallback(self, description: str) -> str:
        skill_id = self._slugify(description)
        return f"""---
name: {description[:50]}
description: Custom skill: {description[:100]}
version: 1.0.0
category: custom
tags: [custom, user-created]
source: conversational
---

# {description[:50]}

## Description
{description}

## When to Use
Load this skill when the task involves the patterns described above.

## Key Patterns
- Follow user-defined patterns
- Adapt to context
- Apply as needed

## Integration
Auto-loads when agent detects relevant context.

## Examples
User: "{description}"
Agent: loads skill and applies patterns.
"""

    def _parse_skill_metadata(self, content: str) -> dict:
        """Parse frontmatter from SKILL.md."""
        metadata = {}
        frontmatter_match = re.search(r"^---\n(.*?)\n---", content, re.DOTALL)
        if frontmatter_match:
            for line in frontmatter_match.group(1).split("\n"):
                if ":" in line:
                    key, val = line.split(":", 1)
                    key = key.strip()
                    val = val.strip()
                    if val.startswith("["):
                        val = [v.strip() for v in val[1:-1].split(",")]
                    metadata[key] = val
        return metadata

    def _slugify(self, text: str) -> str:
        slug = re.sub(r"[^\w\s-]", "", text.lower())
        slug = re.sub(r"[\s-]+", "-", slug).strip("-")
        return slug[:40] if slug else "custom-skill"
