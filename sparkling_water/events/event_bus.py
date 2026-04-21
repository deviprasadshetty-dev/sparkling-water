"""Event Bus and Orchestrator for Event-Driven Architecture."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from datetime import datetime
import asyncio
import uuid


class EventType(Enum):
    """Standard event types for the system."""

    TASK_REQUESTED = "task.requested"
    TASK_STARTED = "task.started"
    PLAN_CREATED = "plan.created"
    TOOL_CALL = "tool.call"
    TOOL_RESULT = "tool.result"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    FILE_MODIFIED = "file.modified"
    FILE_READ = "file.read"
    ERROR_DETECTED = "error.detected"
    CONTEXT_PRUNED = "context.pruned"
    GRAPH_QUERY = "graph.query"
    AST_TRANSFORM = "ast.transform"


@dataclass
class Event:
    """Immutable event representation."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: EventType = EventType.TASK_REQUESTED
    timestamp: datetime = field(default_factory=datetime.utcnow)
    data: Dict[str, Any] = field(default_factory=dict)
    parent_id: Optional[str] = None
    correlation_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        return {
            "id": self.id,
            "type": self.type.value,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
            "parent_id": self.parent_id,
            "correlation_id": self.correlation_id,
        }


class EventBus:
    """Async event bus for event-driven architecture."""

    def __init__(self):
        self._subscribers: Dict[EventType, List[Callable]] = {}
        self._event_log: List[Event] = []
        self._lock = asyncio.Lock()

    async def subscribe(self, event_type: EventType, handler: Callable[[Event], None]) -> None:
        """Subscribe to an event type."""
        async with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            self._subscribers[event_type].append(handler)

    async def publish(self, event: Event) -> None:
        """Publish an event to all subscribers."""
        async with self._lock:
            self._event_log.append(event)

        # Notify subscribers asynchronously
        handlers = self._subscribers.get(event.type, [])
        tasks = []
        for handler in handlers:
            task = asyncio.create_task(self._safe_call(handler, event))
            tasks.append(task)

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def get_event_log(self, limit: Optional[int] = None) -> List[Event]:
        """Get event log with optional limit."""
        async with self._lock:
            if limit:
                return self._event_log[-limit:]
            return self._event_log.copy()

    async def clear_log(self) -> None:
        """Clear event log."""
        async with self._lock:
            self._event_log.clear()


class Saga:
    """Saga pattern for distributed transaction management."""

    def __init__(self, event_bus: EventBus, saga_id: str):
        self.event_bus = event_bus
        self.saga_id = saga_id
        self.steps: List[Dict[str, Any]] = []
        self.current_step = 0
        self.completed = False
        self.failed = False

    def add_step(
        self, action: Callable, compensation: Optional[Callable] = None, name: str = ""
    ) -> None:
        """Add a step to the saga."""
        self.steps.append(
            {
                "name": name,
                "action": action,
                "compensation": compensation,
                "executed": False,
                "compensated": False,
            }
        )

    async def execute(self) -> bool:
        """Execute all steps in the saga."""
        try:
            for i, step in enumerate(self.steps):
                self.current_step = i
                await step["action"]()
                step["executed"] = True

            self.completed = True
            return True
        except Exception as e:
            self.failed = True
            await self.compensate()
            raise e

    async def compensate(self) -> None:
        """Compensate executed steps in reverse order."""
        for step in reversed(self.steps[: self.current_step + 1]):
            if step["executed"] and not step["compensated"] and step["compensation"]:
                try:
                    await step["compensation"]()
                    step["compensated"] = True
                except Exception as e:
                    print(f"Compensation failed for step {step['name']}: {e}")


class Orchestrator:
    """Main orchestrator for coordinating events and sagas."""

    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.active_sagas: Dict[str, Saga] = {}
        self._lock = asyncio.Lock()

    async def create_saga(self, saga_id: Optional[str] = None) -> Saga:
        """Create a new saga."""
        if saga_id is None:
            saga_id = str(uuid.uuid4())

        saga = Saga(self.event_bus, saga_id)
        async with self._lock:
            self.active_sagas[saga_id] = saga
        return saga

    async def execute_saga(self, saga: Saga) -> bool:
        """Execute a saga and manage its lifecycle."""
        try:
            await self.event_bus.publish(
                Event(type=EventType.TASK_STARTED, data={"saga_id": saga.saga_id})
            )

            success = await saga.execute()

            if success:
                await self.event_bus.publish(
                    Event(type=EventType.TASK_COMPLETED, data={"saga_id": saga.saga_id})
                )
            else:
                await self.event_bus.publish(
                    Event(type=EventType.TASK_FAILED, data={"saga_id": saga.saga_id})
                )

            return success
        except Exception as e:
            await self.event_bus.publish(
                Event(type=EventType.TASK_FAILED, data={"saga_id": saga.saga_id, "error": str(e)})
            )
            raise
        finally:
            async with self._lock:
                if saga.saga_id in self.active_sagas:
                    del self.active_sagas[saga.saga_id]

    async def get_active_sagas(self) -> List[Saga]:
        """Get list of active sagas."""
        async with self._lock:
            return list(self.active_sagas.values())

    async def publish_event(self, event_type: EventType, data: Dict[str, Any], correlation_id: Optional[str] = None):
        """Helper to publish an event."""
        await self.event_bus.publish(
            Event(type=event_type, data=data, correlation_id=correlation_id)
        )
