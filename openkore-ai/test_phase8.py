"""
Phase 8 Integration Test
Tests social interaction system
"""

import requests
import time

BASE_URL = "http://127.0.0.1:9902"

def test_personality():
    """Test personality engine"""
    print("\n=== Testing Personality Engine ===")
    response = requests.get(f"{BASE_URL}/api/v1/social/personality")
    personality = response.json()
    
    print(f"Chattiness: {personality['traits']['chattiness']}")
    print(f"Friendliness: {personality['traits']['friendliness']}")
    print(f"Style: {personality['conversation_style']}")
    print(f"Emoji rate: {personality['emoji_usage_rate']:.2f}")
    
    return response.status_code == 200

def test_reputation():
    """Test reputation system"""
    print("\n=== Testing Reputation System ===")
    
    # Get initial reputation
    response = requests.get(
        f"{BASE_URL}/api/v1/social/reputation",
        params={"character_name": "MyChar", "player_name": "TestPlayer"}
    )
    rep = response.json()
    print(f"Initial: {rep['reputation']} ({rep['tier']})")
    
    # Update reputation (positive)
    response = requests.post(
        f"{BASE_URL}/api/v1/social/reputation/update",
        params={
            "character_name": "MyChar",
            "player_name": "TestPlayer",
            "change": 10,
            "reason": "helpful interaction"
        }
    )
    rep = response.json()
    print(f"After +10: {rep['new_reputation']} ({rep['tier']})")
    
    return response.status_code == 200

def test_chat_generation():
    """Test human-like chat with DeepSeek"""
    print("\n=== Testing Chat Generation (DeepSeek LLM) ===")
    
    response = requests.post(
        f"{BASE_URL}/api/v1/social/chat",
        params={
            "character_name": "MyChar",
            "player_name": "FriendlyPlayer",
            "message": "Hi! How are you doing?",
            "message_type": "whisper",
            "my_level": 75,
            "player_level": 70,
            "my_job": "Knight"
        },
        timeout=60
    )
    
    result = response.json()
    print(f"Action: {result.get('action', 'N/A')}")
    if 'response_text' in result:
        print(f"Response: {result['response_text']}")
    else:
        print(f"Reason: {result.get('reason', 'N/A')}")
    
    return response.status_code == 200

def test_party_invite():
    """Test party invite handling"""
    print("\n=== Testing Party Invite ===")
    
    # Set up reputation first
    requests.post(
        f"{BASE_URL}/api/v1/social/reputation/update",
        params={
            "character_name": "MyChar",
            "player_name": "PartyLeader",
            "change": 50,
            "reason": "known player"
        }
    )
    
    response = requests.post(
        f"{BASE_URL}/api/v1/social/party_invite",
        params={
            "character_name": "MyChar",
            "player_name": "PartyLeader",
            "my_level": 60
        }
    )
    
    result = response.json()
    print(f"Action: {result['action']}")
    if 'message' in result:
        print(f"Message: {result['message']}")
    
    return response.status_code == 200

def test_trade_handling():
    """Test trade evaluation"""
    print("\n=== Testing Trade Handling ===")
    
    # Fair trade
    response = requests.post(
        f"{BASE_URL}/api/v1/social/trade",
        params={"character_name": "MyChar", "player_name": "Trader"},
        json={
            "my_zeny_offer": 0,
            "their_zeny_offer": 10000,
            "my_items": [],
            "their_items": [{"name": "Blue Potion", "amount": 10}]
        }
    )
    
    result = response.json()
    print(f"Action: {result['action']}")
    if 'reason' in result:
        print(f"Reason: {result['reason']}")
    
    return response.status_code == 200

if __name__ == "__main__":
    print("=" * 60)
    print("PHASE 8 SOCIAL INTERACTION SYSTEM TEST")
    print("=" * 60)
    
    personality_ok = test_personality()
    reputation_ok = test_reputation()
    chat_ok = test_chat_generation()
    party_ok = test_party_invite()
    trade_ok = test_trade_handling()
    
    print("\n" + "=" * 60)
    print("TEST RESULTS")
    print("=" * 60)
    print(f"Personality Engine: {'[PASS]' if personality_ok else '[FAIL]'}")
    print(f"Reputation System: {'[PASS]' if reputation_ok else '[FAIL]'}")
    print(f"Chat Generation: {'[PASS]' if chat_ok else '[FAIL]'}")
    print(f"Party Invite: {'[PASS]' if party_ok else '[FAIL]'}")
    print(f"Trade Handling: {'[PASS]' if trade_ok else '[FAIL]'}")
    
    if all([personality_ok, reputation_ok, chat_ok, party_ok, trade_ok]):
        print("\n[SUCCESS] Phase 8 tests PASSED - Social intelligence operational!")
    else:
        print("\n[FAILED] Phase 8 tests FAILED")
