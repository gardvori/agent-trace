#!/usr/bin/env python3
"""
agent-trace — Lightweight observability CLI for AI agents.

Trace decisions, tool calls, costs, and failures across any AI agent framework.
Think "Chrome DevTools for AI agents."

Usage:
    agent-trace init                    # Initialize tracing session
    agent-trace log <agent> <event>     # Log an agent event
    agent-trace show                    # Show current session trace
    agent-trace summary                 # Show session summary
    agent-trace export <format>         # Export trace (json|csv|html)
    agent-trace sessions                # List all sessions
    agent-trace watch                   # Watch live agent activity
"""

import argparse
import json
import csv
import os
import sys
import time
import uuid
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict

TRACE_DIR = Path.home() / ".agent-trace"
SESSION_FILE = TRACE_DIR / "current_session.json"
SESSIONS_DIR = TRACE_DIR / "sessions"

# ─── ANSI Colors ───────────────────────────────────────────────────────────────

class C:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    GRAY = "\033[90m"

def colored(text, color):
    return f"{color}{text}{C.RESET}"

# ─── Helpers ───────────────────────────────────────────────────────────────────

def ensure_dirs():
    TRACE_DIR.mkdir(parents=True, exist_ok=True)
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def duration_str(start, end):
    if not start or not end:
        return "N/A"
    try:
        s = datetime.fromisoformat(start)
        e = datetime.fromisoformat(end)
        d = (e - s).total_seconds()
        if d < 60:
            return f"{d:.1f}s"
        elif d < 3600:
            return f"{d/60:.1f}m"
        else:
            return f"{d/3600:.1f}h"
    except Exception:
        return "N/A"

def load_session(path):
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return None

def save_session(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)

def event_icon(event_type):
    icons = {
        "decision": "🧠",
        "tool_call": "🔧",
        "tool_result": "✅",
        "error": "❌",
        "warning": "⚠️",
        "cost": "💰",
        "start": "🚀",
        "end": "🏁",
        "info": "ℹ️",
        "llm_call": "🤖",
        "llm_response": "💬",
        "memory_read": "📖",
        "memory_write": "✍️",
        "user_input": "👤",
        "agent_spawn": "🐣",
        "agent_join": "🔗",
    }
    return icons.get(event_type, "📌")

def event_color(event_type):
    colors = {
        "error": C.RED,
        "warning": C.YELLOW,
        "cost": C.GREEN,
        "decision": C.CYAN,
        "tool_call": C.BLUE,
        "llm_call": C.MAGENTA,
    }
    return colors.get(event_type, C.RESET)

# ─── Commands ──────────────────────────────────────────────────────────────────

def cmd_init(args):
    ensure_dirs()
    session_id = str(uuid.uuid4())[:8]
    session = {
        "id": session_id,
        "agent": args.agent or "unknown",
        "started_at": now_iso(),
        "ended_at": None,
        "status": "active",
        "metadata": {},
        "events": [],
        "stats": {
            "total_events": 0,
            "errors": 0,
            "warnings": 0,
            "tool_calls": 0,
            "llm_calls": 0,
            "total_cost": 0.0,
            "total_tokens": 0,
        },
    }
    if args.label:
        session["metadata"]["label"] = args.label
    if args.framework:
        session["metadata"]["framework"] = args.framework

    save_session(SESSION_FILE, session)
    print(colored(f"🚀 Agent trace session initialized", C.BOLD))
    print(f"   Session ID : {colored(session_id, C.CYAN)}")
    print(f"   Agent      : {colored(session['agent'], C.YELLOW)}")
    if args.framework:
        print(f"   Framework  : {colored(args.framework, C.GREEN)}")
    print(f"   Started    : {session['started_at']}")
    print(f"   Storage    : {TRACE_DIR}")

