import os

new_key = "AIzaSyBjgylOeqwDE7_DnZHHvah5RIbh8bTN1Vc"
env_file = ".env"

try:
    with open(env_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    with open(env_file, "w", encoding="utf-8") as f:
        for line in lines:
            if line.startswith("GEMINI_API_KEY="):
                f.write(f"GEMINI_API_KEY={new_key}\n")
                print("Updated GEMINI_API_KEY")
            else:
                f.write(line)
    print("Done updating .env")
except Exception as e:
    print(f"Error updating .env: {e}")
