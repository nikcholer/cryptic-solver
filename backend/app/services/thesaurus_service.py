from __future__ import annotations

import json
import re
from pathlib import Path


class ThesaurusService:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root
        self.data_path = repo_root / "cryptic_skills" / "thesaurus.json"
        self.data = self._load()

    def lookup(self, term: str, length: int | None = None) -> list[dict[str, object]]:
        normalized = self._normalize(term)
        if not normalized:
            return []
        entries = self.data.get(normalized, {})
        results: list[dict[str, object]] = []
        seen: set[tuple[str, str]] = set()
        for pos, words in entries.items():
            for word in words:
                candidate = self._normalize(word)
                if not candidate:
                    continue
                if length is not None and len(candidate.replace(' ', '')) != length:
                    continue
                key = (candidate, pos)
                if key in seen:
                    continue
                seen.add(key)
                results.append({
                    'word': word,
                    'pos': pos,
                    'length': len(candidate.replace(' ', '')),
                })
        return results

    def _load(self) -> dict[str, dict[str, list[str]]]:
        if not self.data_path.exists():
            return {}
        return json.loads(self.data_path.read_text(encoding='utf-8'))

    def _normalize(self, term: str) -> str:
        return re.sub(r'\s+', ' ', re.sub(r"[^a-z ]+", ' ', term.lower())).strip()
