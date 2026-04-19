"""Simple tests for Sparkling Water components."""

import pytest
import asyncio
from pathlib import Path
import tempfile
import os

from sparkling_water.events.event_bus import EventBus, Event, EventType, Orchestrator
from sparkling_water.graph.knowledge_graph import KnowledgeGraph, CodeNode
from sparkling_water.vfs.virtual_filesystem import VirtualFileSystem
from sparkling_water.router.slm_router import SLMRouter, TaskType
from sparkling_water.core.ast_transformer import (
    ASTTransformationEngine,
    TransformationIntent,
    TransformationAction,
)


@pytest.mark.asyncio
async def test_event_bus():
    """Test event bus functionality."""
    bus = EventBus()
    events_received = []

    async def handler(event: Event):
        events_received.append(event)

    await bus.subscribe(EventType.TASK_REQUESTED, handler)

    event = Event(type=EventType.TASK_REQUESTED, data={"test": "data"})
    await bus.publish(event)

    assert len(events_received) == 1
    assert events_received[0].data["test"] == "data"


@pytest.mark.asyncio
async def test_knowledge_graph():
    """Test knowledge graph indexing."""
    kg = KnowledgeGraph(db_path=":memory:")
    await kg.initialize()

    # Create a temporary Python file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write("""
def authenticate(username, password):
    '''Authenticate user credentials.'''
    if username == "admin" and password == "secret":
        return True
    return False

class AuthService:
    '''Authentication service.'''
    def __init__(self):
        self.users = {}
    
    def verify_token(self, token):
        '''Verify authentication token.'''
        return token in self.users
""")
        temp_file = f.name

    try:
        # Index the file
        nodes = await kg.index_file(temp_file, Path(temp_file).read_text())

        # Verify nodes were created
        assert nodes > 0

        # Query functions
        functions = await kg.query_nodes(node_type="function")
        assert len(functions) > 0

        # Query classes
        classes = await kg.query_nodes(node_type="class")
        assert len(classes) > 0

        # Get stats
        stats = await kg.get_stats()
        assert stats["nodes"] > 0

    finally:
        os.unlink(temp_file)


@pytest.mark.asyncio
async def test_virtual_filesystem():
    """Test virtual file system progressive disclosure."""
    kg = KnowledgeGraph(db_path=":memory:")
    await kg.initialize()

    # Create a temporary Python file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write("""
def authenticate(username, password):
    '''Authenticate user credentials.'''
    return True

def verify_token(token):
    '''Verify authentication token.'''
    return token is not None
""")
        temp_file = f.name

    try:
        # Index the file
        await kg.index_file(temp_file, Path(temp_file).read_text())

        # Create VFS
        vfs = VirtualFileSystem(knowledge_graph=kg, root_path=Path(temp_file).parent)

        # Read file with signatures only
        content = await vfs.read_file(temp_file)
        assert "authenticate" in content
        assert "verify_token" in content

        # Expand a function
        content = await vfs.read_file(temp_file, expand_function="authenticate")
        assert "authenticate" in content

        # Get stats
        stats = await vfs.get_file_stats(temp_file)
        assert stats["token_savings"] >= 0

    finally:
        os.unlink(temp_file)


@pytest.mark.asyncio
async def test_slm_router():
    """Test SLM router task classification."""
    router = SLMRouter()

    # Test task classification
    task_type = await router.classify_task("Find where the authenticate function is called")
    assert task_type == TaskType.STRUCTURAL_QUERY

    task_type = await router.classify_task("Create a new authentication function")
    assert task_type == TaskType.CODE_GENERATION

    task_type = await router.classify_task("Fix the authentication bug")
    assert task_type == TaskType.DEBUGGING

    # Create a task
    task = await router.create_task("Find all authentication functions")
    assert task.type == TaskType.STRUCTURAL_QUERY
    assert task.estimated_tokens > 0


@pytest.mark.asyncio
async def test_ast_transformation():
    """Test AST transformation engine."""
    # Create a temporary Python file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write("""
def authenticate(username, password):
    '''Authenticate user credentials.'''
    return True
""")
        temp_file = f.name

    try:
        # Create transformation engine
        engine = ASTTransformationEngine()

        # Create transformation intent
        intent = await engine.create_transformation_intent(
            action="add_argument",
            target_file=temp_file,
            target_function="authenticate",
            argument_name="timeout",
            default_value="30",
        )

        # Apply transformation
        result = await engine.apply_transformation(intent)

        # Verify transformation succeeded
        assert result.success
        assert "timeout" in result.modified_content

        # Verify syntax is valid
        is_valid = await engine.validate_syntax(result.modified_content)
        assert is_valid

    finally:
        os.unlink(temp_file)


@pytest.mark.asyncio
async def test_integration():
    """Test integration of all components."""
    # Create a temporary directory with a Python file
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test.py"
        test_file.write_text("""
def authenticate(username, password):
    '''Authenticate user credentials.'''
    return True

class AuthService:
    '''Authentication service.'''
    def verify_token(self, token):
        '''Verify authentication token.'''
        return token is not None
""")

        # Initialize components
        kg = KnowledgeGraph(db_path=":memory:")
        await kg.initialize()

        vfs = VirtualFileSystem(knowledge_graph=kg, root_path=Path(tmpdir))
        router = SLMRouter()
        engine = ASTTransformationEngine()

        # Index the file
        nodes = await kg.index_file(str(test_file), test_file.read_text())
        assert nodes > 0

        # Query functions
        functions = await kg.query_nodes(node_type="function")
        assert len(functions) > 0

        # Read file with progressive disclosure
        content = await vfs.read_file(str(test_file))
        assert "authenticate" in content

        # Route a task
        task = await router.create_task("Find authentication functions")
        assert task.type == TaskType.STRUCTURAL_QUERY

        # Apply transformation
        intent = await engine.create_transformation_intent(
            action="add_argument",
            target_file=str(test_file),
            target_function="authenticate",
            argument_name="timeout",
            default_value="30",
        )

        result = await engine.apply_transformation(intent)
        assert result.success


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
