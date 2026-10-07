"""
Asynchronous Event Bus [Member 4]
In-process asynchronous event bus for decoupled pub/sub inter-agent messaging.
"""

import asyncio
import inspect
import logging
from typing import Dict, List, Callable, Any, Union, Set
from .protocol import AgentMessageEnvelope, EventType

logger = logging.getLogger(__name__)


class AsyncEventBus:
    """
    Asynchronous pub/sub event bus with handler error isolation and non-blocking execution.
    """

    def __init__(self):
        # Maps event_type (str) -> Set of handler callables
        self._subscribers: Dict[str, Set[Callable]] = {}
        self._history: List[AgentMessageEnvelope] = []
        self._max_history = 100

    def subscribe(self, event_type: Union[EventType, str], handler: Callable) -> None:
        """
        Subscribe a callback handler to a specific event type or '*' for all events.
        
        Args:
            event_type: EventType enum or string representation.
            handler: Sync or async callable taking (event: AgentMessageEnvelope).
        """
        key = str(event_type.value if isinstance(event_type, EventType) else event_type)
        if key not in self._subscribers:
            self._subscribers[key] = set()
        self._subscribers[key].add(handler)
        logger.debug("Subscribed handler %s to event '%s'", getattr(handler, '__name__', str(handler)), key)

    def unsubscribe(self, event_type: Union[EventType, str], handler: Callable) -> None:
        """
        Unsubscribe a callback handler from an event type.
        """
        key = str(event_type.value if isinstance(event_type, EventType) else event_type)
        if key in self._subscribers and handler in self._subscribers[key]:
            self._subscribers[key].remove(handler)
            logger.debug("Unsubscribed handler %s from event '%s'", getattr(handler, '__name__', str(handler)), key)

    async def publish(self, event: Union[AgentMessageEnvelope, Dict[str, Any]]) -> AgentMessageEnvelope:
        """
        Publish an event packet asynchronously to all subscribed handlers.
        
        Args:
            event: AgentMessageEnvelope or dictionary convertible to AgentMessageEnvelope.
            
        Returns:
            The published AgentMessageEnvelope instance.
        """
        if isinstance(event, dict):
            envelope = AgentMessageEnvelope(**event)
        else:
            envelope = event

        # Store in rolling event history
        self._history.append(envelope)
        if len(self._history) > self._max_history:
            self._history.pop(0)

        event_key = str(envelope.event_type)
        logger.info("[EventBus] [%s] %s -> %s | %s", 
                    envelope.event_type, envelope.source, envelope.destination, envelope.message_id)

        # Gather target handlers for specific event_key + wildcard '*'
        handlers: Set[Callable] = set()
        if event_key in self._subscribers:
            handlers.update(self._subscribers[event_key])
        if "*" in self._subscribers:
            handlers.update(self._subscribers["*"])

        if not handlers:
            logger.debug("[EventBus] No subscribers for event '%s'", event_key)
            return envelope

        # Execute all handlers with error isolation
        tasks = []
        for handler in handlers:
            tasks.append(self._execute_handler(handler, envelope))

        await asyncio.gather(*tasks, return_exceptions=True)
        return envelope

    async def _execute_handler(self, handler: Callable, envelope: AgentMessageEnvelope) -> None:
        """Helper to invoke a single handler safely with exception isolation."""
        try:
            if inspect.iscoroutinefunction(handler):
                await handler(envelope)
            else:
                # Run synchronous handlers safely in default thread pool
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, handler, envelope)
        except Exception as e:
            handler_name = getattr(handler, '__name__', str(handler))
            logger.error("[EventBus Exception] Handler '%s' failed on event '%s': %s",
                         handler_name, envelope.event_type, e, exc_info=True)

    def get_history(self, limit: int = 50) -> List[AgentMessageEnvelope]:
        """Return recent event history log."""
        return self._history[-limit:]

    def clear(self) -> None:
        """Clear all subscribers and history (useful for test resets)."""
        self._subscribers.clear()
        self._history.clear()


# Global event bus instance
_global_event_bus = AsyncEventBus()


def get_event_bus() -> AsyncEventBus:
    """Return singleton AsyncEventBus instance."""
    return _global_event_bus
