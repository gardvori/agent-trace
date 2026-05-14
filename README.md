# 🔍 agent-trace

**Lightweight observability CLI for AI agents.**

Trace decisions, tool calls, costs, and failures across any AI agent framework.
Think *"Chrome DevTools for AI agents."*

## Why agent-trace?

AI agents are getting more complex — multi-step reasoning, tool use, memory access, LLM calls — but there's no standard way to **observe what they're doing**. When an agent fails, you're left guessing:

- Which tool call went wrong?
- How much did this agent run cost?
- What decisions led to this outcome?
- How long did each step take?

`agent-trace` solves this with a simple CLI that any agent (or developer) can use to log, inspect, and export agent activity.

## Features

- 🚀 **Zero-config init** — Start tracing in one command
- 📊 **Rich event types** — decisions, tool calls, LLM calls, errors, costs, memory ops
- 💰 **Cost tracking** — Track per-event and total costs
- 🔢 **Token counting** — Monitor token usage across LLM calls
- 📈 **Summary dashboard** — Beautiful terminal summary with event breakdown
- 📁 **Multi-format export** — JSON, CSV, and HTML reports
- 👁️ **Live watch mode** — Real-time monitoring of agent activity
- 📋 **Session management** — Archive and list past sessions
- 🎨 **Color-coded output** — Easy-to-read terminal UI

## Installation

```bash
# Clone the repo
git clone https://github.com/gardvori/agent-trace.git
cd agent-trace

# No dependencies! Uses only Python stdlib
# Requires Python 3.10+
python3 --version

# Optional: add to PATH
chmod +x agent_trace.py
ln -s "$(pwd)/agent_trace.py" /usr/local/bin/agent-trace
```

## Quick Start

```bash
# 1. Initialize a session
agent-trace init --agent "my-agent" --framework "hermes" --label "testing"

# 2. Log events as your agent runs
agent-trace log decision "Choosing to use search tool" --agent "my-agent"
agent-trace log tool_call "Calling search_api" --tool "search" --duration 245
agent-trace log tool_result "Got 5 results"
agent-trace log llm_call "Sending prompt to GPT-4" --tokens 150 --cost 0.0045
agent-trace log llm_response "Received completion" --tokens 80 --cost 0.0024
agent-trace log error "Rate limit hit on search_api"
agent-trace log decision "Falling back to cached results"

# 3. View the full trace
agent-trace show

# 4. Get a summary
agent-trace summary

# 5. Export for sharing
agent-trace export html --output report.html
agent-trace export json
agent-trace export csv

# 6. End and archive the session
agent-trace end

# 7. List all past sessions
agent-trace sessions

# 8. Watch live activity
agent-trace watch
```

## Event Types

| Type | Icon | Description |
|------|------|-------------|
| `decision` | 🧠 | Agent made a decision |
| `tool_call` | 🔧 | Agent called a tool |
| `tool_result` | ✅ | Tool returned a result |
| `llm_call` | 🤖 | LLM API call sent |
| `llm_response` | 💬 | LLM response received |
| `error` | ❌ | Something went wrong |
| `warning` | ⚠️ | Warning condition |
| `cost` | 💰 | Cost-related event |
| `memory_read` | 📖 | Read from agent memory |
| `memory_write` | ✍️ | Wrote to agent memory |
| `user_input` | 👤 | User provided input |
| `agent_spawn` | 🐣 | Spawned a sub-agent |
| `agent_join` | 🔗 | Sub-agent joined/completed |
| `info` | ℹ️ | General information |
| `start` | 🚀 | Session/agent started |
| `end` | 🏁 | Session/agent ended |

## Integration Example

```python
import subprocess
import json

def trace_event(event_type, message, **kwargs):
    cmd = ["agent-trace", "log", event_type, message]
    if "cost" in kwargs:
        cmd.extend(["--cost", str(kwargs["cost"])])
    if "tokens" in kwargs:
        cmd.extend(["--tokens", str(kwargs["tokens"])])
    if "tool" in kwargs:
        cmd.extend(["--tool", kwargs["tool"]])
    if "duration" in kwargs:
        cmd.extend(["--duration", str(kwargs["duration"])])
    subprocess.run(cmd)

# In your agent code:
trace_event("start", "Agent session started")
trace_event("decision", "Need to search for user data")
trace_event("tool_call", "Calling database.query", tool="database", duration=120)
trace_event("llm_call", "Sending context to LLM", tokens=2000, cost=0.006)
trace_event("end", "Task completed successfully")
```

## Storage

All trace data is stored locally in `~/.agent-trace/`:

```
~/.agent-trace/
├── current_session.json      # Active session
└── sessions/
    ├── a1b2c3d4_1715600000.json   # Archived sessions
    └── e5f6g7h8_1715603600.json
```

## License

MIT License — see [LICENSE](LICENSE) for details.

## Contributing

Contributions welcome! Areas we'd love help with:

- Plugin system for custom event types
- Web dashboard (React/Vue)
- Integration adapters (LangChain, CrewAI, AutoGen, Hermes)
- Prometheus/Grafana export
- OpenTelemetry support

---

Built with ❤️ by [gardvori](https://github.com/gardvori)
