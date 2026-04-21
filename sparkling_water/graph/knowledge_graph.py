"""Knowledge Graph and AST Engine for structural code representation."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Any
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
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
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
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
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
        try:
            py_lang = Language(tree_sitter_python.language())
            py_parser = Parser(py_lang)
            self.parsers["python"] = py_parser
            self.languages["python"] = py_lang
        except: pass

        # JavaScript
        try:
            js_lang = Language(tree_sitter_javascript.language())
            js_parser = Parser(js_lang)
            self.parsers["javascript"] = js_parser
            self.languages["javascript"] = js_lang
        except: pass

        # TypeScript
        try:
            ts_lang = Language(tree_sitter_typescript.language_typescript())
            ts_parser = Parser(ts_lang)
            self.parsers["typescript"] = ts_parser
            self.languages["typescript"] = ts_lang
        except: pass

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

    def extract_functions(self, node: Node, file_path: str, lang: str) -> List[CodeNode]:
        """Extract function definitions from AST."""
        functions = []

        def traverse(n: Node):
            # Python or JS/TS function types
            is_func = False
            if lang == "python" and n.type == "function_definition":
                is_func = True
            elif lang in ["javascript", "typescript"] and n.type in ["function_declaration", "method_definition", "arrow_function"]:
                is_func = True

            if is_func:
                name_node = n.child_by_field_name("name")
                # Handle cases where name might be different (e.g. arrow functions in JS)
                func_name = "anonymous"
                if name_node:
                    func_name = name_node.text.decode("utf8")

                func_id = f"{file_path}:{func_name}:{n.start_point[0]}"

                functions.append(
                    CodeNode(
                        id=func_id,
                        type="function",
                        name=func_name,
                        file_path=file_path,
                        line_start=n.start_point[0] + 1,
                        line_end=n.end_point[0] + 1,
                        signature=n.text.decode("utf8").split('\n')[0],
                    )
                )

            for child in n.children:
                traverse(child)

        traverse(node)
        return functions

    def extract_classes(self, node: Node, file_path: str, lang: str) -> List[CodeNode]:
        """Extract class definitions from AST."""
        classes = []

        def traverse(n: Node):
            is_class = False
            if lang == "python" and n.type == "class_definition":
                is_class = True
            elif lang in ["javascript", "typescript"] and n.type == "class_declaration":
                is_class = True

            if is_class:
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
                            signature=n.text.decode("utf8").split('\n')[0],
                        )
                    )

            for child in n.children:
                traverse(child)

        traverse(node)
        return classes

    def extract_imports(self, node: Node, file_path: str, lang: str) -> List[CodeNode]:
        """Extract import statements from AST."""
        imports = []

        def traverse(n: Node):
            is_import = False
            if lang == "python" and n.type in ["import_statement", "import_from_statement"]:
                is_import = True
            elif lang in ["javascript", "typescript"] and n.type == "import_statement":
                is_import = True

            if is_import:
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


class KnowledgeGraph:
    """Knowledge graph for structural code representation."""

    def __init__(self, db_path: str = ":memory:"):
        self.graph = nx.DiGraph()
        self.db_path = db_path
        self.parser = ASTParser()
        self._lock = asyncio.Lock()
        self._db: Optional[aiosqlite.Connection] = None

    async def _get_db(self) -> aiosqlite.Connection:
        if self._db is None:
            self._db = await aiosqlite.connect(self.db_path)
            await self._db.execute("PRAGMA synchronous = OFF")
            await self._db.execute("PRAGMA journal_mode = MEMORY")
        return self._db

    async def close(self):
        if self._db:
            await self._db.close()
            self._db = None

    async def initialize(self):
        db = await self._get_db()
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
        await db.execute("CREATE INDEX IF NOT EXISTS idx_nodes_type ON nodes(type)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_nodes_file ON nodes(file_path)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_nodes_name ON nodes(name)")
        await db.commit()

    async def index_file(self, file_path: str, content: str) -> int:
        node = self.parser.parse_file(file_path, content)
        if not node: return 0

        lang = self.parser.get_language(file_path)
        functions = self.parser.extract_functions(node, file_path, lang)
        classes = self.parser.extract_classes(node, file_path, lang)
        imports = self.parser.extract_imports(node, file_path, lang)

        all_nodes = functions + classes + imports
        db = await self._get_db()
        async with self._lock:
            await db.execute("BEGIN TRANSACTION")
            for code_node in all_nodes:
                await db.execute(
                    "INSERT OR REPLACE INTO nodes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (code_node.id, code_node.type, code_node.name, code_node.file_path,
                     code_node.line_start, code_node.line_end, code_node.docstring,
                     code_node.signature, str(code_node.metadata))
                )
            await db.commit()
        return len(all_nodes)

    async def query_nodes(self, node_type: Optional[str] = None, file_path: Optional[str] = None, name_pattern: Optional[str] = None) -> List[CodeNode]:
        db = await self._get_db()
        query = "SELECT * FROM nodes WHERE 1=1"
        params = []
        if node_type: query += " AND type = ?"; params.append(node_type)
        if file_path: query += " AND file_path = ?"; params.append(file_path)
        if name_pattern: query += " AND name LIKE ?"; params.append(f"%{name_pattern}%")

        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()
        return [CodeNode(id=r[0], type=r[1], name=r[2], file_path=r[3], line_start=r[4], line_end=r[5], docstring=r[6], signature=r[7], metadata=eval(r[8]) if r[8] else {}) for r in rows]

    async def get_stats(self) -> Dict[str, int]:
        db = await self._get_db()
        async with db.execute("SELECT COUNT(*) FROM nodes") as c: n = (await c.fetchone())[0]
        async with db.execute("SELECT COUNT(DISTINCT file_path) FROM nodes") as c: f = (await c.fetchone())[0]
        return {"nodes": n, "files": f}
