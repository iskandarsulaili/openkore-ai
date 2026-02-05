"""
Human-Like Chat Generator
Uses DeepSeek LLM to generate natural, personality-driven responses
"""

from typing import Dict, Any, Optional
from loguru import logger
from llm.provider_chain import llm_chain

class ChatGenerator:
    """Generates human-like chat responses"""
    
    def __init__(self, personality_engine_instance):
        self.personality = personality_engine_instance
        self.chat_history = []
        logger.info("Chat Generator initialized with DeepSeek LLM")
        
    async def generate_response(self, message: str, context: Dict[str, Any]) -> Optional[str]:
        """Generate natural chat response using LLM"""
        
        # Get conversation style
        style = self.personality.get_conversation_style()
        emoji_rate = self.personality.get_emoji_usage_rate()
        
        # Build personality-aware prompt
        personality_desc = self._build_personality_description()
        
        prompt = f"""
You are roleplaying as a Ragnarok Online player with this personality:
{personality_desc}

Context:
- Your character: Level {context.get('my_level', 50)} {context.get('my_job', 'Knight')}
- Player who messaged you: {context.get('player_name', 'Player')} (Level {context.get('player_level', 40)})
- Relationship: {context.get('reputation_tier', 'Neutral')}
- Message type: {context.get('message_type', 'whisper')}

They said: "{message}"

Generate a natural, human-like response (1-2 sentences max).
Conversation style: {style}
Use emojis sparingly: {"Yes (rate: " + str(emoji_rate) + ")" if emoji_rate > 0.3 else "No"}

Response:"""
        
        try:
            llm_result = await llm_chain.query(prompt, context)
            
            if llm_result:
                response = llm_result['response'].strip()
                
                # Clean up common LLM formatting
                response = response.replace('"', '').replace("Response:", "").strip()
                
                # Limit length for game chat
                if len(response) > 120:
                    response = response[:117] + "..."
                    
                logger.debug(f"Generated chat response: {response}")
                return response
            else:
                # Fallback if LLM unavailable
                return self._get_fallback_response(message, style)
                
        except Exception as e:
            logger.error(f"Chat generation error: {e}")
            return self._get_fallback_response(message, style)
            
    def _build_personality_description(self) -> str:
        """Build personality description for LLM"""
        traits = self.personality.traits
        
        desc = []
        if traits['chattiness'] > 0.7:
            desc.append("very talkative and social")
        elif traits['chattiness'] < 0.3:
            desc.append("quiet and reserved")
            
        if traits['friendliness'] > 0.7:
            desc.append("warm and welcoming")
        elif traits['friendliness'] < 0.3:
            desc.append("distant and aloof")
            
        if traits['helpfulness'] > 0.7:
            desc.append("always eager to help others")
        elif traits['helpfulness'] < 0.3:
            desc.append("focused on own goals")
            
        if traits['humor'] > 0.7:
            desc.append("playful and humorous")
        elif traits['humor'] < 0.3:
            desc.append("serious and businesslike")
            
        return ", ".join(desc) if desc else "balanced and moderate"
        
    def _get_fallback_response(self, message: str, style: str) -> str:
        """Fallback responses when LLM unavailable"""
        message_lower = message.lower()
        
        if any(word in message_lower for word in ['hi', 'hello', 'hey', 'sup']):
            return "Hi there!" if style != "formal" else "Greetings."
        elif any(word in message_lower for word in ['help', 'assist', 'can you']):
            return "Sure, what do you need?" if style != "formal" else "How may I assist you?"
        elif any(word in message_lower for word in ['party', 'join', 'invite']):
            return "Thanks for the invite!" if style != "formal" else "I appreciate the invitation."
        elif any(word in message_lower for word in ['bye', 'cya', 'later', 'goodbye']):
            return "See ya!" if style != "formal" else "Farewell."
        else:
            return "Interesting!" if style == "casual" else "I see."

chat_generator = None  # Initialized in main.py
