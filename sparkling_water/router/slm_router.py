"""SLM Router for task routing and orchestration."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import json
import asyncio
from datetime import datetime
from ..providers.manager import ProviderManager
from ..providers.base import ModelTier


class TaskType(Enum):
    """Types of tasks that can be routed."""

    STRUCTURAL_QUERY = "structural_query"
    CODE_GENERATION = "code_generation"
    CODE_REFACTORING = "code_refactoring"
    DEBUGGING = "debugging"
    DOCUMENTATION = "documentation"
    ARCHITECTURE_ANALYSIS = "architecture_analysis"
    FILE_OPERATION = "file_operation"
    UNKNOWN = "unknown"


@dataclass
class Task:
    """Represents a task to be executed."""

    id: str
    type: TaskType
    description: str
    context: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    requires_frontier: bool = False
    estimated_tokens: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "type": self.type.value,
            "description": self.description,
            "context": self.context,
            "priority": self.priority,
            "created_at": self.created_at.isoformat(),
            "requires_frontier": self.requires_frontier,
            "estimated_tokens": self.estimated_tokens,
        }


@dataclass
class RoutingDecision:
    """Represents a routing decision."""

    task: Task
    model_tier: ModelTier
    reasoning: str
    confidence: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "task": self.task.to_dict(),
            "model_tier": self.model_tier.value,
            "reasoning": self.reasoning,
            "confidence": self.confidence,
        }


class SLMRouter:
    """SLM-based router for task classification and routing."""

    def __init__(self, provider_manager: Optional[ProviderManager] = None):
        self.provider_manager = provider_manager or ProviderManager()
        self.routing_history: List[RoutingDecision] = []
        self._lock = asyncio.Lock()

        # Task type patterns for heuristic routing
        self.task_patterns = {
            TaskType.STRUCTURAL_QUERY: [
                "find",
                "locate",
                "where",
                "which",
                "list",
                "show",
                "map",
                "traverse",
                "navigate",
                "explore",
                "identify",
            ],
            TaskType.CODE_GENERATION: [
                "create",
                "generate",
                "write",
                "implement",
                "build",
                "add",
                "new",
                "make",
                "develop",
            ],
            TaskType.CODE_REFACTORING: [
                "refactor",
                "optimize",
                "improve",
                "clean",
                "simplify",
                "restructure",
                "reorganize",
            ],
            TaskType.DEBUGGING: [
                "debug",
                "fix",
                "error",
                "issue",
                "problem",
                "broken",
                "not working",
                "fail",
                "exception",
            ],
            TaskType.DOCUMENTATION: [
                "document",
                "explain",
                "describe",
                "comment",
                "readme",
                "docstring",
            ],
            TaskType.ARCHITECTURE_ANALYSIS: [
                "architecture",
                "design",
                "structure",
                "pattern",
                "analyze",
                "review",
                "assess",
            ],
            TaskType.FILE_OPERATION: ["read", "write", "delete", "move", "copy", "create file"],
        }

    async def classify_task(self, description: str, context: Dict[str, Any] = None) -> TaskType:
        """Classify a task into its type."""
        description_lower = description.lower()

        # Heuristic classification based on keywords
        for task_type, patterns in self.task_patterns.items():
            for pattern in patterns:
                if pattern in description_lower:
                    return task_type

        # If primary provider is available, use it for classification
        if self.provider_manager.get_primary_provider():
            try:
                task_type = await self._slm_classify(description, context)
                return task_type
            except Exception as e:
                # print(f"SLM classification failed: {e}, falling back to heuristic")
                pass

        return TaskType.UNKNOWN

    async def _slm_classify(self, description: str, context: Dict[str, Any] = None) -> TaskType:
        """Use SLM to classify task type."""
        prompt = f"""
Classify the following task into one of these categories:
- structural_query: Finding, locating, or exploring code structure
- code_generation: Creating new code or features
- code_refactoring: Improving or restructuring existing code
- debugging: Fixing errors or issues
- documentation: Writing or updating documentation
- architecture_analysis: Analyzing code architecture or design
- file_operation: Reading, writing, or manipulating files

Task: {description}

Context: {json.dumps(context, indent=2) if context else "None"}

