from __future__ import annotations

from app.models.common import HintKind, ValidationResult


class StubRuntimeAdapter:
    def next_hint(self, clue_id: str, clue_text: str, pattern: str, next_level: int):
        hint_map = {
            1: (HintKind.CLUE_TYPE, "This looks like a cryptic clue with standard wordplay."),
            2: (HintKind.STRUCTURE, "The definition is likely at one end of the clue."),
            3: (HintKind.WORDPLAY_FOCUS, "Look for indicator words and possible fodder.") ,
            4: (HintKind.CANDIDATE_SPACE, f"Use the current pattern {pattern} to narrow candidates."),
            5: (HintKind.ANSWER_REVEAL, "Answer reveal is not available in the stub runtime."),
        }
        kind, text = hint_map.get(next_level, hint_map[5])
        return {
            "clueId": clue_id,
            "hintLevel": next_level,
            "kind": kind,
            "text": text,
            "confidence": 0.25,
        }

    def validate_answer(self, clue_id: str, clue_text: str, proposed_answer: str, pattern_before: str):
        if not proposed_answer:
            return {
                "clueId": clue_id,
                "result": ValidationResult.CONFLICT,
                "reason": "Empty answer.",
                "confidence": 0.0,
            }
        if '.' in pattern_before and not self._matches_pattern(proposed_answer, pattern_before):
            return {
                "clueId": clue_id,
                "result": ValidationResult.CONFLICT,
                "reason": "Submitted answer conflicts with current checking letters.",
                "confidence": 0.9,
            }
        return {
            "clueId": clue_id,
            "result": ValidationResult.PLAUSIBLE,
            "reason": "Fits length and current checking letters. Semantic validation is stubbed.",
            "confidence": 0.35,
        }

    def _matches_pattern(self, answer: str, pattern: str) -> bool:
        answer = ''.join(ch for ch in answer.upper() if ch.isalpha())
        if len(answer) != len(pattern):
            return False
        return all(p == '.' or p == a for p, a in zip(pattern, answer))