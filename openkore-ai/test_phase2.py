"""
Phase 2 Integration Test
Tests multi-tier decision system
"""

import requests
import json
import time

def test_reflex_tier():
    """Test reflex tier with critical HP"""
    print("\n=== Testing Reflex Tier (<1ms) ===")
    
    game_state = {
        "character": {
            "name": "TestChar",
            "level": 50,
            "hp": 100,      # Critical HP (20% of 500)
            "max_hp": 500,
            "sp": 50,
            "max_sp": 200,
            "position": {"map": "prontera", "x": 150, "y": 180},
            "weight": 500,
            "max_weight": 2000,
            "zeny": 50000,
            "job_class": "Swordsman",
            "status_effects": []
        },
        "monsters": [],
        "inventory": [],
        "nearby_players": [],
        "party_members": {},
        "timestamp_ms": int(time.time() * 1000)
    }
    
    response = requests.post(
        "http://127.0.0.1:9901/api/v1/decide",
        json={
            "game_state": game_state,
            "request_id": "test_reflex",
            "timestamp_ms": int(time.time() * 1000)
        },
        timeout=5
    )
    
    result = response.json()
    print(f"Tier used: {result['tier_used']}")
    print(f"Action: {result['action']['type']}")
    print(f"Reason: {result['action']['reason']}")
    print(f"Latency: {result['latency_ms']}ms")
    
    assert result['tier_used'] == 'reflex', "Should use reflex tier for critical HP"
    assert result['action']['type'] == 'item', "Should use healing item"
    assert result['latency_ms'] < 5, "Reflex should be < 5ms"
    return True

def test_rules_tier():
    """Test rules tier with combat situation"""
    print("\n=== Testing Rules Tier (<10ms) ===")
    
    game_state = {
        "character": {
            "name": "TestChar",
            "level": 50,
            "hp": 800,      # Healthy
            "max_hp": 1000,
            "sp": 150,
            "max_sp": 300,
            "position": {"map": "prontera", "x": 150, "y": 180},
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
                "distance": 8,
                "is_aggressive": False
            },
            {
                "id": "1002",
                "name": "Lunatic",
                "hp": 60,
                "max_hp": 60,
                "distance": 5,
                "is_aggressive": True
            }
        ],
        "inventory": [],
        "nearby_players": [],
        "party_members": {},
        "timestamp_ms": int(time.time() * 1000)
    }
    
    response = requests.post(
        "http://127.0.0.1:9901/api/v1/decide",
        json={
            "game_state": game_state,
            "request_id": "test_rules",
            "timestamp_ms": int(time.time() * 1000)
        },
        timeout=5
    )
    
    result = response.json()
    print(f"Tier used: {result['tier_used']}")
    print(f"Action: {result['action']['type']}")
    print(f"Reason: {result['action']['reason']}")
    print(f"Latency: {result['latency_ms']}ms")
    
    assert result['tier_used'] == 'rules', "Should use rules tier for combat"
    assert result['action']['type'] in ['attack', 'skill'], "Should attack or use skill"
    assert result['latency_ms'] < 15, "Rules should be < 15ms"
    return True

def test_tier_statistics():
    """Test metrics endpoint"""
    print("\n=== Testing Metrics Endpoint ===")
    
    response = requests.get("http://127.0.0.1:9901/api/v1/metrics", timeout=5)
    metrics = response.json()
    
    print(f"Total requests: {metrics['requests_total']}")
    print(f"Reflex tier: {metrics['requests_by_tier']['reflex']}")
    print(f"Rules tier: {metrics['requests_by_tier']['rules']}")
    print(f"ML tier: {metrics['requests_by_tier']['ml']}")
    print(f"LLM tier: {metrics['requests_by_tier']['llm']}")
    print(f"Average latency: {metrics['avg_latency_ms']:.2f}ms")
    
    return True

if __name__ == "__main__":
    print("=" * 60)
    print("PHASE 2 MULTI-TIER DECISION SYSTEM TEST")
    print("=" * 60)
    
    try:
        reflex_ok = test_reflex_tier()
        rules_ok = test_rules_tier()
        stats_ok = test_tier_statistics()
        
        print("\n" + "=" * 60)
        print("TEST RESULTS")
        print("=" * 60)
        print(f"Reflex Tier: {'✓ PASS' if reflex_ok else '✗ FAIL'}")
        print(f"Rules Tier: {'✓ PASS' if rules_ok else '✗ FAIL'}")
        print(f"Statistics: {'✓ PASS' if stats_ok else '✗ FAIL'}")
        
        if reflex_ok and rules_ok and stats_ok:
            print("\n✓ Phase 2 tests PASSED - Multi-tier system working!")
        else:
            print("\n✗ Phase 2 tests FAILED")
            
    except Exception as e:
        print(f"\n✗ TEST ERROR: {e}")
