"""
LLM Provider Chain with automatic failover
Priority: DeepSeek (default) → OpenAI → Anthropic
"""

from typing import Optional, Dict, Any, List
from abc import ABC, abstractmethod
import os
import httpx
from loguru import logger

class LLMProvider(ABC):
    """
    Abstract base class for LLM providers
    
    All concrete provider implementations must inherit from this class
    and implement the abstract methods: query() and check_availability()
    """
    
    def __init__(self, name: str, priority: int):
        self.name = name
        self.priority = priority
        self.available = False
        
    @abstractmethod
    async def query(self, prompt: str, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Query the LLM provider with a prompt
        
        Args:
            prompt: The prompt to send to the LLM
            context: Additional context information
            
        Returns:
            Dictionary containing response and metadata, or None if query fails
            Expected format: {
                'provider': str,
                'response': str,
                'model': str
            }
        """
        pass
        
    @abstractmethod
    async def check_availability(self) -> bool:
        """
        Check if the provider is available (e.g., API key is set)
        
        Returns:
            True if provider is available and ready to use, False otherwise
        """
        pass
    
    def is_available(self) -> bool:
        """
        Synchronous check for provider availability
        
        Returns:
            Current availability status
        """
        return self.available

class DeepSeekProvider(LLMProvider):
    """DeepSeek LLM provider (default, $4.20/month)"""
    
    def __init__(self):
        super().__init__("DeepSeek", priority=1)
        self.api_key = os.getenv("DEEPSEEK_API_KEY", "")
        self.endpoint = "https://api.deepseek.com/v1/chat/completions"
        # Latest DeepSeek model - using deepseek-chat (latest stable version)
        self.model = "deepseek-chat"
        
    async def check_availability(self) -> bool:
        """Check if DeepSeek API key is set"""
        self.available = bool(self.api_key)
        return self.available
        
    async def query(self, prompt: str, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Query DeepSeek API"""
        if not self.api_key:
            logger.warning("DeepSeek API key not set")
            return None
            
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    self.endpoint,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": "You are an AI assistant for Ragnarok Online gameplay."},
                            {"role": "user", "content": prompt}
                        ],
                        "max_tokens": 8192,  # Increased token limit for deepseek-v3
                        "temperature": 0.7
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    content = data['choices'][0]['message']['content']
                    logger.success(f"DeepSeek query successful")
                    return {
                        'provider': 'DeepSeek',
                        'response': content,
                        'model': self.model
                    }
                else:
                    logger.error(f"DeepSeek API error: {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"DeepSeek query failed: {e}")
            return None

class OpenAIProvider(LLMProvider):
    """OpenAI GPT provider (fallback #1)"""
    
    def __init__(self):
        super().__init__("OpenAI", priority=2)
        self.api_key = os.getenv("OPENAI_API_KEY", "")
        self.model = "gpt-4-turbo-preview"
        
    async def check_availability(self) -> bool:
        """Check if OpenAI API key is set"""
        self.available = bool(self.api_key)
        return self.available
        
    async def query(self, prompt: str, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Query OpenAI API"""
        if not self.api_key:
            logger.warning("OpenAI API key not set")
            return None
            
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=self.api_key)
            
            completion = await client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an AI assistant for Ragnarok Online gameplay."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1024,
                temperature=0.7
            )
            
            content = completion.choices[0].message.content
            logger.success(f"OpenAI query successful")
            return {
                'provider': 'OpenAI',
                'response': content,
                'model': self.model
            }
            
        except Exception as e:
            logger.error(f"OpenAI query failed: {e}")
            return None

class AnthropicProvider(LLMProvider):
    """Anthropic Claude provider (fallback #2)"""
    
    def __init__(self):
        super().__init__("Anthropic", priority=3)
        self.api_key = os.getenv("ANTHROPIC_API_KEY", "")
        self.model = "claude-3-opus-20240229"
        
    async def check_availability(self) -> bool:
        """Check if Anthropic API key is set"""
        self.available = bool(self.api_key)
        return self.available
        
    async def query(self, prompt: str, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Query Anthropic API"""
        if not self.api_key:
            logger.warning("Anthropic API key not set")
            return None
            
        try:
            from anthropic import AsyncAnthropic
            client = AsyncAnthropic(api_key=self.api_key)
            
            message = await client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            content = message.content[0].text
            logger.success(f"Anthropic query successful")
            return {
                'provider': 'Anthropic',
                'response': content,
                'model': self.model
            }
            
        except Exception as e:
            logger.error(f"Anthropic query failed: {e}")
            return None

class LLMProviderChain:
    """Manages LLM provider chain with automatic failover"""
    
    def __init__(self):
        self.providers: List[LLMProvider] = [
            DeepSeekProvider(),
            OpenAIProvider(),
            AnthropicProvider()
        ]
        # Sort by priority
        self.providers.sort(key=lambda p: p.priority)
        logger.info(f"LLM Provider Chain initialized with {len(self.providers)} providers")
        
    async def initialize(self):
        """Check availability of all providers"""
        for provider in self.providers:
            await provider.check_availability()
            status = "[OK] Available" if provider.available else "✗ Unavailable"
            logger.info(f"  Priority {provider.priority}: {provider.name} - {status}")
            
    async def query(self, prompt: str, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Query providers in priority order until one succeeds"""
        logger.info("Querying LLM provider chain...")
        
        for provider in self.providers:
            if not provider.available:
                logger.debug(f"Skipping {provider.name} (not available)")
                continue
                
            logger.info(f"Trying provider: {provider.name}")
            result = await provider.query(prompt, context)
            
            if result:
                return result
                
        logger.error("All LLM providers failed")
        return None
    
    def get_crewai_llm(self):
        """
        Get a CrewAI-compatible LLM instance
        Uses DeepSeek as primary, with fallback to OpenAI if needed
        """
        from crewai import LLM
        
        # Try DeepSeek first (priority 1)
        deepseek_key = os.getenv("DEEPSEEK_API_KEY", "")
        if deepseek_key:
            logger.info("Creating CrewAI LLM with DeepSeek provider")
            return LLM(
                model="deepseek/deepseek-chat",
                api_key=deepseek_key,
                base_url="https://api.deepseek.com/v1"
            )
        
        # Fallback to OpenAI if DeepSeek not available
        openai_key = os.getenv("OPENAI_API_KEY", "")
        if openai_key:
            logger.warning("DeepSeek unavailable, falling back to OpenAI for CrewAI")
            return LLM(
                model="gpt-4-turbo-preview",
                api_key=openai_key
            )
        
        # If no API keys available, raise error
        logger.error("No LLM API keys available for CrewAI agents")
        raise ValueError(
            "No LLM provider available. Please set DEEPSEEK_API_KEY or OPENAI_API_KEY "
            "in environment variables or .env file"
        )

llm_chain = LLMProviderChain()
