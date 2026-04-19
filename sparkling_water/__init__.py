"""Sparkling Water - Next-Generation CLI Coding Agent."""

__version__ = "0.1.0"
__author__ = "Sparkling Water Team"

from .events.event_bus import EventBus, Event, EventType, Orchestrator, Saga
from .graph.knowledge_graph import KnowledgeGraph, CodeNode, EdgeType
from .vfs.virtual_filesystem import VirtualFileSystem, FileView
from .router.slm_router import SLMRouter, Task, TaskType, ModelTier
from .core.ast_transformer import (
    ASTTransformationEngine,
    TransformationIntent,
    TransformationAction,
)
from .core.code_editor import CodeEditor, EditIntent, EditOperation
from .providers import ProviderManager, ModelInfo, ModelTier as ProviderModelTier

__all__ = [
    "EventBus",
    "Event",
    "EventType",
    "Orchestrator",
    "Saga",
    "KnowledgeGraph",
    "CodeNode",
    "EdgeType",
    "VirtualFileSystem",
    "FileView",
    "SLMRouter",
    "Task",
    "TaskType",
    "ModelTier",
    "ASTTransformationEngine",
    "TransformationIntent",
    "TransformationAction",
    "CodeEditor",
    "EditIntent",
    "EditOperation",
    "ProviderManager",
    "ModelInfo",
    "ProviderModelTier",
]
