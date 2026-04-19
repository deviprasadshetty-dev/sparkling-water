"""Knowledge Graph and AST Engine for structural code representation."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from pathlib import Path
import networkx as nx
from tree_sitter import Language, Parser, Node
import tree_sitter_python, tree_sitter_javascript, tree_sitter_typescript
import sqlite3
import asyncio
import aiosqlite
from datetime import datetime


@dataclass
class CodeNode:
    """Represents a code entity in the knowledge graph."""

    id: str
    type: str  # function, class, variable, import, etc.
    name: str
    file_path: str
    line_start: int
    line_end: int
    docstring: Optional[str] = None
    signature: Optional[str] = None
    metadata: Dict[str, any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "type": self.type,
            "name": self.name,
            "file_path": self.file_path,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "docstring": self.docstring,
            "signature": self.signature,
            "metadata": self.metadata,
        }


class EdgeType:
    """Types of relationships in the code graph."""

    CALLS = "calls"
    IMPORTS = "imports"
    DEFINES = "defines"
    IMPLEMENTS = "implements"
    INHERITS = "inherits"
    REFERENCES = "references"
    CONTAINS = "contains"


@dataclass
class CodeEdge:
    """Represents a relationship between code nodes."""

    source_id: str
    target_id: str
    edge_type: str
    metadata: Dict[str, any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, any]:
        """Convert to dictionary."""
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "edge_type": self.edge_type,
            "metadata": self.metadata,
        }


class ASTParser:
    """AST Parser using Tree-sitter for multiple languages."""

    def __init__(self):
        self.parsers: Dict[str, Parser] = {}
        self.languages: Dict[str, Language] = {}
        self._init_parsers()

    def _init_parsers(self):
        """Initialize parsers for supported languages."""
        # Python
        py_lang = Language(tree_sitter_python.language())
        py_parser = Parser(py_lang)
        self.parsers["python"] = py_parser
        self.languages["python"] = py_lang

        # JavaScript
        js_lang = Language(tree_sitter_javascript.language())
        js_parser = Parser(js_lang)
        self.parsers["javascript"] = js_parser
        self.languages["javascript"] = js_lang

        # TypeScript
        ts_lang = Language(tree_sitter_typescript.language_typescript())
        ts_parser = Parser(ts_lang)
        self.parsers["typescript"] = ts_parser
        self.languages["typescript"] = ts_lang

    def get_language(self, file_path: str) -> Optional[str]:
        """Detect language from file extension."""
        ext = Path(file_path).suffix.lower()
        mapping = {
            ".py": "python",
            ".js": "javascript",
            ".jsx": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
        }
        return mapping.get(ext)

    def parse_file(self, file_path: str, content: str) -> Optional[Node]:
        """Parse a file and return the AST root node."""
        language = self.get_language(file_path)
        if not language or language not in self.parsers:
            return None

        parser = self.parsers[language]
        tree = parser.parse(bytes(content, "utf8"))
        return tree.root_node

    def extract_functions(self, node: Node, file_path: str) -> List[CodeNode]:
        """Extract function definitions from AST."""
        functions = []

        def traverse(n: Node):
            if n.type == "function_definition":
                name_node = n.child_by_field_name("name")
                if name_node:
                    func_name = name_node.text.decode("utf8")
                    func_id = f"{file_path}:{func_name}:{n.start_point[0]}"

                    # Extract docstring
                    docstring = None
                    body = n.child_by_field_name("body")
                    if body and body.child_count > 0:
                        first_child = body.child(0)
                        if first_child.type == "expression_statement":
                            string_node = first_child.child(0)
                            if string_node and string_node.type in ["string", "string_content"]:
                                docstring = string_node.text.decode("utf8").strip("\"'")

                    functions.append(
                        CodeNode(
                            id=func_id,
                            type="function",
                            name=func_name,
                            file_path=file_path,
                            line_start=n.start_point[0] + 1,
                            line_end=n.end_point[0] + 1,
                            docstring=docstring,
                            signature=n.text.decode("utf8"),
                        )
                    )

            for child in n.children:
                traverse(child)

        traverse(node)
        return functions

    def extract_classes(self, node: Node, file_path: str) -> List[CodeNode]:
        """Extract class definitions from AST."""
        classes = []

        def traverse(n: Node):
            if n.type == "class_definition":
                name_node = n.child_by_field_name("name")
                if name_node:
                    class_name = name_node.text.decode("utf8")
                    class_id = f"{file_path}:{class_name}:{n.start_point[0]}"

                    classes.append(
                        CodeNode(
                            id=class_id,
                            type="class",
                            name=class_name,
                            file_path=file_path,
                            line_start=n.start_point[0] + 1,
                            line_end=n.end_point[0] + 1,
                            signature=n.text.decode("utf8"),
                        )
                    )

            for child in n.children:
                traverse(child)

        traverse(node)
        return classes

    def extract_imports(self, node: Node, file_path: str) -> List[CodeNode]:
        """Extract import statements from AST."""
        imports = []

        def traverse(n: Node):
            if n.type in ["import_statement", "import_from_statement"]:
                import_text = n.text.decode("utf8")
                import_id = f"{file_path}:import:{n.start_point[0]}"

                imports.append(
                    CodeNode(
                        id=import_id,
                        type="import",
                        name=import_text.strip(),
                        file_path=file_path,
                        line_start=n.start_point[0] + 1,
                        line_end=n.end_point[0] + 1,
                        signature=import_text,
                    )
                )

            for child in n.children:
                traverse(child)

        traverse(node)
        return imports

    def extract_calls(self, node: Node, file_path: str) -> List[Tuple[str, str]]:
        """Extract function calls from AST."""
        calls = []

        def traverse(n: Node):
            if n.type == "call":
                func_node = n.child_by_field_name("function")
                if func_node:
                    func_name = func_node.text.decode("utf8")
                    caller_id = f"{file_path}:{func_name}:{n.start_point[0]}"
                    calls.append((caller_id, func_name))

            for child in n.children:
                traverse(child)

        traverse(node)
        return calls


class KnowledgeGraph:
    """Knowledge graph for structural code representation."""

    def __init__(self, db_path: str = ":memory:"):
        self.graph = nx.DiGraph()
        self.db_path = db_path
        self.parser = ASTParser()
        self._lock = asyncio.Lock()

    async def initialize(self):
        """Initialize the knowledge graph database."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS nodes (
                    id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    name TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    line_start INTEGER NOT NULL,
                    line_end INTEGER NOT NULL,
                    docstring TEXT,
                    signature TEXT,
                    metadata TEXT
                )
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS edges (
                    source_id TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    edge_type TEXT NOT NULL,
                    metadata TEXT,
                    PRIMARY KEY (source_id, target_id, edge_type)
                )
            """)

            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_nodes_type ON nodes(type)
            """)

            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_nodes_file ON nodes(file_path)
            """)

            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source_id)
            """)

            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target_id)
            """)

            await db.commit()

    async def index_file(self, file_path: str, content: str) -> int:
        """Index a file and add to knowledge graph."""
        node = self.parser.parse_file(file_path, content)
        if not node:
            return 0

        # Extract code entities
        functions = self.parser.extract_functions(node, file_path)
        classes = self.parser.extract_classes(node, file_path)
        imports = self.parser.extract_imports(node, file_path)
        calls = self.parser.extract_calls(node, file_path)

        # Add nodes to graph
        all_nodes = functions + classes + imports
        for code_node in all_nodes:
            self.graph.add_node(code_node.id, **code_node.to_dict())

        # Add edges
        for caller_id, func_name in calls:
            # Find the function node that contains this call
            for func in functions:
                if func.line_start <= int(caller_id.split(":")[-1]) <= func.line_end:
                    # Find the target function
                    for target_func in functions:
                        if target_func.name == func_name:
                            self.graph.add_edge(
                                func.id,
                                target_func.id,
                                edge_type=EdgeType.CALLS,
                            )
                            break

        # Store in database
        async with aiosqlite.connect(self.db_path) as db:
            for code_node in all_nodes:
                await db.execute(
                    """
                    INSERT OR REPLACE INTO nodes 
                    (id, type, name, file_path, line_start, line_end, docstring, signature, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        code_node.id,
                        code_node.type,
                        code_node.name,
                        code_node.file_path,
                        code_node.line_start,
                        code_node.line_end,
                        code_node.docstring,
                        code_node.signature,
                        str(code_node.metadata),
                    ),
                )

            # Store edges
            for source, target, data in self.graph.edges(data=True):
                await db.execute(
                    """
                    INSERT OR REPLACE INTO edges (source_id, target_id, edge_type, metadata)
                    VALUES (?, ?, ?, ?)
                    """,
                    (source, target, data.get("edge_type", ""), str(data)),
                )

            await db.commit()

        return len(all_nodes)

    async def query_nodes(
        self,
        node_type: Optional[str] = None,
        file_path: Optional[str] = None,
        name_pattern: Optional[str] = None,
    ) -> List[CodeNode]:
        """Query nodes from the knowledge graph."""
        async with aiosqlite.connect(self.db_path) as db:
            query = "SELECT * FROM nodes WHERE 1=1"
            params = []

            if node_type:
                query += " AND type = ?"
                params.append(node_type)

            if file_path:
                query += " AND file_path = ?"
                params.append(file_path)

            if name_pattern:
                query += " AND name LIKE ?"
                params.append(f"%{name_pattern}%")

            cursor = await db.execute(query, params)
            rows = await cursor.fetchall()

            nodes = []
            for row in rows:
                nodes.append(
                    CodeNode(
                        id=row[0],
                        type=row[1],
                        name=row[2],
                        file_path=row[3],
                        line_start=row[4],
                        line_end=row[5],
                        docstring=row[6],
                        signature=row[7],
                        metadata=eval(row[8]) if row[8] else {},
                    )
                )

            return nodes

    async def get_call_graph(self, function_id: str, depth: int = 2) -> Dict[str, List[str]]:
        """Get call graph for a function."""
        result = {function_id: []}
        visited = set()

        def traverse(node_id: str, current_depth: int):
            if current_depth > depth or node_id in visited:
                return

            visited.add(node_id)

            for _, target, data in self.graph.out_edges(node_id, data=True):
                if data.get("edge_type") == EdgeType.CALLS:
                    if node_id not in result:
                        result[node_id] = []
                    result[node_id].append(target)
                    traverse(target, current_depth + 1)

        traverse(function_id, 0)
        return result

    async def bfs_traversal(self, start_node: str, edge_type: str) -> List[str]:
        """Breadth-first search traversal."""
        visited = set()
        queue = [start_node]
        result = []

        while queue:
            node = queue.pop(0)
            if node in visited:
                continue

            visited.add(node)
            result.append(node)

            for _, target, data in self.graph.out_edges(node, data=True):
                if data.get("edge_type") == edge_type and target not in visited:
                    queue.append(target)

        return result

    async def get_stats(self) -> Dict[str, int]:
        """Get knowledge graph statistics."""
        async with aiosqlite.connect(self.db_path) as db:
            node_count = await db.execute("SELECT COUNT(*) FROM nodes")
            node_count = (await node_count.fetchone())[0]

            edge_count = await db.execute("SELECT COUNT(*) FROM edges")
            edge_count = (await edge_count.fetchone())[0]

            file_count = await db.execute("SELECT COUNT(DISTINCT file_path) FROM nodes")
            file_count = (await file_count.fetchone())[0]

            return {
                "nodes": node_count,
                "edges": edge_count,
                "files": file_count,
            }
