"""
Skill Registry - manage SKILL.md files, index, search, install.
Inspired by OpenClaw skill-registry + CowAgent Skill Hub.
"""

import json
import os
import re
from pathlib import Path
from datetime import datetime


class SkillRegistry:
    """Registry of all skills. SKILL.md files + index.json catalog."""

    def __init__(self, skills_dir: str = "./config/skills"):
        self.skills_dir = Path(skills_dir)
        self.skills_dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.skills_dir / "index.json"

    def load_index(self) -> dict:
        """Load skill index from index.json."""
        if not self.index_path.exists():
            return {"skills": []}
        with open(self.index_path, encoding="utf-8") as f:
            return json.load(f)

    def save_index(self, index: dict):
        with open(self.index_path, "w", encoding="utf-8") as f:
            json.dump(index, f, indent=2, ensure_ascii=False)

    def list_skills(self, category: str = None,
                     tags: list[str] = None) -> list[dict]:
        """List all skills, optionally filtered."""
        index = self.load_index()
        skills = index.get("skills", [])
        if category:
            skills = [s for s in skills if s.get("category") == category]
        if tags:
            skills = [s for s in skills
                       if any(t in s.get("tags", []) for t in tags)]
        return skills

    def search_skills(self, query: str) -> list[dict]:
        """Search skills by name, description, or tags."""
        index = self.load_index()
        query_lower = query.lower()
        results = []
        for skill in index.get("skills", []):
            name = skill.get("name", "").lower()
            desc = skill.get("description", "").lower()
            tags = [t.lower() for t in skill.get("tags", [])]
            if (query_lower in name or
                query_lower in desc or
                any(query_lower in t for t in tags)):
                results.append(skill)
        return results

    def get_skill(self, skill_id: str) -> dict | None:
        """Get a skill by ID."""
        index = self.load_index()
        for skill in index.get("skills", []):
            if skill["id"] == skill_id:
                content = self.load_skill_content(skill_id)
                return {**skill, "content": content}
        return None

    def load_skill_content(self, skill_id: str) -> str:
        """Load SKILL.md content for a skill."""
        skill_file = self.skills_dir / f"{skill_id}.md"
        if skill_file.exists():
            return skill_file.read_text(encoding="utf-8")
        return ""

    def install_skill(self, skill_id: str, content: str,
                       metadata: dict) -> bool:
        """Install or update a skill."""
        skill_file = self.skills_dir / f"{skill_id}.md"
        skill_file.write_text(content, encoding="utf-8")
        index = self.load_index()
        skills = index.get("skills", [])
        existing = [i for i, s in enumerate(skills) if s["id"] == skill_id]
        entry = {
            "id": skill_id,
            "name": metadata.get("name", skill_id),
            "description": metadata.get("description", ""),
            "category": metadata.get("category", "general"),
            "tags": self._sanitize_tags(metadata.get("tags", [])),
            "source": metadata.get("source", "custom"),
            "version": metadata.get("version", "1.0.0"),
            "installed_at": datetime.now().isoformat(),
        }
        if existing:
            skills[existing[0]] = entry
        else:
            skills.append(entry)
        index["skills"] = skills
        self.save_index(index)
        return True

    def remove_skill(self, skill_id: str) -> bool:
        """Remove a skill."""
        skill_file = self.skills_dir / f"{skill_id}.md"
        if skill_file.exists():
            skill_file.unlink()
        index = self.load_index()
        index["skills"] = [s for s in index.get("skills", [])
                           if s["id"] != skill_id]
        self.save_index(index)
        return True

    def get_categories(self) -> list[str]:
        """Get all skill categories."""
        index = self.load_index()
        cats = set()
        for s in index.get("skills", []):
            cats.add(s.get("category", "general"))
        return sorted(cats)

    @staticmethod
    def _sanitize_tags(tags) -> list:
        """Ensure tags is always a clean list[str]."""
        if isinstance(tags, list):
            return [str(t).strip() for t in tags if str(t).strip()]
        if isinstance(tags, str):
            return [t.strip() for t in tags.split(",") if t.strip()]
        return []

    def stats(self) -> dict:
        """Get skill registry statistics."""
        index = self.load_index()
        skills = index.get("skills", [])
        cats = {}
        for s in skills:
            c = s.get("category", "general")
            cats[c] = cats.get(c, 0) + 1
        return {
            "total": len(skills),
            "categories": cats,
            "installed": len(skills),
        }

    # ============================================================
    # Prompt Storage
    # ============================================================

    def _prompts_path(self) -> Path:
        return self.skills_dir / "prompts.json"

    def _load_prompts(self) -> dict:
        path = self._prompts_path()
        if not path.exists():
            return {"prompts": []}
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def _save_prompts(self, data: dict):
        path = self._prompts_path()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def list_prompts(self, category: str = None,
                     query: str = None) -> list[dict]:
        """List all saved prompts with optional filters."""
        data = self._load_prompts()
        prompts = data.get("prompts", [])
        if category:
            prompts = [p for p in prompts if p.get("category") == category]
        if query:
            q = query.lower()
            prompts = [p for p in prompts
                       if q in p.get("name", "").lower()
                       or q in p.get("content", "").lower()
                       or any(q in t.lower() for t in p.get("tags", []))]
        return prompts

    def save_prompt(self, name: str, content: str, category: str = "general",
                    tags: list[str] = None, description: str = "") -> dict:
        """Save a new prompt."""
        import hashlib
        prompt_id = f"prompt_{hashlib.sha256(name.encode()).hexdigest()[:10]}"
        entry = {
            "id": prompt_id,
            "name": name,
            "content": content,
            "category": category,
            "tags": tags or [],
            "description": description,
            "uses": 0,
            "created_at": datetime.now().isoformat(),
        }
        data = self._load_prompts()
        data["prompts"].append(entry)
        self._save_prompts(data)
        return {"prompt_id": prompt_id, "status": "saved"}

    def delete_prompt(self, prompt_id: str) -> bool:
        """Delete a saved prompt."""
        data = self._load_prompts()
        before = len(data["prompts"])
        data["prompts"] = [p for p in data["prompts"] if p["id"] != prompt_id]
        if len(data["prompts"]) < before:
            self._save_prompts(data)
            return True
        return False

    def use_prompt(self, prompt_id: str) -> dict:
        """Mark a prompt as used (increment counter)."""
        data = self._load_prompts()
        for p in data["prompts"]:
            if p["id"] == prompt_id:
                p["uses"] = p.get("uses", 0) + 1
                self._save_prompts(data)
                return {"prompt_id": prompt_id, "uses": p["uses"]}
        return {"error": "Prompt not found"}
