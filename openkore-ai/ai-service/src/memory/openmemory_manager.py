"""
OpenMemory SDK integration with synthetic embeddings
5 cognitive sectors: Episodic, Semantic, Procedural, Emotional, Reflective
"""

from typing import List, Dict, Any, Optional
import numpy as np
import hashlib
from loguru import logger

class SyntheticEmbeddings:
    """Generate synthetic embeddings without external API calls"""
    
    def __init__(self, dimension: int = 384):
        self.dimension = dimension
        
    def encode(self, text: str) -> List[float]:
        """
        Generate deterministic synthetic embedding from text
        Uses hash-based approach for consistency
        """
        # Create hash of text
        hash_obj = hashlib.sha256(text.encode())
        hash_bytes = hash_obj.digest()
        
        # Convert to deterministic floats
        np.random.seed(int.from_bytes(hash_bytes[:4], 'big'))
        embedding = np.random.randn(self.dimension).tolist()
        
        # Normalize
        norm = np.linalg.norm(embedding)
        embedding = (np.array(embedding) / norm).tolist()
        
        return embedding
        
    def similarity(self, emb1: List[float], emb2: List[float]) -> float:
        """Calculate cosine similarity between embeddings"""
        dot_product = np.dot(emb1, emb2)
        return float(dot_product)  # Already normalized

class OpenMemoryManager:
    """
    Manages AI memory across 5 cognitive sectors
    Uses synthetic embeddings (no external API)
    """
    
    SECTORS = ['episodic', 'semantic', 'procedural', 'emotional', 'reflective']
    
    def __init__(self, db_instance):
        self.db = db_instance
        self.embedder = SyntheticEmbeddings(dimension=384)
        logger.info("OpenMemory Manager initialized with synthetic embeddings")
        
    async def add_memory(self, session_id: str, sector: str, content: str, importance: float = 0.5):
        """Add memory to specific cognitive sector"""
        if sector not in self.SECTORS:
            raise ValueError(f"Invalid sector: {sector}. Must be one of {self.SECTORS}")
            
        # Generate synthetic embedding
        embedding = self.embedder.encode(content)
        
        # Store in database
        await self.db.add_memory(session_id, sector, content, embedding, importance)
        logger.debug(f"Added {sector} memory: {content[:50]}...")
        
    async def query_similar(self, session_id: str, query_text: str, sector: Optional[str] = None, 
                          top_k: int = 5) -> List[Dict[str, Any]]:
        """Query similar memories using embedding similarity"""
        query_embedding = self.embedder.encode(query_text)
        
        # Retrieve memories from database
        memories = await self.db.get_recent_memories(session_id, sector, limit=50)
        
        # Calculate similarities
        results = []
        for memory in memories:
            memory_id, sid, mem_type, content, emb_str, importance, timestamp = memory
            
            if emb_str:
                import json
                memory_embedding = json.loads(emb_str)
                similarity = self.embedder.similarity(query_embedding, memory_embedding)
                
                results.append({
                    'memory_id': memory_id,
                    'type': mem_type,
                    'content': content,
                    'importance': importance,
                    'similarity': similarity,
                    'timestamp': timestamp
                })
        
        # Sort by similarity and return top_k
        results.sort(key=lambda x: x['similarity'], reverse=True)
        return results[:top_k]
        
    async def add_episodic(self, session_id: str, event: str, importance: float = 0.5):
        """Add episodic memory (what happened)"""
        await self.add_memory(session_id, 'episodic', event, importance)
        
    async def add_semantic(self, session_id: str, knowledge: str, importance: float = 0.7):
        """Add semantic memory (general knowledge)"""
        await self.add_memory(session_id, 'semantic', knowledge, importance)
        
    async def add_procedural(self, session_id: str, skill: str, importance: float = 0.8):
        """Add procedural memory (how to do things)"""
        await self.add_memory(session_id, 'procedural', skill, importance)
        
    async def add_emotional(self, session_id: str, emotion: str, importance: float = 0.6):
        """Add emotional memory (feelings about events)"""
        await self.add_memory(session_id, 'emotional', emotion, importance)
        
    async def add_reflective(self, session_id: str, reflection: str, importance: float = 0.9):
        """Add reflective memory (meta-cognition)"""
        await self.add_memory(session_id, 'reflective', reflection, importance)

memory_manager = None  # Initialized in main.py
