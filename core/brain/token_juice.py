"""
TokenJuice — Token compression (Caveman #6 + RTK #7 + Headroom #8)

Three compression modes:
  1. Output compression (Caveman): drop filler, articles, hedging
  2. Input compression (Headroom): content-aware (JSON, code, logs, diffs)
  3. Shell compression (RTK): smart filtering per command type

Rules:
  - Originals ALWAYS cached before lossy transform
  - Drop compression on: security, approval, destructive, ambiguity
  - Never drop: not/never/no/only/except, numbers, units, technical terms
  - Measure before compressing
"""

import re
import json
import hashlib
import os
from typing import Any


class TokenJuice:
    """Content-aware token compression. Same info, fewer tokens."""

    FILLER_WORDS = {
        # English filler
        "the", "a", "an", "is", "are", "was", "were", "be", "been",
        "being", "have", "has", "had", "do", "does", "did", "will",
        "would", "could", "should", "may", "might", "shall",
        "very", "quite", "rather", "somewhat", "fairly", "pretty",
        "just", "really", "actually", "basically", "essentially",
        "simply", "certainly", "definitely", "probably", "perhaps",
        "maybe", "possibly", "likely", "unlikely",
        "i", "you", "we", "they", "he", "she", "it",
        "me", "him", "her", "us", "them",
        "my", "your", "our", "their", "his", "its",
        "this", "that", "these", "those",
        "and", "or", "but", "so", "because", "if", "when", "while",
        "although", "though", "however", "therefore", "thus",
        "of", "to", "in", "on", "at", "by", "for", "with", "about",
        "from", "into", "onto", "upon", "over", "under", "through",
        # Malay filler
        "yang", "untuk", "dengan", "pada", "dari", "ke", "di",
        "ini", "itu", "akan", "telah", "sudah", "masih", "juga",
        "sahaja", "pun", "lah", "kah", "tah",
    }

    NEVER_DROP = {
        "not", "never", "no", "only", "except", "without",
        "must", "required", "mandatory", "critical", "warning",
        "error", "fail", "danger", "stop", "abort", "cancel",
    }

    DROP_CONTEXTS = ["security", "approval", "destructive", "ambiguous"]

    def __init__(self, config: dict | None = None):
        self.config = config or {}
        self.enabled = self.config.get("enabled", True)
        self.output_enabled = self.config.get("output_compression", True)
        self.input_enabled = self.config.get("input_compression", True)
        self.shell_enabled = self.config.get("shell_compression", True)
        self.cache_originals = self.config.get("cache_originals", True)
        self.drop_on = self.config.get("drop_compression_on", self.DROP_CONTEXTS)
        self._cache: dict[str, str] = {}

    def _cache_key(self, content: str) -> str:
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _should_skip(self, context: str | None) -> bool:
        if not context:
            return False
        context_lower = context.lower()
        return any(d in context_lower for d in self.drop_on)

    # ============================================================
    # 1. OUTPUT COMPRESSION (Caveman #6)
    # ============================================================

    def compress_output(self, text: str, context: str | None = None) -> str:
        """Caveman: drop articles, filler, hedging. Fragments OK."""
        if not self.enabled or not self.output_enabled:
            return text
        if self._should_skip(context):
            return text

        if self.cache_originals:
            key = self._cache_key(text)
            self._cache[key] = text

        words = text.split()
        kept = []
        for w in words:
            clean = re.sub(r"[^\w-]", "", w.lower())
            if clean in self.NEVER_DROP:
                kept.append(w)
            elif clean in self.FILLER_WORDS and len(kept) > 0:
                continue
            else:
                kept.append(w)

        result = " ".join(kept)
        if len(result) >= len(text):
            return text
        return result

    # ============================================================
    # 2. INPUT COMPRESSION (Headroom #8) — content-aware
    # ============================================================

    def compress_input(self, content: str, content_type: str | None = None) -> str:
        """Headroom: detect content type → route to right compressor."""
        if not self.enabled or not self.input_enabled:
            return content
        if self._should_skip(content_type):
            return content

        if self.cache_originals:
            key = self._cache_key(content)
            self._cache[key] = content

        if content_type is None:
            content_type = self._detect_type(content)

        if content_type == "json":
            return self._compress_json(content)
        elif content_type == "code":
            return self._compress_code(content)
        elif content_type == "logs":
            return self._compress_logs(content)
        elif content_type == "diff":
            return self._compress_diff(content)
        elif content_type == "search_results":
            return self._compress_search_results(content)
        return content

    def _detect_type(self, content: str) -> str:
        stripped = content.strip()
        if stripped.startswith("{") or stripped.startswith("["):
            try:
                json.loads(stripped)
                return "json"
            except Exception:
                pass
        if stripped.startswith("diff --git") or stripped.startswith("---"):
            return "diff"
        if re.search(r"\b(error|traceback|exception|warn)\b", stripped, re.I):
            if re.search(r"^\d{4}-\d{2}-\d{2}", stripped, re.M):
                return "logs"
        if re.search(r"^(def |class |import |from |func |package )", stripped, re.M):
            return "code"
        if "search results" in stripped.lower() or "results:" in stripped.lower():
            return "search_results"
        return "text"

    def _compress_json(self, content: str) -> str:
        try:
            data = json.loads(content)
        except Exception:
            return content
        compact = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
        if isinstance(data, list) and len(data) > 5:
            head = json.dumps(data[:3], separators=(",", ":"), ensure_ascii=False)
            compact = f"[{head[:-1]}, ... {len(data) - 3} more items]"
        return compact

    def _compress_code(self, content: str) -> str:
        lines = content.split("\n")
        kept = []
        for line in lines:
            stripped = line.strip()
            if (stripped.startswith("import ") or
                stripped.startswith("from ") or
                stripped.startswith("package ") or
                stripped.startswith("def ") or
                stripped.startswith("class ") or
                stripped.startswith("func ") or
                stripped.startswith("async ") or
                stripped.startswith("pub ") or
                stripped.endswith(":") or
                stripped.endswith("{") or
                stripped == "}" or
                stripped == "}" or
                stripped.startswith("#") or
                stripped.startswith("//")):
                kept.append(line)
            elif "(" in stripped and ")" in stripped:
                kept.append(line)
        if len(kept) < len(lines) * 0.3:
            return content
        return "\n".join(kept)

    def _compress_logs(self, content: str) -> str:
        lines = content.split("\n")
        kept = []
        for line in lines:
            if re.search(r"\b(error|ERROR|Error|traceback|Traceback|"
                        r"exception|Exception|FATAL|fatal|warn|WARN)\b", line):
                kept.append(line)
            elif re.search(r"^\s*File \"|^\s*at ", line):
                kept.append(line)
        if not kept:
            kept = [lines[0]] if lines else []
            if len(lines) > 1:
                kept.append(lines[-1])
        if len(lines) > 100 and len(kept) < 20:
            kept = lines[:5] + ["... (truncated) ..."] + lines[-5:]
        return "\n".join(kept)

    def _compress_diff(self, content: str) -> str:
        lines = content.split("\n")
        kept = []
        for line in lines:
            if (line.startswith("diff --git") or
                line.startswith("---") or
                line.startswith("+++") or
                line.startswith("@@") or
                line.startswith("+") or
                line.startswith("-")):
                kept.append(line)
        return "\n".join(kept)

    def _compress_search_results(self, content: str) -> str:
        lines = content.split("\n")
        kept = lines[:5]
        if len(lines) > 10:
            kept += ["..."] + lines[-5:]
        return "\n".join(kept)

    # ============================================================
    # 3. SHELL OUTPUT COMPRESSION (RTK #7)
    # ============================================================

    SHELL_RULES = {
        "ls": "tree+counts",
        "cat": "signatures",
        "grep": "grouped_by_file",
        "git status": "compact_stat",
        "git log": "hash_author_subject",
        "git add": "confirmation",
        "git commit": "confirmation",
        "git push": "confirmation",
        "test": "failures_only",
        "lint": "grouped_by_rule",
        "npm": "summary_line",
        "pip": "summary_line",
    }

    def compress_shell(self, command: str, output: str) -> str:
        """RTK: smart filtering per command type."""
        if not self.enabled or not self.shell_enabled:
            return output
        if self._should_skip(command):
            return output

        if self.cache_originals:
            key = self._cache_key(output)
            self._cache[key] = output

        cmd_lower = command.lower().strip()
        rule = None
        for pattern, handler in self.SHELL_RULES.items():
            if pattern in cmd_lower:
                rule = handler
                break

        if rule == "tree+counts":
            return self._shell_tree(output)
        elif rule == "signatures":
            return self._shell_signatures(output)
        elif rule == "failures_only":
            return self._shell_failures(output)
        elif rule == "grouped_by_rule":
            return self._shell_grouped(output)
        elif rule in ("confirmation", "summary_line"):
            return self._shell_summary(output)
        elif rule == "compact_stat":
            return self._shell_git_status(output)
        elif rule == "hash_author_subject":
            return self._shell_git_log(output)
        return output

    def _shell_tree(self, output: str) -> str:
        lines = [l for l in output.split("\n") if l.strip()]
        dirs = [l for l in lines if l.endswith("/") or l.endswith("\\")]
        files = [l for l in lines if not (l.endswith("/") or l.endswith("\\"))]
        result = f"Dirs: {len(dirs)}, Files: {len(files)}\n"
        if dirs:
            result += "Dirs: " + ", ".join(dirs[:10]) + "\n"
        if files:
            result += "Files: " + ", ".join(files[:10]) + "\n"
        return result

    def _shell_signatures(self, output: str) -> str:
        lines = output.split("\n")
        sigs = [l for l in lines if re.search(r"\b(def |class |func |fn |async )", l)]
        return "\n".join(sigs) if sigs else output

    def _shell_failures(self, output: str) -> str:
        lines = output.split("\n")
        fails = [l for l in lines if re.search(r"\b(FAIL|ERROR|fail|error|✗|❌)\b", l)]
        if fails:
            return f"Failures ({len(fails)}):\n" + "\n".join(fails)
        passed = [l for l in lines if re.search(r"\b(PASS|pass|✓|✅)\b", l)]
        return f"All passed ({len(passed)} tests)"

    def _shell_grouped(self, output: str) -> str:
        lines = output.split("\n")
        groups: dict[str, list[str]] = {}
        for line in lines:
            parts = line.split(":", 2)
            key = parts[0] if parts else "other"
            groups.setdefault(key, []).append(line)
        result = []
        for key, items in groups.items():
            result.append(f"[{key}] ({len(items)}):")
            result.extend(items[:3])
        return "\n".join(result)

    def _shell_summary(self, output: str) -> str:
        lines = [l for l in output.split("\n") if l.strip()]
        if not lines:
            return output
        return lines[-1]

    def _shell_git_status(self, output: str) -> str:
        lines = output.split("\n")
        modified = [l for l in lines if l.startswith(" M") or l.startswith("M ")]
        added = [l for l in lines if l.startswith("A ") or l.startswith(" A")]
        deleted = [l for l in lines if l.startswith(" D") or l.startswith("D ")]
        return (f"Modified: {len(modified)}, Added: {len(added)}, "
                f"Deleted: {len(deleted)}")

    def _shell_git_log(self, output: str) -> str:
        lines = output.split("\n")
        compact = []
        for line in lines:
            if line.startswith("commit ") or "Author:" in line:
                compact.append(line)
            elif line.strip() and not line.startswith(" "):
                compact.append(line.strip()[:80])
        return "\n".join(compact[:20])

    # ============================================================
    # Cache retrieval
    # ============================================================

    def get_original(self, compressed: str) -> str | None:
        key = self._cache_key(compressed)
        return self._cache.get(key)
