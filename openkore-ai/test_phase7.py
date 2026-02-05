"""
Phase 7 Integration Test
Tests game lifecycle autonomy features
"""

import requests
import json
import sys

# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = "http://127.0.0.1:9902"

def test_character_creation():
    """Test character creation planning"""
    print("\n=== Testing Character Creation ===")
    try:
        response = requests.post(f"{BASE_URL}/api/v1/lifecycle/create_character", params={"playstyle": "solo_melee"})
        plan = response.json()
        
        print(f"[OK] Job path: {plan['job_path']['name']}")
        print(f"[OK] First job: {plan['job_path']['first_job']}")
        print(f"[OK] Second job: {plan['job_path']['second_job']}")
        print(f"[OK] Milestones: {len(plan['level_milestones'])}")
        print(f"[OK] Stats distribution: {len(plan['stats_per_level'])} levels")
        print(f"[OK] Skills progression: {len(plan['skill_progression'])} skills")
        
        return response.status_code == 200
    except Exception as e:
        print(f"[FAIL] Error: {e}")
        return False

def test_progression_system():
    """Test progression tracking"""
    print("\n=== Testing Progression System ===")
    try:
        character_state = {"name": "TestHero", "level": 35, "job_class": "Swordsman"}
        
        response = requests.post(
            f"{BASE_URL}/api/v1/lifecycle/update_state",
            params={"session_id": "test_lifecycle"},
            json=character_state
        )
        
        result = response.json()
        print(f"[OK] Stage: {result['stage']}")
        print(f"[OK] Goal: {result['goal']}")
        
        if result['next_milestone']:
            print(f"[OK] Next milestone: Level {result['next_milestone']['level']} - {result['next_milestone']['event']}")
            print(f"  Preparation: {result['next_milestone']['preparation']}")
        
        return response.status_code == 200
    except Exception as e:
        print(f"[FAIL] Error: {e}")
        return False

def test_goal_generation():
    """Test autonomous goal generation"""
    print("\n=== Testing Goal Generation ===")
    try:
        character_state = {"level": 50, "job_class": "Knight", "zeny": 100000}
        
        # Test short-term goals
        response = requests.post(
            f"{BASE_URL}/api/v1/lifecycle/generate_goals",
            params={"goal_type": "short"},
            json=character_state
        )
        
        result = response.json()
        print(f"[OK] Short-term goals generated: {result['count']}")
        for i, goal in enumerate(result['goals'][:3], 1):
            print(f"  {i}. [{goal['priority']}] {goal['goal']} ({goal['estimated_time_minutes']} min)")
        
        # Test long-term goals
        response2 = requests.post(
            f"{BASE_URL}/api/v1/lifecycle/generate_goals",
            params={"goal_type": "long"},
            json=character_state
        )
        
        result2 = response2.json()
        print(f"[OK] Long-term goals generated: {result2['count']}")
        for i, goal in enumerate(result2['goals'][:3], 1):
            print(f"  {i}. [{goal['priority']}] {goal['goal']}")
        
        return response.status_code == 200 and response2.status_code == 200
    except Exception as e:
        print(f"[FAIL] Error: {e}")
        return False

def test_quest_detection():
    """Test quest detection"""
    print("\n=== Testing Quest Detection ===")
    try:
        # Test novice level
        response = requests.get(
            f"{BASE_URL}/api/v1/lifecycle/quests",
            params={"character_level": 8, "job_class": "Novice"}
        )
        
        result = response.json()
        print(f"[OK] Available quests for Level 8 Novice: {result['count']}")
        for quest in result['available_quests']:
            print(f"  - {quest['name']} (ID: {quest['id']}, {quest['steps']} steps)")
        
        # Test job change level
        response2 = requests.get(
            f"{BASE_URL}/api/v1/lifecycle/quests",
            params={"character_level": 10, "job_class": "Novice"}
        )
        
        result2 = response2.json()
        print(f"[OK] Available quests for Level 10 Novice: {result2['count']}")
        for quest in result2['available_quests']:
            print(f"  - {quest['name']} (ID: {quest['id']}, {quest['steps']} steps)")
        
        return response.status_code == 200
    except Exception as e:
        print(f"[FAIL] Error: {e}")
        return False

