import argparse
import json
import re

# ----------------------------------------------------------------------
# Core Foreman Skill: Grid State Manager
# 
# This skill handles the spatial reasoning of a cryptic crossword grid.
# It maintains the state of the 15x15 (or arbitrary size) puzzle mathematically, 
# calculates intersecting checked letters, and returns the current '.' 
# pattern for any given clue to pass to algorithmic solvers.
# 
# Input: A JSON file defining the grid layout (which clue starts at which 
# coordinates) and the current placed answers.
# ----------------------------------------------------------------------

class CrosswordGrid:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        # Initialize an empty grid of '.'
        self.grid = [['.' for _ in range(width)] for _ in range(height)]
        # Map clue IDs (e.g., "1A") to their starting coordinates (x, y), length, and direction
        self.clues = {}

    def add_clue_metadata(self, clue_id, x, y, length, direction):
        self.clues[clue_id] = {
            "x": x,
            "y": y,
            "length": length,
            "direction": direction
        }
        
    def get_pattern(self, clue_id):
        """Returns the current known letters for a clue, e.g., 'P...S....'"""
        if clue_id not in self.clues:
            return {"error": f"Clue {clue_id} not found in grid metadata."}
            
        meta = self.clues[clue_id]
        pattern = ""
        x, y = meta["x"], meta["y"]
        
        for i in range(meta["length"]):
            curr_x = x + (i if meta["direction"] == "Across" else 0)
            curr_y = y + (i if meta["direction"] == "Down" else 0)
            
            if curr_x >= self.width or curr_y >= self.height:
                return {"error": f"Clue {clue_id} extends beyond grid boundaries."}
                
            pattern += self.grid[curr_y][curr_x]
            
        return {"pattern": pattern}

    def place_answer(self, clue_id, answer):
        """Places a solved answer into the grid, updating intersecting cells."""
        if clue_id not in self.clues:
            return {"error": f"Clue {clue_id} not found in grid metadata."}
            
        meta = self.clues[clue_id]
        if len(answer) != meta["length"]:
            return {"error": f"Answer length ({len(answer)}) does not match clue length ({meta['length']})."}
            
        x, y = meta["x"], meta["y"]
        
        for i, char in enumerate(answer.upper()):
            curr_x = x + (i if meta["direction"] == "Across" else 0)
            curr_y = y + (i if meta["direction"] == "Down" else 0)
            
            # Check for conflicting letters already placed
            existing = self.grid[curr_y][curr_x]
            if existing != '.' and existing != char:
                return {"error": f"Conflict at ({curr_x},{curr_y}): Tried to place '{char}' but '{existing}' is already there."}
                
            self.grid[curr_y][curr_x] = char
            
        return {"success": True, "message": f"Placed {answer} at {clue_id}"}
        
    def print_grid(self):
        """Utility to visualize the raw grid array."""
        return "\n".join(" ".join(row) for row in self.grid)

# --- Helper to load and orchestrate state via CLI ---

def load_and_execute(state_file, action, clue_id, answer=None):
    # 1. Load the state (in a real agent, this lives in memory or a DB)
    try:
        with open(state_file, 'r', encoding='utf-8') as f:
            state_data = json.load(f)
    except FileNotFoundError:
        return {"error": f"State file {state_file} not found. Please initialize one."}

    # 2. Rehydrate the grid object
    grid = CrosswordGrid(state_data.get("width", 15), state_data.get("height", 15))
    
    for c_id, meta in state_data.get("clues", {}).items():
        grid.add_clue_metadata(c_id, meta["x"], meta["y"], meta["length"], meta["direction"])
        
    for c_id, placed_ans in state_data.get("placed_answers", {}).items():
        grid.place_answer(c_id, placed_ans)

    # 3. Execute the requested action
    if action == "get_pattern":
        return grid.get_pattern(clue_id)
        
    elif action == "place_answer":
        if not answer:
            return {"error": "Must provide an --answer string to place."}
        res = grid.place_answer(clue_id, answer)
        
        if "success" in res:
            # 4. Save the updated state out
            state_data.setdefault("placed_answers", {})[clue_id] = answer.upper()
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(state_data, f, indent=2)
                
            res["new_grid_state"] = grid.print_grid()
        return res
        
    else:
        return {"error": f"Unknown action: {action}"}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Skill: Foreman Grid State Manager")
    parser.add_argument("--state_file", required=True, help="Path to the JSON file tracking the grid structure and placed answers")
    parser.add_argument("--action", required=True, choices=["get_pattern", "place_answer"], help="Action to perform")
    parser.add_argument("--clue", required=True, help="The Clue ID (e.g. '1A')")
    parser.add_argument("--answer", required=False, help="The string to place (if action=place_answer)")
    
    args = parser.parse_args()
    
    result = load_and_execute(args.state_file, args.action, args.clue, args.answer)
    print(json.dumps(result, indent=2))
