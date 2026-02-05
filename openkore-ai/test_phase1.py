"""
Phase 1 Integration Test
Tests HTTP communication between all three components
"""

import requests
import json
import time

# Test data
test_game_state = {
    "character": {
        "name": "TestChar",
        "level": 50,
        "base_exp": 1000000,
        "job_exp": 500000,
        "hp": 500,
        "max_hp": 2000,
        "sp": 100,
        "max_sp": 300,
        "position": {
            "map": "prontera",
            "x": 150,
            "y": 180
        },
        "weight": 500,
        "max_weight": 2000,
        "zeny": 50000,
        "job_class": "Swordsman",
        "status_effects": []
    },
    "monsters": [
        {
            "id": "1001",
            "name": "Poring",
            "hp": 50,
            "max_hp": 50,
            "distance": 5,
            "is_aggressive": False
        }
    ],
    "inventory": [],
    "nearby_players": [],
    "party_members": {},
    "timestamp_ms": int(time.time() * 1000)
}

def test_cpp_engine():
    """Test C++ AI Engine"""
    print("\n=== Testing C++ AI Engine (port 9901) ===")
    
    try:
        # Health check
        response = requests.get("http://127.0.0.1:9901/api/v1/health", timeout=5)
        print(f"Health check: {response.status_code}")
        print(json.dumps(response.json(), indent=2))
        
        # Decision request
        decision_request = {
            "game_state": test_game_state,
            "request_id": "test_001",
            "timestamp_ms": int(time.time() * 1000)
        }
        
        response = requests.post(
            "http://127.0.0.1:9901/api/v1/decide",
            json=decision_request,
            timeout=5
        )
        print(f"\nDecision request: {response.status_code}")
        print(json.dumps(response.json(), indent=2))
        
        return True
    except Exception as e:
        print(f"ERROR: {e}")
        return False

def test_python_service():
    """Test Python AI Service"""
    print("\n=== Testing Python AI Service (port 9902) ===")
    
    try:
        # Health check
        response = requests.get("http://127.0.0.1:9902/api/v1/health", timeout=5)
        print(f"Health check: {response.status_code}")
        print(json.dumps(response.json(), indent=2))
        
        # LLM query
        llm_request = {
            "prompt": "What should I do next?",
            "game_state": test_game_state,
            "context": "Testing Phase 1",
            "request_id": "test_llm_001"
        }
        
        response = requests.post(
            "http://127.0.0.1:9902/api/v1/llm/query",
            json=llm_request,
            timeout=5
        )
        print(f"\nLLM query: {response.status_code}")
        print(json.dumps(response.json(), indent=2))
        
        return True
    except Exception as e:
        print(f"ERROR: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("PHASE 1 INTEGRATION TEST")
    print("=" * 60)
    
    cpp_ok = test_cpp_engine()
    python_ok = test_python_service()
    
    print("\n" + "=" * 60)
    print("TEST RESULTS")
    print("=" * 60)
    print(f"C++ AI Engine: {'PASS' if cpp_ok else 'FAIL'}")
    print(f"Python AI Service: {'PASS' if python_ok else 'FAIL'}")
    
    if cpp_ok and python_ok:
        print("\n[SUCCESS] Phase 1 tests PASSED - HTTP communication working!")
        exit(0)
    else:
        print("\n[FAILED] Phase 1 tests FAILED - check server logs")
        exit(1)
