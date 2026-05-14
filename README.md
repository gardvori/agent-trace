# 🔍 agent-trace

Trace and debug AI agent decisions. Think Chrome DevTools for AI agents.

## Features

- **Session Tracing** — Record every step of an agent's reasoning chain
- **LLM Call Tracking** — Log inputs, outputs, tokens, duration, model used
- **Tool Call Tracking** — Log tool name, args, results, duration
- **Decision Points** — Explicitly log why a decision was made
- **Error Tracking** — Capture and analyze error patterns
- **Performance Analysis** — Find slow steps, token usage patterns
- **Session Comparison** — Compare multiple sessions side by side
- **Zero Dependencies** — Pure Python stdlib + SQLite

## Installation

```bash
git clone https://github.com/gardvori/agent-trace.git
cd agent-trace
python3 agent_trace.py init
```

## Usage

```bash
# Initialize
python3 agent_trace.py init

# List sessions
python3 agent_trace.py sessions --agent meridian

# Show session details
python3 agent_trace.py show <session_id> --verbose

# Agent statistics
python3 agent_trace.py stats meridian --days 7

# Find slow steps
python3 agent_trace.py slow --threshold 5000

# Error patterns
python3 agent_trace.py errors --agent meridian

# Compare sessions
python3 agent_trace.py compare <session1> <session2>

# Export session
python3 agent_trace.py export <session_id> --output trace.json
```

## Programmatic Usage

```python
from agent_trace import TraceSession

with TraceSession("meridian") as trace:
    trace.log_llm_call(
        input_text="Should I deploy to pool X?",
        output_text="Yes, pool X meets all criteria",
        reasoning="Low volatility, high organic score",
        duration_ms=2500,
        tokens_input=1500,
        tokens_output=200,
        model="openai/gpt-oss-120b:free"
    )
    
    trace.log_tool_call(
        tool_name="deploy_position",
        tool_args={"pool": "X", "amount": 0.05},
        tool_result="Position opened successfully",
        duration_ms=5000
    )
```

## License

MIT