Respond with only the category name (e.g., "code_generation").
"""

        try:
            # We want to use the primary model (often an SLM) for classification
            response = await self.provider_manager.chat_completion(
                messages=[
                    {"role": "system", "content": "You are a task classifier for a coding agent."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                max_tokens=50,
            )

            result = response.strip().lower()

            # Map result to TaskType
            for task_type in TaskType:
                if task_type.value == result:
                    return task_type

            return TaskType.UNKNOWN
        except Exception:
            return TaskType.UNKNOWN

    async def route_task(self, task: Task) -> RoutingDecision:
        """Route a task to the appropriate model tier."""
        # Determine if task requires frontier model
        requires_frontier = await self._requires_frontier_model(task)

        if requires_frontier:
            model_tier = ModelTier.FRONTIER
            reasoning = "Task requires complex reasoning or synthesis beyond SLM capabilities"
            confidence = 0.9
        else:
            model_tier = ModelTier.SLM
            reasoning = "Task can be handled efficiently by SLM"
            confidence = 0.85

        decision = RoutingDecision(
            task=task,
            model_tier=model_tier,
            reasoning=reasoning,
            confidence=confidence,
        )

        # Store in history
        async with self._lock:
            self.routing_history.append(decision)

        return decision

    async def _requires_frontier_model(self, task: Task) -> bool:
        """Determine if task requires frontier model."""
        # Heuristic rules
        frontier_required_tasks = {
            TaskType.CODE_GENERATION,
            TaskType.CODE_REFACTORING,
            TaskType.DEBUGGING,
        }

        if task.type in frontier_required_tasks:
            # Check complexity indicators
            description = task.description.lower()

            # Complex indicators
            complex_indicators = [
                "algorithm",
                "optimization",
                "performance",
                "security",
                "concurrent",
                "parallel",
                "distributed",
                "architecture",
                "design pattern",
                "complex",
                "sophisticated",
            ]

            for indicator in complex_indicators:
                if indicator in description:
                    return True

            # Large context
            if task.estimated_tokens > 4000:
                return True

        return False

    async def execute_task(self, task: Task, prompt: str) -> str:
        """Execute a task using the appropriate model tier."""
        decision = await self.route_task(task)

        # Use secondary (Frontier) model if decision is FRONTIER
        use_secondary = decision.model_tier == ModelTier.FRONTIER

        # If secondary is not configured, it will fall back to primary in chat_completion
        return await self.provider_manager.chat_completion(
            messages=[
                {"role": "system", "content": "You are a helpful coding assistant."},
                {"role": "user", "content": prompt},
            ],
            use_secondary=use_secondary,
            max_tokens=min(4096, task.estimated_tokens + 1000),
            temperature=0.3
        )

    async def get_routing_stats(self) -> Dict[str, Any]:
        """Get routing statistics."""
        async with self._lock:
            total = len(self.routing_history)
            slm_count = sum(1 for d in self.routing_history if d.model_tier == ModelTier.SLM)
            frontier_count = sum(
                1 for d in self.routing_history if d.model_tier == ModelTier.FRONTIER
            )

            # Calculate cost savings (rough estimate)
            # Assume SLM costs $0.0001 per 1K tokens, Frontier costs $0.01 per 1K tokens
            slm_tokens = sum(
                d.task.estimated_tokens
                for d in self.routing_history
                if d.model_tier == ModelTier.SLM
            )
            frontier_tokens = sum(
                d.task.estimated_tokens
                for d in self.routing_history
                if d.model_tier == ModelTier.FRONTIER
            )

            slm_cost = (slm_tokens / 1000) * 0.0001
            frontier_cost = (frontier_tokens / 1000) * 0.01

            # What if everything went to frontier?
            all_tokens = slm_tokens + frontier_tokens
            all_frontier_cost = (all_tokens / 1000) * 0.01

            cost_savings = all_frontier_cost - (slm_cost + frontier_cost)

            return {
                "total_tasks": total,
                "slm_tasks": slm_count,
                "frontier_tasks": frontier_count,
                "slm_percentage": (slm_count / total * 100) if total > 0 else 0,
                "slm_tokens": slm_tokens,
                "frontier_tokens": frontier_tokens,
                "estimated_cost_savings": cost_savings,
                "cost_savings_percentage": (cost_savings / all_frontier_cost * 100)
                if all_frontier_cost > 0
                else 0,
            }

    async def create_task(
        self, description: str, context: Dict[str, Any] = None, priority: int = 0
    ) -> Task:
        """Create a new task."""
        import uuid

        task_type = await self.classify_task(description, context)

        # Estimate tokens (rough approximation)
        estimated_tokens = len(description) // 4
        if context:
            estimated_tokens += len(json.dumps(context)) // 4

        return Task(
            id=str(uuid.uuid4()),
            type=task_type,
            description=description,
            context=context or {},
            priority=priority,
            estimated_tokens=estimated_tokens,
        )
