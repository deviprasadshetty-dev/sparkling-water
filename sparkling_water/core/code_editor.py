"""Enhanced code editor with write, edit, and delete capabilities."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from enum import Enum
import libcst as cst
from libcst import matchers as m
from pathlib import Path
import asyncio


class EditOperation(Enum):
    """Types of edit operations."""

    WRITE = "write"
    EDIT = "edit"
    DELETE = "delete"
    INSERT = "insert"
    REPLACE = "replace"
    MOVE = "move"
    COPY = "copy"


@dataclass
class EditIntent:
    """Represents an edit intent."""

    operation: EditOperation
    target_file: str
    target_function: Optional[str] = None
    target_class: Optional[str] = None
    target_line: Optional[int] = None
    content: Optional[str] = None
    old_content: Optional[str] = None
    new_content: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "operation": self.operation.value,
            "target_file": self.target_file,
            "target_function": self.target_function,
            "target_class": self.target_class,
            "target_line": self.target_line,
            "content": self.content,
            "old_content": self.old_content,
            "new_content": self.new_content,
            "parameters": self.parameters,
        }


@dataclass
class EditResult:
    """Result of an edit operation."""

    success: bool
    operation: EditOperation
    modified_file: str
    original_content: str
    modified_content: str
    changes: List[str]
    lines_changed: List[int]
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "operation": self.operation.value,
            "modified_file": self.modified_file,
            "original_content": self.original_content,
            "modified_content": self.modified_content,
            "changes": self.changes,
            "lines_changed": self.lines_changed,
            "error": self.error,
        }


class WriteTransformer(cst.CSTTransformer):
    """Transformer to write new code."""

    def __init__(self, new_code: str):
        super().__init__()
        self.new_code = new_code
        self.modified = False

    def leave_Module(self, original_node: cst.Module, updated_node: cst.Module) -> cst.Module:
        """Replace entire module with new code."""
        self.modified = True
        return cst.parse_module(self.new_code)


class EditTransformer(cst.CSTTransformer):
    """Transformer to edit specific code."""

    def __init__(
        self,
        target_function: Optional[str] = None,
        target_class: Optional[str] = None,
        target_line: Optional[int] = None,
        old_content: Optional[str] = None,
        new_content: Optional[str] = None,
    ):
        super().__init__()
        self.target_function = target_function
        self.target_class = target_class
        self.target_line = target_line
        self.old_content = old_content
        self.new_content = new_content
        self.modified = False
        self.lines_changed = []

    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        """Edit matching function."""
        if self.target_function and original_node.name.value == self.target_function:
            self.modified = True
            self.lines_changed.extend(
                range(original_node.start_position[0] + 1, original_node.end_position[0] + 1)
            )

            if self.new_content:
                # Replace function body
                new_body = cst.IndentedBlock(body=[cst.parse_statement(self.new_content)])
                return updated_node.with_changes(body=new_body)

        return updated_node

    def leave_ClassDef(
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        """Edit matching class."""
        if self.target_class and original_node.name.value == self.target_class:
            self.modified = True
            self.lines_changed.extend(
                range(original_node.start_position[0] + 1, original_node.end_position[0] + 1)
            )

            if self.new_content:
                # Replace class body
                new_body = cst.IndentedBlock(body=[cst.parse_statement(self.new_content)])
                return updated_node.with_changes(body=new_body)

        return updated_node


class DeleteTransformer(cst.CSTTransformer):
    """Transformer to delete code."""

    def __init__(
        self,
        target_function: Optional[str] = None,
        target_class: Optional[str] = None,
        target_line: Optional[int] = None,
    ):
        super().__init__()
        self.target_function = target_function
        self.target_class = target_class
        self.target_line = target_line
        self.modified = False
        self.lines_changed = []

    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.CSTTransformer:
        """Delete matching function."""
        if self.target_function and original_node.name.value == self.target_function:
            self.modified = True
            self.lines_changed.extend(
                range(original_node.start_position[0] + 1, original_node.end_position[0] + 1)
            )
            # Return None to delete
            return cst.RemoveFromParent

        return updated_node

    def leave_ClassDef(
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.CSTTransformer:
        """Delete matching class."""
        if self.target_class and original_node.name.value == self.target_class:
            self.modified = True
            self.lines_changed.extend(
                range(original_node.start_position[0] + 1, original_node.end_position[0] + 1)
            )
            # Return None to delete
            return cst.RemoveFromParent

        return updated_node


class InsertTransformer(cst.CSTTransformer):
    """Transformer to insert code."""

    def __init__(
        self,
        target_function: Optional[str] = None,
        target_class: Optional[str] = None,
        insert_position: str = "start",  # "start" or "end"
        content: Optional[str] = None,
    ):
        super().__init__()
        self.target_function = target_function
        self.target_class = target_class
        self.insert_position = insert_position
        self.content = content
        self.modified = False
        self.lines_changed = []

    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        """Insert code into matching function."""
        if self.target_function and original_node.name.value == self.target_function:
            self.modified = True
            self.lines_changed.append(original_node.start_position[0] + 1)

            if self.content:
                # Parse the content
                new_statements = cst.parse_module(self.content).body

                # Get existing body
                body = updated_node.body

                if self.insert_position == "start":
                    new_body = cst.IndentedBlock(body=new_statements + list(body.body))
                else:  # end
                    new_body = cst.IndentedBlock(body=list(body.body) + new_statements)

                return updated_node.with_changes(body=new_body)

        return updated_node

    def leave_ClassDef(
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        """Insert code into matching class."""
        if self.target_class and original_node.name.value == self.target_class:
            self.modified = True
            self.lines_changed.append(original_node.start_position[0] + 1)

            if self.content:
                # Parse the content
                new_statements = cst.parse_module(self.content).body

                # Get existing body
                body = updated_node.body

                if self.insert_position == "start":
                    new_body = cst.IndentedBlock(body=new_statements + list(body.body))
                else:  # end
                    new_body = cst.IndentedBlock(body=list(body.body) + new_statements)

                return updated_node.with_changes(body=new_body)

        return updated_node


class CodeEditor:
    """Lightweight code editor with write, edit, and delete capabilities."""

    def __init__(self):
        self.edit_history: List[EditResult] = []
        self._lock = asyncio.Lock()

    async def write_file(self, file_path: str, content: str) -> EditResult:
        """Write new content to a file."""
        path = Path(file_path)

        # Read original content if exists
        original_content = ""
        if path.exists():
            original_content = path.read_text(encoding="utf-8")

        try:
            # Write new content
            path.write_text(content, encoding="utf-8")

            # Validate syntax
            is_valid = await self.validate_syntax(content)
            if not is_valid:
                # Restore original
                if original_content:
                    path.write_text(original_content, encoding="utf-8")
                return EditResult(
                    success=False,
                    operation=EditOperation.WRITE,
                    modified_file=file_path,
                    original_content=original_content,
                    modified_content=content,
                    changes=[],
                    lines_changed=[],
                    error="Invalid syntax in written code",
                )

            # Create result
            result = EditResult(
                success=True,
                operation=EditOperation.WRITE,
                modified_file=file_path,
                original_content=original_content,
                modified_content=content,
                changes=[f"Wrote new content to {file_path}"],
                lines_changed=list(range(1, len(content.split("\n")) + 1)),
            )

            # Store in history
            async with self._lock:
                self.edit_history.append(result)

            return result

        except Exception as e:
            return EditResult(
                success=False,
                operation=EditOperation.WRITE,
                modified_file=file_path,
                original_content=original_content,
                modified_content=content,
                changes=[],
                lines_changed=[],
                error=str(e),
            )

    async def edit_code(self, intent: EditIntent) -> EditResult:
        """Edit code based on intent."""
        file_path = Path(intent.target_file)

        if not file_path.exists():
            return EditResult(
                success=False,
                operation=intent.operation,
                modified_file=intent.target_file,
                original_content="",
                modified_content="",
                changes=[],
                lines_changed=[],
                error=f"File not found: {intent.target_file}",
            )

        # Read original content
        original_content = file_path.read_text(encoding="utf-8")

        try:
            # Parse the file
            module = cst.parse_module(original_content)

            # Select appropriate transformer
            transformer = self._get_transformer(intent)

            if transformer is None:
                return EditResult(
                    success=False,
                    operation=intent.operation,
                    modified_file=intent.target_file,
                    original_content=original_content,
                    modified_content=original_content,
                    changes=[],
                    lines_changed=[],
                    error=f"Unsupported edit operation: {intent.operation}",
                )

            # Apply transformation
            modified_module = module.visit(transformer)
            modified_content = modified_module.code

            # Check if anything was modified
            if not getattr(transformer, "modified", False):
                return EditResult(
                    success=False,
                    operation=intent.operation,
                    modified_file=intent.target_file,
                    original_content=original_content,
                    modified_content=original_content,
                    changes=[],
                    lines_changed=[],
                    error="No matching target found for edit",
                )

            # Write modified content
            file_path.write_text(modified_content, encoding="utf-8")

            # Create result
            result = EditResult(
                success=True,
                operation=intent.operation,
                modified_file=intent.target_file,
                original_content=original_content,
                modified_content=modified_content,
                changes=[f"Applied {intent.operation.value} to {intent.target_file}"],
                lines_changed=getattr(transformer, "lines_changed", []),
            )

            # Store in history
            async with self._lock:
                self.edit_history.append(result)

            return result

        except Exception as e:
            return EditResult(
                success=False,
                operation=intent.operation,
                modified_file=intent.target_file,
                original_content=original_content,
                modified_content=original_content,
                changes=[],
                lines_changed=[],
                error=str(e),
            )

    def _get_transformer(self, intent: EditIntent) -> Optional[cst.CSTTransformer]:
        """Get the appropriate transformer for the intent."""
        if intent.operation == EditOperation.WRITE:
            return WriteTransformer(new_code=intent.content or "")

        elif intent.operation == EditOperation.EDIT:
            return EditTransformer(
                target_function=intent.target_function,
                target_class=intent.target_class,
                target_line=intent.target_line,
                old_content=intent.old_content,
                new_content=intent.new_content,
            )

        elif intent.operation == EditOperation.DELETE:
            return DeleteTransformer(
                target_function=intent.target_function,
                target_class=intent.target_class,
                target_line=intent.target_line,
            )

        elif intent.operation == EditOperation.INSERT:
            return InsertTransformer(
                target_function=intent.target_function,
                target_class=intent.target_class,
                insert_position=intent.parameters.get("position", "start"),
                content=intent.content,
            )

        elif intent.operation == EditOperation.REPLACE:
            return EditTransformer(
                target_function=intent.target_function,
                target_class=intent.target_class,
                target_line=intent.target_line,
                old_content=intent.old_content,
                new_content=intent.new_content,
            )

        return None

    async def delete_code(self, intent: EditIntent) -> EditResult:
        """Delete code based on intent."""
        intent.operation = EditOperation.DELETE
        return await self.edit_code(intent)

    async def insert_code(self, intent: EditIntent) -> EditResult:
        """Insert code based on intent."""
        intent.operation = EditOperation.INSERT
        return await self.edit_code(intent)

    async def replace_code(self, intent: EditIntent) -> EditResult:
        """Replace code based on intent."""
        intent.operation = EditOperation.REPLACE
        return await self.edit_code(intent)

    async def validate_syntax(self, code: str) -> bool:
        """Validate that code has valid syntax."""
        try:
            cst.parse_module(code)
            return True
        except Exception:
            return False

    async def get_diff(self, original: str, modified: str) -> str:
        """Get a simple diff between original and modified code."""
        import difflib

        diff = difflib.unified_diff(
            original.splitlines(keepends=True),
            modified.splitlines(keepends=True),
            fromfile="original",
            tofile="modified",
        )

        return "".join(diff)

    async def get_edit_history(self) -> List[EditResult]:
        """Get edit history."""
        async with self._lock:
            return self.edit_history.copy()

    async def clear_history(self) -> None:
        """Clear edit history."""
        async with self._lock:
            self.edit_history.clear()

    async def create_edit_intent(self, operation: str, target_file: str, **kwargs) -> EditIntent:
        """Create an edit intent from parameters."""
        try:
            operation_enum = EditOperation(operation)
        except ValueError:
            raise ValueError(f"Invalid edit operation: {operation}")

        return EditIntent(
            operation=operation_enum,
            target_file=target_file,
            target_function=kwargs.get("target_function"),
            target_class=kwargs.get("target_class"),
            target_line=kwargs.get("target_line"),
            content=kwargs.get("content"),
            old_content=kwargs.get("old_content"),
            new_content=kwargs.get("new_content"),
            parameters=kwargs,
        )

    async def undo_last_edit(self) -> Optional[EditResult]:
        """Undo the last edit."""
        async with self._lock:
            if not self.edit_history:
                return None

            last_result = self.edit_history.pop()

            # Restore original content
            if last_result.success:
                Path(last_result.modified_file).write_text(
                    last_result.original_content, encoding="utf-8"
                )

            return last_result
