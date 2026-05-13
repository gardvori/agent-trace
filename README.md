# 🔍 agent-trace

**CLI tool for tracing and debugging AI agent decisions.**

Think "Chrome DevTools for AI agents."

`agent-trace` captures, inspects, and analyzes agent decision chains, tool calls, memory reads/writes, and reasoning steps. Log events from any agent framework, then analyze patterns, export reports, and debug failures — all from the terminal.

## Why agent-trace?

As AI agents become more complex, understanding *why* an agent made a specific decision becomes critical. Existing observability tools (Langfuse, LangSmith) are cloud-hosted SaaS platforms. `agent-trace` is:

- **Local-first** — all data stays in your project directory
- **Framework-agnostic** — works with any agent framework (LangChain, CrewAI, AutoGen, custom)
- **Zero dependencies** — pure Python, no external packages required
- **CLI-native** — pipe-friendly, scriptable, CI/CD compatible

## Installation

```bash
pip install agent-trace
```

Or install from source:

```bash
git clone https://github.com/gardvori/agent-trace.git
cd agent-trace
pip install -e .
```

## Quick Start

```bash
# 1. Initialize in your project
cd your-agent-project
agent-trace init

# 2. Log events from your agent code
agent-trace log my-agent tool_call "Called OpenAI API (gpt-4)"
agent-trace log my-agent reasoning "Decided to use search tool based on user query"
agent-trace log my-agent memory_read "Retrieved context from session-abc123"
agent-trace log my-agent error "Rate limited by API, switching to fallback model"

# 3. View recent events
agent-trace show

# 4. Analyze agent behavior
agent-trace analyze

# 5. Export report
agent-trace export --format html -o report.html
```

## Commands

| Command | Description |
|---------|-------------|
| `agent-trace init` | Initialize tracing in current project |
| `agent-trace log <agent> <type> <message>` | Log a decision event |
| `agent-trace show` | Show recent trace log |
| `agent-trace analyze` | Analyze patterns in agent behavior |
| `agent-trace export` | Export trace report (JSON or HTML) |
| `agent-trace clear` | Clear trace log |

## Event Types

| Type | Description |
|------|-------------|
| `tool_call` | Agent invoked an external tool/API |
| `memory_read` | Agent read from memory |
| `memory_write` | Agent wrote to memory |
| `reasoning` | Agent reasoning step |
| `error` | Error or exception occurred |
| `fallback` | Agent used fallback behavior |
| `user_input` | User input received |
| `observation` | General observation (default) |

## Filtering & Search

```bash
# Show last 20 events
agent-trace show --limit 20

# Filter by agent name
agent-trace show --agent my-agent

# Filter by event type
agent-trace show --filter error

# Combine filters
agent-trace show --agent my-agent --filter error --limit 10
```

## Export Formats

### JSON Export
```bash
agent-trace export --format json -o trace-report.json
```

### HTML Report
```bash
agent-trace export --format html -o trace-report.html
```
Generates a styled HTML report with color-coded events, statistics, and timeline.

## Integration Example

```python
# In your agent code, shell out to log events:
import subprocess

def log_event(agent, event_type, message):
    subprocess.run([
        "agent-trace", "log", agent, event_type, message
    ], capture_output=True)

# Usage in your agent:
log_event("trading-agent", "tool_call", "Fetched BTC price: $67,432")
log_event("trading-agent", "reasoning", "Price above threshold, considering sell")
log_event("tracing-agent", "error", "API timeout after 30s")
```

## Trace Data Format

Events are stored as JSON Lines in `.agent-trace/trace.jsonl`:

```json
{"id": "a1b2c3d4e5f6", "timestamp": "2026-05-13T16:30:00Z", "agent": "my-agent", "type": "tool_call", "message": "Called search API"}
{"id": "b2c3d4e5f6a1", "timestamp": "2026-05-13T16:30:01Z", "agent": "my-agent", "type": "reasoning", "message": "Found 3 relevant results"}
```

## Configuration

`.agent-trace/config.json`:

```json
{
  "version": "0.1.0",
  "created": "2026-05-13T16:00:00Z",
  "project": "my-agent-project",
  "settings": {
    "max_events": 10000,
    "auto_export": false,
    "export_format": "json"
  }
}
```

## Roadmap

- [ ] Real-time streaming mode (`agent-trace watch`)
- [ ] Agent decision tree visualization
- [ ] Cost attribution per agent action
- [ ] Integration adapters (LangChain, CrewAI, AutoGen)
- [ ] Web dashboard (`agent-trace serve`)
- [ ] Multi-project aggregation

## License

MIT License — see [LICENSE](LICENSE) for details.
