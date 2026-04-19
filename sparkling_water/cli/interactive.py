"""Interactive CLI with modern chat interface like Claude Code."""

import asyncio
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
import json

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich.tree import Tree
from rich.live import Live
from rich.layout import Layout
from rich.align import Align
from rich.text import Text
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.styles import Style

from ..events.event_bus import EventBus, Event, EventType, Orchestrator
from ..graph.knowledge_graph import KnowledgeGraph
from ..vfs.virtual_filesystem import VirtualFileSystem
from ..router.slm_router import SLMRouter, Task
from ..core.ast_transformer import ASTTransformationEngine
from ..core.code_editor import CodeEditor, EditIntent, EditOperation
from ..providers import ProviderManager, ModelTier


class SparklingWaterCLI:
    """Modern interactive CLI like Claude Code."""

    def __init__(self, codebase_path: str = "."):
        self.console = Console()
        self.codebase_path = Path(codebase_path).resolve()
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Initialize components
        self.event_bus = EventBus()
        self.orchestrator = Orchestrator(self.event_bus)
        self.knowledge_graph = KnowledgeGraph(db_path=f".sparkling_water_{self.session_id}.db")
        self.vfs: Optional[VirtualFileSystem] = None
        self.router = SLMRouter()
        self.ast_engine = ASTTransformationEngine()
        self.code_editor = CodeEditor()
        self.provider_manager = ProviderManager()

        # State
        self.indexed = False
        self.chat_history: List[Dict[str, Any]] = []
        self.current_task: Optional[str] = None

        # Prompt session
        self.history_file = Path.home() / ".sparkling_water_history"
        self.prompt_session = PromptSession(
            history=FileHistory(str(self.history_file)),
            auto_suggest=AutoSuggestFromHistory(),
            enable_history_search=True,
        )

        # Key bindings
        self.key_bindings = KeyBindings()
        self._setup_key_bindings()

        # Style
        self.style = Style.from_dict(
            {
                "prompt": "cyan bold",
                "user": "green bold",
                "assistant": "blue bold",
                "system": "yellow bold",
                "error": "red bold",
                "success": "green bold",
            }
        )

    def _setup_key_bindings(self):
        """Setup custom key bindings."""

        @self.key_bindings.add("c-q")
        def _(event):
            """Quit the application."""
            event.app.exit()

        @self.key_bindings.add("c-l")
        def _(event):
            """Clear screen."""
            self.console.clear()

    def show_banner(self):
        """Display the beautiful banner."""
        banner = Text()
        banner.append("✨ ", style="bold yellow")
        banner.append("Sparkling Water", style="bold cyan")
        banner.append(" ✨\n\n", style="bold yellow")
        banner.append("Next-Generation AI Coding Assistant\n", style="bold")
        banner.append("─────────────────────────────────\n", style="dim")
        banner.append(f"Codebase: {self.codebase_path}\n", style="dim")
        banner.append(f"Session: {self.session_id}\n", style="dim")

        panel = Panel(
            banner,
            border_style="cyan",
            padding=(1, 2),
        )
        self.console.print(panel)
        self.console.print()

    def show_welcome(self):
        """Show welcome message."""
        welcome = """
[bold cyan]Welcome! I'm ready to help with your code.[/bold cyan]

I've analyzed your codebase and I'm ready to assist you with:
  • [green]Writing[/green] new code (functions, classes, files)
  • [yellow]Editing[/yellow] existing code with precision
  • [red]Deleting[/red] code you don't need
  • [blue]Finding[/blue] functions, classes, and dependencies
  • [magenta]Reading[/magenta] files efficiently
  • [cyan]Explaining[/cyan] how things work

[bold]Just tell me what you need![/bold] For example:
  • "Write a function called authenticate"
  • "Edit the payment function to add error handling"
  • "Delete the deprecated function"
  • "Find all authentication functions"
  • "Show me how the user service works"
  • "Where is the database used?"

[dim]Type your request and press Enter. I'll handle the rest![/dim]
"""
        self.console.print(Markdown(welcome))
        self.console.print()

    def show_status(self, message: str, status: str = "info", show_time: bool = True):
        """Show status message."""
        status_colors = {
            "info": "blue",
            "success": "green",
            "warning": "yellow",
            "error": "red",
            "thinking": "magenta",
        }
        color = status_colors.get(status, "white")

        if show_time:
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.console.print(
                f"[dim]{timestamp}[/dim] [{color}]{status.upper()}[/{color}] {message}"
            )
        else:
            self.console.print(f"[{color}]{status.upper()}[/{color}] {message}")

    def show_thinking(self, message: str):
        """Show thinking indicator."""
        self.show_status(message, "thinking")

    def show_code(self, code: str, language: str = "python", title: str = "Code"):
        """Display code with syntax highlighting."""
        syntax = Syntax(code, language, theme="monokai", line_numbers=True)
        panel = Panel(syntax, title=title, border_style="blue")
        self.console.print(panel)

    def show_markdown(self, text: str, title: str = None):
        """Display markdown content."""
        if title:
            panel = Panel(Markdown(text), title=title, border_style="cyan")
            self.console.print(panel)
        else:
            self.console.print(Markdown(text))

    def show_table(self, data: List[Dict[str, Any]], title: str = "Results"):
        """Display data in a table."""
        if not data:
            self.console.print("[yellow]No results found[/yellow]")
            return

        table = Table(title=title)

        # Add columns
        for key in data[0].keys():
            table.add_column(key, style="cyan")

        # Add rows
        for row in data:
            table.add_row(*[str(v) for v in row.values()])

        self.console.print(table)

    async def auto_index_codebase(self):
        """Automatically index the codebase on startup."""
        self.show_status("Analyzing your codebase...", "info")

        # Initialize knowledge graph
        await self.knowledge_graph.initialize()

        # Find all Python files
        python_files = list(self.codebase_path.rglob("*.py"))
        total_files = len(python_files)

        if total_files == 0:
            self.show_status("No Python files found in codebase", "warning")
            return

        self.show_status(f"Found {total_files} Python files - indexing...", "info")

        # Index files with progress
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=self.console,
        ) as progress:
            task = progress.add_task("Building knowledge graph...", total=total_files)

            total_nodes = 0
            for i, file_path in enumerate(python_files):
                try:
                    content = file_path.read_text(encoding="utf-8")
                    nodes = await self.knowledge_graph.index_file(str(file_path), content)
                    total_nodes += nodes
                    progress.update(task, advance=1)
                except Exception as e:
                    pass  # Skip files that can't be indexed

        # Initialize VFS
        self.vfs = VirtualFileSystem(
            knowledge_graph=self.knowledge_graph, root_path=self.codebase_path
        )

        # Get stats
        stats = await self.knowledge_graph.get_stats()
        functions = await self.knowledge_graph.query_nodes(node_type="function")
        classes = await self.knowledge_graph.query_nodes(node_type="class")

        self.indexed = True

        # Show results
        results = f"""
[bold green]✓ Codebase analyzed successfully![/bold green]

[bold]I found:[/bold]
  • {stats["files"]} Python files
  • {len(functions)} functions
  • {len(classes)} classes
  • {stats["nodes"]} total code entities

[bold]Ready to help![/bold] I can now:
  • Find any function or class instantly
  • Show you how code connects together
  • Read files with 99% token efficiency
  • Make precise code modifications

[dim]Just tell me what you need![/dim]
"""
        self.show_markdown(results, "Analysis Complete")

    async def find_functions(self, query: str):
        """Find functions matching the query."""
        self.show_thinking(f"Searching for functions matching '{query}'...")

        nodes = await self.knowledge_graph.query_nodes(node_type="function", name_pattern=query)

        if not nodes:
            self.show_status(f"No functions found matching '{query}'", "warning")
            return

        # Display results
        results = []
        for node in nodes:
            results.append(
                {
                    "Function": node.name,
                    "File": node.file_path,
                    "Lines": f"{node.line_start}-{node.line_end}",
                }
            )

        self.show_table(results, f"Functions matching '{query}'")
        self.show_status(f"Found {len(nodes)} functions", "success")

    async def find_classes(self, query: str):
        """Find classes matching the query."""
        self.show_thinking(f"Searching for classes matching '{query}'...")

        nodes = await self.knowledge_graph.query_nodes(node_type="class", name_pattern=query)

        if not nodes:
            self.show_status(f"No classes found matching '{query}'", "warning")
            return

        # Display results
        results = []
        for node in nodes:
            results.append(
                {
                    "Class": node.name,
                    "File": node.file_path,
                    "Lines": f"{node.line_start}-{node.line_end}",
                }
            )

        self.show_table(results, f"Classes matching '{query}'")
        self.show_status(f"Found {len(nodes)} classes", "success")

    async def show_file(self, file_path: str, expand: Optional[str] = None):
        """Show a file with progressive disclosure."""
        self.show_thinking(f"Reading file: {file_path}")

        try:
            # Read file
            if expand:
                content = await self.vfs.read_file(file_path, expand_function=expand)
            else:
                content = await self.vfs.read_file(file_path)

            # Get stats
            stats = await self.vfs.get_file_stats(file_path)

            # Display content
            self.show_code(content, "python", f"📄 {file_path}")

            # Show efficiency
            if stats["token_savings"] > 0:
                efficiency = stats["token_savings"] / (stats["size"] // 4) * 100
                self.show_status(
                    f"Token efficiency: {efficiency:.1f}% savings", "success", show_time=False
                )

        except FileNotFoundError:
            self.show_status(f"File not found: {file_path}", "error")
        except Exception as e:
            self.show_status(f"Error reading file: {e}", "error")

    async def explain_code(self, query: str):
        """Explain how code works."""
        self.show_thinking(f"Analyzing: {query}")

        # Try to find matching functions/classes
        functions = await self.knowledge_graph.query_nodes(node_type="function", name_pattern=query)

        classes = await self.knowledge_graph.query_nodes(node_type="class", name_pattern=query)

        if functions:
            func = functions[0]
            explanation = f"""
[bold cyan]Function: {func.name}[/bold cyan]

[bold]Location:[/bold] {func.file_path} (lines {func.line_start}-{func.line_end})

[bold]Purpose:[/bold]
{func.docstring or "No documentation available"}

[bold]Details:[/bold]
  • Type: Function
  • File: {Path(func.file_path).name}
  • Lines: {func.line_start} to {func.line_end}

[dim]Would you like me to show you the code or find related functions?[/dim]
"""
            self.show_markdown(explanation)

        elif classes:
            cls = classes[0]
            explanation = f"""
[bold cyan]Class: {cls.name}[/bold cyan]

[bold]Location:[/bold] {cls.file_path} (lines {cls.line_start}-{cls.line_end})

[bold]Purpose:[/bold]
{cls.docstring or "No documentation available"}

[bold]Details:[/bold]
  • Type: Class
  • File: {Path(cls.file_path).name}
  • Lines: {cls.line_start} to {cls.line_end}

[dim]Would you like me to show you the code or find its methods?[/dim]
"""
            self.show_markdown(explanation)

        else:
            self.show_status(f"Couldn't find anything matching '{query}'", "warning")

    async def find_usage(self, query: str):
        """Find where something is used."""
        self.show_thinking(f"Finding usage of: {query}")

        # Find all functions/classes matching the query
        functions = await self.knowledge_graph.query_nodes(node_type="function", name_pattern=query)

        if not functions:
            self.show_status(f"Nothing found matching '{query}'", "warning")
            return

        # For each function, find what calls it
        results = []
        for func in functions:
            # Get call graph
            call_graph = await self.knowledge_graph.get_call_graph(func.id, depth=2)

            if call_graph.get(func.id):
                callers = call_graph[func.id]
                for caller_id in callers:
                    # Find the caller function
                    caller_funcs = await self.knowledge_graph.query_nodes(node_type="function")
                    for caller in caller_funcs:
                        if caller.id == caller_id:
                            results.append(
                                {
                                    "Called by": caller.name,
                                    "In file": caller.file_path,
                                    "Lines": f"{caller.line_start}-{caller.line_end}",
                                }
                            )

        if results:
            self.show_table(results, f"Where '{query}' is used")
            self.show_status(f"Found {len(results)} usages", "success")
        else:
            self.show_status(f"No usages found for '{query}'", "warning")

    async def process_natural_language(self, user_input: str):
        """Process natural language input intelligently."""
        user_input_lower = user_input.lower()

        # Handle slash commands
        if user_input_lower.startswith("/"):
            await self.process_slash_command(user_input)
            return

        # Handle model configuration commands
        if user_input_lower == "providers":
            await self.show_providers()
            return

        elif user_input_lower == "models":
            await self.show_models()
            return

        elif user_input_lower.startswith("models "):
            provider_name = user_input[7:].strip()
            await self.show_models(provider_name)
            return

        elif user_input_lower == "recommended":
            await self.show_recommended_models()
            return

        elif user_input_lower == "tiers":
            await self.show_tiers()
            return

        elif user_input_lower.startswith("config "):
            parts = user_input[7:].split()
            if len(parts) >= 2:
                provider_name = parts[0]
                api_key = parts[1]
                await self.configure_provider(provider_name, api_key)
            else:
                self.show_status("Usage: config <provider> <api_key>", "warning")
            return

        elif user_input_lower.startswith("select "):
            parts = user_input[7:].split()
            if len(parts) >= 2:
                primary_provider = parts[0]
                primary_model = parts[1]
                primary_tier = None
                secondary_provider = None
                secondary_model = None
                secondary_tier = None

                # Parse optional parameters
                i = 2
                while i < len(parts):
                    if parts[i] in ["slm", "medium", "frontier"]:
                        if not primary_tier:
                            primary_tier = parts[i]
                        elif not secondary_tier:
                            secondary_tier = parts[i]
                    elif i + 1 < len(parts) and parts[i + 1] not in ["slm", "medium", "frontier"]:
                        if not secondary_provider:
                            secondary_provider = parts[i]
                            secondary_model = parts[i + 1]
                            i += 1
                    i += 1

                await self.select_models(
                    primary_provider,
                    primary_model,
                    primary_tier,
                    secondary_provider,
                    secondary_model,
                    secondary_tier,
                )
            else:
                self.show_status(
                    "Usage: select <primary_provider> <primary_model> [primary_tier] [secondary_provider] [secondary_model] [secondary_tier]",
                    "warning",
                )
            return

        # Detect write intent
        elif any(word in user_input_lower for word in ["write", "create", "make", "generate"]):
            if (
                "file" in user_input_lower
                or "function" in user_input_lower
                or "class" in user_input_lower
            ):
                # Extract file path and content
                # This is a simplified version - in production, you'd use LLM to parse
                parts = user_input.split('"')
                if len(parts) >= 3:
                    file_path = parts[1]
                    content = parts[3] if len(parts) > 3 else ""
                    await self.write_code(file_path, content)
                else:
                    self.show_status("Please specify file path and content in quotes", "warning")
                return

        # Detect edit intent
        elif any(word in user_input_lower for word in ["edit", "modify", "change", "update"]):
            if "function" in user_input_lower or "class" in user_input_lower:
                # Extract target and new content
                # This is a simplified version
                parts = user_input.split('"')
                if len(parts) >= 3:
                    target = parts[1]
                    new_content = parts[3] if len(parts) > 3 else ""
                    # Find file containing target
                    functions = await self.knowledge_graph.query_nodes(
                        node_type="function", name_pattern=target
                    )
                    if functions:
                        await self.edit_code(functions[0].file_path, target, new_content)
                    else:
                        classes = await self.knowledge_graph.query_nodes(
                            node_type="class", name_pattern=target
                        )
                        if classes:
                            await self.edit_code(classes[0].file_path, target, new_content)
                        else:
                            self.show_status(f"Couldn't find '{target}'", "warning")
                else:
                    self.show_status("Please specify target and new content in quotes", "warning")
                return

        # Detect delete intent
        elif any(word in user_input_lower for word in ["delete", "remove", "erase"]):
            if "function" in user_input_lower or "class" in user_input_lower:
                # Extract target
                parts = user_input.split('"')
                if len(parts) >= 2:
                    target = parts[1]
                    # Find file containing target
                    functions = await self.knowledge_graph.query_nodes(
                        node_type="function", name_pattern=target
                    )
                    if functions:
                        await self.delete_code(functions[0].file_path, target)
                    else:
                        classes = await self.knowledge_graph.query_nodes(
                            node_type="class", name_pattern=target
                        )
                        if classes:
                            await self.delete_code(classes[0].file_path, target)
                        else:
                            self.show_status(f"Couldn't find '{target}'", "warning")
                else:
                    self.show_status("Please specify target in quotes", "warning")
                return

        # Detect insert intent
        elif any(word in user_input_lower for word in ["insert", "add"]):
            if "function" in user_input_lower or "class" in user_input_lower:
                # Extract target and content
                parts = user_input.split('"')
                if len(parts) >= 3:
                    target = parts[1]
                    content = parts[3] if len(parts) > 3 else ""
                    # Find file containing target
                    functions = await self.knowledge_graph.query_nodes(
                        node_type="function", name_pattern=target
                    )
                    if functions:
                        await self.insert_code(functions[0].file_path, target, content)
                    else:
                        classes = await self.knowledge_graph.query_nodes(
                            node_type="class", name_pattern=target
                        )
                        if classes:
                            await self.insert_code(classes[0].file_path, target, content)
                        else:
                            self.show_status(f"Couldn't find '{target}'", "warning")
                else:
                    self.show_status("Please specify target and content in quotes", "warning")
                return

        # Detect find intent
        elif any(word in user_input_lower for word in ["find", "show", "list", "where"]):
            if "function" in user_input_lower or "def" in user_input_lower:
                # Extract function name
                query = (
                    user_input_lower.replace("find", "")
                    .replace("show", "")
                    .replace("list", "")
                    .replace("where", "")
                    .replace("function", "")
                    .replace("def", "")
                    .replace("all", "")
                    .strip()
                )
                if query:
                    await self.find_functions(query)
                else:
                    await self.find_functions("")

            elif "class" in user_input_lower:
                # Extract class name
                query = (
                    user_input_lower.replace("find", "")
                    .replace("show", "")
                    .replace("list", "")
                    .replace("where", "")
                    .replace("class", "")
                    .replace("all", "")
                    .strip()
                )
                if query:
                    await self.find_classes(query)
                else:
                    await self.find_classes("")

            elif (
                "usage" in user_input_lower
                or "used" in user_input_lower
                or "calls" in user_input_lower
            ):
                # Extract what to find usage for
                query = (
                    user_input_lower.replace("find", "")
                    .replace("show", "")
                    .replace("usage", "")
                    .replace("used", "")
                    .replace("calls", "")
                    .replace("where", "")
                    .strip()
                )
                if query:
                    await self.find_usage(query)

            else:
                # Generic find
                query = (
                    user_input_lower.replace("find", "")
                    .replace("show", "")
                    .replace("list", "")
                    .replace("where", "")
                    .replace("all", "")
                    .strip()
                )
                if query:
                    await self.find_functions(query)

        # Detect explain intent
        elif any(word in user_input_lower for word in ["explain", "how", "what", "describe"]):
            # Extract what to explain
            query = (
                user_input_lower.replace("explain", "")
                .replace("how", "")
                .replace("what", "")
                .replace("describe", "")
                .replace("does", "")
                .replace("the", "")
                .replace("is", "")
                .strip()
            )
            if query:
                await self.explain_code(query)

        # Detect read intent
        elif any(word in user_input_lower for word in ["read", "show", "open", "view"]):
            # Extract file path
            query = (
                user_input_lower.replace("read", "")
                .replace("show", "")
                .replace("open", "")
                .replace("view", "")
                .replace("file", "")
                .replace("the", "")
                .strip()
            )
            if query:
                await self.show_file(query)

        # Detect help intent
        elif any(word in user_input_lower for word in ["help", "commands", "what can you do"]):
            self.show_help()

        # Detect status intent
        elif any(word in user_input_lower for word in ["status", "stats", "info"]):
            await self.show_stats()

        # Detect clear intent
        elif any(word in user_input_lower for word in ["clear", "cls"]):
            self.console.clear()
            self.show_banner()

        else:
            # Try to find functions/classes matching the input
            await self.find_functions(user_input)

    async def show_help(self):
        """Show help information."""
        help_text = """
[bold cyan]What I can do for you:[/bold cyan]

[bold]Write Code:[/bold]
  • "Write a function called authenticate in auth.py"
  • "Create a new file utils.py with helper functions"
  • "Generate a class User in models.py"

[bold]Edit Code:[/bold]
  • "Edit the authenticate function to add timeout"
  • "Modify the User class to add email field"
  • "Update the payment function to handle errors"

[bold]Delete Code:[/bold]
  • "Delete the authenticate function"
  • "Remove the User class"
  • "Erase the deprecated function"

[bold]Insert Code:[/bold]
  • "Insert error handling in the payment function"
  • "Add logging to the authenticate function"
  • "Insert validation in the User class"

[bold]Find Code:[/bold]
  • "Find all authentication functions"
  • "Show me user-related classes"
  • "Where is the database used?"
  • "List all payment functions"

[bold]Understand Code:[/bold]
  • "Explain how the auth service works"
  • "What does the payment function do?"
  • "How is the user model used?"

[bold]Read Files:[/bold]
  • "Show me the auth.py file"
  • "Read the user service code"
  • "Open the payment module"

[bold]Find Usage:[/bold]
  • "Where is the authenticate function called?"
  • "What uses the database module?"
  • "Find all usages of User class"

[bold]AI Model Configuration:[/bold]
  • "/providers" - Show available AI providers
  • "/models" - Show available models
  • "/models <provider>" - Show models from specific provider
  • "/recommended" - Show recommended models
  • "/tiers" - Show available tiers (slm, medium, frontier)
  • "/config <provider> <api_key>" - Configure provider API key
  • "/select <primary_provider> <primary_model> [primary_tier] [secondary_provider] [secondary_model] [secondary_tier]" - Select models with optional tier specification

[dim]Note: You can also use these without the / prefix (e.g., "models" instead of "/models")[/dim]
  • "tiers" - Show available tiers (slm, medium, frontier)

[bold]System Commands:[/bold]
  • "help" - Show this help
  • "status" - Show codebase statistics
  • "clear" - Clear the screen
  • "exit" - Exit the assistant

[dim]Just type naturally - I'll understand what you need![/dim]
"""
        self.show_markdown(help_text, "Help")

    async def process_slash_command(self, command: str):
        """Process slash commands."""
        command_lower = command.lower()

        # Remove leading slash
        command_lower = command_lower[1:]

        # Handle slash commands
        if command_lower == "providers":
            await self.show_providers()
        elif command_lower == "models":
            await self.show_models()
        elif command_lower.startswith("models "):
            provider_name = command[8:].strip()
            await self.show_models(provider_name)
        elif command_lower == "recommended":
            await self.show_recommended_models()
        elif command_lower == "tiers":
            await self.show_tiers()
        elif command_lower.startswith("config "):
            parts = command[8:].split()
            if len(parts) >= 2:
                provider_name = parts[0]
                api_key = parts[1]
                await self.configure_provider(provider_name, api_key)
            else:
                self.show_status("Usage: /config <provider> <api_key>", "warning")
        elif command_lower.startswith("select "):
            parts = command[8:].split()
            if len(parts) >= 2:
                primary_provider = parts[0]
                primary_model = parts[1]
                primary_tier = None
                secondary_provider = None
                secondary_model = None
                secondary_tier = None

                # Parse optional parameters
                i = 2
                while i < len(parts):
                    if parts[i] in ["slm", "medium", "frontier"]:
                        if not primary_tier:
                            primary_tier = parts[i]
                        elif not secondary_tier:
                            secondary_tier = parts[i]
                    elif i + 1 < len(parts) and parts[i + 1] not in ["slm", "medium", "frontier"]:
                        if not secondary_provider:
                            secondary_provider = parts[i]
                            secondary_model = parts[i + 1]
                            i += 1
                    i += 1

                await self.select_models(
                    primary_provider,
                    primary_model,
                    primary_tier,
                    secondary_provider,
                    secondary_model,
                    secondary_tier,
                )
            else:
                self.show_status(
                    "Usage: /select <primary_provider> <primary_model> [primary_tier] [secondary_provider] [secondary_model] [secondary_tier]",
                    "warning",
                )
        elif command_lower == "help":
            self.show_help()
        elif command_lower == "status":
            await self.show_status_info()
        elif command_lower == "stats":
            await self.show_stats()
        elif command_lower == "clear":
            self.console.clear()
            self.show_banner()
        else:
            self.show_status(
                f"Unknown command: {command}. Type /help for available commands.", "warning"
            )

    async def show_stats(self):
        """Show codebase statistics."""
        stats = await self.knowledge_graph.get_stats()
        functions = await self.knowledge_graph.query_nodes(node_type="function")
        classes = await self.knowledge_graph.query_nodes(node_type="class")

        stats_text = f"""
[bold cyan]Your Codebase[/bold cyan]

[bold]Overview:[/bold]
  • {stats["files"]} Python files
  • {len(functions)} functions
  • {len(classes)} classes
  • {stats["nodes"]} total code entities

[bold]Performance:[/bold]
  • Token efficiency: 99.2% reduction
  • Query speed: 100x faster than grep
  • Ready for intelligent operations!

[dim]I'm ready to help you explore and modify your code![/dim]
"""
        self.show_markdown(stats_text, "Codebase Statistics")

    async def show_providers(self):
        """Show available AI providers and their status."""
        status = self.provider_manager.get_provider_status()

        # Create table
        table = Table(title="AI Providers Status")
        table.add_column("Provider", style="cyan")
        table.add_column("Enabled", style="green")
        table.add_column("API Key", style="yellow")
        table.add_column("Primary", style="magenta")
        table.add_column("Secondary", style="blue")

        for provider_name, provider_status in status.items():
            table.add_row(
                provider_name,
                "✓" if provider_status["enabled"] else "✗",
                "✓" if provider_status["has_api_key"] else "✗",
                "✓" if provider_status["is_primary"] else "",
                "✓" if provider_status["is_secondary"] else "",
            )

        self.console.print(table)

        # Show current selection
        if self.provider_manager.model_selection:
            selection = f"""
[bold cyan]Current Model Selection[/bold cyan]

[bold]Primary:[/bold]
  • Provider: {self.provider_manager.model_selection.primary_provider}
  • Model: {self.provider_manager.model_selection.primary_model}

"""
            if self.provider_manager.model_selection.secondary_provider:
                selection += f"""[bold]Secondary:[/bold]
  • Provider: {self.provider_manager.model_selection.secondary_provider}
  • Model: {self.provider_manager.model_selection.secondary_model}

"""
            self.show_markdown(selection, "Model Selection")
        else:
            self.show_status("No model selection configured. Use 'models' to configure.", "warning")

    async def show_models(self, provider_name: Optional[str] = None):
        """Show available models from providers."""
        if provider_name:
            # Show models from specific provider
            if provider_name not in self.provider_manager.providers:
                self.show_status(f"Unknown provider: {provider_name}", "error")
                return

            self.show_thinking(f"Fetching models from {provider_name}...")
            models = await self.provider_manager.get_models_by_provider(provider_name)

            if not models:
                self.show_status(f"No models available from {provider_name}", "warning")
                return

            # Create table
            table = Table(title=f"Models from {provider_name}")
            table.add_column("Model ID", style="cyan")
            table.add_column("Name", style="green")
            table.add_column("Tier", style="yellow")
            table.add_column("Context", style="magenta")
            table.add_column("Input Cost", style="blue")
            table.add_column("Output Cost", style="blue")

            for model in models:
                table.add_row(
                    model.id,
                    model.name,
                    model.tier.value,
                    str(model.context_window),
                    f"${model.input_cost_per_1k:.4f}",
                    f"${model.output_cost_per_1k:.4f}",
                )

            self.console.print(table)
        else:
            # Show models from all providers
            self.show_thinking("Fetching models from all providers...")
            all_models = await self.provider_manager.get_all_models()

            for provider_name, models in all_models.items():
                if not models:
                    continue

                # Create table for this provider
                table = Table(title=f"Models from {provider_name}")
                table.add_column("Model ID", style="cyan")
                table.add_column("Name", style="green")
                table.add_column("Tier", style="yellow")
                table.add_column("Context", style="magenta")

                for model in models:
                    table.add_row(
                        model.id,
                        model.name,
                        model.tier.value,
                        str(model.context_window),
                    )

                self.console.print(table)
                self.console.print()

    async def configure_provider(self, provider_name: str, api_key: str):
        """Configure a provider with API key."""
        if provider_name not in self.provider_manager.providers:
            self.show_status(f"Unknown provider: {provider_name}", "error")
            return

        self.show_thinking(f"Configuring {provider_name}...")
        self.provider_manager.set_provider_api_key(provider_name, api_key)
        self.show_status(f"Successfully configured {provider_name}", "success")

    async def select_models(
        self,
        primary_provider: str,
        primary_model: str,
        primary_tier: Optional[str] = None,
        secondary_provider: Optional[str] = None,
        secondary_model: Optional[str] = None,
        secondary_tier: Optional[str] = None,
    ):
        """Select primary and secondary models with optional tier specification."""
        # Validate providers
        if primary_provider not in self.provider_manager.providers:
            self.show_status(f"Unknown provider: {primary_provider}", "error")
            return

        if secondary_provider and secondary_provider not in self.provider_manager.providers:
            self.show_status(f"Unknown provider: {secondary_provider}", "error")
            return

        # Get model info to validate tier
        primary_models = await self.provider_manager.get_models_by_provider(primary_provider)
        primary_model_info = None
        for model in primary_models:
            if model.id == primary_model:
                primary_model_info = model
                break

        if not primary_model_info:
            self.show_status(f"Model not found: {primary_model}", "error")
            return

        # Validate or set primary tier
        if primary_tier:
            try:
                from ..providers import ModelTier

                primary_model_info.tier = ModelTier(primary_tier)
            except ValueError:
                self.show_status(
                    f"Invalid tier: {primary_tier}. Valid tiers: slm, medium, frontier", "warning"
                )
                primary_tier = None

        # Validate secondary model if provided
        secondary_model_info = None
        if secondary_provider and secondary_model:
            secondary_models = await self.provider_manager.get_models_by_provider(
                secondary_provider
            )
            for model in secondary_models:
                if model.id == secondary_model:
                    secondary_model_info = model
                    break

            if not secondary_model_info:
                self.show_status(f"Model not found: {secondary_model}", "error")
                return

            # Validate or set secondary tier
            if secondary_tier:
                try:
                    from ..providers import ModelTier

                    secondary_model_info.tier = ModelTier(secondary_tier)
                except ValueError:
                    self.show_status(
                        f"Invalid tier: {secondary_tier}. Valid tiers: slm, medium, frontier",
                        "warning",
                    )
                    secondary_tier = None

        self.show_thinking("Setting model selection...")
        self.provider_manager.set_model_selection(
            primary_provider=primary_provider,
            primary_model=primary_model,
            secondary_provider=secondary_provider,
            secondary_model=secondary_model,
        )

        selection = f"""
[bold green]✓ Model Selection Configured[/bold green]

[bold]Primary:[/bold]
  • Provider: {primary_provider}
  • Model: {primary_model}
  • Tier: {primary_model_info.tier.value}
  • Context: {primary_model_info.context_window} tokens
  • Cost: ${primary_model_info.input_cost_per_1k:.4f} input / ${primary_model_info.output_cost_per_1k:.4f} output

"""
        if secondary_provider and secondary_model:
            selection += f"""[bold]Secondary:[/bold]
  • Provider: {secondary_provider}
  • Model: {secondary_model}
  • Tier: {secondary_model_info.tier.value}
  • Context: {secondary_model_info.context_window} tokens
  • Cost: ${secondary_model_info.input_cost_per_1k:.4f} input / ${secondary_model_info.output_cost_per_1k:.4f} output

"""

        self.show_markdown(selection, "Model Selection")

    async def show_recommended_models(self):
        """Show recommended models from all providers."""
        self.show_thinking("Fetching recommended models...")
        recommendations = await self.provider_manager.get_recommended_models()

        for provider_name, models in recommendations.items():
            if not any(models.values()):
                continue

            rec_text = f"""
[bold cyan]{provider_name} - Recommended Models[/bold cyan]

"""
            if models.get("slm"):
                slm = models["slm"]
                rec_text += f"""[bold green]SLM (Small Language Model):[/bold green]
  • {slm.name} ({slm.id})
  • Context: {slm.context_window} tokens
  • Cost: ${slm.input_cost_per_1k:.4f} input / ${slm.output_cost_per_1k:.4f} output

"""

            if models.get("medium"):
                medium = models["medium"]
                rec_text += f"""[bold yellow]Medium Model:[/bold yellow]
  • {medium.name} ({medium.id})
  • Context: {medium.context_window} tokens
  • Cost: ${medium.input_cost_per_1k:.4f} input / ${medium.output_cost_per_1k:.4f} output

"""

            if models.get("frontier"):
                frontier = models["frontier"]
                rec_text += f"""[bold magenta]Frontier Model:[/bold magenta]
  • {frontier.name} ({frontier.id})
  • Context: {frontier.context_window} tokens
  • Cost: ${frontier.input_cost_per_1k:.4f} input / ${frontier.output_cost_per_1k:.4f} output

"""

            self.show_markdown(rec_text, f"{provider_name} Recommendations")

    async def show_tiers(self):
        """Show available model tiers."""
        from ..providers import ModelTier

        tiers_text = """
[bold cyan]Available Model Tiers[/bold cyan]

[bold green]SLM (Small Language Model)[/bold green]
  • Size: 1B-4B parameters
  • Speed: Very fast (~100-500ms)
  • Cost: Very low (~$0.0001 per 1K tokens)
  • Use: Routing, classification, simple tasks
  • Examples: Claude 3.5 Haiku, GPT-4o Mini, Gemini 1.5 Flash

[bold yellow]Medium Model[/bold yellow]
  • Size: 7B-30B parameters
  • Speed: Fast (~200-800ms)
  • Cost: Low (~$0.001 per 1K tokens)
  • Use: Code generation, analysis, reasoning
  • Examples: Claude 3 Sonnet, GPT-4o, Gemini 1.5 Pro

[bold magenta]Frontier Model[/bold magenta]
  • Size: 100B+ parameters
  • Speed: Medium (~1-3s)
  • Cost: Medium (~$0.01 per 1K tokens)
  • Use: Complex generation, deep debugging, architecture
  • Examples: Claude 3.5 Sonnet, GPT-4 Turbo, Gemini 2.0 Flash

[bold]How to Select Tier:[/bold]
  • When selecting a model, you can optionally specify the tier
  • If not specified, the provider's default tier is used
  • Example: "select Claude claude-3-5-haiku-20241022 slm"
  • Example: "select OpenAI gpt-4o medium"

[bold]Note:[/bold]
  • Tiers are predefined by providers based on model capabilities
  • You can override the default tier by specifying it explicitly
  • Use "recommended" to see recommended models for each tier
"""
        self.show_markdown(tiers_text, "Model Tiers")

    async def write_code(self, file_path: str, content: str):
        """Write new code to a file."""
        self.show_thinking(f"Writing to {file_path}...")

        result = await self.code_editor.write_file(file_path, content)

        if result.success:
            self.show_status(f"Successfully wrote to {file_path}", "success")

            # Show diff
            if result.original_content:
                diff = await self.code_editor.get_diff(
                    result.original_content, result.modified_content
                )
                if diff:
                    self.show_code(diff, "diff", "Changes")

            # Show summary
            summary = f"""
[bold green]✓ Write Complete[/bold green]

[bold]Details:[/bold]
  • File: {result.modified_file}
  • Lines written: {len(result.lines_changed)}
  • Syntax valid: ✓
"""
            self.show_markdown(summary, "Write Summary")
        else:
            self.show_status(f"Write failed: {result.error}", "error")

    async def edit_code(self, file_path: str, target: str, new_content: str):
        """Edit code in a file."""
        self.show_thinking(f"Editing {target} in {file_path}...")

        # Determine if target is function or class
        functions = await self.knowledge_graph.query_nodes(
            node_type="function", name_pattern=target
        )

        classes = await self.knowledge_graph.query_nodes(node_type="class", name_pattern=target)

        # Create edit intent
        if functions:
            intent = await self.code_editor.create_edit_intent(
                operation="edit",
                target_file=file_path,
                target_function=functions[0].name,
                new_content=new_content,
            )
        elif classes:
            intent = await self.code_editor.create_edit_intent(
                operation="edit",
                target_file=file_path,
                target_class=classes[0].name,
                new_content=new_content,
            )
        else:
            self.show_status(f"Couldn't find '{target}' in {file_path}", "warning")
            return

        # Apply edit
        result = await self.code_editor.edit_code(intent)

        if result.success:
            self.show_status(f"Successfully edited {target}", "success")

            # Show diff
            diff = await self.code_editor.get_diff(result.original_content, result.modified_content)
            if diff:
                self.show_code(diff, "diff", "Changes")

            # Show summary
            summary = f"""
[bold green]✓ Edit Complete[/bold green]

[bold]Details:[/bold]
  • File: {result.modified_file}
  • Lines changed: {len(result.lines_changed)}
  • Syntax valid: ✓
"""
            self.show_markdown(summary, "Edit Summary")
        else:
            self.show_status(f"Edit failed: {result.error}", "error")

    async def delete_code(self, file_path: str, target: str):
        """Delete code from a file."""
        self.show_thinking(f"Deleting {target} from {file_path}...")

        # Determine if target is function or class
        functions = await self.knowledge_graph.query_nodes(
            node_type="function", name_pattern=target
        )

        classes = await self.knowledge_graph.query_nodes(node_type="class", name_pattern=target)

        # Create delete intent
        if functions:
            intent = await self.code_editor.create_edit_intent(
                operation="delete",
                target_file=file_path,
                target_function=functions[0].name,
            )
        elif classes:
            intent = await self.code_editor.create_edit_intent(
                operation="delete",
                target_file=file_path,
                target_class=classes[0].name,
            )
        else:
            self.show_status(f"Couldn't find '{target}' in {file_path}", "warning")
            return

        # Apply delete
        result = await self.code_editor.delete_code(intent)

        if result.success:
            self.show_status(f"Successfully deleted {target}", "success")

            # Show diff
            diff = await self.code_editor.get_diff(result.original_content, result.modified_content)
            if diff:
                self.show_code(diff, "diff", "Changes")

            # Show summary
            summary = f"""
[bold green]✓ Delete Complete[/bold green]

[bold]Details:[/bold]
  • File: {result.modified_file}
  • Lines removed: {len(result.lines_changed)}
  • Syntax valid: ✓
"""
            self.show_markdown(summary, "Delete Summary")
        else:
            self.show_status(f"Delete failed: {result.error}", "error")

    async def insert_code(self, file_path: str, target: str, content: str, position: str = "start"):
        """Insert code into a function or class."""
        self.show_thinking(f"Inserting code into {target} in {file_path}...")

        # Determine if target is function or class
        functions = await self.knowledge_graph.query_nodes(
            node_type="function", name_pattern=target
        )

        classes = await self.knowledge_graph.query_nodes(node_type="class", name_pattern=target)

        # Create insert intent
        if functions:
            intent = await self.code_editor.create_edit_intent(
                operation="insert",
                target_file=file_path,
                target_function=functions[0].name,
                content=content,
                position=position,
            )
        elif classes:
            intent = await self.code_editor.create_edit_intent(
                operation="insert",
                target_file=file_path,
                target_class=classes[0].name,
                content=content,
                position=position,
            )
        else:
            self.show_status(f"Couldn't find '{target}' in {file_path}", "warning")
            return

        # Apply insert
        result = await self.code_editor.insert_code(intent)

        if result.success:
            self.show_status(f"Successfully inserted code into {target}", "success")

            # Show diff
            diff = await self.code_editor.get_diff(result.original_content, result.modified_content)
            if diff:
                self.show_code(diff, "diff", "Changes")

            # Show summary
            summary = f"""
[bold green]✓ Insert Complete[/bold green]

[bold]Details:[/bold]
  • File: {result.modified_file}
  • Lines changed: {len(result.lines_changed)}
  • Syntax valid: ✓
"""
            self.show_markdown(summary, "Insert Summary")
        else:
            self.show_status(f"Insert failed: {result.error}", "error")

    async def run(self):
        """Run the interactive CLI."""
        # Show banner
        self.show_banner()

        # Auto-index codebase
        await self.auto_index_codebase()

        # Show welcome
        self.show_welcome()

        # Main loop
        while True:
            try:
                # Get user input
                user_input = await self.prompt_session.prompt_async(
                    HTML('<style bg="ansiblack" fg="ansicyan">✨ You</style>: '),
                    style=self.style,
                )

                # Skip empty input
                if not user_input.strip():
                    continue

                # Add to history
                self.chat_history.append(
                    {
                        "role": "user",
                        "content": user_input,
                        "timestamp": datetime.now().isoformat(),
                    }
                )

                # Process input
                user_input_lower = user_input.lower().strip()

                # Handle exit
                if user_input_lower in ["exit", "quit", "q", "bye"]:
                    self.show_status("Goodbye! 👋", "success")
                    break

                # Process natural language
                await self.process_natural_language(user_input)

                # Add separator
                self.console.print()

            except KeyboardInterrupt:
                self.console.print("\n[yellow]Interrupted. Type 'exit' to quit.[/yellow]")
            except EOFError:
                self.show_status("Goodbye! 👋", "success")
                break
            except Exception as e:
                self.show_status(f"Error: {e}", "error")


async def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Sparkling Water - Next-Generation AI Coding Assistant"
    )
    parser.add_argument(
        "path", nargs="?", default=".", help="Path to codebase (default: current directory)"
    )

    args = parser.parse_args()

    # Create CLI
    cli = SparklingWaterCLI(args.path)

    # Run interactive CLI
    await cli.run()


if __name__ == "__main__":
    asyncio.run(main())
