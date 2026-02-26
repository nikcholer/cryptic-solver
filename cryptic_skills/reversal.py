import argparse
import json
import os

# ----------------------------------------------------------------------
# Core Foreman Skill: Reversal Solver
# 
# This deterministic skill takes a fodder string and reverses it.
# It handles two primary cryptic reversal cases:
# 1. The fodder IS the word to be reversed (e.g. "Monster therefore returns" -> "ergo" reversed = OGRE)
# 2. The fodder is the reversed OUTCOME, and we need to find synonyms of it.
# 
# For v1, we focus on Case 1: Reversing the literal fodder.
# ----------------------------------------------------------------------

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WORDLIST_PATH = os.path.join(SCRIPT_DIR, "words.txt")

def load_wordlist(filepath):
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

def filter_by_pattern(word, pattern):
    """Checks if a single word matches the known checked letters."""
    if not pattern:
        return True
    
    if len(word) != len(pattern):
        return False
        
    for w_char, p_char in zip(word, pattern):
        if p_char != '.' and w_char != p_char:
            return False
            
    return True

def solve_reversal(fodder, pattern=None, wordlist_path=WORDLIST_PATH):
    """Core skill logic: Reverses 'fodder' and validates."""
    
    # Clean the fodder
    clean_fodder = "".join(c.lower() for c in fodder if c.isalpha())
    
    # The literal reversal
    reversed_string = clean_fodder[::-1]
    
    # 1. Check length constraints
    if pattern and len(reversed_string) != len(pattern):
        return {"error": f"Fodder length ({len(reversed_string)}) does not match pattern length ({len(pattern)})"}

    candidates = []
    
    # 2. Check pattern constraint
    if filter_by_pattern(reversed_string, pattern):
        # 3. Validate against English dictionary
        valid_words = load_wordlist(wordlist_path)
        if reversed_string in valid_words:
            candidates.append(reversed_string)

    return {
        "fodder": clean_fodder,
        "reversed": reversed_string,
        "pattern": pattern,
        "candidates": candidates,
        "candidate_count": len(candidates)
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Skill: Reversal Solver for Cryptic Crosswords")
    parser.add_argument("--fodder", required=True, help="The string to be reversed (e.g. 'therefore' -> 'ergo', or literal 'ogre')")
    parser.add_argument("--pattern", required=False, help="Known letters pattern (e.g. '....')")
    parser.add_argument("--synonym", action="store_true", help="If true, treats fodder as a definition to find synonyms for before reversing.")
    
    args = parser.parse_args()
    
    # In v1 we only handle literal reversal (Case 1). 
    # If the fodder is a synonym (Case 2: "therefore" -> "ergo" -> "ogre"), 
    # an advanced Foreman LLM should pass "ergo" as the fodder,
    # or we need a local synonym Knowledge Base.
    
    result = solve_reversal(args.fodder, args.pattern)
    print(json.dumps(result, indent=2))
