import argparse
import json
import os

# ----------------------------------------------------------------------
# Core Foreman Skill: LLM Clue Categorization
# 
# This skill takes a raw cryptic clue and uses an LLM to parse it into
# our structured format (clue_type, definition_span, fodder_span, etc.).
# 
# To use dynamically in an agent framework, you can hook this up to your
# preferred API (OpenAI, Gemini, Ollama, Anthropic) using the system prompt below.
# ----------------------------------------------------------------------

SYSTEM_PROMPT = """
You are an expert, highly analytical cryptic crossword solver. 
Your task is to analyze a raw cryptic crossword clue and break it down into its component parts.

A cryptic clue typically consists of two halves:
1. A straight Definition.
2. Wordplay (Fodder + Indicator).

Analyze the clue and return a strict JSON object with the following schema:
{
  "clue_type": "string (e.g., 'anagram', 'hidden', 'reversal', 'insertion', 'double_definition', 'charade', 'acrostic', 'acrostic_all_in_one')",
  "definition_span": "string (the exact substring representing the straight definition)",
  "fodder_span": "string (the exact substring representing the letters or words to be manipulated)",
  "outer_span": "string or null (only used for insertion/container clues to represent the container text)",
  "indicator_word": "string (the word/phrase that indicates the operation, e.g., 'scrambled', 'returns')"
}

CRITICAL RULES:
- The `definition_span`, `fodder_span`, `outer_span`, and `indicator_word` MUST be exact substrings from the original clue text (ignore punctuation).
- Be incredibly precise. Do not include the indicator word inside the fodder span.
"""

def parse_clue_with_llm(clue, length):
    """
    Given a clue and length, calls an LLM to structured-parse it.
    """
    # ------------------------------------------------------------------
    # Example using standard OpenAI / LMStudio / Ollama Python Client:
    # ------------------------------------------------------------------
    # try:
    #     from openai import OpenAI
    #     client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    #     response = client.chat.completions.create(
    #         model="gpt-4o",  # Or your local 'charlie' model
    #         response_format={ "type": "json_object" },
    #         messages=[
    #             {"role": "system", "content": SYSTEM_PROMPT},
    #             {"role": "user", "content": f"Clue: {clue}\nLength: {length}"}
    #         ]
    #     )
    #     return json.loads(response.choices[0].message.content)
    # except Exception as e:
    #     return {"error": str(e)}

    # ------------------------------------------------------------------
    # Mocking block for local testing without an API Key configured yet.
    # ------------------------------------------------------------------
    mock_responses = {
        "Smashing atoms up": {
            "clue_type": "anagram",
            "definition_span": "element",
            "fodder_span": "atoms up is",
            "outer_span": None,
            "indicator_word": "Smashing"
        },
        "Glides using paddle on board ship": {
            "clue_type": "insertion",
            "definition_span": "Glides",
            "fodder_span": "paddle",
            "outer_span": "ship",
            "indicator_word": "on board"
        },
        "Monster therefore returns": {
            "clue_type": "reversal",
            "definition_span": "Monster",
            "fodder_span": "therefore",
            "outer_span": None,
            "indicator_word": "returns"
        }
    }

    for key, mock_resp in mock_responses.items():
        if key.lower() in clue.lower():
            return mock_resp

    return {
        "error": "LLM client not hooked up. Please provide an API key in cryptic_skills/categorize.py.",
        "System_Prompt": "See SYSTEM_PROMPT in script.",
        "clue": clue,
        "length": length
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Skill: Parse and Categorize Cryptic Clues via LLM")
    parser.add_argument("--clue", required=True, help="The raw clue string")
    parser.add_argument("--length", required=True, type=int, help="The integer length of the answer")
    
    args = parser.parse_args()
    
    result = parse_clue_with_llm(args.clue, args.length)
    print(json.dumps(result, indent=2))
