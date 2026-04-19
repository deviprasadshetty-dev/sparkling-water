"""AST Transformation Engine for surgical code modifications."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from enum import Enum
import libcst as cst
from libcst import matchers as m
from pathlib import Path
import asyncio


class TransformationAction(Enum):
    """Types of AST transformations."""

    ADD_ARGUMENT = "add_argument"
    REMOVE_ARGUMENT = "remove_argument"
    MODIFY_ARGUMENT = "modify_argument"
    ADD_FUNCTION = "add_function"
    REMOVE_FUNCTION = "remove_function"
    MODIFY_FUNCTION = "modify_function"
    ADD_CLASS = "add_class"
    REMOVE_CLASS = "remove_class"
    ADD_IMPORT = "add_import"
    REMOVE_IMPORT = "remove_import"
    MODIFY_STATEMENT = "modify_statement"
    INSERT_LOGIC = "insert_logic"
    REPLACE_LOGIC = "replace_logic"
    WRAP_IN_TRY_EXCEPT = "wrap_in_try_except"
    ADD_DECORATOR = "add_decorator"
    REMOVE_DECORATOR = "remove_decorator"


@dataclass
class TransformationIntent:
    """Represents a transformation intent."""

    action: TransformationAction
    target_file: str
    target_function: Optional[str] = None
    target_class: Optional[str] = None
    target_line: Optional[int] = None
    parameters: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "action": self.action.value,
            "target_file": self.target_file,
            "target_function": self.target_function,
            "target_class": self.target_class,
            "target_line": self.target_line,
            "parameters": self.parameters,
        }


@dataclass
class TransformationResult:
    """Result of a transformation."""

    success: bool
    modified_file: str
    original_content: str
    modified_content: str
    changes: List[str]
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "modified_file": self.modified_file,
            "original_content": self.original_content,
            "modified_content": self.modified_content,
            "changes": self.changes,
            "error": self.error,
        }


class AddArgumentTransformer(cst.CSTTransformer):
    """Transformer to add an argument to a function."""

    def __init__(self, function_name: str, argument_name: str, default_value: Optional[str] = None):
        super().__init__()
        self.function_name = function_name
        self.argument_name = argument_name
        self.default_value = default_value
        self.modified = False

    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        """Add argument to matching function."""
        if original_node.name.value == self.function_name:
            self.modified = True

            # Create new parameter
            new_param = cst.Param(
                name=cst.Name(value=self.argument_name),
                default=cst.parse_expression(self.default_value) if self.default_value else None,
            )

            # Add to parameters
            new_params = list(updated_node.params.params) + [new_param]

            return updated_node.with_changes(
                params=updated_node.params.with_changes(
                    params=new_params,
                )
            )

        return updated_node


class RemoveArgumentTransformer(cst.CSTTransformer):
    """Transformer to remove an argument from a function."""

    def __init__(self, function_name: str, argument_name: str):
        super().__init__()
        self.function_name = function_name
        self.argument_name = argument_name
        self.modified = False

    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        """Remove argument from matching function."""
        if original_node.name.value == self.function_name:
            self.modified = True

            # Remove the parameter
            new_params = [
                p for p in updated_node.params.params if p.name.value != self.argument_name
            ]

            return updated_node.with_changes(
                params=updated_node.params.with_changes(
                    params=new_params,
                )
            )

        return updated_node


class InsertLogicTransformer(cst.CSTTransformer):
    """Transformer to insert logic into a function."""

    def __init__(self, function_name: str, logic_code: str, position: str = "start"):
        super().__init__()
        self.function_name = function_name
        self.logic_code = logic_code
        self.position = position
        self.modified = False

    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        """Insert logic into matching function."""
        if original_node.name.value == self.function_name:
            self.modified = True

            # Parse the logic code
            logic_statements = cst.parse_module(self.logic_code).body

            # Get existing body
            body = updated_node.body

            if self.position == "start":
                new_body = cst.IndentedBlock(body=logic_statements + list(body.body))
            else:  # end
                new_body = cst.IndentedBlock(body=list(body.body) + logic_statements)

            return updated_node.with_changes(body=new_body)

        return updated_node


class WrapInTryExceptTransformer(cst.CSTTransformer):
    """Transformer to wrap function body in try-except."""

    def __init__(self, function_name: str, exception_type: str = "Exception"):
        super().__init__()
        self.function_name = function_name
        self.exception_type = exception_type
        self.modified = False

    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        """Wrap function body in try-except."""
        if original_node.name.value == self.function_name:
            self.modified = True

            # Create try-except block
            try_body = cst.Try(
                body=cst.IndentedBlock(body=list(updated_node.body.body)),
                handlers=[
                    cst.ExceptHandler(
                        type=cst.Name(value=self.exception_type),
                        body=cst.IndentedBlock(
                            body=[
                                cst.SimpleStatementLine(
                                    body=[
                                        cst.Raise(),
                                    ]
                                )
                            ]
                        ),
                    )
                ],
            )

            new_body = cst.IndentedBlock(body=[try_body])

            return updated_node.with_changes(body=new_body)

        return updated_node


class AddImportTransformer(cst.CSTTransformer):
    """Transformer to add an import statement."""

    def __init__(self, import_statement: str):
        super().__init__()
        self.import_statement = import_statement
        self.modified = False
        self.import_added = False

    def leave_Module(self, original_node: cst.Module, updated_node: cst.Module) -> cst.Module:
        """Add import to module."""
        if not self.import_added:
            self.import_added = True
            self.modified = True

            # Parse the import statement
            import_node = cst.parse_statement(self.import_statement)

            # Add to the beginning of the module
            new_body = [import_node] + list(updated_node.body)

            return updated_node.with_changes(body=new_body)

        return updated_node


class ASTTransformationEngine:
    """Engine for applying AST transformations."""

    def __init__(self):
        self.transformations: List[TransformationResult] = []
        self._lock = asyncio.Lock()

    async def apply_transformation(self, intent: TransformationIntent) -> TransformationResult:
        """Apply a transformation intent to a file."""
        file_path = Path(intent.target_file)

        if not file_path.exists():
            return TransformationResult(
                success=False,
                modified_file=intent.target_file,
                original_content="",
                modified_content="",
                changes=[],
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
                return TransformationResult(
                    success=False,
                    modified_file=intent.target_file,
                    original_content=original_content,
                    modified_content=original_content,
                    changes=[],
                    error=f"Unsupported transformation action: {intent.action}",
                )

            # Apply transformation
            modified_module = module.visit(transformer)
            modified_content = modified_module.code

            # Check if anything was modified
            if not getattr(transformer, "modified", False):
                return TransformationResult(
                    success=False,
                    modified_file=intent.target_file,
                    original_content=original_content,
                    modified_content=original_content,
                    changes=[],
                    error="No matching target found for transformation",
                )

            # Write modified content
            file_path.write_text(modified_content, encoding="utf-8")

            # Create result
            result = TransformationResult(
                success=True,
                modified_file=intent.target_file,
                original_content=original_content,
                modified_content=modified_content,
                changes=[f"Applied {intent.action.value} to {intent.target_file}"],
            )

            # Store in history
            async with self._lock:
                self.transformations.append(result)

            return result

        except Exception as e:
            return TransformationResult(
                success=False,
                modified_file=intent.target_file,
                original_content=original_content,
                modified_content=original_content,
                changes=[],
                error=str(e),
            )

    def _get_transformer(self, intent: TransformationIntent) -> Optional[cst.CSTTransformer]:
        """Get the appropriate transformer for the intent."""
        if intent.action == TransformationAction.ADD_ARGUMENT:
            return AddArgumentTransformer(
                function_name=intent.target_function,
                argument_name=intent.parameters.get("argument_name"),
                default_value=intent.parameters.get("default_value"),
            )

        elif intent.action == TransformationAction.REMOVE_ARGUMENT:
            return RemoveArgumentTransformer(
                function_name=intent.target_function,
                argument_name=intent.parameters.get("argument_name"),
            )

        elif intent.action == TransformationAction.INSERT_LOGIC:
            return InsertLogicTransformer(
                function_name=intent.target_function,
                logic_code=intent.parameters.get("logic_code"),
                position=intent.parameters.get("position", "start"),
            )

        elif intent.action == TransformationAction.WRAP_IN_TRY_EXCEPT:
            return WrapInTryExceptTransformer(
                function_name=intent.target_function,
                exception_type=intent.parameters.get("exception_type", "Exception"),
            )

        elif intent.action == TransformationAction.ADD_IMPORT:
            return AddImportTransformer(
                import_statement=intent.parameters.get("import_statement"),
            )

        return None

    async def apply_multiple_transformations(
        self, intents: List[TransformationIntent]
    ) -> List[TransformationResult]:
        """Apply multiple transformations in sequence."""
        results = []

        for intent in intents:
            result = await self.apply_transformation(intent)
            results.append(result)

            if not result.success:
                # Stop on first failure
                break

        return results

    async def get_transformation_history(self) -> List[TransformationResult]:
        """Get transformation history."""
        async with self._lock:
            return self.transformations.copy()

    async def clear_history(self) -> None:
        """Clear transformation history."""
        async with self._lock:
            self.transformations.clear()

    async def create_transformation_intent(
        self, action: str, target_file: str, **kwargs
    ) -> TransformationIntent:
        """Create a transformation intent from parameters."""
        try:
            action_enum = TransformationAction(action)
        except ValueError:
            raise ValueError(f"Invalid transformation action: {action}")

        return TransformationIntent(
            action=action_enum,
            target_file=target_file,
            target_function=kwargs.get("target_function"),
            target_class=kwargs.get("target_class"),
            target_line=kwargs.get("target_line"),
            parameters=kwargs,
        )

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
