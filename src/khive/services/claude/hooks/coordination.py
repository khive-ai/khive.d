"""
Simple coordination service for Claude Code hooks.

Provides intelligent task deduplication, context sharing, and agent coordination.
"""

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any


@dataclass
class TaskInfo:
    """Information about an active task."""

    task_id: str
    description: str
    task_hash: str
    agents: list[str] = field(default_factory=list)
    status: str = "pending"  # pending, active, completed
    created_at: datetime = field(default_factory=datetime.now)
    context_key: str = ""
    artifacts: list[str] = field(default_factory=list)
    result: str | None = None


@dataclass
class SharedContext:
    """Shared context from completed agents."""

    context_key: str
    task_id: str
    agent_id: str
    output: str
    artifacts: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)


class CoordinationRegistry:
    """Simple coordination registry for agent communication."""

    def __init__(self):
        # Task tracking
        self.active_tasks: dict[str, TaskInfo] = {}
        self.task_by_hash: dict[str, str] = {}  # hash -> task_id mapping

        # Shared context
        self.shared_contexts: dict[str, SharedContext] = {}

        # Agent tracking
        self.agent_tasks: dict[str, str] = {}  # agent_id -> task_id
        self.agent_count = 0

        # Inter-agent communication queue
        self.message_queue: list[dict[str, Any]] = []
        self.agent_subscriptions: dict[str, list[str]] = {}  # agent_id -> [event_types]

        # Subscribe to HookEventBroadcaster for inter-agent awareness
        self._setup_event_subscriptions()

        # Cleanup old entries periodically
        self._cleanup_interval = 3600  # 1 hour
        self._max_context_age = timedelta(hours=2)

        # Performance metrics
        self.task_metrics: dict[str, dict[str, Any]] = {}  # task_id -> metrics

        # Thinking patterns from old swarm system
        self.thinking_patterns = {
            "critical": ["review", "audit", "debug", "error", "fix", "validate"],
            "system": ["architecture", "integration", "refactor", "dependencies"],
            "creative": ["design", "implement", "build", "create", "develop"],
            "risk": ["security", "production", "migration", "deployment"],
            "practical": ["setup", "configure", "install", "test", "run"],
        }

        # Role suggestions based on task keywords
        self.role_patterns = {
            "researcher": ["analyze", "research", "investigate", "explore", "discover"],
            "architect": ["design", "architecture", "structure", "system", "plan"],
            "implementer": ["implement", "code", "build", "develop", "create"],
            "tester": ["test", "validate", "verify", "check", "ensure"],
            "reviewer": ["review", "audit", "assess", "evaluate", "critique"],
        }

        # Coordination patterns for different scenarios
        self.coordination_patterns = {
            "fan_out": {
                "description": "Split work into parallel independent subtasks",
                "best_for": ["analysis", "research", "testing"],
                "min_agents": 3,
                "max_agents": 7,
                "benefits": "Maximum parallelization, fastest completion",
            },
            "pipeline": {
                "description": "Sequential handoff between specialized agents",
                "best_for": ["implementation", "review", "deployment"],
                "min_agents": 2,
                "max_agents": 5,
                "benefits": "Clear dependencies, quality gates at each stage",
            },
            "consensus": {
                "description": "Multiple agents verify and validate results",
                "best_for": ["security", "critical", "verification"],
                "min_agents": 3,
                "max_agents": 5,
                "benefits": "High confidence, reduced errors",
            },
            "hierarchical": {
                "description": "Coordinator agent manages worker agents",
                "best_for": ["complex", "large-scale", "multi-phase"],
                "min_agents": 4,
                "max_agents": 10,
                "benefits": "Organized structure, clear oversight",
            },
        }

        # Pattern effectiveness history (will be populated through learning)
        self.pattern_effectiveness: dict[str, dict[str, float]] = {}

    def hash_task(self, description: str) -> str:
        """Generate a hash for task deduplication."""
        # Normalize the description
        normalized = description.lower().strip()
        # Create a short hash
        return hashlib.md5(normalized.encode()).hexdigest()[:8]

    def check_duplicate_task(self, description: str) -> TaskInfo | None:
        """Check if a similar task is already running using semantic similarity."""
        # First try exact hash match
        task_hash = self.hash_task(description)

        if task_hash in self.task_by_hash:
            task_id = self.task_by_hash[task_hash]
            task = self.active_tasks.get(task_id)

            # Only return if task is still active
            if task and task.status in ["pending", "active"]:
                return task

        # Now try semantic similarity matching
        from khive.services.claude.hooks.semantic_dedup import get_semantic_deduplicator

        dedup = get_semantic_deduplicator()

        # Check against all active tasks
        for task_id, task in self.active_tasks.items():
            if task.status in ["pending", "active"]:
                # Add task to dedup index if not already there
                if task_id not in dedup.task_embeddings:
                    dedup.add_task(task_id, task.description)

        # Check for semantic duplicate
        result = dedup.check_duplicate(description)
        if result["is_duplicate"] and result["similarity_score"] > 0.85:
            similar_task_id = result["similar_task_id"]
            return self.active_tasks.get(similar_task_id)

        return None

    def register_task(self, description: str, agent_id: str | None = None) -> TaskInfo:
        """Register a new task or join existing one."""
        # Check for duplicates
        existing = self.check_duplicate_task(description)
        if existing:
            if agent_id:
                existing.agents.append(agent_id)
                self.agent_tasks[agent_id] = existing.task_id
            existing.status = "active"
            return existing

        # Create new task
        task_hash = self.hash_task(description)
        task_id = f"task_{task_hash}_{datetime.now().strftime('%H%M%S')}"
        context_key = f"ctx_{task_id}"

        task = TaskInfo(
            task_id=task_id,
            description=description,
            task_hash=task_hash,
            context_key=context_key,
            status="pending",
        )

        if agent_id:
            task.agents.append(agent_id)
            self.agent_tasks[agent_id] = task_id
            task.status = "active"

        self.active_tasks[task_id] = task
        self.task_by_hash[task_hash] = task_id

        return task

    def share_context(
        self,
        task_id: str,
        agent_id: str,
        output: str,
        artifacts: list[str] | None = None,
    ) -> SharedContext:
        """Share agent output as context for other agents."""
        task = self.active_tasks.get(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        context = SharedContext(
            context_key=task.context_key,
            task_id=task_id,
            agent_id=agent_id,
            output=output,
            artifacts=artifacts or [],
        )

        self.shared_contexts[task.context_key] = context

        # Update task with result
        task.result = output
        task.artifacts.extend(artifacts or [])
        task.status = "completed"

        return context

    def get_relevant_context(
        self, description: str, limit: int = 5
    ) -> list[SharedContext]:
        """Get relevant context from completed tasks."""
        relevant = []

        # Simple keyword matching for now
        keywords = set(description.lower().split())

        for context in self.shared_contexts.values():
            # Skip old contexts
            if datetime.now() - context.created_at > self._max_context_age:
                continue

            # Check for keyword overlap
            context_keywords = set(context.output.lower().split())
            overlap = len(keywords & context_keywords)

            if overlap > 2:  # At least 3 common keywords
                relevant.append(context)

        # Sort by recency and limit
        relevant.sort(key=lambda x: x.created_at, reverse=True)
        return relevant[:limit]

    def get_active_agent_count(self) -> int:
        """Get count of currently active agents."""
        return len([t for t in self.active_tasks.values() if t.status == "active"])

    def cleanup_old_entries(self):
        """Remove old completed tasks and contexts."""
        now = datetime.now()

        # Clean up old tasks
        to_remove = []
        for task_id, task in self.active_tasks.items():
            if (
                task.status == "completed"
                and now - task.created_at > self._max_context_age
            ):
                to_remove.append(task_id)

        for task_id in to_remove:
            task = self.active_tasks.pop(task_id)
            self.task_by_hash.pop(task.task_hash, None)

        # Clean up old contexts
        context_keys_to_remove = []
        for key, context in self.shared_contexts.items():
            if now - context.created_at > self._max_context_age:
                context_keys_to_remove.append(key)

        for key in context_keys_to_remove:
            self.shared_contexts.pop(key)

    def get_coordination_status(self) -> dict[str, Any]:
        """Get current coordination status and metrics."""
        active_tasks = [t for t in self.active_tasks.values() if t.status == "active"]
        completed_tasks = [
            t for t in self.active_tasks.values() if t.status == "completed"
        ]

        return {
            "active_tasks": len(active_tasks),
            "completed_tasks": len(completed_tasks),
            "shared_contexts": len(self.shared_contexts),
            "active_agents": self.get_active_agent_count(),
            "task_details": [
                {
                    "task_id": t.task_id,
                    "description": t.description[:100],
                    "status": t.status,
                    "agent_count": len(t.agents),
                }
                for t in active_tasks
            ],
        }

    def suggest_coordination(self, task_description: str) -> dict[str, Any]:
        """Suggest coordination strategies based on current state."""
        suggestions = []

        # Suggest thinking pattern based on task type
        thinking_pattern = self._suggest_thinking_pattern(task_description)
        if thinking_pattern:
            suggestions.append({
                "type": "thinking_pattern",
                "message": f"Use {thinking_pattern['pattern']} thinking for this task",
                "action": "apply_pattern",
                "pattern": thinking_pattern,
            })

        # Check for duplicate work
        duplicate = self.check_duplicate_task(task_description)
        if duplicate:
            suggestions.append({
                "type": "duplicate_detected",
                "message": f"Similar task already running: {duplicate.task_id}",
                "action": "wait_or_merge",
            })

        # Check agent load
        active_agents = self.get_active_agent_count()
        if active_agents > 5:
            suggestions.append({
                "type": "high_load",
                "message": f"{active_agents} agents currently active",
                "action": "consider_queuing",
            })

        # Check for relevant context
        relevant_contexts = self.get_relevant_context(task_description, limit=3)
        if relevant_contexts:
            suggestions.append({
                "type": "context_available",
                "message": f"Found {len(relevant_contexts)} relevant completed tasks",
                "action": "inherit_context",
                "contexts": [c.context_key for c in relevant_contexts],
            })

        return {
            "suggestions": suggestions,
            "should_proceed": len([
                s for s in suggestions if s["type"] == "duplicate_detected"
            ])
            == 0,
        }

    def _suggest_thinking_pattern(self, task_description: str) -> dict[str, Any] | None:
        """Suggest thinking pattern based on task type (from old swarm system)."""
        task_lower = task_description.lower()

        for pattern, keywords in self.thinking_patterns.items():
            if any(keyword in task_lower for keyword in keywords):
                return {
                    "pattern": pattern,
                    "description": self._get_pattern_description(pattern),
                    "keywords_matched": [k for k in keywords if k in task_lower],
                }

        # Default to system thinking for complex tasks
        if len(task_description) > 200:
            return {
                "pattern": "system",
                "description": "See interconnections, dependencies, ripple effects",
                "reason": "complex_task",
            }

        return None

    def _get_pattern_description(self, pattern: str) -> str:
        """Get description for thinking pattern."""
        descriptions = {
            "critical": "Question assumptions, find flaws, evaluate evidence",
            "system": "See interconnections, dependencies, ripple effects",
            "creative": "Generate novel approaches, think outside constraints",
            "risk": "Identify what could go wrong, mitigation strategies",
            "practical": "Focus on implementation details, concrete steps",
        }
        return descriptions.get(pattern, "Standard analytical thinking")

    def suggest_agent_role(self, task_description: str) -> str | None:
        """Suggest best agent role for a task (from old swarm system)."""
        task_lower = task_description.lower()

        role_scores = {}
        for role, keywords in self.role_patterns.items():
            score = sum(1 for keyword in keywords if keyword in task_lower)
            if score > 0:
                role_scores[role] = score

        if role_scores:
            # Return role with highest score
            return max(role_scores, key=role_scores.get)

        return None

    def track_task_performance(self, task_id: str, metrics: dict[str, Any]):
        """Track performance metrics for tasks (inspired by old swarm metrics)."""
        if task_id not in self.task_metrics:
            self.task_metrics[task_id] = {"start_time": datetime.now(), "updates": []}

        self.task_metrics[task_id]["updates"].append({
            "timestamp": datetime.now(),
            "metrics": metrics,
        })

        # Calculate duration if task is complete
        if metrics.get("status") == "completed":
            start = self.task_metrics[task_id]["start_time"]
            duration = (datetime.now() - start).total_seconds()
            self.task_metrics[task_id]["duration_seconds"] = duration
            self.task_metrics[task_id]["completion_time"] = datetime.now()

    def broadcast_event(self, event_type: str, agent_id: str, data: dict[str, Any]):
        """Broadcast an event to all interested agents (the magic of old swarm)."""
        event = {
            "type": event_type,
            "from_agent": agent_id,
            "timestamp": datetime.now().isoformat(),
            "data": data,
        }

        # Add to message queue
        self.message_queue.append(event)

        # Keep only last 100 messages
        if len(self.message_queue) > 100:
            self.message_queue = self.message_queue[-100:]

        return event

    def subscribe_agent(self, agent_id: str, event_types: list[str]):
        """Subscribe an agent to specific event types."""
        self.agent_subscriptions[agent_id] = event_types

    def get_agent_messages(
        self, agent_id: str, since_timestamp: str | None = None
    ) -> list[dict[str, Any]]:
        """Get messages for a specific agent based on their subscriptions."""
        if agent_id not in self.agent_subscriptions:
            return []

        subscribed_types = self.agent_subscriptions[agent_id]
        messages = []

        for msg in self.message_queue:
            # Skip own messages
            if msg["from_agent"] == agent_id:
                continue

            # Check if agent is subscribed to this event type
            if msg["type"] in subscribed_types or "all" in subscribed_types:
                # Filter by timestamp if provided
                if since_timestamp:
                    if msg["timestamp"] > since_timestamp:
                        messages.append(msg)
                else:
                    messages.append(msg)

        return messages

    def notify_file_edit(self, agent_id: str, file_path: str, operation: str):
        """Notify other agents about file edits (key to old swarm coordination)."""
        # Find agents working on related tasks
        related_agents = []

        for aid, tid in self.agent_tasks.items():
            if aid != agent_id and tid in self.active_tasks:
                task = self.active_tasks[tid]
                # Check if task might be related to this file
                if file_path in task.description or any(
                    file_path in a for a in task.artifacts
                ):
                    related_agents.append(aid)

        # Broadcast the edit event
        event_data = {
            "file_path": file_path,
            "operation": operation,
            "related_agents": related_agents,
            "task_id": self.agent_tasks.get(agent_id),
        }

        self.broadcast_event("file_edit", agent_id, event_data)

        return related_agents

    def get_coordination_messages(self, agent_id: str) -> dict[str, Any]:
        """Get coordination messages for an agent (for hook responses)."""
        messages = self.get_agent_messages(agent_id)

        # Analyze messages for actionable insights
        file_conflicts = []
        related_completions = []
        waiting_for = []

        for msg in messages:
            if msg["type"] == "file_edit":
                if msg["data"].get("file_path"):
                    file_conflicts.append({
                        "file": msg["data"]["file_path"],
                        "agent": msg["from_agent"],
                        "operation": msg["data"].get("operation", "unknown"),
                    })
            elif msg["type"] == "task_complete":
                related_completions.append({
                    "agent": msg["from_agent"],
                    "task": msg["data"].get("task_id"),
                    "output": msg["data"].get("summary", "")[:100],
                })
            elif msg["type"] == "waiting_for_input":
                waiting_for.append({
                    "agent": msg["from_agent"],
                    "needs": msg["data"].get("requirement", "unknown"),
                })

        return {
            "message_count": len(messages),
            "file_conflicts": file_conflicts,
            "related_completions": related_completions,
            "waiting_for": waiting_for,
            "raw_messages": messages[-5:] if messages else [],  # Last 5 messages
        }

    def _setup_event_subscriptions(self):
        """Subscribe to HookEventBroadcaster for inter-agent communication."""
        from khive.services.claude.hooks.hook_event import HookEventBroadcaster

        # Subscribe to hook events for coordination
        def handle_hook_event(event):
            """Process hook events for inter-agent coordination."""
            if hasattr(event, "content"):
                content = event.content
                event_type = content.get("event_type", "")

                # Map hook events to coordination events
                if event_type == "pre_edit" and content.get("file_paths"):
                    # Broadcast file edit notification
                    agent_id = content.get("session_id", "unknown")[:8]
                    for file_path in content.get("file_paths", []):
                        self.notify_file_edit(f"agent_{agent_id}", file_path, "edit")

                elif event_type == "post_agent_spawn" and content.get("task_id"):
                    # Broadcast task completion
                    agent_id = content.get("session_id", "unknown")[:8]
                    self.broadcast_event(
                        "task_complete",
                        f"agent_{agent_id}",
                        {
                            "task_id": content.get("task_id"),
                            "summary": content.get("output", "")[:200],
                            "success": content.get("success", False),
                        },
                    )

        HookEventBroadcaster.subscribe(handle_hook_event)

    def suggest_coordination_pattern(
        self, task_description: str, agent_count: int = 0
    ) -> dict[str, Any]:
        """Suggest optimal coordination pattern based on task and context."""
        task_lower = task_description.lower()

        # Check pattern effectiveness history first
        if task_lower in self.pattern_effectiveness:
            # Return the most effective pattern from history
            best_pattern = max(
                self.pattern_effectiveness[task_lower].items(), key=lambda x: x[1]
            )
            return {
                "pattern": best_pattern[0],
                "confidence": "high",
                "reason": "proven_effective",
                "expected_efficiency": best_pattern[1],
                "details": self.coordination_patterns[best_pattern[0]],
            }

        # Analyze task to suggest pattern
        suggested_pattern = None
        confidence = "medium"

        # Check for pattern keywords
        for pattern_name, pattern_info in self.coordination_patterns.items():
            for keyword in pattern_info["best_for"]:
                if keyword in task_lower:
                    suggested_pattern = pattern_name
                    confidence = "high"
                    break
            if suggested_pattern:
                break

        # Default patterns based on agent count
        if not suggested_pattern and agent_count > 0:
            if agent_count >= 4:
                suggested_pattern = "fan_out"
            elif agent_count == 2:
                suggested_pattern = "pipeline"
            elif agent_count == 3:
                suggested_pattern = "consensus"
            else:
                suggested_pattern = "hierarchical"
            confidence = "low"

        # Default to fan_out if nothing else matches
        if not suggested_pattern:
            suggested_pattern = "fan_out"
            confidence = "low"

        return {
            "pattern": suggested_pattern,
            "confidence": confidence,
            "reason": "keyword_match" if confidence == "high" else "default",
            "details": self.coordination_patterns[suggested_pattern],
        }

    def record_pattern_effectiveness(
        self, task_description: str, pattern_used: str, metrics: dict[str, Any]
    ):
        """Record how well a pattern worked for a task type."""
        task_key = task_description.lower()[:50]  # Use first 50 chars as key

        if task_key not in self.pattern_effectiveness:
            self.pattern_effectiveness[task_key] = {}

        # Calculate effectiveness score
        efficiency_score = 0.0
        if "time_saved_pct" in metrics:
            efficiency_score += metrics["time_saved_pct"] * 0.4
        if "success_rate" in metrics:
            efficiency_score += metrics["success_rate"] * 0.3
        if "conflict_rate" in metrics:
            efficiency_score += (100 - metrics["conflict_rate"]) * 0.2
        if "dedup_rate" in metrics:
            efficiency_score += metrics["dedup_rate"] * 0.1

        # Update rolling average
        if pattern_used in self.pattern_effectiveness[task_key]:
            old_score = self.pattern_effectiveness[task_key][pattern_used]
            # Weighted average: 70% old, 30% new
            self.pattern_effectiveness[task_key][pattern_used] = (
                old_score * 0.7 + efficiency_score * 0.3
            )
        else:
            self.pattern_effectiveness[task_key][pattern_used] = efficiency_score

    def get_pattern_recommendations(self) -> list[dict[str, Any]]:
        """Get recommendations based on learned pattern effectiveness."""
        recommendations = []

        for task_type, patterns in self.pattern_effectiveness.items():
            if patterns:
                best_pattern = max(patterns.items(), key=lambda x: x[1])
                worst_pattern = min(patterns.items(), key=lambda x: x[1])

                if best_pattern[1] - worst_pattern[1] > 20:  # Significant difference
                    recommendations.append({
                        "task_type": task_type,
                        "recommendation": f"Use {best_pattern[0]} pattern (score: {best_pattern[1]:.1f})",
                        "avoid": f"Avoid {worst_pattern[0]} pattern (score: {worst_pattern[1]:.1f})",
                        "confidence": "high" if best_pattern[1] > 70 else "medium",
                    })

        return recommendations

    def get_performance_insights(self) -> dict[str, Any]:
        """Get performance insights (inspired by old swarm monitoring)."""
        completed_tasks = [
            m for tid, m in self.task_metrics.items() if "duration_seconds" in m
        ]

        if not completed_tasks:
            return {"message": "No completed tasks to analyze"}

        durations = [t["duration_seconds"] for t in completed_tasks]
        avg_duration = sum(durations) / len(durations) if durations else 0

        return {
            "avg_task_duration": avg_duration,
            "completed_tasks": len(completed_tasks),
            "fastest_task": min(durations) if durations else None,
            "slowest_task": max(durations) if durations else None,
            "optimization_suggestion": (
                "Use batch operations" if avg_duration > 60 else "Performance optimal"
            ),
        }


# Global registry instance
_registry = CoordinationRegistry()


def get_registry() -> CoordinationRegistry:
    """Get the global coordination registry."""
    return _registry


# Helper functions for easy integration
def coordinate_task_start(
    description: str, agent_id: str | None = None
) -> dict[str, Any]:
    """Coordinate task start with deduplication and context."""
    registry = get_registry()

    # Get coordination suggestions
    suggestions = registry.suggest_coordination(description)

    # Register the task
    task = registry.register_task(description, agent_id)

    # Get relevant context
    contexts = registry.get_relevant_context(description)

    return {
        "task_id": task.task_id,
        "context_key": task.context_key,
        "is_duplicate": task.task_hash in registry.task_by_hash
        and len(task.agents) > 1,
        "suggestions": suggestions["suggestions"],
        "relevant_contexts": [
            {"key": c.context_key, "summary": c.output[:200]} for c in contexts
        ],
        "should_proceed": suggestions["should_proceed"],
    }


def coordinate_task_complete(
    task_id: str, agent_id: str, output: str, artifacts: list[str] | None = None
) -> dict[str, Any]:
    """Coordinate task completion with result sharing."""
    registry = get_registry()

    # Share the context
    context = registry.share_context(task_id, agent_id, output, artifacts)

    # Clean up old entries periodically
    registry.cleanup_old_entries()

    return {
        "context_shared": True,
        "context_key": context.context_key,
        "artifacts_registered": len(artifacts) if artifacts else 0,
    }


def get_coordination_insights(task_description: str = "") -> dict[str, Any]:
    """Get insights about current coordination state."""
    registry = get_registry()

    # If task_description provided, get task-specific insights
    if task_description:
        # Check for duplicate/similar tasks
        task_hash = hashlib.sha256(task_description.encode()).hexdigest()[:8]
        is_duplicate = task_hash in registry.task_by_hash

        # Get relevant context
        context = registry.get_relevant_context(task_description)

        # Get coordination suggestions
        suggestions = registry.suggest_coordination_pattern(task_description)

        return {
            "task_description": task_description,
            "is_duplicate": is_duplicate,
            "similar_tasks": len([
                t
                for t in registry.active_tasks.values()
                if task_description.lower() in t.description.lower()
            ]),
            "relevant_context": context,
            "suggested_pattern": suggestions.get("pattern"),
            "suggested_role": registry.suggest_agent_role(task_description),
            "active_tasks": len(registry.active_tasks),
        }

    # Otherwise return general coordination status
    status = registry.get_coordination_status()

    # Add insights
    insights = []

    if status["active_agents"] > 7:
        insights.append("High agent activity - consider batching or queuing")

    if status["completed_tasks"] > status["active_tasks"] * 2:
        insights.append("Many completed tasks available for context inheritance")

    if status["shared_contexts"] < status["completed_tasks"]:
        insights.append("Not all completed tasks are sharing context")

    status["insights"] = insights
    return status
