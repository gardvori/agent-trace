#!/usr/bin/env python3
"""
agent-trace — CLI tool for tracing and debugging AI agent decisions.

Think "Chrome DevTools for AI agents."
Capture, inspect, and analyze agent decision chains, tool calls,
memory reads/writes, and reasoning steps.

Usage:
    agent-trace init                    Initialize tracing in current project
    agent-trace log <agent> <decision>  Log a decision event
    agent-trace show                    Show recent trace log
    agent-trace analyze                 Analyze patterns in agent behavior
    agent-trace export [--format json|html]  Export trace report
    agent-trace clear                   Clear trace log
    agent-trace --version               Show version
"""

import argparse
import json
import os
import sys
import hashlib
import datetime
from pathlib import Path

__version__ = "0.1.0"

TRACE_DIR = ".agent-trace"
TRACE_FILE = "trace.jsonl"
CONFIG_FILE = "config.json"

DECISION_TYPES = [
    "tool_call",
    "memory_read",
    "memory_write",
    "reasoning",
    "error",
    "fallback",
    "user_input",
    "observation",
]

COLORS = {
    "tool_call": "\033[36m",     # cyan
    "memory_read": "\033[34m",   # blue
    "memory_write": "\033[35m",  # magenta
    "reasoning": "\033[33m",     # yellow
    "error": "\033[31m",         # red
    "fallback": "\033[91m",      # light red
    "user_input": "\033[32m",    # green
    "observation": "\033[90m",   # gray
    "reset": "\033[0m",
    "bold": "\033[1m",
    "dim": "\033[2m",
}


def get_trace_dir():
    """Find or create .agent-trace directory."""
    cwd = Path.cwd()
    trace_dir = cwd / TRACE_DIR
    return trace_dir


def get_trace_path():
    return get_trace_dir() / TRACE_FILE


def get_config_path():
    return get_trace_dir() / CONFIG_FILE


def init_tracing(args=None):
    """Initialize agent-trace in current project."""
    trace_dir = get_trace_dir()
    trace_dir.mkdir(exist_ok=True)

    trace_path = get_trace_path()
    if not trace_path.exists():
        trace_path.touch()

    config_path = get_config_path()
    if not config_path.exists():
        config = {
            "version": __version__,
            "created": datetime.datetime.utcnow().isoformat() + "Z",
            "project": Path.cwd().name,
            "settings": {
                "max_events": 10000,
                "auto_export": False,
                "export_format": "json",
            },
        }
        config_path.write_text(json.dumps(config, indent=2))

    print(f"{COLORS['bold']}✓ agent-trace initialized{COLORS['reset']}")
    print(f"  Trace dir:  {trace_dir}")
    print(f"  Trace log:  {trace_path}")
    print(f"  Config:     {config_path}")
    print(f"\n  Log decisions with: agent-trace log <agent> <type> <message>")


def log_event(args):
    """Log a decision event to the trace."""
    trace_path = get_trace_path()
    trace_dir = get_trace_dir()

    if not trace_dir.exists():
        print(f"{COLORS['error']}Error: agent-trace not initialized. Run 'agent-trace init' first.{COLORS['reset']}")
        sys.exit(1)

    agent = args.agent
    decision_type = args.type or "observation"
    message = " ".join(args.message) if isinstance(args.message, list) else args.message

    if decision_type not in DECISION_TYPES:
        print(f"{COLORS['error']}Error: Unknown type '{decision_type}'. Valid types: {', '.join(DECISION_TYPES)}{COLORS['reset']}")
        sys.exit(1)

    event = {
        "id": hashlib.sha256(
            f"{datetime.datetime.utcnow().isoformat()}{agent}{message}".encode()
        ).hexdigest()[:12],
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "agent": agent,
        "type": decision_type,
        "message": message,
    }

    if args.data:
        try:
            event["data"] = json.loads(args.data)
        except json.JSONDecodeError:
            event["data"] = args.data

    with open(trace_path, "a") as f:
        f.write(json.dumps(event) + "\n")

    color = COLORS.get(decision_type, "")
    reset = COLORS["reset"]
    dim = COLORS["dim"]
    print(f"{dim}[{event['timestamp']}]{reset} {color}[{decision_type}]{reset} {COLORS['bold']}{agent}{reset}: {message}")