def test_all_job_paths():
    """Test all 6 job path generations"""
    print("\n=== Testing All Job Paths ===")
    try:
        job_styles = ["solo_melee", "solo_magic", "solo_ranged", "support", "economy", "stealth"]
        success = True
        
        for style in job_styles:
            response = requests.post(f"{BASE_URL}/api/v1/lifecycle/create_character", params={"playstyle": style})
            if response.status_code == 200:
                plan = response.json()
                print(f"[OK] {style}: {plan['job_path']['first_job']} -> {plan['job_path']['second_job']}")
            else:
                print(f"[FAIL] {style}: Failed")
                success = False
        
        return success
    except Exception as e:
        print(f"[FAIL] Error: {e}")
        return False

def test_health_check():
    """Test health check includes lifecycle"""
    print("\n=== Testing Health Check ===")
    try:
        response = requests.get(f"{BASE_URL}/api/v1/health")
        health = response.json()
        
        print(f"[OK] Status: {health['status']}")
        print(f"[OK] Version: {health['version']}")
        print(f"[OK] Uptime: {health['uptime_seconds']} seconds")
        
        return response.status_code == 200 and "1.0.0-phase7" in health['version']
    except Exception as e:
        print(f"[FAIL] Error: {e}")
        return False

def test_root_endpoint():
    """Test root endpoint shows lifecycle features"""
    print("\n=== Testing Root Endpoint ===")
    try:
        response = requests.get(f"{BASE_URL}/")
        info = response.json()
        
        print(f"[OK] Phase: {info['phase']}")
        print(f"[OK] Features count: {len(info['features'])}")
        
        lifecycle_features = [f for f in info['features'] if 'Character' in f or 'Progression' in f or 'Goal' in f or 'Quest' in f]
        print(f"[OK] Lifecycle features: {len(lifecycle_features)}")
        for feature in lifecycle_features:
            print(f"  - {feature}")
        
        lifecycle_endpoints = [e for e in info['endpoints'] if 'lifecycle' in e]
        print(f"[OK] Lifecycle endpoints: {len(lifecycle_endpoints)}")
        for endpoint in lifecycle_endpoints:
            print(f"  - {endpoint}")
        
        return response.status_code == 200 and len(lifecycle_features) >= 4
    except Exception as e:
        print(f"[FAIL] Error: {e}")
        return False

if __name__ == "__main__":
    print("=" * 70)
    print("PHASE 7: GAME LIFECYCLE AUTONOMY TEST")
    print("=" * 70)
    
    results = {}
    
    results['health'] = test_health_check()
    results['root'] = test_root_endpoint()
    results['creation'] = test_character_creation()
    results['job_paths'] = test_all_job_paths()
    results['progression'] = test_progression_system()
    results['goals'] = test_goal_generation()
    results['quests'] = test_quest_detection()
    
    print("\n" + "=" * 70)
    print("TEST RESULTS SUMMARY")
    print("=" * 70)
    print(f"Health Check:          {'[PASS]' if results['health'] else '[FAIL]'}")
    print(f"Root Endpoint:         {'[PASS]' if results['root'] else '[FAIL]'}")
    print(f"Character Creation:    {'[PASS]' if results['creation'] else '[FAIL]'}")
    print(f"All Job Paths:         {'[PASS]' if results['job_paths'] else '[FAIL]'}")
    print(f"Progression System:    {'[PASS]' if results['progression'] else '[FAIL]'}")
    print(f"Goal Generation:       {'[PASS]' if results['goals'] else '[FAIL]'}")
    print(f"Quest Detection:       {'[PASS]' if results['quests'] else '[FAIL]'}")
    print("=" * 70)
    
    if all(results.values()):
        print("\n*** ALL TESTS PASSED - Phase 7 Complete! ***")
        print("\n[OK] Full game autonomy operational!")
        print("[OK] Character creation: 6 job paths available")
        print("[OK] Progression tracking: Novice -> First Job -> Second Job -> Endgame")
        print("[OK] Goal generation: Short-term and long-term goals")
        print("[OK] Quest automation: Detection and execution framework")
        print("\nNext: Phase 8 - Social Interaction System")
    else:
        print("\n[FAIL] SOME TESTS FAILED")
        failed = [name for name, passed in results.items() if not passed]
        print(f"Failed tests: {', '.join(failed)}")
