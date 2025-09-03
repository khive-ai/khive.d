"""
Semantic deduplication for intelligent task matching.

Uses embedding-based similarity to detect semantically similar tasks
even when phrasing differs.
"""

from dataclasses import dataclass

import numpy as np


@dataclass
class TaskEmbedding:
    """Represents a task with its semantic embedding."""

    task_id: str
    description: str
    embedding: list[float]
    metadata: dict


class SemanticDeduplicator:
    """Semantic task deduplication using lightweight embeddings."""

    def __init__(self, similarity_threshold: float = 0.85):
        """
        Initialize semantic deduplicator.

        Args:
            similarity_threshold: Minimum similarity score to consider tasks duplicate (0-1)
        """
        self.similarity_threshold = similarity_threshold
        self.task_embeddings: dict[str, TaskEmbedding] = {}

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
        Create a simple embedding vector from task description.

        In production, this would use sentence-transformers or similar.
        For now, using keyword-based embeddings.
        """
        # Initialize embedding vector
        embedding = [0.0] * len(set(self.feature_keywords.values()))

        # Normalize description
        desc_lower = description.lower()
        words = desc_lower.split()

        # Count keyword occurrences
        keyword_counts = {}
        for word in words:
            # Check exact matches
            if word in self.feature_keywords:
                idx = self.feature_keywords[word]
                keyword_counts[idx] = keyword_counts.get(idx, 0) + 1

            # Check partial matches (e.g., "refactoring" matches "refactor")
            for keyword, idx in self.feature_keywords.items():
                if keyword in word and len(keyword) > 3:
                    keyword_counts[idx] = keyword_counts.get(idx, 0) + 0.5

        # Create embedding with TF-IDF-like weighting
        total_keywords = sum(keyword_counts.values()) if keyword_counts else 1
        for idx, count in keyword_counts.items():
            embedding[idx] = count / total_keywords

        # Add length feature
        embedding.append(len(words) / 100.0)  # Normalized length

        # Add complexity features
        has_multiple_components = (
            sum(
                1
                for k in ["controller", "model", "service", "middleware"]
                if k in desc_lower
            )
            > 1
        )
        embedding.append(1.0 if has_multiple_components else 0.0)

        return embedding

    def _cosine_similarity(
        self, embedding1: list[float], embedding2: list[float]
    ) -> float:
        """Calculate cosine similarity between two embeddings."""
        # Convert to numpy arrays for easier computation
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)

        # Calculate cosine similarity
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        similarity = dot_product / (norm1 * norm2)
        return float(similarity)

    def find_similar_task(self, description: str) -> tuple[str, float] | None:
        """
        Find the most similar existing task.

        Returns:
            Tuple of (task_id, similarity_score) if found, None otherwise
        """
        if not self.task_embeddings:
            return None

        # Create embedding for new task
        new_embedding = self._create_embedding(description)

        # Find most similar task
        best_match = None
        best_score = 0.0

        for task_id, task_emb in self.task_embeddings.items():
            similarity = self._cosine_similarity(new_embedding, task_emb.embedding)

            if similarity > best_score:
                best_score = similarity
                best_match = task_id

        if best_score >= self.similarity_threshold:
            return (best_match, best_score)

        return None

    def add_task(
        self, task_id: str, description: str, metadata: dict | None = None
    ) -> TaskEmbedding:
        """Add a task to the deduplication index."""
        embedding = self._create_embedding(description)

        task_emb = TaskEmbedding(
            task_id=task_id,
            description=description,
            embedding=embedding,
            metadata=metadata or {},
        )

        self.task_embeddings[task_id] = task_emb
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


# Global instance
_semantic_dedup = SemanticDeduplicator()


def get_semantic_deduplicator() -> SemanticDeduplicator:
    """Get the global semantic deduplicator instance."""
    return _semantic_dedup


def check_semantic_duplicate(description: str) -> dict[str, any]:
    """Quick function to check for semantic duplicates."""
    return _semantic_dedup.check_duplicate(description)


def add_task_to_index(task_id: str, description: str) -> None:
    """Add a task to the semantic index."""
    _semantic_dedup.add_task(task_id, description)
