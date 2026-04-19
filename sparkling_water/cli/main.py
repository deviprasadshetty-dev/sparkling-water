"""Main CLI interface for Sparkling Water."""

import asyncio
import click
from pathlib import Path
from typing import Optional
import json
from datetime import datetime
import time
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from ..events.event_bus import EventBus, Event, EventType, Orchestrator
from ..graph.knowledge_graph import KnowledgeGraph
from ..vfs.virtual_filesystem import VirtualFileSystem
from ..router.slm_router import SLMRouter, Task
from ..core.ast_transformer import ASTTransformationEngine, TransformationIntent


console = Console()


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """Sparkling Water - Next-Generation CLI Coding Agent

    A modern, event-driven coding agent with AST-based intelligence,
    SLM routing, and surgical code modifications.
    """
    pass


@cli.command()
@click.argument("path", type=click.Path(exists=True))
@click.option("--db", default=":memory:", help="Database path for knowledge graph")
def index(path: str, db: str):
    """Index a codebase into the knowledge graph."""

    async def _index():
        console.print(f"[bold blue]Indexing codebase at: {path}[/bold blue]")

        # Initialize components
        kg = KnowledgeGraph(db_path=db)
        await kg.initialize()

        # Find all Python files
        codebase_path = Path(path).resolve()
        python_files = list(codebase_path.rglob("*.py"))

        console.print(f"Found {len(python_files)} Python files")

        # Index files
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Indexing files...", total=len(python_files))

            total_nodes = 0
            for file_path in python_files:
                try:
                    content = file_path.read_text(encoding="utf-8")
                    nodes = await kg.index_file(str(file_path), content)
                    total_nodes += nodes
                    progress.update(task, advance=1)
                except Exception as e:
                    console.print(f"[red]Error indexing {file_path}: {e}[/red]")

        # Get stats
        stats = await kg.get_stats()

        console.print("\n[bold green]Indexing complete![/bold green]")
        console.print(f"  Files indexed: {stats['files']}")
        console.print(f"  Nodes created: {stats['nodes']}")
        console.print(f"  Edges created: {stats['edges']}")

    asyncio.run(_index())


