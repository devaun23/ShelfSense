"""
Question Cache Service using Redis

Provides high-performance caching for question generation to achieve <3s latency target.

Features:
- Question caching by specialty/topic/difficulty
- Graceful degradation when Redis is unavailable
- TTL-based expiration
- Cache statistics for monitoring

Usage:
    from app.services.cache_service import question_cache

    # Get cached question
    cached = question_cache.get_cached_question("Internal Medicine")
    if cached:
        return cached

    # Cache new question
    question_cache.cache_question(question_data, "Internal Medicine")
"""

import redis
import json
import hashlib
import logging
import os
from typing import Optional, Dict, List, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class QuestionCacheService:
    """
    Redis-based question caching for <3s latency target.

    Provides graceful degradation when Redis is unavailable -
    all methods return None/False safely without raising exceptions.
    """

    # TTL Configuration (in seconds)
    TTL_QUESTION = 7 * 24 * 3600      # 7 days for generated questions
    TTL_EXPLANATION = 24 * 3600       # 24 hours for explanations
    TTL_USER_ANSWERED = 30 * 24 * 3600  # 30 days for user answer tracking

    # Cache key prefixes
    PREFIX_QUESTION = "shelfsense:question"
    PREFIX_POOL = "shelfsense:pool"
    PREFIX_STATS = "shelfsense:stats"

    def __init__(self):
        """Initialize Redis connection from environment variable."""
        self.redis: Optional[redis.Redis] = None
        self._initialized = False
        self._connect()

    def _connect(self):
        """Establish Redis connection."""
        redis_url = os.getenv("REDIS_URL")

        if not redis_url:
            logger.info("REDIS_URL not set - caching disabled")
            return

        try:
            self.redis = redis.from_url(
                redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            # Test connection
            self.redis.ping()
            self._initialized = True
            logger.info("Redis cache connected successfully")
        except redis.ConnectionError as e:
            logger.warning(f"Redis connection failed: {e}. Caching disabled.")
            self.redis = None
        except Exception as e:
            logger.error(f"Unexpected Redis error: {e}. Caching disabled.")
            self.redis = None

    @property
    def is_connected(self) -> bool:
        """Check if Redis is available."""
        if not self.redis:
            return False
        try:
            self.redis.ping()
            return True
        except Exception:
            return False

    def _generate_cache_key(
        self,
        specialty: str = None,
        topic: str = None,
        difficulty: str = "medium"
    ) -> str:
        """
        Generate a deterministic cache key for a question.

        Args:
            specialty: Medical specialty
            topic: Specific topic
            difficulty: easy/medium/hard

        Returns:
            Cache key string
        """
        key_data = f"{specialty or 'any'}:{topic or 'any'}:{difficulty}"
        hash_suffix = hashlib.md5(key_data.encode()).hexdigest()[:12]
        return f"{self.PREFIX_QUESTION}:{hash_suffix}"

    def get_cached_question(
        self,
        specialty: str = None,
        topic: str = None,
        difficulty: str = "medium"
    ) -> Optional[Dict]:
        """
        Get a cached question if available.

        Args:
            specialty: Medical specialty filter
            topic: Topic filter
            difficulty: Difficulty level

        Returns:
            Question dict if found, None otherwise
        """
        if not self.redis:
            return None

        try:
            key = self._generate_cache_key(specialty, topic, difficulty)
            data = self.redis.get(key)

            if data:
                logger.debug(f"Cache HIT: {key}")
                self._record_hit()
                return json.loads(data)

            logger.debug(f"Cache MISS: {key}")
            self._record_miss()
            return None

        except Exception as e:
            logger.error(f"Cache read error: {e}")
            return None

    def cache_question(
        self,
        question: Dict,
        specialty: str = None,
        topic: str = None,
        difficulty: str = "medium",
        ttl: int = None
    ) -> bool:
        """
        Cache a generated question.

        Args:
            question: Question data dict
            specialty: Medical specialty
            topic: Topic
            difficulty: Difficulty level
            ttl: Custom TTL in seconds (default: 7 days)

        Returns:
            True if cached successfully, False otherwise
        """
        if not self.redis:
            return False

        try:
            key = self._generate_cache_key(specialty, topic, difficulty)
            ttl = ttl or self.TTL_QUESTION

            # Add cache metadata
            question_with_meta = {
                **question,
                "_cache_metadata": {
                    "cached_at": datetime.utcnow().isoformat(),
                    "specialty": specialty,
                    "topic": topic,
                    "difficulty": difficulty
                }
            }

            self.redis.setex(key, ttl, json.dumps(question_with_meta))
            logger.debug(f"Cached question: {key}")
            return True

        except Exception as e:
            logger.error(f"Cache write error: {e}")
            return False

    def get_any_cached_question(self, specialty: str = None) -> Optional[Dict]:
        """
        Get any available cached question, optionally filtered by specialty.

        Used for fallback scenarios when specific cache misses.

        Args:
            specialty: Optional specialty filter

        Returns:
            A cached question or None
        """
        if not self.redis:
            return None

        try:
            # Build pattern based on specialty
            if specialty:
                # Hash the specialty to match key format
                pattern = f"{self.PREFIX_QUESTION}:*"
            else:
                pattern = f"{self.PREFIX_QUESTION}:*"

            # Get first available key
            keys = list(self.redis.scan_iter(pattern, count=100))

            if not keys:
                return None

            # Try keys until we find valid data
            for key in keys[:10]:  # Limit attempts
                data = self.redis.get(key)
                if data:
                    question = json.loads(data)
                    # Check specialty if filter provided
                    if specialty:
                        q_specialty = question.get("specialty") or question.get("_cache_metadata", {}).get("specialty")
                        if q_specialty and specialty.lower() in q_specialty.lower():
                            return question
                    else:
                        return question

            return None

        except Exception as e:
            logger.error(f"Cache scan error: {e}")
            return None

    def add_to_pool(
        self,
        question: Dict,
        specialty: str,
        difficulty: str = "medium"
    ) -> bool:
        """
        Add a question to the specialty pool (sorted set).

        Args:
            question: Question data
            specialty: Medical specialty
            difficulty: Difficulty level

        Returns:
            True if added successfully
        """
        if not self.redis:
            return False

        try:
            pool_key = f"{self.PREFIX_POOL}:{specialty}:{difficulty}"

            # Generate unique question ID
            question_id = question.get("id") or hashlib.md5(
                question.get("vignette", "")[:100].encode()
            ).hexdigest()[:16]

            # Store question data
            question_data_key = f"{self.PREFIX_QUESTION}:data:{question_id}"
            self.redis.setex(question_data_key, self.TTL_QUESTION, json.dumps(question))

            # Add to pool sorted set (score = timestamp)
            self.redis.zadd(pool_key, {question_id: datetime.utcnow().timestamp()})

            return True

        except Exception as e:
            logger.error(f"Pool add error: {e}")
            return False

    def get_from_pool(
        self,
        specialty: str,
        difficulty: str = "medium"
    ) -> Optional[Dict]:
        """
        Get and remove a question from the pool (FIFO).

        Args:
            specialty: Medical specialty
            difficulty: Difficulty level

        Returns:
            Question data or None
        """
        if not self.redis:
            return None

        try:
            pool_key = f"{self.PREFIX_POOL}:{specialty}:{difficulty}"

            # Get oldest question (lowest score)
            result = self.redis.zpopmin(pool_key, count=1)

            if not result:
                return None

            question_id = result[0][0]
            question_data_key = f"{self.PREFIX_QUESTION}:data:{question_id}"

            data = self.redis.get(question_data_key)
            if data:
                return json.loads(data)

            return None

        except Exception as e:
            logger.error(f"Pool get error: {e}")
            return None

    def get_pool_size(self, specialty: str, difficulty: str = "medium") -> int:
        """Get the number of questions in a pool."""
        if not self.redis:
            return 0

        try:
            pool_key = f"{self.PREFIX_POOL}:{specialty}:{difficulty}"
            return self.redis.zcard(pool_key) or 0
        except Exception:
            return 0

    def _record_hit(self):
        """Record a cache hit for statistics."""
        if self.redis:
            try:
                self.redis.incr(f"{self.PREFIX_STATS}:hits")
            except Exception:
                pass

    def _record_miss(self):
        """Record a cache miss for statistics."""
        if self.redis:
            try:
                self.redis.incr(f"{self.PREFIX_STATS}:misses")
            except Exception:
                pass

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics for monitoring.

        Returns:
            Dict with cache status, hit rate, memory usage, etc.
        """
        if not self.redis:
            return {
                "status": "disabled",
                "reason": "Redis not connected"
            }

        try:
            hits = int(self.redis.get(f"{self.PREFIX_STATS}:hits") or 0)
            misses = int(self.redis.get(f"{self.PREFIX_STATS}:misses") or 0)
            total = hits + misses

            # Count cached questions
            question_keys = list(self.redis.scan_iter(f"{self.PREFIX_QUESTION}:*", count=1000))

            # Get memory info
            info = self.redis.info("memory")

            return {
                "status": "connected",
                "total_cached_questions": len(question_keys),
                "cache_hits": hits,
                "cache_misses": misses,
                "hit_rate": f"{(hits / total * 100):.1f}%" if total > 0 else "N/A",
                "memory_used_mb": round(info.get("used_memory", 0) / 1024 / 1024, 2),
                "ttl_days": self.TTL_QUESTION / 86400
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }

    def flush_cache(self) -> int:
        """
        Clear all cached questions (admin function).

        Returns:
            Number of keys deleted
        """
        if not self.redis:
            return 0

        try:
            # Find all shelfsense keys
            keys = list(self.redis.scan_iter("shelfsense:*", count=10000))

            if keys:
                deleted = self.redis.delete(*keys)
                logger.warning(f"Cache flushed: {deleted} keys deleted")
                return deleted

            return 0

        except Exception as e:
            logger.error(f"Cache flush error: {e}")
            return 0

    def warm_cache(
        self,
        questions: List[Dict],
        specialty: str = None
    ) -> int:
        """
        Warm the cache with pre-generated questions.

        Args:
            questions: List of question dicts
            specialty: Optional specialty to tag questions with

        Returns:
            Number of questions cached
        """
        if not self.redis:
            return 0

        cached_count = 0
        for question in questions:
            q_specialty = specialty or question.get("specialty", "General")
            if self.cache_question(question, specialty=q_specialty):
                cached_count += 1

        logger.info(f"Cache warmed with {cached_count} questions")
        return cached_count


# Global singleton instance
question_cache = QuestionCacheService()


def get_cache_status() -> Dict[str, Any]:
    """Get cache status without importing the service."""
    return question_cache.get_cache_stats()
