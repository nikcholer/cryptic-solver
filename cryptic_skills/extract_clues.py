import argparse
import sys
import ruamel.yaml

# ----------------------------------------------------------------------
# Core Foreman Skill: LLM Clue Extraction
# 
# This skill takes raw, messy text (like an OCR dump of a PDF crossword)
# and uses an LLM to reliably extract the clues, enumerations, and directions
# into our standard YAML working format.
# ----------------------------------------------------------------------

SYSTEM_PROMPT = """
You are an expert data extraction assistant. You will be provided with raw, potentially messy text containing cryptic crossword clues (often from OCR).

Your task is to extract every clue into a specific YAML structure.

CRITICAL RULES:
1. Extract the clue number, direction (Across or Down), the exact clue text, and the enumeration (e.g., "(5)" or "(4,3)").
2. Calculate the total string length of the answer based on the enumeration (e.g., "(4,3)" -> 7).
3. The root must be a YAML sequence (a list).
4. Do not output markdown code blocks (```yaml). Output ONLY valid YAML.

Required YAML Schema per item:
- id: "1A" (Number + 'A' for Across or 'D' for Down)
  clue: "The exact clue text (number)"
  enumeration: "(N,M)"
  length: integer 
  direction: "Across" or "Down"
  status: "unsolved"
  clue_type: null
  definition_span: null
  fodder_span: null
  outer_span: null
  indicator_word: null
  algorithmic_candidates: []
  llm_ranking: {}
  answer: null
  checked_letters: "........." (Dots matching the length of the answer)
"""

def extract_clues_with_llm(raw_text):
    """
    Given raw text, calls an LLM to extract the clues into YAML.
    """
    # ------------------------------------------------------------------
    # Example using standard OpenAI / LMStudio / Ollama Python Client:
    # ------------------------------------------------------------------
    # try:
    #     from openai import OpenAI
    #     import os
    #     client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    #     response = client.chat.completions.create(
    #         model="gpt-4o",
    #         messages=[
    #             {"role": "system", "content": SYSTEM_PROMPT},
    #             {"role": "user", "content": raw_text}
    #         ],
    #         temperature=0.0
    #     )
    #     return response.choices[0].message.content.strip()
    # except Exception as e:
    #     return f"Error: {e}"

    # ------------------------------------------------------------------
    # Mock behavior for local testing: outputs a stub of the required YAML
    # ------------------------------------------------------------------
    mock_yaml = """\
- id: "1A"
  clue: "Smashing atoms up is creating element (9)"
  enumeration: "(9)"
  length: 9
  direction: "Across"
  status: "unsolved"
  clue_type: null
  definition_span: null
  fodder_span: null
  outer_span: null
  indicator_word: null
  algorithmic_candidates: []
  llm_ranking: {}
  answer: null
  checked_letters: "........."
"""
    return mock_yaml

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Skill: Extract Cryptic Clues from Raw Text into YAML")
    parser.add_argument("--input", required=True, help="Path to a text file containing the raw puzzle data (e.g., OCR dump)")
    parser.add_argument("--output", required=True, help="Path where the YAML output should be saved")
    
    args = parser.parse_args()
    
    try:
        with open(args.input, 'r', encoding='utf-8') as f:
            raw_data = f.read()
    except Exception as e:
        print(f"Error reading input file: {e}")
        sys.exit(1)
        
    print(f"Extracting clues using LLM constraint prompt...")
    yaml_output = extract_clues_with_llm(raw_data)
    
    if yaml_output.startswith("Error"):
        print(yaml_output)
        sys.exit(1)
        
    try:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(yaml_output)
        print(f"Successfully wrote parsed YAML to {args.output}")
    except Exception as e:
        print(f"Error writing to output file: {e}")
        sys.exit(1)
