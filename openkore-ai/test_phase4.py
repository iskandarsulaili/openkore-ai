"""
Phase 4 Integration Test
Tests PDCA cycle: Plan-Do-Check-Act
"""

import requests
import json
import time

BASE_URL = "http://127.0.0.1:9902"

def test_pdca_plan():
    """Test Plan phase"""
    print("\n=== Testing PDCA Plan Phase ===")
    
    character_state = {
        "name": "TestKnight",
        "level": 75,
        "hp": 3500,
        "max_hp": 4000,
        "sp": 600,
        "max_sp": 800,
        "job_class": "Knight",
        "position": {"map": "prt_fild08", "x": 150, "y": 200},
        "weight": 1200,
        "max_weight": 2000,
        "zeny": 250000
    }
    
    response = requests.post(
        f"{BASE_URL}/api/v1/pdca/plan",
        params={"session_id": "test_pdca_001"},
        json=character_state,
        timeout=60
    )
    
    result = response.json()
    print(f"Strategy provider: {result['strategy'].get('provider', 'unknown')}")
    print(f"Macros generated: {result['macros_generated']}")
    print(f"Macro files: {result['macro_files']}")
    
    return response.status_code == 200 and result['macros_generated'] > 0

def test_pdca_check():
    """Test Check phase"""
    print("\n=== Testing PDCA Check Phase ===")
    
    game_state = {
        "character": {
            "level": 75,
            "hp": 3500,
            "max_hp": 4000,
            "sp": 600,
            "max_sp": 800,
            "weight": 1200,
            "max_weight": 2000,
            "position": {"map": "prt_fild08"}
        },
        "monsters": [{"name": "Poring", "is_aggressive": False}]
    }
    
    response = requests.post(
        f"{BASE_URL}/api/v1/pdca/check",
        params={"session_id": "test_pdca_001"},
        json=game_state,
        timeout=10
    )
    
    result = response.json()
    print(f"HP ratio: {result['current_metrics']['hp_ratio']:.2f}")
    print(f"Weight ratio: {result['current_metrics']['weight_ratio']:.2f}")
    print(f"Evaluation status: {result['evaluation']['status']}")
    
    return response.status_code == 200

def test_full_pdca_cycle():
    """Test complete PDCA cycle"""
    print("\n=== Testing Full PDCA Cycle ===")
    
    character_state = {
        "name": "TestKnight",
        "level": 75,
        "hp": 3500,
        "max_hp": 4000,
        "sp": 600,
        "max_sp": 800,
        "job_class": "Knight",
        "position": {"map": "prt_fild08", "x": 150, "y": 200},
        "weight": 1200,
        "max_weight": 2000,
        "zeny": 250000
    }
    
    response = requests.post(
        f"{BASE_URL}/api/v1/pdca/cycle",
        params={"session_id": "test_pdca_full"},
        json=character_state,
        timeout=90
    )
    
    result = response.json()
    print(f"Status: {result['status']}")
    print(f"Macros generated: {result['macros_generated']}")
    print(f"Strategy from: {result['strategy_provider']}")
    
    # Check if macros were written
    import os
    macro_dir = "openkore-ai/macros"
    if os.path.exists(macro_dir):
        macro_files = [f for f in os.listdir(macro_dir) if f.endswith('.txt')]
        print(f"Macro files in directory: {macro_files}")
    else:
        print(f"Macro directory not found: {macro_dir}")
    
    return response.status_code == 200 and result['status'] == 'cycle_complete'

if __name__ == "__main__":
    print("=" * 60)
    print("PHASE 4 PDCA CYCLE TEST")
    print("=" * 60)
    
    try:
        plan_ok = test_pdca_plan()
        check_ok = test_pdca_check()
        cycle_ok = test_full_pdca_cycle()
        
        print("\n" + "=" * 60)
        print("TEST RESULTS")
        print("=" * 60)
        print(f"PDCA Plan: {'[PASS]' if plan_ok else '[FAIL]'}")
        print(f"PDCA Check: {'[PASS]' if check_ok else '[FAIL]'}")
        print(f"Full PDCA Cycle: {'[PASS]' if cycle_ok else '[FAIL]'}")
        
        if plan_ok and check_ok and cycle_ok:
            print("\n[SUCCESS] Phase 4 tests PASSED - PDCA cycle operational!")
        else:
            print("\n[FAILED] Phase 4 tests FAILED")
            
    except Exception as e:
        print(f"\n[ERROR] TEST ERROR: {e}")
        import traceback
        traceback.print_exc()
