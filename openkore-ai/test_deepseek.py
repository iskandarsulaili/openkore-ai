"""
Test DeepSeek API Connection
Verify that the API key is configured correctly and the latest model is working
"""

import os
import sys
import asyncio
import httpx
from pathlib import Path

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Add ai-service/src to path to import modules
sys.path.insert(0, str(Path(__file__).parent / "ai-service" / "src"))

from dotenv import load_dotenv

# Load .env from ai-service directory
env_path = Path(__file__).parent / "ai-service" / ".env"
load_dotenv(env_path)

async def test_deepseek_connection():
    """Test DeepSeek API with latest model"""
    
    api_key = os.getenv("DEEPSEEK_API_KEY")
    
    print("=" * 60)
    print("DeepSeek API Connection Test")
    print("=" * 60)
    print(f"API Key: {'✓ Found' if api_key else '✗ Not Found'}")
    
    if not api_key:
        print("\n❌ DEEPSEEK_API_KEY not found in environment variables")
        print("Please ensure .env file exists with the API key")
        return False
    
    # Show partial key for verification
    print(f"API Key (partial): {api_key[:15]}...{api_key[-4:]}")
    
    # Test with deepseek-chat (latest stable model)
    endpoint = "https://api.deepseek.com/v1/chat/completions"
    model = "deepseek-chat"
    
    print(f"\nEndpoint: {endpoint}")
    print(f"Model: {model}")
    print("\nTest Query: 'What is the best strategy for a level 50 Knight in Ragnarok Online?'")
    print("\nSending request...")
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                endpoint,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "messages": [
                        {
                            "role": "system", 
                            "content": "You are an AI assistant for Ragnarok Online gameplay with deep knowledge of game mechanics, character builds, and strategies."
                        },
                        {
                            "role": "user", 
                            "content": "What is the best strategy for a level 50 Knight in Ragnarok Online?"
                        }
                    ],
                    "max_tokens": 8192,
                    "temperature": 0.7
                }
            )
            
            print(f"\nStatus Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                
                print("\n" + "=" * 60)
                print("✓ SUCCESS - DeepSeek API is working!")
                print("=" * 60)
                
                # Extract response
                message = data['choices'][0]['message']['content']
                model_used = data['model']
                usage = data.get('usage', {})
                
                print(f"\nModel Used: {model_used}")
                print(f"Tokens Used: {usage.get('total_tokens', 'N/A')}")
                print(f"  - Prompt: {usage.get('prompt_tokens', 'N/A')}")
                print(f"  - Completion: {usage.get('completion_tokens', 'N/A')}")
                
                print("\n" + "-" * 60)
                print("RESPONSE:")
                print("-" * 60)
                print(message)
                print("-" * 60)
                
                return True
            else:
                print(f"\n❌ API Error: {response.status_code}")
                print(f"Response: {response.text}")
                return False
                
    except httpx.TimeoutException:
        print("\n❌ Request timed out (60s)")
        print("This could indicate network issues or API unavailability")
        return False
    except Exception as e:
        print(f"\n❌ Connection Error: {e}")
        print(f"Error Type: {type(e).__name__}")
        return False

async def test_provider_chain():
    """Test the LLMProviderChain class directly"""
    
    print("\n" + "=" * 60)
    print("Testing LLMProviderChain Class")
    print("=" * 60)
    
    try:
        from llm.provider_chain import LLMProviderChain
        
        chain = LLMProviderChain()
        await chain.initialize()
        
        print("\nProvider Status:")
        for provider in chain.providers:
            status = "✓ Available" if provider.available else "✗ Unavailable"
            model = getattr(provider, 'model', 'N/A')
            print(f"  {provider.name} (Priority {provider.priority}): {status} - Model: {model}")
        
        # Test query
        print("\nTesting chain query...")
        result = await chain.query(
            "What is the best leveling strategy for a level 50 Knight?",
            {"test": "context"}
        )
        
        if result:
            print(f"\n✓ Query Successful!")
            print(f"  Provider: {result['provider']}")
            print(f"  Model: {result['model']}")
            print(f"  Response (first 200 chars): {result['response'][:200]}...")
            return True
        else:
            print("\n❌ Query failed - no provider succeeded")
            return False
            
    except Exception as e:
        print(f"\n❌ Provider Chain Test Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("\nStarting DeepSeek API Tests...\n")
    
    # Run tests
    success = asyncio.run(test_deepseek_connection())
    
    if success:
        print("\n")
        chain_success = asyncio.run(test_provider_chain())
        
        if chain_success:
            print("\n" + "=" * 60)
            print("✅ ALL TESTS PASSED")
            print("=" * 60)
            print("\nDeepSeek is configured correctly and ready to use!")
            print("Latest model (deepseek-v3) is working with 8192 max tokens.")
            sys.exit(0)
    
    print("\n" + "=" * 60)
    print("❌ TESTS FAILED")
    print("=" * 60)
    print("\nPlease check the error messages above.")
    sys.exit(1)
