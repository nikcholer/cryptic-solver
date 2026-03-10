import argparse
import json
import collections

import os
from typing import Any, Dict, List, Optional

# Path to our local knowledge base
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WORDLIST_PATH = os.path.join(SCRIPT_DIR, "words.txt")

def build_anagram_signature(word: str) -> str:
    """Creates a sorted string of letters to act as an anagram hash."""
    return "".join(sorted(word.lower()))

def load_wordlist(filepath: str) -> Dict[str, List[str]]:
    """Loads the wordlist into a hash map where keys are anagram signatures."""
    anagram_dict = collections.defaultdict(list)
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                word = line.strip().lower()
                # Basic filter: Cryptic crosswords rarely use single letters other than A/I
                if len(word) > 1 or word in ['a', 'i']:
                    sig = build_anagram_signature(word)
                    anagram_dict[sig].append(word)
        return anagram_dict
    except FileNotFoundError:
        print(json.dumps({"error": f"Wordlist not found at {filepath}"}))
        exit(1)

def filter_by_pattern(words: List[str], pattern: Optional[str]) -> List[str]:
    """Filters a list of words by a given pattern (e.g. 'P...S....')."""
    if not pattern:
        return words
        
    pattern = pattern.lower()
    filtered = []
    for word in words:
        if len(word) != len(pattern):
            continue
            
        match = True
        for w_char, p_char in zip(word, pattern):
            if p_char != '.' and w_char != p_char:
                match = False
                break
        
        if match:
            filtered.append(word)
            
    return filtered

def solve_anagram(fodder: str, pattern: Optional[str] = None, wordlist_path: str = WORDLIST_PATH) -> Dict[str, Any]:
    """Core skill logic: Finds anagrams of 'fodder' matching 'pattern'."""
    # Clean the fodder (remove spaces, punctuation)
    clean_fodder = "".join(c.lower() for c in fodder if c.isalpha())
    
    # 1. Check length constraints
    if pattern and len(clean_fodder) != len(pattern):
         return {"error": f"Fodder length ({len(clean_fodder)}) does not match pattern length ({len(pattern)})"}

    # 2. Build target signature
    target_sig = build_anagram_signature(clean_fodder)
    
    # 3. Load dictionary (In a real long-running agent, this would be loaded once)
    anagram_dict = load_wordlist(wordlist_path)
    
    # 4. Lookup
    candidates = anagram_dict.get(target_sig, [])
    
    # 5. Apply pattern constraints if any checked letters exist
    final_candidates = filter_by_pattern(candidates, pattern)
    
    return {
        "fodder": clean_fodder,
        "pattern": pattern,
        "candidates": final_candidates,
        "candidate_count": len(final_candidates)
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Skill: Anagram Solver for Cryptic Crosswords")
    parser.add_argument("--fodder", required=True, help="The letters to anagram (e.g. 'atomsupis')")
    parser.add_argument("--pattern", required=False, help="Known letters pattern (e.g. 'p........' or '.........')")
    
    args = parser.parse_args()
    
    # Execute skill and output JSON for the Foreman agent to parse
    result = solve_anagram(args.fodder, args.pattern)
    print(json.dumps(result, indent=2))
