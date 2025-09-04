"""
Semantic deduplication for intelligent task matching.

Uses embedding-based similarity to detect semantically similar tasks
even when phrasing differs.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Set
import hashlib
import time
from collections import defaultdict, deque

import numpy as np


@dataclass
class TaskEmbedding:
    """Represents a task with its semantic embedding."""

    task_id: str
    description: str
    embedding: list[float]
    metadata: dict


class SemanticDeduplicator:
    """Semantic task deduplication using lightweight embeddings with O(1) duplicate detection."""

    def __init__(self, similarity_threshold: float = 0.85):
        """
        Initialize semantic deduplicator with performance optimizations.

        Args:
            similarity_threshold: Minimum similarity score to consider tasks duplicate (0-1)
        """
        self.similarity_threshold = similarity_threshold
        self.task_embeddings: dict[str, TaskEmbedding] = {}
        
        # Performance optimization: Hash-based index for O(1) lookups
        self._keyword_hash_index: Dict[str, Set[str]] = defaultdict(set)
        self._embedding_cache: Dict[str, List[float]] = {}  # LRU cache for embeddings
        self._similarity_cache: Dict[Tuple[str, str], float] = {}  # Cache similarity calculations
        self._cache_max_size = 10000
        self._cache_access_times: Dict[str, float] = {}  # For LRU eviction
        
        # Spatial indexing for fast nearest neighbor search
        self._bucket_grid: Dict[int, List[str]] = defaultdict(list)
        self._grid_resolution = 20  # Number of buckets per dimension
        
        # Performance metrics
        self._lookup_times: deque = deque(maxlen=1000)  # Track lookup performance
        self._cache_hits = 0
        self._cache_misses = 0

        # Simple keyword-based embeddings (no external dependencies)
        # In production, would use sentence-transformers
        self.feature_keywords = {
            # Action keywords (what)
            "refactor": 0,
            "implement": 1,
            "fix": 2,
            "update": 3,
            "create": 4,
            "analyze": 5,
            "test": 6,
            "review": 7,
            "optimize": 8,
            "debug": 9,
            "design": 10,
            "build": 11,
            "deploy": 12,
            "migrate": 13,
            "integrate": 14,
            # Domain keywords (where)
            "auth": 15,
            "authentication": 15,
            "database": 16,
            "api": 17,
            "frontend": 18,
            "backend": 19,
            "middleware": 20,
            "model": 21,
            "controller": 22,
            "service": 23,
            "security": 24,
            "performance": 25,
            "ui": 26,
            "ux": 27,
            "configuration": 28,
            # Technical keywords (how)
            "async": 29,
            "cache": 30,
            "queue": 31,
            "webhook": 32,
            "rest": 33,
            "graphql": 34,
            "websocket": 35,
            "jwt": 36,
            "oauth": 37,
            "encryption": 38,
            "validation": 39,
            "schema": 40,
            "migration": 41,
            "index": 42,
            "query": 43,
        }

    def _create_embedding(self, description: str) -> list[float]:
        """
        Create optimized embedding vector with caching and fast keyword matching.

        Performance optimizations:
        - LRU cache for repeated descriptions
        - Optimized keyword matching with early termination
        - Vectorized operations where possible
        """
        # Check cache first (O(1) lookup)
        desc_hash = hashlib.md5(description.encode()).hexdigest()
        if desc_hash in self._embedding_cache:
            self._cache_hits += 1
            self._cache_access_times[desc_hash] = time.time()
            return self._embedding_cache[desc_hash]
        
        self._cache_misses += 1
        start_time = time.time()
        
        # Initialize embedding vector
        embedding = [0.0] * len(set(self.feature_keywords.values()))

        # Normalize description (optimized)
        desc_lower = description.lower()
        words = desc_lower.split()
        word_set = set(words)  # O(1) lookups for exact matches

        # Optimized keyword matching
        keyword_counts = {}
        
        # Fast exact matches using set intersection
        matched_keywords = word_set.intersection(self.feature_keywords.keys())
        for keyword in matched_keywords:
            idx = self.feature_keywords[keyword]
            keyword_counts[idx] = keyword_counts.get(idx, 0) + 1

        # Optimized partial matches with early termination
        for word in words:
            if len(word) > 3:  # Skip very short words
                for keyword, idx in self.feature_keywords.items():
                    if len(keyword) > 3 and keyword in word and keyword not in word_set:
                        keyword_counts[idx] = keyword_counts.get(idx, 0) + 0.5
                        break  # Early termination after first match

        # Vectorized embedding creation
        total_keywords = sum(keyword_counts.values()) if keyword_counts else 1
        for idx, count in keyword_counts.items():
            embedding[idx] = count / total_keywords

        # Add optimized features
        embedding.append(len(words) / 100.0)  # Normalized length
        
        # Fast component detection using set operations
        component_keywords = {"controller", "model", "service", "middleware"}
        has_multiple_components = len(word_set.intersection(component_keywords)) > 1
        embedding.append(1.0 if has_multiple_components else 0.0)

        # Cache result with LRU eviction
        self._cache_embedding(desc_hash, embedding)
        
        # Track performance
        self._lookup_times.append(time.time() - start_time)
        
        return embedding

    def _cache_embedding(self, desc_hash: str, embedding: List[float]) -> None:
        """Cache embedding with LRU eviction."""
        if len(self._embedding_cache) >= self._cache_max_size:
            # Evict least recently used entry
            oldest_hash = min(self._cache_access_times.keys(), 
                             key=self._cache_access_times.get)
            del self._embedding_cache[oldest_hash]
            del self._cache_access_times[oldest_hash]
        
        self._embedding_cache[desc_hash] = embedding
        self._cache_access_times[desc_hash] = time.time()
    
    def _cosine_similarity(
        self, embedding1: list[float], embedding2: list[float]
    ) -> float:
        """Calculate optimized cosine similarity with caching."""
        # Create cache key
        key1 = tuple(embedding1)
        key2 = tuple(embedding2)
        cache_key = (key1, key2) if key1 < key2 else (key2, key1)
        
        # Check cache
        if cache_key in self._similarity_cache:
            return self._similarity_cache[cache_key]
        
        # Convert to numpy arrays (optimized)
        vec1 = np.array(embedding1, dtype=np.float32)  # Use float32 for speed
        vec2 = np.array(embedding2, dtype=np.float32)

        # Early termination for zero vectors
        norm1_sq = np.sum(vec1 * vec1)
        norm2_sq = np.sum(vec2 * vec2)
        if norm1_sq == 0 or norm2_sq == 0:
            return 0.0

        # Optimized cosine similarity calculation
        dot_product = np.dot(vec1, vec2)
        similarity = float(dot_product / (np.sqrt(norm1_sq) * np.sqrt(norm2_sq)))
        
        # Cache result (with size limit)
        if len(self._similarity_cache) < self._cache_max_size // 2:
            self._similarity_cache[cache_key] = similarity
        
        return similarity

    def _get_grid_bucket(self, embedding: List[float]) -> int:
        """Get spatial grid bucket for embedding (for O(1) candidate filtering)."""
        # Use first few dimensions for spatial bucketing
        if len(embedding) < 3:
            return 0
        
        # Quantize first 3 dimensions to create bucket ID
        x = int(embedding[0] * self._grid_resolution)
        y = int(embedding[1] * self._grid_resolution) if len(embedding) > 1 else 0
        z = int(embedding[2] * self._grid_resolution) if len(embedding) > 2 else 0
        
        # Combine into single bucket ID
        return x + y * self._grid_resolution + z * self._grid_resolution ** 2
    
    def _get_candidate_buckets(self, bucket_id: int) -> List[int]:
        """Get nearby buckets for similarity search (includes current + neighbors)."""
        candidates = [bucket_id]
        
        # Add neighboring buckets for better recall
        for offset in [-1, 0, 1]:
            for y_offset in [-self._grid_resolution, 0, self._grid_resolution]:
                for z_offset in [-self._grid_resolution**2, 0, self._grid_resolution**2]:
                    neighbor = bucket_id + offset + y_offset + z_offset
                    if neighbor != bucket_id and neighbor >= 0:
                        candidates.append(neighbor)
        
        return candidates
    
    def _update_keyword_index(self, task_id: str, description: str) -> None:
        """Update hash-based keyword index for fast filtering."""
        words = description.lower().split()
        for word in words:
            if word in self.feature_keywords:
                self._keyword_hash_index[word].add(task_id)
    
    def find_similar_task(self, description: str) -> tuple[str, float] | None:
        """
        Find the most similar existing task using optimized O(1) candidate filtering.

        Performance optimizations:
        - Spatial grid indexing for O(1) candidate filtering  
        - Keyword-based pre-filtering
        - Early termination on high similarity
        - Vectorized similarity calculations

        Returns:
            Tuple of (task_id, similarity_score) if found, None otherwise
        """
        if not self.task_embeddings:
            return None

        start_time = time.time()
        
        # Create embedding for new task
        new_embedding = self._create_embedding(description)
        
        # Step 1: Fast keyword-based candidate filtering (O(1) average)
        candidate_tasks = set()
        words = description.lower().split()
        keyword_candidates = set()
        
        for word in words:
            if word in self._keyword_hash_index:
                keyword_candidates.update(self._keyword_hash_index[word])
        
        # Step 2: Spatial grid filtering (O(1) average)
        bucket_id = self._get_grid_bucket(new_embedding)
        spatial_candidates = set()
        
        for bucket in self._get_candidate_buckets(bucket_id):
            if bucket in self._bucket_grid:
                spatial_candidates.update(self._bucket_grid[bucket])
        
        # Combine candidates (intersection for precision, union for recall)
        if keyword_candidates and spatial_candidates:
            candidate_tasks = keyword_candidates.intersection(spatial_candidates)
            if not candidate_tasks:  # Fallback to union if intersection is empty
                candidate_tasks = keyword_candidates.union(spatial_candidates)
        elif keyword_candidates:
            candidate_tasks = keyword_candidates
        elif spatial_candidates:
            candidate_tasks = spatial_candidates
        else:
            # Fallback to all tasks if no candidates found
            candidate_tasks = set(self.task_embeddings.keys())
        
        # Limit candidates for performance (top K most promising)
        if len(candidate_tasks) > 50:  # Configurable threshold
            candidate_tasks = set(list(candidate_tasks)[:50])

        # Step 3: Similarity calculation only on candidates
        best_match = None
        best_score = 0.0

        for task_id in candidate_tasks:
            if task_id not in self.task_embeddings:
                continue
                
            task_emb = self.task_embeddings[task_id]
            similarity = self._cosine_similarity(new_embedding, task_emb.embedding)

            if similarity > best_score:
                best_score = similarity
                best_match = task_id
                
                # Early termination for very high similarity
                if similarity > 0.98:
                    break

        # Track performance
        lookup_time = time.time() - start_time
        self._lookup_times.append(lookup_time)
        
        if best_score >= self.similarity_threshold:
            return (best_match, best_score)

        return None

    def add_task(
        self, task_id: str, description: str, metadata: dict | None = None
    ) -> TaskEmbedding:
        """Add a task to the deduplication index with optimized indexing."""
        embedding = self._create_embedding(description)

        task_emb = TaskEmbedding(
            task_id=task_id,
            description=description,
            embedding=embedding,
            metadata=metadata or {},
        )

        # Update main index
        self.task_embeddings[task_id] = task_emb
        
        # Update performance indexes
        self._update_keyword_index(task_id, description)
        
        # Update spatial grid index
        bucket_id = self._get_grid_bucket(embedding)
        self._bucket_grid[bucket_id].append(task_id)
        
        return task_emb

    def check_duplicate(self, description: str) -> dict[str, any]:
        """
        Check if a task is semantically similar to existing tasks.

        Returns:
            Dict with duplicate info or None
        """
        result = self.find_similar_task(description)

        if result:
            task_id, similarity = result
            existing_task = self.task_embeddings[task_id]

            return {
                "is_duplicate": True,
                "similar_task_id": task_id,
                "similarity_score": similarity,
                "similar_description": existing_task.description,
                "confidence": (
                    "high"
                    if similarity > 0.95
                    else "medium" if similarity > 0.9 else "low"
                ),
            }

        return {"is_duplicate": False, "similarity_score": 0.0}

    def get_performance_stats(self) -> Dict[str, any]:
        """Get performance statistics for monitoring."""
        avg_lookup_time = sum(self._lookup_times) / len(self._lookup_times) if self._lookup_times else 0
        cache_hit_rate = self._cache_hits / (self._cache_hits + self._cache_misses) if (self._cache_hits + self._cache_misses) > 0 else 0
        
        return {
            "average_lookup_time_ms": avg_lookup_time * 1000,
            "cache_hit_rate": cache_hit_rate,
            "cache_size": len(self._embedding_cache),
            "total_tasks": len(self.task_embeddings),
            "keyword_index_size": sum(len(tasks) for tasks in self._keyword_hash_index.values()),
            "spatial_buckets_used": len(self._bucket_grid),
            "similarity_cache_size": len(self._similarity_cache),
            "recent_lookup_times": list(self._lookup_times)[-10:]  # Last 10 lookup times
        }
    
    def optimize_indexes(self) -> None:
        """Optimize indexes for better performance (maintenance operation)."""
        # Rebuild spatial index for better distribution
        self._bucket_grid.clear()
        for task_id, task_emb in self.task_embeddings.items():
            bucket_id = self._get_grid_bucket(task_emb.embedding)
            self._bucket_grid[bucket_id].append(task_id)
        
        # Clean up similarity cache if too large
        if len(self._similarity_cache) > self._cache_max_size:
            # Keep only most recent entries
            items = list(self._similarity_cache.items())
            self._similarity_cache = dict(items[-self._cache_max_size//2:])
    
    def get_task_clusters(self, min_similarity: float = 0.7) -> list[list[str]]:
        """
        Group tasks into clusters based on similarity.

        Returns:
            List of task clusters (groups of similar tasks)
        """
        if not self.task_embeddings:
            return []

        # Build similarity matrix
        task_ids = list(self.task_embeddings.keys())
        n = len(task_ids)
        similarity_matrix = np.zeros((n, n))

        for i in range(n):
            for j in range(i + 1, n):
                emb1 = self.task_embeddings[task_ids[i]].embedding
                emb2 = self.task_embeddings[task_ids[j]].embedding
                sim = self._cosine_similarity(emb1, emb2)
                similarity_matrix[i, j] = sim
                similarity_matrix[j, i] = sim

        # Simple clustering: group tasks that are similar to each other
        clusters = []
        visited = set()

        for i, task_id in enumerate(task_ids):
            if task_id in visited:
                continue

            cluster = [task_id]
            visited.add(task_id)

            # Find all tasks similar to this one
            for j, other_id in enumerate(task_ids):
                if (
                    other_id not in visited
                    and similarity_matrix[i, j] >= min_similarity
                ):
                    cluster.append(other_id)
                    visited.add(other_id)

            if len(cluster) > 1:
                clusters.append(cluster)

        return clusters

    def suggest_merge_strategy(self, task_descriptions: list[str]) -> dict[str, any]:
        """
        Suggest how to merge or coordinate similar tasks.

        Args:
            task_descriptions: List of task descriptions to analyze

        Returns:
            Strategy for handling the tasks
        """
        # Add all tasks temporarily
        temp_tasks = []
        for i, desc in enumerate(task_descriptions):
            task_id = f"temp_{i}"
            self.add_task(task_id, desc)
            temp_tasks.append(task_id)

        # Find clusters
        clusters = self.get_task_clusters(min_similarity=0.8)

        # Build strategy
        strategy = {
            "merge_groups": [],
            "independent_tasks": [],
            "coordination_needed": False,
        }

        # Identify which temp tasks are in clusters
        clustered_tasks = set()
        for cluster in clusters:
            cluster_temps = [t for t in cluster if t.startswith("temp_")]
            if len(cluster_temps) > 1:
                strategy["merge_groups"].append(
                    {
                        "tasks": [
                            task_descriptions[int(t.split("_")[1])]
                            for t in cluster_temps
                        ],
                        "suggested_merge": f"Combine into single task: {task_descriptions[int(cluster_temps[0].split('_')[1])]}",
                    }
                )
                clustered_tasks.update(cluster_temps)
                strategy["coordination_needed"] = True

        # Identify independent tasks
        for i, task_id in enumerate(temp_tasks):
            if task_id not in clustered_tasks:
                strategy["independent_tasks"].append(task_descriptions[i])

        # Clean up temp tasks
        for task_id in temp_tasks:
            del self.task_embeddings[task_id]

        return strategy


# Global instance with performance monitoring
_semantic_dedup = SemanticDeduplicator()

def get_performance_stats() -> Dict[str, any]:
    """Get global performance statistics."""
    return _semantic_dedup.get_performance_stats()

def optimize_global_indexes() -> None:
    """Optimize global indexes for better performance."""
    _semantic_dedup.optimize_indexes()

# Global instance


def get_semantic_deduplicator() -> SemanticDeduplicator:
    """Get the global semantic deduplicator instance."""
    return _semantic_dedup


def check_semantic_duplicate(description: str) -> dict[str, any]:
    """Quick function to check for semantic duplicates."""
    return _semantic_dedup.check_duplicate(description)


def add_task_to_index(task_id: str, description: str) -> None:
    """Add a task to the semantic index."""
    _semantic_dedup.add_task(task_id, description)
