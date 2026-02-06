"""
ChromaDB-compatible embedder wrapper for OpenMemory synthetic embeddings
Allows CrewAI to use synthetic embeddings without OpenAI API
"""

from typing import List, Union, Dict, Any
from chromadb.api.types import EmbeddingFunction, Embeddings
from loguru import logger
from memory.openmemory_manager import SyntheticEmbeddings


class OpenMemoryEmbedder(EmbeddingFunction):
    """
    ChromaDB-compatible embedding function using OpenMemory synthetic embeddings
    Enables CrewAI memory to work without OpenAI API key
    """
    
    def __init__(self, dimension: int = 384):
        """
        Initialize the embedder with synthetic embeddings
        
        Args:
            dimension: Embedding dimension (default 384 for compatibility)
        """
        self.dimension = dimension
        self.embedder = SyntheticEmbeddings(dimension=dimension)
        logger.info(f"OpenMemoryEmbedder initialized with dimension={dimension}")
    
    def __call__(self, input: Union[str, List[str]]) -> Embeddings:
        """
        Generate embeddings for input text(s)
        
        Args:
            input: Single text string or list of text strings
            
        Returns:
            List of embeddings (list of lists of floats)
        """
        # Handle both single string and list of strings
        if isinstance(input, str):
            texts = [input]
        else:
            texts = input
        
        # Generate embeddings for each text
        embeddings = [self.embedder.encode(text) for text in texts]
        
        logger.debug(f"Generated {len(embeddings)} embeddings")
        return embeddings
    
    def embed_query(self, input: Union[str, List[str]]) -> Embeddings:
        """
        Embed query text(s) - uses same implementation as __call__
        
        Args:
            input: Single text string or list of text strings
            
        Returns:
            List of embeddings
        """
        return self.__call__(input)
    
    @staticmethod
    def name() -> str:
        """Return the name of this embedding function"""
        return "openmemory_synthetic"
    
    def get_config(self) -> Dict[str, Any]:
        """
        Get configuration for serialization
        
        Returns:
            Configuration dictionary
        """
        return {
            "name": self.name(),
            "dimension": self.dimension,
            "type": "synthetic"
        }
    
    @staticmethod
    def build_from_config(config: Dict[str, Any]) -> "OpenMemoryEmbedder":
        """
        Build embedder from configuration
        
        Args:
            config: Configuration dictionary
            
        Returns:
            New OpenMemoryEmbedder instance
        """
        dimension = config.get("dimension", 384)
        return OpenMemoryEmbedder(dimension=dimension)
    
    def default_space(self) -> str:
        """Return the default distance metric space"""
        return "cosine"
    
    def supported_spaces(self) -> List[str]:
        """Return supported distance metrics"""
        return ["cosine", "l2", "ip"]


def get_crewai_embedder(dimension: int = 384) -> OpenMemoryEmbedder:
    """
    Factory function to create OpenMemory embedder for CrewAI
    
    Args:
        dimension: Embedding dimension
        
    Returns:
        Configured OpenMemoryEmbedder instance
    """
    logger.info("Creating OpenMemory embedder for CrewAI memory system")
    return OpenMemoryEmbedder(dimension=dimension)