@cli.command()
@click.argument("query")
@click.option("--db", default=":memory:", help="Database path for knowledge graph")
def query(query: str, db: str):
    """Query the knowledge graph."""

    async def _query():
        console.print(f"[bold blue]Querying knowledge graph: {query}[/bold blue]")

        # Initialize components
        kg = KnowledgeGraph(db_path=db)
        await kg.initialize()

        # Parse query
        query_lower = query.lower()

        # Determine query type
        if "function" in query_lower:
            nodes = await kg.query_nodes(
                node_type="function", name_pattern=query.replace("function", "").strip()
            )
        elif "class" in query_lower:
            nodes = await kg.query_nodes(
                node_type="class", name_pattern=query.replace("class", "").strip()
            )
        else:
            nodes = await kg.query_nodes(name_pattern=query)

        # Display results
        if not nodes:
            console.print("[yellow]No results found[/yellow]")
            return

        table = Table(title="Query Results")
        table.add_column("Type", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("File", style="blue")
        table.add_column("Lines", style="magenta")

        for node in nodes:
            table.add_row(
                node.type,
                node.name,
                node.file_path,
                f"{node.line_start}-{node.line_end}",
            )

        console.print(table)
        console.print(f"\n[bold]Found {len(nodes)} results[/bold]")

    asyncio.run(_query())


@cli.command()
@click.argument("file_path", type=click.Path(exists=True))
@click.option("--expand", help="Function or class to expand")
@click.option("--db", default=":memory:", help="Database path for knowledge graph")
def read(file_path: str, expand: Optional[str], db: str):
    """Read a file with progressive disclosure."""

    async def _read():
        console.print(f"[bold blue]Reading file: {file_path}[/bold blue]")

        # Initialize components
        kg = KnowledgeGraph(db_path=db)
        await kg.initialize()

        vfs = VirtualFileSystem(knowledge_graph=kg, root_path=Path(file_path).parent)

        # Read file
        start_time = time.time()

        if expand:
            content = await vfs.read_file(file_path, expand_function=expand)
        else:
            content = await vfs.read_file(file_path)

        elapsed = time.time() - start_time

        # Display content
        console.print(Panel(content, title=f"File: {file_path}"))

        # Get stats
        stats = await vfs.get_file_stats(file_path)
        savings = await vfs.get_token_savings()

        console.print(f"\n[bold]Performance Metrics:[/bold]")
        console.print(f"  Read time: {elapsed:.3f}s")
        console.print(f"  File size: {stats['size']} bytes")
        if stats["token_savings"] > 0:
            console.print(f"  Token savings: {stats['token_savings']} tokens")
            console.print(
                f"  [green]Efficiency gain: {(stats['token_savings'] / (stats['size'] // 4) * 100):.1f}%[/green]"
            )

    asyncio.run(_read())


@cli.command()
@click.argument("file_path", type=click.Path(exists=True))
@click.argument("action")
@click.option("--function", "target_function", help="Target function name")
@click.option("--class", "target_class", help="Target class name")
@click.option("--param", multiple=True, help="Parameters for the transformation")
def transform(
    file_path: str,
    action: str,
    target_function: Optional[str],
    target_class: Optional[str],
    param: tuple,
):
    """Apply an AST transformation to a file."""

    async def _transform():
        console.print(f"[bold blue]Applying transformation: {action}[/bold blue]")
        console.print(f"  Target file: {file_path}")
        if target_function:
            console.print(f"  Target function: {target_function}")
        if target_class:
            console.print(f"  Target class: {target_class}")

        # Parse parameters
        params = {}
        for p in param:
            if "=" in p:
                key, value = p.split("=", 1)
                params[key] = value

        # Initialize components
        engine = ASTTransformationEngine()

        # Create transformation intent
        intent = await engine.create_transformation_intent(
            action=action,
            target_file=file_path,
            target_function=target_function,
            target_class=target_class,
            **params,
        )

        # Apply transformation
        start_time = time.time()
        result = await engine.apply_transformation(intent)
        elapsed = time.time() - start_time

        # Display result
        if result.success:
            console.print("[bold green]Transformation successful![/bold green]")
            console.print(f"  Modified file: {result.modified_file}")
            console.print(f"  Time: {elapsed:.3f}s")

            # Show diff
            diff = await engine.get_diff(result.original_content, result.modified_content)
            if diff:
                console.print("\n[bold]Changes:[/bold]")
                console.print(diff)
        else:
            console.print("[bold red]Transformation failed![/bold red]")
            console.print(f"  Error: {result.error}")

    asyncio.run(_transform())


@cli.command()
@click.argument("description")
@click.option("--db", default=":memory:", help="Database path for knowledge graph")
@click.option("--slm-key", help="SLM API key")
@click.option("--frontier-key", help="Frontier model API key")
def route(description: str, db: str, slm_key: Optional[str], frontier_key: Optional[str]):
    """Route a task and show routing decision."""

    async def _route():
        console.print(f"[bold blue]Routing task: {description}[/bold blue]")

        # Initialize router
        router = SLMRouter(
            slm_api_key=slm_key,
            frontier_api_key=frontier_key,
        )

        # Create task
        start_time = time.time()
        task = await router.create_task(description)
        elapsed = time.time() - start_time

        # Route task
        decision = await router.route_task(task)

        # Display result
        console.print(f"\n[bold]Task Classification:[/bold]")
        console.print(f"  Type: {task.type.value}")
        console.print(f"  Estimated tokens: {task.estimated_tokens}")
        console.print(f"  Classification time: {elapsed:.3f}s")

        console.print(f"\n[bold]Routing Decision:[/bold]")
        console.print(f"  Model tier: {decision.model_tier.value}")
        console.print(f"  Confidence: {decision.confidence:.2f}")
        console.print(f"  Reasoning: {decision.reasoning}")

        # Get stats
        stats = await router.get_routing_stats()
        console.print(f"\n[bold]Routing Statistics:[/bold]")
        console.print(f"  Total tasks: {stats['total_tasks']}")
        console.print(f"  SLM tasks: {stats['slm_tasks']} ({stats['slm_percentage']:.1f}%)")
        console.print(f"  Frontier tasks: {stats['frontier_tasks']}")
        console.print(f"  Estimated cost savings: ${stats['estimated_cost_savings']:.4f}")
        console.print(f"  Cost savings percentage: {stats['cost_savings_percentage']:.1f}%")

    asyncio.run(_route())


@cli.command()
@click.argument("path", type=click.Path(exists=True))
@click.option("--db", default=":memory:", help="Database path for knowledge graph")
def benchmark(path: str, db: str):
    """Run benchmark comparing Sparkling Water vs traditional approaches."""

    async def _benchmark():
        console.print("[bold blue]Running Benchmark: Sparkling Water vs Traditional[/bold blue]\n")

        # Initialize components
        kg = KnowledgeGraph(db_path=db)
        await kg.initialize()

        vfs = VirtualFileSystem(knowledge_graph=kg, root_path=Path(path))

        # Find Python files
        codebase_path = Path(path).resolve()
        python_files = list(codebase_path.rglob("*.py"))[:10]  # Limit to 10 files for benchmark

        console.print(f"Benchmarking with {len(python_files)} files\n")

        # Benchmark 1: File reading with progressive disclosure
        console.print("[bold]Benchmark 1: File Reading Efficiency[/bold]")
        table = Table()
        table.add_column("File", style="cyan")
        table.add_column("Traditional (tokens)", style="red")
        table.add_column("Sparkling Water (tokens)", style="green")
        table.add_column("Savings", style="yellow")
        table.add_column("Efficiency", style="magenta")

        total_traditional = 0
        total_sw = 0

        for file_path in python_files:
            # Traditional approach (read entire file)
            content = file_path.read_text(encoding="utf-8")
            traditional_tokens = len(content) // 4
            total_traditional += traditional_tokens

            # Sparkling Water approach (progressive disclosure)
            sw_content = await vfs.read_file(str(file_path))
            sw_tokens = len(sw_content) // 4
            total_sw += sw_tokens

            savings = traditional_tokens - sw_tokens
            efficiency = (savings / traditional_tokens * 100) if traditional_tokens > 0 else 0

            table.add_row(
                file_path.name,
                str(traditional_tokens),
                str(sw_tokens),
                str(savings),
                f"{efficiency:.1f}%",
            )

        console.print(table)

        overall_savings = total_traditional - total_sw
        overall_efficiency = (
            (overall_savings / total_traditional * 100) if total_traditional > 0 else 0
        )

        console.print(f"\n[bold]Overall Results:[/bold]")
        console.print(f"  Traditional total: {total_traditional} tokens")
        console.print(f"  Sparkling Water total: {total_sw} tokens")
        console.print(f"  Total savings: {overall_savings} tokens")
        console.print(f"  Overall efficiency: [green]{overall_efficiency:.1f}%[/green]")

        # Benchmark 2: Graph traversal vs grep
        console.print(f"\n[bold]Benchmark 2: Graph Traversal vs Grep[/bold]")

        # Index files first
        for file_path in python_files:
            try:
                content = file_path.read_text(encoding="utf-8")
                await kg.index_file(str(file_path), content)
            except Exception as e:
                console.print(f"[red]Error indexing {file_path}: {e}[/red]")

        # Graph traversal
        start_time = time.time()
        nodes = await kg.query_nodes(node_type="function")
        graph_time = time.time() - start_time

        # Grep (simulated)
        start_time = time.time()
        import subprocess

        try:
            result = subprocess.run(
                ["grep", "-r", "def ", str(codebase_path)],
                capture_output=True,
                text=True,
                timeout=5,
            )
            grep_results = result.stdout.count("\n")
        except Exception:
            grep_results = 0
        grep_time = time.time() - start_time

        console.print(f"  Graph traversal: {graph_time:.3f}s, found {len(nodes)} functions")
        console.print(f"  Grep search: {grep_time:.3f}s, found {grep_results} functions")

        if graph_time > 0:
            speedup = grep_time / graph_time
            console.print(f"  Speedup: [green]{speedup:.1f}x[/green]")

        # Summary
        console.print(f"\n[bold green]Benchmark Complete![/bold green]")
        console.print(f"  Token efficiency: {overall_efficiency:.1f}% reduction")
        console.print(f"  Graph traversal: {speedup:.1f}x faster than grep")

    asyncio.run(_benchmark())


@cli.command()
@click.argument("path", default=".", type=click.Path(exists=True))
def chat(path: str):
    """Launch interactive AI assistant (default mode)."""
    import asyncio
    from .interactive import SparklingWaterCLI

    async def run_chat():
        cli = SparklingWaterCLI(path)
        await cli.run()

    asyncio.run(run_chat())


@cli.command()
def demo():
    """Run a demo showcasing Sparkling Water capabilities."""
    console.print(
        Panel.fit(
            "[bold blue]Sparkling Water Demo[/bold blue]\n\n"
            "Next-Generation AI Coding Assistant\n"
            "with AST-based intelligence and SLM routing",
            title="Welcome",
        )
    )

    console.print("\n[bold]Key Features:[/bold]")
    console.print("  • Event-driven architecture")
    console.print("  • AST-based code representation")
    console.print("  • Progressive disclosure for token efficiency")
    console.print("  • SLM routing for cost optimization")
    console.print("  • Surgical code modifications")

    console.print("\n[bold]Quick Start:[/bold]")
    console.print("  Just run: [cyan]sw chat[/cyan] or [cyan]sw[/cyan]")
    console.print("  I'll automatically analyze your codebase and help you!")

    console.print("\n[bold]Example:[/bold]")
    console.print("  $ sw chat ./myproject")
    console.print("  $ sw  # Uses current directory")


if __name__ == "__main__":
    cli()
