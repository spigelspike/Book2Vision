
import sys
import os

# Add project root to sys.path
sys.path.append(os.getcwd())

from src.analysis import ensure_minimum_scenes

def test_ensure_minimum_scenes():
    # Case 1: Empty scenes
    analysis_result = {"scenes": []}
    ensure_minimum_scenes(analysis_result, min_scenes=4)
    print(f"Case 1 (Empty): {len(analysis_result['scenes'])} scenes")
    assert len(analysis_result['scenes']) == 4

    # Case 2: 1 scene
    analysis_result = {"scenes": [{"description": "Scene 1"}]}
    ensure_minimum_scenes(analysis_result, min_scenes=4)
    print(f"Case 2 (1 Scene): {len(analysis_result['scenes'])} scenes")
    assert len(analysis_result['scenes']) == 4

    # Case 3: 5 scenes (should not change)
    analysis_result = {"scenes": [{"description": f"Scene {i}"} for i in range(5)]}
    ensure_minimum_scenes(analysis_result, min_scenes=4)
    print(f"Case 3 (5 Scenes): {len(analysis_result['scenes'])} scenes")
    assert len(analysis_result['scenes']) == 5

if __name__ == "__main__":
    test_ensure_minimum_scenes()
