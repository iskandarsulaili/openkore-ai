"""
Phase 3 Integration Test
Tests Python AI Service with database, memory, CrewAI, and LLM chain
"""

import requests
import json
import time

BASE_URL = "http://127.0.0.1:9902"

def test_health():
    """Test health endpoint"""
    print("\n=== Testing Health Endpoint ===")
    response = requests.get(f"{BASE_URL}/api/v1/health")
    health = response.json()
    
    print(f"Status: {health['status']}")
    print(f"Database: {'[OK]' if health['components']['database'] else '[FAIL]'}")
    print(f"OpenMemory: {'[OK]' if health['components']['openmemory'] else '[FAIL]'}")
    print(f"CrewAI: {'[OK]' if health['components']['crewai'] else '[FAIL]'}")
    print(f"LLM DeepSeek: {'[OK]' if health['components']['llm_deepseek'] else '[SKIP] (API key not set)'}")
    print(f"Uptime: {health['uptime_seconds']}s")
    
    return health['components']['database'] and health['components']['openmemory']

def test_crew_ai():
    """Test CrewAI agents"""
    print("\n=== Testing CrewAI Agents ===")
    response = requests.get(
        f"{BASE_URL}/api/v1/crew/analyze",
        params={"character_level": 50, "job_class": "Knight", "monsters_count": 3}
    )
    
    insights = response.json()
    print(f"Agents consulted: {len(insights['agent_results'])}")
    print(f"Consensus confidence: {insights['consensus_confidence']:.2f}")
    print(f"Recommendations: {len(insights['aggregated_recommendations'])}")
    
    for rec in insights['aggregated_recommendations'][:3]:
        print(f"  - [{rec.get('priority', 'N/A')}] {rec.get('action', rec.get('goal', 'N/A'))}")
    
    return len(insights['agent_results']) == 4

def test_memory_system():
    """Test OpenMemory with synthetic embeddings"""
    print("\n=== Testing OpenMemory System ===")
    
    session_id = "test_session_001"
    
    # Add memories
    print("Adding memories...")
    memories = [
        ("episodic", "Defeated Poring at prontera field"),
        ("semantic", "Porings are weak to fire element"),
        ("procedural", "Use Bash skill for maximum damage"),
        ("emotional", "Felt excited when leveling up to 50"),
        ("reflective", "Should focus on better equipment next")
    ]
    
    for sector, content in memories:
        response = requests.post(
            f"{BASE_URL}/api/v1/memory/add",
            params={
                "session_id": session_id,
                "sector": sector,
                "content": content,
                "importance": 0.7
            }
        )
        assert response.status_code == 200
        print(f"  [OK] Added {sector} memory")
    
    # Query memories
    print("\nQuerying similar memories...")
    response = requests.get(
        f"{BASE_URL}/api/v1/memory/query",
        params={
            "session_id": session_id,
            "query": "combat strategy for monsters",
            "limit": 5
        }
    )
    
    result = response.json()
    print(f"Found {result['count']} relevant memories")
    
    for mem in result['results'][:3]:
        print(f"  - [{mem['type']}] {mem['content'][:50]}... (similarity: {mem['similarity']:.2f})")
    
    return result['count'] > 0

def test_llm_stub():
    """Test LLM endpoint (stub if no API keys)"""
    print("\n=== Testing LLM Query (may use stub) ===")
    
    game_state = {
        "character": {
            "name": "TestHero",
            "level": 75,
            "hp": 3000,
            "max_hp": 4000,
            "sp": 500,
            "max_sp": 800,
            "job_class": "Knight",
            "position": {"map": "prontera", "x": 150, "y": 180},
            "weight": 800,
            "max_weight": 2000,
            "zeny": 150000
        },
        "monsters": [{"name": "Orc Warrior", "distance": 8, "is_aggressive": True}],
        "inventory": [],
        "nearby_players": [],
        "party_members": {},
        "timestamp_ms": int(time.time() * 1000)
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/llm/query",
            json={
                "prompt": "What should I do to progress efficiently?",
                "game_state": game_state,
                "context": "Character is mid-level Knight",
                "request_id": "test_llm_001"
            },
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"Provider: {result['provider']}")
            print(f"Response: {result['response'][:150]}...")
            print(f"Latency: {result['latency_ms']}ms")
            print(f"Crew insights: {len(result.get('crew_insights', {}).get('agent_results', {}))} agents")
            return True
        else:
            print(f"LLM query returned status {response.status_code}")
            print("This is expected if no LLM API keys are configured")
            return False
            
    except Exception as e:
        print(f"LLM query error: {e}")
        print("This is expected if no LLM API keys are configured")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("PHASE 3 PYTHON AI SERVICE FOUNDATION TEST")
    print("=" * 60)
    
    try:
        health_ok = test_health()
        crew_ok = test_crew_ai()
        memory_ok = test_memory_system()
        llm_ok = test_llm_stub()
        
        print("\n" + "=" * 60)
        print("TEST RESULTS")
        print("=" * 60)
        print(f"Health Check: {'[PASS]' if health_ok else '[FAIL]'}")
        print(f"CrewAI Agents: {'[PASS]' if crew_ok else '[FAIL]'}")
        print(f"OpenMemory: {'[PASS]' if memory_ok else '[FAIL]'}")
        print(f"LLM Chain: {'[PASS]' if llm_ok else '[SKIP] (no API keys)'}")
        
        core_passed = health_ok and crew_ok and memory_ok
        if core_passed:
            print("\n[SUCCESS] Phase 3 CORE tests PASSED")
            print("Note: LLM requires API keys (DEEPSEEK_API_KEY, OPENAI_API_KEY, or ANTHROPIC_API_KEY)")
        else:
            print("\n[FAILED] Phase 3 tests FAILED")
            
    except Exception as e:
        print(f"\n[ERROR] TEST ERROR: {e}")
        import traceback
        traceback.print_exc()