def show_trace(args):
    """Show recent trace log."""
    trace_path = get_trace_path()

    if not trace_path.exists():
        print(f"{COLORS['error']}No trace log found. Run 'agent-trace init' first.{COLORS['reset']}")
        sys.exit(1)

    lines = trace_path.read_text().strip().split("\n")
    lines = [l for l in lines if l.strip()]

    limit = args.limit if hasattr(args, "limit") else 50
    agent_filter = args.agent if hasattr(args, "agent") and args.agent else None
    type_filter = args.filter if hasattr(args, "filter") and args.filter else None

    events = []
    for line in lines:
        try:
            event = json.loads(line)
            if agent_filter and event.get("agent") != agent_filter:
                continue
            if type_filter and event.get("type") != type_filter:
                continue
            events.append(event)
        except json.JSONDecodeError:
            continue

    # Show last N events
    events = events[-limit:]

    if not events:
        print(f"{COLORS['dim']}No events found matching criteria.{COLORS['reset']}")
        return

    print(f"\n{COLORS['bold']}agent-trace — Last {len(events)} events{COLORS['reset']}")
    print(f"{COLORS['dim']}{'─' * 70}{COLORS['reset']}")

    for event in events:
        color = COLORS.get(event.get("type", ""), "")
        reset = COLORS["reset"]
        dim = COLORS["dim"]
        bold = COLORS["bold"]

        ts = event.get("timestamp", "")[:19]
        etype = event.get("type", "?")
        agent = event.get("agent", "?")
        msg = event.get("message", "")

        print(f"{dim}{ts}{reset} {color}[{etype:>12}]{reset} {bold}{agent}{reset}: {msg}")

        if event.get("data"):
            data_str = json.dumps(event["data"], indent=2)
            for dl in data_str.split("\n")[:5]:
                print(f"  {dim}└─ {dl}{reset}")

    print(f"{COLORS['dim']}{'─' * 70}{COLORS['reset']}")
    print(f"  Total events in log: {len(lines)}")


def analyze_trace(args):
    """Analyze patterns in agent behavior."""
    trace_path = get_trace_path()

    if not trace_path.exists():
        print(f"{COLORS['error']}No trace log found.{COLORS['reset']}")
        sys.exit(1)

    lines = trace_path.read_text().strip().split("\n")
    events = []
    for line in lines:
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    if not events:
        print(f"{COLORS['dim']}No events to analyze.{COLORS['reset']}")
        return

    # Analysis
    agents = {}
    types = {}
    errors = []
    timeline = []

    for e in events:
        agent = e.get("agent", "unknown")
        etype = e.get("type", "unknown")

        agents[agent] = agents.get(agent, 0) + 1
        types[etype] = types.get(etype, 0) + 1

        if etype == "error":
            errors.append(e)

    # Time range
    timestamps = [e.get("timestamp", "") for e in events if e.get("timestamp")]
    first_ts = timestamps[0][:19] if timestamps else "N/A"
    last_ts = timestamps[-1][:19] if timestamps else "N/A"

    print(f"\n{COLORS['bold']}agent-trace Analysis Report{COLORS['reset']}")
    print(f"{COLORS['dim']}{'═' * 50}{COLORS['reset']}")
    print(f"  Total events:    {len(events)}")
    print(f"  Time range:      {first_ts} → {last_ts}")
    print(f"  Unique agents:   {len(agents)}")
    print(f"  Errors:          {COLORS['error']}{len(errors)}{COLORS['reset']}")

    print(f"\n{COLORS['bold']}Events by Agent:{COLORS['reset']}")
    for agent, count in sorted(agents.items(), key=lambda x: -x[1]):
        bar = "█" * min(count, 40)
        print(f"  {agent:20s} {bar} {count}")

    print(f"\n{COLORS['bold']}Events by Type:{COLORS['reset']}")
    for etype, count in sorted(types.items(), key=lambda x: -x[1]):
        color = COLORS.get(etype, "")
        bar = "█" * min(count, 40)
        print(f"  {color}{etype:20s}{COLORS['reset']} {bar} {count}")

    if errors:
        print(f"\n{COLORS['bold']}{COLORS['error']}Recent Errors:{COLORS['reset']}")
        for err in errors[-5:]:
            ts = err.get("timestamp", "")[:19]
            agent = err.get("agent", "?")
            msg = err.get("message", "")
            print(f"  {COLORS['dim']}{ts}{COLORS['reset']} {COLORS['error']}{agent}{COLORS['reset']}: {msg}")

    # Decision chain analysis
    print(f"\n{COLORS['bold']}Decision Chain (last 10):{COLORS['reset']}")
    for e in events[-10:]:
        color = COLORS.get(e.get("type", ""), "")
        arrow = f"{color}→{COLORS['reset']}"
        print(f"  {arrow} [{e.get('type', '?')}] {e.get('agent', '?')}: {e.get('message', '')[:60]}")

    print(f"\n{COLORS['dim']}{'═' * 50}{COLORS['reset']}")