def cmd_log(args):
    ensure_dirs()
    session = load_session(SESSION_FILE)
    if not session:
        print(colored("❌ No active session. Run 'agent-trace init' first.", C.RED))
        sys.exit(1)

    event = {
        "id": str(uuid.uuid4())[:6],
        "timestamp": now_iso(),
        "type": args.event_type,
        "agent": args.agent or session.get("agent", "unknown"),
        "message": args.message,
        "metadata": {},
    }

    if args.cost:
        event["metadata"]["cost"] = args.cost
        session["stats"]["total_cost"] += args.cost
    if args.tokens:
        event["metadata"]["tokens"] = args.tokens
        session["stats"]["total_tokens"] += args.tokens
    if args.tool:
        event["metadata"]["tool"] = args.tool
    if args.duration:
        event["metadata"]["duration_ms"] = args.duration
    if args.metadata:
        try:
            event["metadata"].update(json.loads(args.metadata))
        except json.JSONDecodeError:
            print(colored("⚠️ Invalid JSON metadata, skipping", C.YELLOW))

    session["events"].append(event)
    session["stats"]["total_events"] += 1

    # Update counters
    if args.event_type == "error":
        session["stats"]["errors"] += 1
    elif args.event_type == "warning":
        session["stats"]["warnings"] += 1
    elif args.event_type == "tool_call":
        session["stats"]["tool_calls"] += 1
    elif args.event_type == "llm_call":
        session["stats"]["llm_calls"] += 1

    save_session(SESSION_FILE, session)

    icon = event_icon(args.event_type)
    color = event_color(args.event_type)
    ts = datetime.fromisoformat(event["timestamp"]).strftime("%H:%M:%S")
    meta_str = ""
    if args.cost:
        meta_str += f" {colored(f'${args.cost:.4f}', C.GREEN)}"
    if args.tokens:
        meta_str += f" {colored(f'{args.tokens} tokens', C.YELLOW)}"
    print(f"  {colored(ts, C.GRAY)} {icon} {color}{args.event_type:12s}{C.RESET} │ {args.message}{meta_str}")

def cmd_show(args):
    ensure_dirs()
    session = load_session(SESSION_FILE)
    if not session:
        print(colored("❌ No active session found.", C.RED))
        sys.exit(1)

    print()
    print(colored("╔══════════════════════════════════════════════════════════╗", C.CYAN))
    print(colored("║              🔍 AGENT TRACE — SESSION VIEW              ║", C.CYAN))
    print(colored("╚══════════════════════════════════════════════════════════╝", C.CYAN))
    print()
    print(f"  Session  : {colored(session['id'], C.CYAN)}")
    print(f"  Agent    : {colored(session['agent'], C.YELLOW)}")
    print(f"  Status   : {colored(session['status'], C.GREEN if session['status'] == 'active' else C.RED)}")
    print(f"  Started  : {session['started_at']}")
    if session.get("ended_at"):
        print(f"  Ended    : {session['ended_at']}")
    print(f"  Duration : {colored(duration_str(session['started_at'], session.get('ended_at') or now_iso()), C.MAGENTA)}")
    print()

    if not session["events"]:
        print(colored("  (no events recorded yet)", C.DIM))
        print()
        return

    print(colored("  ── Events ──────────────────────────────────────────────", C.DIM))
    print()

    for ev in session["events"]:
        icon = event_icon(ev["type"])
        color = event_color(ev["type"])
        ts = datetime.fromisoformat(ev["timestamp"]).strftime("%H:%M:%S.%f")[:-3]
        meta_parts = []
        if "cost" in ev.get("metadata", {}):
            meta_parts.append(colored(f"${ev['metadata']['cost']:.4f}", C.GREEN))
        if "tokens" in ev.get("metadata", {}):
            meta_parts.append(colored(f"{ev['metadata']['tokens']}t", C.YELLOW))
        if "tool" in ev.get("metadata", {}):
            meta_parts.append(colored(f"[{ev['metadata']['tool']}]", C.BLUE))
        if "duration_ms" in ev.get("metadata", {}):
            meta_parts.append(colored(f"{ev['metadata']['duration_ms']}ms", C.MAGENTA))
        meta_str = " ".join(meta_parts)
        if meta_str:
            meta_str = " " + meta_str

        print(f"  {colored(ts, C.GRAY)} {icon} {color}{ev['type']:12s}{C.RESET} │ {ev['message']}{meta_str}")

    print()

