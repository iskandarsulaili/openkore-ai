"""
End-to-End Integration Test
Tests complete system: Perl Plugin -> C++ Engine -> Python Service -> DeepSeek LLM
"""

import requests
import json
import time
import sys

# Force UTF-8 encoding for Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

C_ENGINE = "http://127.0.0.1:9901"
PY_SERVICE = "http://127.0.0.1:9902"

def test_full_decision_pipeline():
    """Test complete decision flow through all tiers"""
    print("\n=== End-to-End Decision Pipeline ===")
    
    # Simulate game state from Perl plugin
    game_state = {
        "character": {
            "name": "IntegrationTest",
            "level": 65,
            "hp": 600,  # Low but not critical
            "max_hp": 1000,
            "sp": 300,
            "max_sp": 500,
            "job_class": "Knight",
            "position": {"map": "prt_fild08", "x": 150, "y": 200},
            "weight": 1500,
            "max_weight": 2000,
            "zeny": 125000,
            "base_exp": 5000000,
            "job_exp": 2500000,
            "status_effects": []
        },
        "monsters": [
            {"id": "1001", "name": "Poring", "hp": 50, "max_hp": 50, "distance": 7, "is_aggressive": False},
            {"id": "1002", "name": "Lunatic", "hp": 60, "max_hp": 60, "distance": 5, "is_aggressive": True}
        ],
        "inventory": [
            {"id": "501", "name": "Red Potion", "amount": 50, "type": "consumable"},
            {"id": "502", "name": "Orange Potion", "amount": 30, "type": "consumable"}
        ],
        "nearby_players": [
            {"name": "FriendPlayer", "level": 70, "guild": "TestGuild", "distance": 10, "is_party_member": False}
        ],
        "party_members": {},
        "timestamp_ms": int(time.time() * 1000)
    }
    
    # Test C++ Engine decision
    response = requests.post(
        f"{C_ENGINE}/api/v1/decide",
        json={
            "game_state": game_state,
            "request_id": "e2e_001",
            "timestamp_ms": int(time.time() * 1000)
        },
        timeout=10
    )
    
    result = response.json()
    print(f"✓ C++ Engine Response:")
    print(f"  Tier: {result['tier_used']}")
    print(f"  Action: {result['action']['type']}")
    print(f"  Reason: {result['action']['reason']}")
    print(f"  Latency: {result['latency_ms']}ms")
    
    assert response.status_code == 200
    assert result['action']['type'] != "error"
    
    return True

def test_full_pdca_cycle():
    """Test complete PDCA cycle with LLM"""
    print("\n=== End-to-End PDCA Cycle ===")
    
    character_state = {
        "name": "PDCATestChar",
        "level": 80,
        "hp": 4500,
        "max_hp": 5000,
        "sp": 800,
        "max_sp": 1000,
        "job_class": "Lord Knight",
        "position": {"map": "gl_knt02", "x": 100, "y": 100},
        "weight": 1800,
        "max_weight": 2500,
        "zeny": 750000
    }
    
    response = requests.post(
        f"{PY_SERVICE}/api/v1/pdca/cycle",
        params={"session_id": "e2e_pdca"},
        json=character_state,
        timeout=90
    )
    
    result = response.json()
    print(f"✓ PDCA Cycle Complete:")
    print(f"  Status: {result['status']}")
    print(f"  Strategy from: {result['strategy_provider']}")
    print(f"  Macros generated: {result['macros_generated']}")
    
    assert response.status_code == 200
    assert result['status'] == 'cycle_complete'
    
    return True

def test_social_chat_e2e():
    """Test social chat through complete pipeline"""
    print("\n=== End-to-End Social Chat ===")
    
    # Update reputation first
    requests.post(
        f"{PY_SERVICE}/api/v1/social/reputation/update",
        params={
            "character_name": "E2ETest",
            "player_name": "ChattyPlayer",
            "change": 50,
            "reason": "integration test"
        }
    )
    
    # Send chat message
    response = requests.post(
        f"{PY_SERVICE}/api/v1/social/chat",
        params={
            "character_name": "E2ETest",
            "player_name": "ChattyPlayer",
            "message": "Want to party up for some grinding?",
            "message_type": "whisper",
            "my_level": 80,
            "player_level": 75,
            "my_job": "Lord Knight"
        },
        timeout=60
    )
    
    result = response.json()
    print(f"✓ Social Chat:")
    print(f"  Action: {result.get('action', 'N/A')}")
    if 'response_text' in result:
        print(f"  AI Response: {result['response_text']}")
    
    assert response.status_code == 200
    
    return True

def test_ml_status():
    """Test ML pipeline status"""
    print("\n=== ML Pipeline Status ===")
    
    response = requests.get(f"{PY_SERVICE}/api/v1/ml/status")
    status = response.json()
    
    print(f"✓ ML System:")
    print(f"  Cold-start phase: {status['cold_start_phase']}")
    print(f"  Training samples: {status['training_samples']}")
    print(f"  Model trained: {status['model_trained']}")
    
    return response.status_code == 200

def test_all_systems_health():
    """Test health of all systems"""
    print("\n=== System Health Check ===")
    
    # C++ Engine
    cpp_health = requests.get(f"{C_ENGINE}/api/v1/health", timeout=5)
    cpp_data = cpp_health.json()
    print(f"✓ C++ Engine: {cpp_data['status']}")
    print(f"  Components: Reflex={cpp_data['components']['reflex_tier']}, Rules={cpp_data['components']['rules_tier']}")
    
    # Python Service
    py_health = requests.get(f"{PY_SERVICE}/api/v1/health", timeout=5)
    py_data = py_health.json()
    print(f"✓ Python Service: {py_data['status']}")
    print(f"  Components: DB={py_data['components']['database']}, LLM={py_data['components']['llm_deepseek']}")
    
    return cpp_health.status_code == 200 and py_health.status_code == 200

if __name__ == "__main__":
    print("=" * 70)
    print("OPENKORE ADVANCED AI - END-TO-END INTEGRATION TEST")
    print("=" * 70)
    
    try:
        health_ok = test_all_systems_health()
        decision_ok = test_full_decision_pipeline()
        pdca_ok = test_full_pdca_cycle()
        chat_ok = test_social_chat_e2e()
        ml_ok = test_ml_status()
        
        print("\n" + "=" * 70)
        print("INTEGRATION TEST RESULTS")
        print("=" * 70)
        print(f"System Health: {'✓ PASS' if health_ok else '✗ FAIL'}")
        print(f"Decision Pipeline: {'✓ PASS' if decision_ok else '✗ FAIL'}")
        print(f"PDCA Cycle: {'✓ PASS' if pdca_ok else '✗ FAIL'}")
        print(f"Social Chat: {'✓ PASS' if chat_ok else '✗ FAIL'}")
        print(f"ML Pipeline: {'✓ PASS' if ml_ok else '✗ FAIL'}")
        
        if all([health_ok, decision_ok, pdca_ok, chat_ok, ml_ok]):
            print("\n" + "=" * 70)
            print("✓✓✓ ALL INTEGRATION TESTS PASSED ✓✓✓")
            print("OpenKore Advanced AI System is PRODUCTION READY!")
            print("=" * 70)
        else:
            print("\n✗ Some integration tests failed - review logs")
            
    except Exception as e:
        print(f"\n✗ INTEGRATION TEST ERROR: {e}")
        import traceback
        traceback.print_exc()
