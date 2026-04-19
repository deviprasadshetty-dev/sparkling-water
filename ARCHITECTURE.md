# Sparkling Water: Next-Generation CLI Coding Agent Architecture

## 1. Vision & Core Philosophy
Sparkling Water is a modern, first-principles CLI coding agent. Following the insights from the latest architectural paradigm shifts, it abandons traditional LLM context-stuffing and naive vector-search RAG. Instead, it acts as a headless, event-driven orchestration engine utilizing structural code representations, Small Language Models (SLMs) for routing, and Frontier Models for deep reasoning.

## 2. Core Architectural Components

### 2.1 Event Bus & Orchestrator
- **Pattern**: Event-Driven Architecture (EDA)
- **Role**: Handles all inputs (CLI commands, webhooks) as immutable events (e.g., `Task.Requested`, `File.Modified`). 
- **Benefit**: Enables asynchronous execution, decoupling, parallel processing, and robust state management via Sagas (capable of rollback and localized self-healing).

### 2.2 SLM Router (The Kernel)
- **Role**: The primary orchestrator. Employs a 1B-4B parameter Small Language Model (e.g., DeepSeek-R1-1.5B, SmolLM) for rapid instruction following, tool calling, and structural graph querying.
- **Function**: Interprets user intent, executes structural queries against the AST graph, and delegates only the heavy logic synthesis to the Frontier engine.

### 2.3 Frontier Reasoning Engine
- **Role**: High-latency, massive parameter models (e.g., Claude 3.5 Sonnet, GPT-4o) reserved strictly as a "co-processor".
- **Function**: Resolves deep architectural debugging, complex algorithm generation, and generates semantic transformation intents based on tightly scoped contexts prepared by the SLM.

### 2.4 Knowledge Graph & AST Engine
- **Role**: Replaces naive vector embeddings with deterministic code representation.
- **Technology**: Tree-sitter for generating Abstract Syntax Trees (AST). In-memory SQLite to persist the graph (nodes: functions/classes/variables; edges: calls/imports).
- **Function**: Enables token-efficient, rapid structural retrieval (e.g., Cypher or BFS graph traversal) instead of brute-force file scanning.

### 2.5 Virtual File System (VFS)
- **Role**: Acts as a synthetic abstraction layer between the AI and the physical disk.
- **Function**: Implements "Progressive Disclosure". When the agent attempts to read a file, the VFS intercepts the call and serves a compressed structural view (signatures and docstrings). Expanded code is only read on-demand.

## 3. Workflows & Features

### 3.1 Spec-Driven Development (SDD)
- The agent anchors its work on a central `SPEC.md` document, mitigating "context rot". 
- **Dynamic Context Pruning**: Employs Dynamic Context Pruning (DCP) to flush verbose, successful step outputs from the working memory, saving the state back to the graph.

### 3.2 Surgical Modification & AST Transformations
- Sparkling Water abandons text-based search/replace and unified diffs.
- Edits are outputted as structured, semantic payload intents (e.g., `{"action": "add_argument", ...}`).
- A deterministic AST refactoring tool (via `libcst` or `jscodeshift`) applies the change, guaranteeing syntactic validity and removing brittleness from the loop.

### 3.3 MCP (Model Context Protocol) Decoupling
- The core engine is decoupled from the CLI. Sparkling Water runs as a headless server using MCP.
- Supports cross-channel interfaces: what starts on the CLI can seamlessly transition to a webhook or a Telegram chat approval flow.

## 4. Next Steps for Implementation
1. Initialize the Event Bus and define standard Event schemas.
2. Integrate Tree-sitter to build the Knowledge Graph & AST Engine.
3. Build the VFS layer to intercept file reads and integrate with the Knowledge Graph.
4. Set up the dual-LLM structure: SLM for orchestration and Frontier API for heavy reasoning.
5. Create the AST transformation action space for edits.