def cmd_summary(args):
    ensure_dirs()
    session = load_session(SESSION_FILE)
    if not session:
        print(colored("❌ No active session found.", C.RED))
        sys.exit(1)

    stats = session["stats"]
    duration = duration_str(session["started_at"], session.get("ended_at") or now_iso())

    print()
    print(colored("╔══════════════════════════════════════════════════════════╗", C.GREEN))
    print(colored("║              📊 AGENT TRACE — SUMMARY                   ║", C.GREEN))
    print(colored("╚══════════════════════════════════════════════════════════╝", C.GREEN))
    print()
    print(f"  Session ID   : {colored(session['id'], C.CYAN)}")
    print(f"  Agent        : {colored(session['agent'], C.YELLOW)}")
    print(f"  Duration     : {colored(duration, C.MAGENTA)}")
    print()
    print(colored("  ── Statistics ─────────────────────────────────────────", C.DIM))
    print(f"  Total Events : {stats['total_events']}")
    print(f"  Tool Calls   : {colored(str(stats['tool_calls']), C.BLUE)}")
    print(f"  LLM Calls    : {colored(str(stats['llm_calls']), C.MAGENTA)}")
    print(f"  Errors       : {colored(str(stats['errors']), C.RED if stats['errors'] > 0 else C.GREEN)}")
    print(f"  Warnings     : {colored(str(stats['warnings']), C.YELLOW if stats['warnings'] > 0 else C.GREEN)}")
    cost_val = f'${stats["total_cost"]:.4f}'
    print(f"  Total Cost   : {colored(cost_val, C.GREEN)}")
    print(f"  Total Tokens : {colored(str(stats['total_tokens']), C.YELLOW)}")
    print()

    # Event type breakdown
    type_counts = defaultdict(int)
    for ev in session["events"]:
        type_counts[ev["type"]] += 1

    if type_counts:
        print(colored("  ── Event Breakdown ────────────────────────────────────", C.DIM))
        for etype, count in sorted(type_counts.items(), key=lambda x: -x[1]):
            icon = event_icon(etype)
            bar = "█" * min(count, 40)
            print(f"  {icon} {etype:14s} {colored(bar, C.CYAN)} {count}")
        print()

    # Error details
    errors = [e for e in session["events"] if e["type"] == "error"]
    if errors:
        print(colored("  ── Errors ─────────────────────────────────────────────", C.RED))
        for err in errors:
            ts = datetime.fromisoformat(err["timestamp"]).strftime("%H:%M:%S")
            print(f"  {colored(ts, C.GRAY)} ❌ {err['message']}")
        print()

def cmd_export(args):
    ensure_dirs()
    session = load_session(SESSION_FILE)
    if not session:
        print(colored("❌ No active session found.", C.RED))
        sys.exit(1)

    fmt = args.format.lower()
    out_path = args.output or f"agent-trace-{session['id']}.{fmt}"

    if fmt == "json":
        with open(out_path, "w") as f:
            json.dump(session, f, indent=2, default=str)

    elif fmt == "csv":
        with open(out_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "type", "agent", "message", "cost", "tokens", "tool", "duration_ms"])
            for ev in session["events"]:
                meta = ev.get("metadata", {})
                writer.writerow([
                    ev["timestamp"], ev["type"], ev["agent"], ev["message"],
                    meta.get("cost", ""), meta.get("tokens", ""),
                    meta.get("tool", ""), meta.get("duration_ms", ""),
                ])

    elif fmt == "html":
        html = _generate_html(session)
        with open(out_path, "w") as f:
            f.write(html)

    else:
        print(colored(f"❌ Unknown format: {fmt}. Use json, csv, or html.", C.RED))
        sys.exit(1)

    print(colored(f"✅ Exported to {out_path}", C.GREEN))

def _generate_html(session):
    events_html = ""
    for ev in session["events"]:
        icon = event_icon(ev["type"])
        ts = datetime.fromisoformat(ev["timestamp"]).strftime("%H:%M:%S")
        meta = ev.get("metadata", {})
        meta_str = ", ".join(f"{k}={v}" for k, v in meta.items())
        events_html += f"""
        <tr>
            <td>{ts}</td>
            <td>{icon} {ev['type']}</td>
            <td>{ev['agent']}</td>
            <td>{ev['message']}</td>
            <td>{meta_str}</td>
        </tr>"""

    stats = session["stats"]
    return f"""<!DOCTYPE html>
<html><head><title>Agent Trace — {session['id']}</title>
<style>
    body {{ font-family: monospace; background: #1a1a2e; color: #eee; padding: 2rem; }}
    h1 {{ color: #00d4ff; }}
    table {{ border-collapse: collapse; width: 100%; margin-top: 1rem; }}
    th, td {{ padding: 0.5rem 1rem; text-align: left; border-bottom: 1px solid #333; }}
    th {{ color: #00d4ff; }}
    .stats {{ display: flex; gap: 2rem; margin: 1rem 0; }}
    .stat {{ background: #16213e; padding: 1rem 1.5rem; border-radius: 8px; }}
    .stat-value {{ font-size: 1.5rem; font-weight: bold; color: #00d4ff; }}
</style></head>
<body>
<h1>🔍 Agent Trace Report</h1>
<p>Session: {session['id']} | Agent: {session['agent']} | Status: {session['status']}</p>
<div class="stats">
    <div class="stat"><div class="stat-value">{stats['total_events']}</div>Events</div>
    <div class="stat"><div class="stat-value">{stats['tool_calls']}</div>Tool Calls</div>
    <div class="stat"><div class="stat-value">{stats['llm_calls']}</div>LLM Calls</div>
    <div class="stat"><div class="stat-value" style="color:#ff6b6b">{stats['errors']}</div>Errors</div>
    <div class="stat"><div class="stat-value" style="color:#51cf66">${stats['total_cost']:.4f}</div>Cost</div>
    <div class="stat"><div class="stat-value" style="color:#ffd43b">{stats['total_tokens']}</div>Tokens</div>
</div>
<table>
<tr><th>Time</th><th>Type</th><th>Agent</th><th>Message</th><th>Metadata</th></tr>
{events_html}
</table>
</body></html>"""

