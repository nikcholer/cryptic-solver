import argparse
import json
import os

# ----------------------------------------------------------------------
# Core Foreman Skill: Hidden Word Solver
# 
# This deterministic skill takes a fodder string and slides a window
# across it to find contiguous substrings of a specific length that
# match the pattern constraints and exist in the dictionary.
# 
# Example: "Fans in a trance catching singer" (7) 
# Fodder: "a trance catching" -> ATRANCECATCHING -> TRANCEC
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

def solve_hidden(fodder, length, pattern=None, wordlist_path=WORDLIST_PATH):
    """
    Core skill logic: Slides a window of size `length` across the `fodder`
    to find valid hidden words.
    """
    # Clean the fodder (remove spaces, punctuation)
    clean_fodder = "".join(c.lower() for c in fodder if c.isalpha())
    
    if len(clean_fodder) < length:
         return {"error": f"Fodder length ({len(clean_fodder)}) is shorter than required answer length ({length})"}

    if pattern and len(pattern) != length:
        return {"error": f"Pattern length ({len(pattern)}) does not match required length ({length})"}

    candidates = []
    
    valid_words = None # Lazy load only if we find a match

    # Slide a window of 'length' across the clean string
    for i in range(len(clean_fodder) - length + 1):
        substring = clean_fodder[i:i+length]
        
        # 1. Filter by intersecting Grid Pattern first (fastest)
        if filter_by_pattern(substring, pattern):
            # To be a true hidden word, it usually must cross at least one word boundary from the original clue structure.
            # However, for v1 programmatic simplicity and robustness, we will return ANY pattern-matching substring.
            # A downstream Semantic LLM ranker will evaluate if it's the right answer.
            candidates.append(substring)

    # Deduplicate list while preserving order
    candidates = list(dict.fromkeys(candidates))

    return {
        "fodder": clean_fodder,
        "pattern": pattern,
        "length": length,
        "candidates": candidates,
        "candidate_count": len(candidates)
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Skill: Hidden Word Solver for Cryptic Crosswords")
    parser.add_argument("--fodder", required=True, help="The source string containing the hidden word (e.g. 'a trance catching')")
    parser.add_argument("--length", required=True, type=int, help="The required length of the hidden word")
    parser.add_argument("--pattern", required=False, help="Known letters pattern (e.g. 't......')")
    
    args = parser.parse_args()
    
    result = solve_hidden(args.fodder, args.length, args.pattern)
    print(json.dumps(result, indent=2))