def export_trace(args):
    """Export trace report."""
    trace_path = get_trace_path()

    if not trace_path.exists():
        print(f"{COLORS['error']}No trace log found.{COLORS['reset']}")
        sys.exit(1)

    fmt = args.format if hasattr(args, "format") else "json"
    output = args.output if hasattr(args, "output") else f"agent-trace-report.{fmt}"

    lines = trace_path.read_text().strip().split("\n")
    events = []
    for line in lines:
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    if fmt == "json":
        report = {
            "generated": datetime.datetime.utcnow().isoformat() + "Z",
            "tool": "agent-trace",
            "version": __version__,
            "total_events": len(events),
            "events": events,
        }
        with open(output, "w") as f:
            json.dump(report, f, indent=2)

    elif fmt == "html":
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>agent-trace Report</title>
    <style>
        body {{ font-family: monospace; background: #1a1a2e; color: #eee; padding: 20px; }}
        h1 {{ color: #00d4ff; }}
        .event {{ padding: 8px; margin: 4px 0; border-left: 3px solid #333; background: #16213e; }}
        .tool_call {{ border-left-color: #00d4ff; }}
        .memory_read {{ border-left-color: #4a9eff; }}
        .memory_write {{ border-left-color: #ff6ec7; }}
        .reasoning {{ border-left-color: #ffd93d; }}
        .error {{ border-left-color: #ff4757; }}
        .fallback {{ border-left-color: #ff6b81; }}
        .user_input {{ border-left-color: #2ed573; }}
        .observation {{ border-left-color: #747d8c; }}
        .meta {{ color: #555; font-size: 0.85em; }}
        .badge {{ display: inline-block; padding: 2px 8px; border-radius: 3px; font-size: 0.8em; font-weight: bold; }}
        .stats {{ display: flex; gap: 20px; margin: 20px 0; }}
        .stat {{ background: #16213e; padding: 15px 25px; border-radius: 8px; text-align: center; }}
        .stat .number {{ font-size: 2em; color: #00d4ff; }}
    </style>
</head>
<body>
    <h1>🔍 agent-trace Report</h1>
    <p class="meta">Generated: {datetime.datetime.utcnow().isoformat()}Z | v{__version__}</p>
    <div class="stats">
        <div class="stat"><div class="number">{len(events)}</div><div>Events</div></div>
    </div>
    <h2>Event Log</h2>
"""
        for e in events:
            etype = e.get("type", "observation")
            ts = e.get("timestamp", "")[:19]
            agent = e.get("agent", "?")
            msg = e.get("message", "")
            html += f'    <div class="event {etype}">\n'
            html += f'        <span class="meta">{ts}</span> <span class="badge">[{etype}]</span> <strong>{agent}</strong>: {msg}\n'
            html += f'    </div>\n'

        html += """</body>
</html>"""
        with open(output, "w") as f:
            f.write(html)

    print(f"{COLORS['bold']}✓ Exported {len(events)} events → {output}{COLORS['reset']}")


def clear_trace(args):
    """Clear trace log."""
    trace_path = get_trace_path()
    if trace_path.exists():
        trace_path.write_text("")
        print(f"{COLORS['bold']}✓ Trace log cleared{COLORS['reset']}")
    else:
        print(f"{COLORS['dim']}No trace log to clear.{COLORS['reset']}")


def main():
    parser = argparse.ArgumentParser(
        prog="agent-trace",
        description="🔍 CLI tool for tracing and debugging AI agent decisions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  agent-trace init                              Initialize in current project
  agent-trace log my-agent tool_call "Called search API"
  agent-trace log my-agent error "API timeout after 30s"
  agent-trace log my-agent reasoning "Decided to retry with fallback"
  agent-trace show --limit 20                  Show last 20 events
  agent-trace show --agent my-agent            Filter by agent
  agent-trace show --filter error              Filter by type
  agent-trace analyze                          Analyze agent behavior
  agent-trace export --format html -o report.html   Export as HTML report
  agent-trace clear                            Clear trace log

Decision types: tool_call, memory_read, memory_write, reasoning, error, fallback, user_input, observation
""",
    )

    parser.add_argument("--version", action="version", version=f"agent-trace {__version__}")

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # init
    subparsers.add_parser("init", help="Initialize tracing in current project")

    # log
    log_parser = subparsers.add_parser("log", help="Log a decision event")
    log_parser.add_argument("agent", help="Agent name")
    log_parser.add_argument("type", nargs="?", default="observation", help="Decision type")
    log_parser.add_argument("message", nargs="+", help="Event message")
    log_parser.add_argument("--data", "-d", help="Additional JSON data")

    # show
    show_parser = subparsers.add_parser("show", help="Show recent trace log")
    show_parser.add_argument("--limit", "-n", type=int, default=50, help="Number of events (default: 50)")
    show_parser.add_argument("--agent", "-a", help="Filter by agent name")
    show_parser.add_argument("--filter", "-f", help="Filter by event type")

    # analyze
    subparsers.add_parser("analyze", help="Analyze patterns in agent behavior")

    # export
    export_parser = subparsers.add_parser("export", help="Export trace report")
    export_parser.add_argument("--format", choices=["json", "html"], default="json", help="Export format")
    export_parser.add_argument("--output", "-o", help="Output file path")

    # clear
    subparsers.add_parser("clear", help="Clear trace log")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    commands = {
        "init": init_tracing,
        "log": log_event,
        "show": show_trace,
        "analyze": analyze_trace,
        "export": export_trace,
        "clear": clear_trace,
    }

    handler = commands.get(args.command)
    if handler:
        handler(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
