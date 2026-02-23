"""
Embedding service for generating vector embeddings using OpenAI API.
"""
import aiohttp
import logging
from typing import List, Optional
from app.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating embeddings using OpenAI API."""
    
    def __init__(self):
        """Initialize embedding service with settings."""
        self.api_key = settings.OPENAI_API_KEY
        self.api_url = settings.OPENAI_API_URL_EMBEDDING
        self.model = settings.OPENAI_MODEL_EMBEDDING
        
        if not self.api_key:
            logger.warning("OPENAI_API_KEY not configured - embeddings will fail")
    
    async def generate_embedding(self, text: str) -> Optional[List[float]]:
        """
        Generate embedding for text using OpenAI API.
        
        Args:
            text: Text to generate embedding for
            
        Returns:
            List of floats representing the embedding vector (1536 dimensions for text-embedding-3-small)
            or None if error occurred
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for embedding")
            return None
        
        if not self.api_key:
            logger.error("OPENAI_API_KEY not configured")
            return None
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "input": text
        }
        
        try:
            timeout = aiohttp.ClientTimeout(total=60)  # 60 seconds timeout
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    self.api_url,
                    headers=headers,
                    json=payload
                ) as resp:
                    resp.raise_for_status()
                    data = await resp.json()
                    
                    # Extract embedding from response
                    # OpenAI embeddings API returns: {"data": [{"embedding": [...]}]}
                    if 'data' in data and len(data['data']) > 0:
                        embedding = data['data'][0].get('embedding')
                        if embedding:
                            logger.debug(f"Generated embedding: {len(embedding)} dimensions")
                            return embedding
                        else:
                            logger.error("No embedding in response data")
                            return None
                    else:
                        logger.error(f"Unexpected response format: {data}")
                        return None
                        
        except aiohttp.ClientError as e:
            logger.error(f"HTTP error generating embedding: {e}")
            return None
        except Exception as e:
            logger.error(f"Error generating embedding: {e}", exc_info=True)
            return None
    
    async def generate_embeddings_batch(self, texts: List[str]) -> List[Optional[List[float]]]:
        """
        Generate embeddings for multiple texts in a single API call.
        
        Args:
            texts: List of texts to generate embeddings for
            
        Returns:
            List of embeddings (same order as input texts, None for failed ones)
        """
        if not texts:
            return []
        
        if not self.api_key:
            logger.error("OPENAI_API_KEY not configured")
            return [None] * len(texts)
        
        # Filter out empty texts
        valid_texts = [t for t in texts if t and t.strip()]
        if not valid_texts:
            return [None] * len(texts)
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "input": valid_texts
        }
        
        try:
            timeout = aiohttp.ClientTimeout(total=120)  # Longer timeout for batch
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    self.api_url,
                    headers=headers,
                    json=payload
                ) as resp:
                    resp.raise_for_status()
                    data = await resp.json()
                    
                    # Extract embeddings from response
                    if 'data' in data and len(data['data']) > 0:
                        embeddings = [item.get('embedding') for item in data['data']]
                        
                        # Map back to original order (with None for empty texts)
                        result = []
                        valid_idx = 0
                        for text in texts:
                            if text and text.strip():
                                result.append(embeddings[valid_idx] if valid_idx < len(embeddings) else None)
                                valid_idx += 1
                            else:
                                result.append(None)
                        
                        logger.debug(f"Generated {len(embeddings)} embeddings in batch")
                        return result
                    else:
                        logger.error(f"Unexpected response format: {data}")
                        return [None] * len(texts)
                        
        except aiohttp.ClientError as e:
            logger.error(f"HTTP error generating batch embeddings: {e}")
            return [None] * len(texts)
        except Exception as e:
            logger.error(f"Error generating batch embeddings: {e}", exc_info=True)
            return [None] * len(texts)

