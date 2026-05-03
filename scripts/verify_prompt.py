
import sys
import os

# Add project root to sys.path
sys.path.append(os.getcwd())

from src.prompts import ENTITY_PROMPT_TEMPLATE

def verify_prompt():
    name = "Moby Dick"
    role = "Antagonist"
    species = "Colossal sperm whale, unnaturally white coloration, massive head covered in old scars"
    style = "Cinematic"
    
    formatted_prompt = ENTITY_PROMPT_TEMPLATE.format(
        name=name,
        role=role,
        species=species,
        style=style
    )
    
    print("--- Formatted Prompt ---")
    print(formatted_prompt)
    
    if species in formatted_prompt:
        print("\n✅ Verification PASSED: Species description is included in the prompt.")
    else:
        print("\n❌ Verification FAILED: Species description is MISSING.")

if __name__ == "__main__":
    verify_prompt()
