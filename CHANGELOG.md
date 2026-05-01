# Changelog

All notable changes to Code Context Engine are documented here.

## [0.4.4] - 2025-04-30

### Added
- Multi-editor auto-detection: `cce init` configures Claude Code, VS Code, Cursor, Gemini CLI, and Codex in one command
- Reproducible benchmark suite with FastAPI (93% savings, 20 queries)
- Session savings visibility at every Claude Code session start
- `cce upgrade` command with auto-detection of install method (uv, pipx, pip)
- `cce uninstall` for clean removal of all CCE artifacts
- OpenAI Codex CLI support

### Changed
- Promoted `aiohttp` from optional to core dependency (required for memory capture hooks)

## [0.4.3] - 2025-04-25

### Added
- Web dashboard with donut charts, file health, and session history (`cce dashboard`)
- Dollar cost estimates from live Anthropic pricing
- `cce savings --all` to view savings across all projects

## [0.4.2] - 2025-04-20

### Added
- AST-aware chunking for PHP, Go, Rust, Java via tree-sitter
- 7-layer security: secret file detection, content redaction (AWS keys, GitHub tokens, JWTs), PII scrubbing, path traversal protection

### Changed
- Migrated from LanceDB to sqlite-vec (99% smaller install, ~2 MB vs 217 MB)

## [0.4.1] - 2025-04-15

### Added
- Output compression with 4 levels (off, lite, standard, max)
- Content-hash embedding cache (96% hit rate on re-index)
- Deterministic grammar compression for memory entries

## [0.4.0] - 2025-04-10

### Added
- Cross-session memory: `record_decision`, `record_code_area`, `session_recall`
- Code graph with CALLS/IMPORTS edges and graph expansion
- `cce services` command for Ollama, dashboard, and MCP status
- Hybrid retrieval: vector + BM25 via Reciprocal Rank Fusion
- Confidence scoring with similarity (50%), keyword (30%), recency (20%) weights

## [0.3.0] - 2025-03-15

### Added
- Initial release with semantic indexing and MCP server
- Tree-sitter parsing for Python, JavaScript, TypeScript
- Git hooks for automatic re-indexing
- Token savings tracking