def cmd_sessions(args):
    ensure_dirs()
    sessions = []
    for f in sorted(SESSIONS_DIR.iterdir(), reverse=True):
        if f.suffix == ".json":
            with open(f) as fp:
                s = json.load(fp)
            sessions.append(s)

    # Also check current session
    current = load_session(SESSION_FILE)
    if current:
        sessions.insert(0, current)

    if not sessions:
        print(colored("No sessions found.", C.DIM))
        return

    print()
    print(colored("  📋 Agent Trace Sessions", C.BOLD))
    print()
    for s in sessions:
        status_color = C.GREEN if s["status"] == "active" else C.GRAY
        dur = duration_str(s["started_at"], s.get("ended_at") or now_iso())
        err_str = ""
        if s["stats"]["errors"] > 0:
            err_str = colored(f" ({s['stats']['errors']} errors)", C.RED)
        print(f"  {colored(s['id'], C.CYAN)}  {colored(s['agent'], C.YELLOW):20s}  {colored(s['status'], status_color):8s}  {dur:8s}  {s['stats']['total_events']} events{err_str}")
    print()

def cmd_end(args):
    ensure_dirs()
    session = load_session(SESSION_FILE)
    if not session:
        print(colored("❌ No active session.", C.RED))
        sys.exit(1)

    session["ended_at"] = now_iso()
    session["status"] = "completed"

    # Save to sessions archive
    archive_path = SESSIONS_DIR / f"{session['id']}_{int(time.time())}.json"
    save_session(archive_path, session)
    save_session(SESSION_FILE, session)

    print(colored(f"🏁 Session {session['id']} ended and archived.", C.GREEN))
    print(f"   Archive: {archive_path}")

def cmd_watch(args):
    ensure_dirs()
    print(colored("👁️  Watching agent activity... (Ctrl+C to stop)", C.CYAN))
    print()
    last_count = 0
    try:
        while True:
            session = load_session(SESSION_FILE)
            if session and len(session["events"]) > last_count:
                new_events = session["events"][last_count:]
                for ev in new_events:
                    icon = event_icon(ev["type"])
                    color = event_color(ev["type"])
                    ts = datetime.fromisoformat(ev["timestamp"]).strftime("%H:%M:%S")
                    print(f"  {colored(ts, C.GRAY)} {icon} {color}{ev['type']:12s}{C.RESET} │ {ev['message']}")
                last_count = len(session["events"])
            time.sleep(1)
    except KeyboardInterrupt:
        print()
        print(colored("Watch stopped.", C.DIM))

# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        prog="agent-trace",
        description="🔍 Lightweight observability CLI for AI agents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command")

    # init
    p_init = sub.add_parser("init", help="Initialize a new tracing session")
    p_init.add_argument("--agent", "-a", help="Agent name")
    p_init.add_argument("--framework", "-f", help="Agent framework (e.g., hermes, langchain, crewai)")
    p_init.add_argument("--label", "-l", help="Session label")

    # log
    p_log = sub.add_parser("log", help="Log an agent event")
    p_log.add_argument("event_type", help="Event type (decision, tool_call, error, llm_call, etc.)")
    p_log.add_argument("message", help="Event message")
    p_log.add_argument("--agent", "-a", help="Agent name (overrides session default)")
    p_log.add_argument("--cost", "-c", type=float, help="Cost in USD")
    p_log.add_argument("--tokens", "-t", type=int, help="Token count")
    p_log.add_argument("--tool", help="Tool name (for tool_call events)")
    p_log.add_argument("--duration", "-d", type=int, help="Duration in milliseconds")
    p_log.add_argument("--metadata", "-m", help="Additional JSON metadata")

    # show
    sub.add_parser("show", help="Show current session trace")

    # summary
    sub.add_parser("summary", help="Show session summary")

    # export
    p_export = sub.add_parser("export", help="Export trace (json, csv, html)")
    p_export.add_argument("format", choices=["json", "csv", "html"], help="Export format")
    p_export.add_argument("--output", "-o", help="Output file path")

    # sessions
    sub.add_parser("sessions", help="List all sessions")

    # end
    sub.add_parser("end", help="End current session and archive")

    # watch
    sub.add_parser("watch", help="Watch live agent activity")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    commands = {
        "init": cmd_init,
        "log": cmd_log,
        "show": cmd_show,
        "summary": cmd_summary,
        "export": cmd_export,
        "sessions": cmd_sessions,
        "end": cmd_end,
        "watch": cmd_watch,
    }

    commands[args.command](args)

if __name__ == "__main__":
    main()
