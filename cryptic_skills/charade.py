import argparse
import json
import os
import itertools
from typing import Any, Dict, List, Optional, Set

# ----------------------------------------------------------------------
# Core Foreman Skill: Charades / Concatenation Solver
# 
# This deterministic skill takes an ordered list of fodder strings and/or synonyms,
# looks up their abbreviations if applicable, and generates all valid
# concatenated English words matching the pattern constraint.
# 
# Example: "Doctor (DR) + and (AND) = DRAND"
# ----------------------------------------------------------------------

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WORDLIST_PATH = os.path.join(SCRIPT_DIR, "words.txt")
ABBREV_PATH = os.path.join(SCRIPT_DIR, "abbreviations.json")

def load_wordlist(filepath: str) -> Set[str]:
    """Loads the valid wordlist into a fast lookup set."""
    valid_words = set()
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                word = line.strip().lower()
                if len(word) > 1 or word in ['a', 'i']:
                    valid_words.add(word)
        return valid_words
    except FileNotFoundError:
        print(json.dumps({"error": f"Wordlist not found at {filepath}"}))
        exit(1)

def load_abbreviations(filepath: str) -> Dict[str, Any]:
    """Loads the common abbreviation lists from our Knowledge Base."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
        
def load_crosswordese(filepath: str) -> None:
    """
    Loads common crossword single-letter indicators.
    These are the non-standard abbreviations that purely exist in cryptics.
    """
    # This acts as a fallback or extension. For now we use the main DB.
    pass

def filter_by_pattern(word: str, pattern: Optional[str]) -> bool:
    """Checks if a single word matches the known checked letters."""
    if not pattern:
        return True
    
    if len(word) != len(pattern):
        return False
        
    for w_char, p_char in zip(word, pattern):
        if p_char != '.' and w_char != p_char:
            return False
            
    return True

def clean_string(s: str) -> str:
    return "".join(c.lower() for c in s if c.isalpha())

def get_candidates_for_component(comp: str, abbrev_db: Dict[str, Any]) -> List[str]:
    """
    Given a single charade component (e.g. "doctor"), return a list of all 
    possible strings it could represent (e.g. ["dr", "mo", "mb", "doctor"]).
    """
    clean_comp = clean_string(comp)
    candidates = [clean_comp]
    
    # 1. Check if the exact component string has abbreviations
    for k, v in abbrev_db.items():
        if clean_comp == k or clean_comp in k.split():
            if isinstance(v, list):
                candidates.extend(v)
            else:
                candidates.append(v)
            
    # Remove duplicates and empty strings
    return list(set([c for c in candidates if c]))

def solve_charade(components: List[str], pattern: Optional[str] = None, wordlist_path: str = WORDLIST_PATH, abbrev_path: str = ABBREV_PATH) -> Dict[str, Any]:
    """
    Core skill logic: Takes a list of ordered components, generates all combinations
    of their abbreviations/synonyms, concatenates them, and filters by dictionary.
    """
    valid_words = load_wordlist(wordlist_path)
    abbreviations_db = load_abbreviations(abbrev_path)

    # 1. Generate all possible translation states for each component
    # e.g. components = ["doctor", "and"]
    # state_lists = [ ["doctor", "dr", "mo"], ["and", "&", "n"] ]
    state_lists = []
    for comp in components:
        # If the LLM passed explicit synonyms comma-separated (e.g., "doctor,medic")
        if ',' in comp:
            sub_comps = [c.strip() for c in comp.split(',')]
            local_states = []
            for sc in sub_comps:
                local_states.extend(get_candidates_for_component(sc, abbreviations_db))
            state_lists.append(list(set(local_states)))
        else:
            state_lists.append(get_candidates_for_component(comp, abbreviations_db))

    results = []

    # 2. Combinatorial generation using itertools.product
    # This generates every cross-combination of the expanded lists.
    for combination in itertools.product(*state_lists):
        candidate_word = "".join(combination)
        
        # Apply length constraints early
        if pattern and len(candidate_word) != len(pattern):
            continue
            
        # Apply pattern constraints
        if filter_by_pattern(candidate_word, pattern):
            # Final Dictionary Validation
            if candidate_word in valid_words:
                results.append({
                    "candidate": candidate_word,
                    "components_used": combination
                })

    # Deduplicate results based on candidate word
    unique_candidates = list({r['candidate']: r for r in results}.values())

    return {
        "original_components": components,
        "pattern": pattern,
        "candidates": unique_candidates,
        "candidate_count": len(unique_candidates)
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Skill: Charades Solver for Cryptic Crosswords")
    parser.add_argument("--components", required=True, nargs='+', help="Ordered list of component strings (e.g. 'doctor', 'and')")
    parser.add_argument("--pattern", required=False, help="Known letters pattern (e.g. '.....')")
    
    args = parser.parse_args()
    
    result = solve_charade(args.components, args.pattern)
    print(json.dumps(result, indent=2))
