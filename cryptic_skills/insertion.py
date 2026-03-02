import argparse
import json
import os

# ----------------------------------------------------------------------
# Core Foreman Skill: Insertion (Container) Solver
# 
# This deterministic skill handles clues where one element (fodder) 
# is inserted inside another element (outer).
# e.g., "Glides using paddle on board ship" -> paddle (OAR) inside ship (SS) -> SOARS
# 
# It utilizes our local abbreviations dictionary to generate candidate
# outer shells when the clue text is a common crossword synonym/abbreviation.
# ----------------------------------------------------------------------

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WORDLIST_PATH = os.path.join(SCRIPT_DIR, "words.txt")
ABBREV_PATH = os.path.join(SCRIPT_DIR, "abbreviations.json")

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

def load_abbreviations(filepath):
    """Loads abbreviations/synonyms from abbreviations.json.

    Returns a mapping of clue-synonym/keyword -> list of abbreviation expansions.
    Example: {"daughter": ["d"], "ship": ["ss"]}
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        abbrev_dict = {}
        for k, v in (data or {}).items():
            if not k or not isinstance(k, str):
                continue
            if isinstance(v, list):
                expansions = [x for x in v if isinstance(x, str) and x]
            elif isinstance(v, str):
                expansions = [v] if v else []
            else:
                expansions = []
            if expansions:
                abbrev_dict[k.lower()] = expansions
        return abbrev_dict
    except FileNotFoundError:
        return {}
    except Exception as e:
        print(json.dumps({"error": f"Error loading abbreviations: {e}"}))
        return {}

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

def clean_string(s):
    return "".join(c.lower() for c in s if c.isalpha())

def solve_insertion(fodder, outer, pattern=None, wordlist_path=WORDLIST_PATH, abbrev_path=ABBREV_PATH):
    """
    Generates all valid English words created by inserting `fodder` into `outer`.
    If `outer` is a known abbreviation keyword, it tries inserting into all of its abbreviations.
    If `fodder` is a known abbreviation keyword, it tries inserting all of its abbreviations.
    """
    valid_words = load_wordlist(wordlist_path)
    abbreviations_db = load_abbreviations(abbrev_path)
    
    # 1. Expand the OUTER possibilities
    clean_outer = clean_string(outer)
    outer_candidates = [clean_outer]
    
    # Expand via abbreviations: if our outer keyword is contained in any key,
    # include its expansions.
    def key_matches(clean: str, key: str) -> bool:
        # Avoid overly-broad substring matches like "i" matching half the database.
        if not clean:
            return False
        if clean == key:
            return True
        if clean in key.split():
            return True
        # Allow substring matching only for reasonably specific strings.
        if len(clean) >= 3 and clean in key:
            return True
        return False

    for k, expansions in abbreviations_db.items():
        if key_matches(clean_outer, k):
            outer_candidates.extend(expansions)
            
    # 2. Expand the FODDER possibilities
    clean_fodder = clean_string(fodder)
    fodder_candidates = [clean_fodder]
    
    for k, expansions in abbreviations_db.items():
        if key_matches(clean_fodder, k):
            fodder_candidates.extend(expansions)
       
    # If the user passed explicit synonyms (comma separated) instead of a literal, handle that.
    if ',' in fodder:
        fodder_candidates = [clean_string(x) for x in fodder.split(',')]
    if ',' in outer:
        outer_candidates = [clean_string(x) for x in outer.split(',')]

    results = []

    # 3. Combinatorial generation
    for o in outer_candidates:
        if len(o) < 2: 
            continue # You can't insert something *inside* a 1-letter string.

        for f in fodder_candidates:
            # We must insert the fodder *strictly inside* the outer shell. 
            # We iterate over every possible insertion point (index 1 to len-1)
            for i in range(1, len(o)):
                candidate_word = o[:i] + f + o[i:]
                
                # Apply length constraints early
                if pattern and len(candidate_word) != len(pattern):
                    continue
                    
                # Apply pattern constraints
                if filter_by_pattern(candidate_word, pattern):
                    # Final Dictionary Validation
                    if candidate_word in valid_words:
                        results.append({
                            "candidate": candidate_word,
                            "outer_used": o,
                            "fodder_used": f,
                            "insertion_index": i
                        })

    # Deduplicate results
    unique_candidates = list({r['candidate']: r for r in results}.values())

    return {
        "original_fodder": clean_fodder,
        "original_outer": clean_outer,
        "pattern": pattern,
        "candidates": unique_candidates,
        "candidate_count": len(unique_candidates)
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Skill: Insertion/Container Solver for Cryptic Crosswords")
    parser.add_argument("--fodder", required=True, help="The string to be inserted, or a comma-separated list of synonyms (e.g. 'oar,paddle')")
    parser.add_argument("--outer", required=True, help="The string acting as the container, or comma-separated list of synonyms (e.g. 'ship,ss')")
    parser.add_argument("--pattern", required=False, help="Known letters pattern (e.g. 's...s')")
    
    args = parser.parse_args()
    
    result = solve_insertion(args.fodder, args.outer, args.pattern)
    print(json.dumps(result, indent=2))
