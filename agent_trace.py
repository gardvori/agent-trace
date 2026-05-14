#!/usr/bin/env python3
"""
agent-trace — Trace and debug AI agent decisions
Think Chrome DevTools for AI agents.
"""

import sqlite3
import json
import time
import hashlib
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

# ── Configuration ──────────────────────────────────────────────────────────

DB_PATH = Path.home() / ".agent-trace" / "traces.db"

# ── Database ──────────────────────────────────────────────────────────────

def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS traces (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trace_id TEXT NOT NULL,
            agent TEXT NOT NULL,
            session_id TEXT,
            timestamp TEXT NOT NULL,
            step_number INTEGER NOT NULL,
            step_type TEXT NOT NULL,
            input_text TEXT,
            output_text TEXT,
            tool_name TEXT,
            tool_args TEXT,
            tool_result TEXT,
            reasoning TEXT,
            duration_ms REAL,
            tokens_input INTEGER,
            tokens_output INTEGER,
            model TEXT,
            metadata TEXT DEFAULT '{}'
        )
    """)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT UNIQUE NOT NULL,
            agent TEXT NOT NULL,
            started_at TEXT NOT NULL,
            ended_at TEXT,
            total_steps INTEGER DEFAULT 0,
            total_duration_ms REAL DEFAULT 0,
            total_tokens_input INTEGER DEFAULT 0,
            total_tokens_output INTEGER DEFAULT 0,
            status TEXT DEFAULT 'active',
            summary TEXT DEFAULT ''
        )
    """)
    
    conn.execute("CREATE INDEX IF NOT EXISTS idx_traces_session ON traces(session_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_traces_agent ON traces(agent)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_traces_timestamp ON traces(timestamp)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_traces_step_type ON traces(step_type)")
    
    conn.commit()
    return conn

def get_conn():
    return sqlite3.connect(str(DB_PATH))

# ── Trace Session ─────────────────────────────────────────────────────────

class TraceSession:
    """Context manager for tracing agent sessions."""
    
    def __init__(self, agent: str, session_id: str = None):
        self.agent = agent
        self.session_id = session_id or self._generate_id()
        self.step = 0
        self.started_at = datetime.now()
        self.conn = get_conn()
        
        self.conn.execute("""
            INSERT OR REPLACE INTO sessions (session_id, agent, started_at, status)
            VALUES (?, ?, ?, 'active')
        """, (self.session_id, self.agent, self.started_at.isoformat()))
        self.conn.commit()
    
    def _generate_id(self) -> str:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        h = hashlib.md5(f"{self.agent}{time.time()}".encode()).hexdigest()[:8]
        return f"{self.agent}_{ts}_{h}"
    
    def log_step(self, step_type: str, input_text: str = None, output_text: str = None,
                 tool_name: str = None, tool_args: dict = None, tool_result: str = None,
                 reasoning: str = None, duration_ms: float = None,
                 tokens_input: int = None, tokens_output: int = None,
                 model: str = None, metadata: dict = None):
        """Log a single step in the trace."""
        self.step += 1
        
        self.conn.execute("""
            INSERT INTO traces (trace_id, agent, session_id, timestamp, step_number, step_type,
                input_text, output_text, tool_name, tool_args, tool_result, reasoning,
                duration_ms, tokens_input, tokens_output, model, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            self.session_id, self.agent, self.session_id,
            datetime.now().isoformat(), self.step, step_type,
            input_text, output_text, tool_name,
            json.dumps(tool_args) if tool_args else None,
            tool_result, reasoning, duration_ms,
            tokens_input, tokens_output, model,
            json.dumps(metadata or {})
        ))
        self.conn.commit()
    
    def log_llm_call(self, input_text: str, output_text: str, reasoning: str = None,
                     duration_ms: float = None, tokens_input: int = None,
                     tokens_output: int = None, model: str = None):
        """Log an LLM call."""
        self.log_step("llm_call", input_text=input_text, output_text=output_text,
                     reasoning=reasoning, duration_ms=duration_ms,
                     tokens_input=tokens_input, tokens_output=tokens_output, model=model)
    
    def log_tool_call(self, tool_name: str, tool_args: dict, tool_result: str,
                      duration_ms: float = None):
        """Log a tool call."""
        self.log_step("tool_call", tool_name=tool_name, tool_args=tool_args,
                     tool_result=tool_result, duration_ms=duration_ms)
    
    def log_decision(self, reasoning: str, decision: str, context: str = None):
        """Log a decision point."""
        self.log_step("decision", input_text=context, output_text=decision,
                     reasoning=reasoning)
    
    def log_error(self, error: str, context: str = None):
        """Log an error."""
        self.log_step("error", input_text=context, output_text=error)
    
    def end(self, summary: str = None):
        """End the trace session."""
        ended_at = datetime.now()
        duration = (ended_at - self.started_at).total_seconds() * 1000
        
        totals = self.conn.execute("""
            SELECT COUNT(*), SUM(tokens_input), SUM(tokens_output)
            FROM traces WHERE session_id = ?
        """, (self.session_id,)).fetchone()
        
        self.conn.execute("""
            UPDATE sessions SET
                ended_at = ?, total_steps = ?, total_duration_ms = ?,
                total_tokens_input = ?, total_tokens_output = ?,
                status = 'completed', summary = ?
            WHERE session_id = ?
        """, (
            ended_at.isoformat(), totals[0] or 0, duration,
            totals[1] or 0, totals[2] or 0,
            summary or "", self.session_id
        ))
        self.conn.commit()
        self.conn.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.end()

# ── Query & Analysis ──────────────────────────────────────────────────────

def get_session(session_id: str) -> dict:
    """Get session details."""
    conn = get_conn()
    
    session = conn.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,)).fetchone()
    if not session:
        conn.close()
        return None
    
    steps = conn.execute("""
        SELECT step_number, step_type, input_text, output_text, tool_name,
               reasoning, duration_ms, tokens_input, tokens_output, model, timestamp
        FROM traces WHERE session_id = ? ORDER BY step_number
    """, (session_id,)).fetchall()
    
    conn.close()
    
    return {
        "session_id": session[1],
        "agent": session[2],
        "started_at": session[3],
        "ended_at": session[4],
        "total_steps": session[5],
        "total_duration_ms": session[6],
        "total_tokens_input": session[7],
        "total_tokens_output": session[8],
        "status": session[9],
        "summary": session[10],
        "steps": [{
            "step": s[0], "type": s[1], "input": s[2], "output": s[3],
            "tool": s[4], "reasoning": s[5], "duration_ms": s[6],
            "tokens_in": s[7], "tokens_out": s[8], "model": s[9],
            "timestamp": s[10]
        } for s in steps]
    }

def list_sessions(agent: str = None, limit: int = 20, status: str = None) -> list:
    """List recent sessions."""
    conn = get_conn()
    
    sql = "SELECT * FROM sessions WHERE 1=1"
    params = []
    
    if agent:
        sql += " AND agent = ?"
        params.append(agent)
    if status:
        sql += " AND status = ?"
        params.append(status)
    
    sql += " ORDER BY started_at DESC LIMIT ?"
    params.append(limit)
    
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    
    return [{
        "session_id": r[1], "agent": r[2], "started_at": r[3],
        "ended_at": r[4], "total_steps": r[5], "total_duration_ms": r[6],
        "total_tokens": (r[7] or 0) + (r[8] or 0),
        "status": r[9], "summary": r[10]
    } for r in rows]

def get_agent_stats(agent: str, days: int = 7) -> dict:
    """Get statistics for an agent."""
    conn = get_conn()
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    
    stats = conn.execute("""
        SELECT
            COUNT(DISTINCT session_id),
            AVG(total_steps),
            AVG(total_duration_ms),
            SUM(total_tokens_input),
            SUM(total_tokens_output),
            AVG(total_duration_ms / NULLIF(total_steps, 0))
        FROM sessions
        WHERE agent = ? AND started_at >= ? AND status = 'completed'
    """, (agent, cutoff)).fetchone()
    
    # Step type distribution
    step_types = conn.execute("""
        SELECT step_type, COUNT(*)
        FROM traces t
        JOIN sessions s ON s.session_id = t.session_id
        WHERE s.agent = ? AND s.started_at >= ?
        GROUP BY step_type
    """, (agent, cutoff)).fetchall()
    
    # Error count
    errors = conn.execute("""
        SELECT COUNT(*) FROM traces t
        JOIN sessions s ON s.session_id = t.session_id
        WHERE s.agent = ? AND s.started_at >= ? AND t.step_type = 'error'
    """, (agent, cutoff)).fetchone()[0]
    
    conn.close()
    
    return {
        "agent": agent,
        "period_days": days,
        "total_sessions": stats[0] or 0,
        "avg_steps_per_session": round(stats[1] or 0, 1),
        "avg_duration_ms": round(stats[2] or 0, 0),
        "total_tokens_input": stats[3] or 0,
        "total_tokens_output": stats[4] or 0,
        "avg_step_duration_ms": round(stats[5] or 0, 0),
        "step_types": {st[0]: st[1] for st in step_types},
        "errors": errors
    }

def find_slow_steps(agent: str = None, threshold_ms: float = 5000, limit: int = 20) -> list:
    """Find slow steps across sessions."""
    conn = get_conn()
    
    sql = """
        SELECT t.session_id, t.step_number, t.step_type, t.tool_name,
               t.duration_ms, t.model, t.timestamp, s.agent
        FROM traces t
        JOIN sessions s ON s.session_id = t.session_id
        WHERE t.duration_ms >= ?
    """
    params = [threshold_ms]
    
    if agent:
        sql += " AND s.agent = ?"
        params.append(agent)
    
    sql += " ORDER BY t.duration_ms DESC LIMIT ?"
    params.append(limit)
    
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    
    return [{
        "session_id": r[0], "step": r[1], "type": r[2], "tool": r[3],
        "duration_ms": r[4], "model": r[5], "timestamp": r[6], "agent": r[7]
    } for r in rows]

def find_error_patterns(agent: str = None, days: int = 7) -> list:
    """Find common error patterns."""
    conn = get_conn()
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    
    sql = """
        SELECT t.output_text, COUNT(*) as count, GROUP_CONCAT(DISTINCT t.tool_name)
        FROM traces t
        JOIN sessions s ON s.session_id = t.session_id
        WHERE t.step_type = 'error' AND s.started_at >= ?
    """
    params = [cutoff]
    
    if agent:
        sql += " AND s.agent = ?"
        params.append(agent)
    
    sql += " GROUP BY t.output_text ORDER BY count DESC LIMIT 10"
    
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    
    return [{"error": r[0][:200], "count": r[1], "tools": r[2]} for r in rows]

def compare_sessions(session_ids: list) -> dict:
    """Compare multiple sessions side by side."""
    sessions = []
    for sid in session_ids:
        s = get_session(sid)
        if s:
            sessions.append(s)
    
    if not sessions:
        return {"error": "No sessions found"}
    
    comparison = {
        "sessions": [],
        "common_tools": set(),
        "common_errors": set()
    }
    
    all_tools = []
    all_errors = []
    
    for s in sessions:
        tools = set()
        errors = set()
        for step in s["steps"]:
            if step["tool"]:
                tools.add(step["tool"])
            if step["type"] == "error":
                errors.add(step["output"][:100] if step["output"] else "")
        
        all_tools.append(tools)
        all_errors.append(errors)
        
        comparison["sessions"].append({
            "session_id": s["session_id"],
            "agent": s["agent"],
            "steps": s["total_steps"],
            "duration_ms": s["total_duration_ms"],
            "tokens": s["total_tokens_input"] + s["total_tokens_output"],
            "tools_used": list(tools),
            "errors": len([e for e in errors if e])
        })
    
    if all_tools:
        comparison["common_tools"] = list(set.intersection(*all_tools)) if len(all_tools) > 1 else list(all_tools[0])
    
    return comparison

# ── CLI Interface ──────────────────────────────────────────────────────────

def cmd_init(args):
    """Initialize database."""
    init_db()
    print(f"✅ Trace database initialized at {DB_PATH}")

def cmd_sessions(args):
    """List sessions."""
    sessions = list_sessions(agent=args.agent, limit=args.limit or 20)
    
    if not sessions:
        print("No sessions found.")
        return
    
    print(f"\n📋 Recent Sessions\n")
    print(f"{'Session ID':<35} {'Agent':<12} {'Steps':<8} {'Duration':<12} {'Tokens':<10} {'Status'}")
    print("─" * 90)
    
    for s in sessions:
        duration = f"{s['total_duration_ms']/1000:.1f}s" if s['total_duration_ms'] else "?"
        tokens = s.get('tokens', 0)
        print(f"{s['session_id'][:33]:<35} {s['agent']:<12} {s['total_steps']:<8} {duration:<12} {tokens:<10} {s['status']}")
    print()

def cmd_show(args):
    """Show session details."""
    session = get_session(args.session_id)
    
    if not session:
        print(f"❌ Session not found: {args.session_id}")
        return
    
    print(f"\n🔍 Session: {session['session_id']}")
    print(f"   Agent: {session['agent']} | Status: {session['status']}")
    print(f"   Duration: {session['total_duration_ms']/1000:.1f}s | Steps: {session['total_steps']}")
    print(f"   Tokens: {session['total_tokens_input'] + session['total_tokens_output']:,}")
    if session['summary']:
        print(f"   Summary: {session['summary']}")
    print()
    
    for step in session['steps']:
        icon = {"llm_call": "🤖", "tool_call": "🔧", "decision": "💡", "error": "❌"}.get(step['type'], "➡️")
        print(f"  {icon} Step {step['step']}: {step['type']}", end="")
        if step['tool']:
            print(f" ({step['tool']})", end="")
        if step['duration_ms']:
            print(f" [{step['duration_ms']:.0f}ms]", end="")
        print()
        
        if step['reasoning'] and args.verbose:
            print(f"     Reasoning: {step['reasoning'][:150]}")
        if step['output'] and args.verbose:
            out = step['output'][:200] + "..." if len(step['output']) > 200 else step['output']
            print(f"     Output: {out}")
    
    print()

def cmd_stats(args):
    """Show agent statistics."""
    stats = get_agent_stats(args.agent, days=args.days or 7)
    
    print(f"\n📊 Agent Stats: {stats['agent']} (last {stats['period_days']} days)\n")
    print(f"Sessions:           {stats['total_sessions']}")
    print(f"Avg Steps/Session:  {stats['avg_steps_per_session']}")
    print(f"Avg Duration:       {stats['avg_duration_ms']/1000:.1f}s")
    print(f"Avg Step Duration:  {stats['avg_step_duration_ms']:.0f}ms")
    print(f"Total Tokens:       {stats['total_tokens_input'] + stats['total_tokens_output']:,}")
    print(f"Errors:             {stats['errors']}")
    
    if stats['step_types']:
        print(f"\nStep Types:")
        for st, count in sorted(stats['step_types'].items(), key=lambda x: x[1], reverse=True):
            print(f"  {st}: {count}")
    print()

def cmd_slow(args):
    """Find slow steps."""
    steps = find_slow_steps(agent=args.agent, threshold_ms=args.threshold or 5000)
    
    if not steps:
        print("No slow steps found.")
        return
    
    print(f"\n🐌 Slow Steps (>{args.threshold or 5000}ms)\n")
    for s in steps:
        print(f"  {s['session_id'][:20]}... Step {s['step']}: {s['type']} ({s['tool'] or 'N/A'}) — {s['duration_ms']:.0f}ms")
    print()

def cmd_errors(args):
    """Find error patterns."""
    errors = find_error_patterns(agent=args.agent, days=args.days or 7)
    
    if not errors:
        print("No errors found.")
        return
    
    print(f"\n❌ Error Patterns\n")
    for e in errors:
        print(f"  ({e['count']}x) {e['error'][:100]}")
        if e['tools']:
            print(f"       Tools: {e['tools']}")
    print()

def cmd_compare(args):
    """Compare sessions."""
    comparison = compare_sessions(args.session_ids)
    
    if "error" in comparison:
        print(f"❌ {comparison['error']}")
        return
    
    print(f"\n📊 Session Comparison\n")
    for s in comparison["sessions"]:
        print(f"  {s['session_id'][:25]}...")
        print(f"    Agent: {s['agent']} | Steps: {s['steps']} | Duration: {s['duration_ms']/1000:.1f}s")
        print(f"    Tokens: {s['tokens']:,} | Errors: {s['errors']}")
        print(f"    Tools: {', '.join(s['tools_used'][:5])}")
        print()
    
    if comparison["common_tools"]:
        print(f"  Common tools: {', '.join(comparison['common_tools'])}")

def cmd_export(args):
    """Export session data."""
    session = get_session(args.session_id)
    if not session:
        print(f"❌ Session not found: {args.session_id}")
        return
    
    output = json.dumps(session, indent=2, default=str)
    
    if args.output:
        Path(args.output).write_text(output)
        print(f"✅ Exported to {args.output}")
    else:
        print(output)

# ── Entry Point ────────────────────────────────────────────────────────────

def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="agent-trace — Trace and debug AI agent decisions",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest="command")
    
    subparsers.add_parser("init", help="Initialize database")
    
    sessions_parser = subparsers.add_parser("sessions", help="List sessions")
    sessions_parser.add_argument("--agent", help="Filter by agent")
    sessions_parser.add_argument("--limit", type=int, default=20)
    
    show_parser = subparsers.add_parser("show", help="Show session details")
    show_parser.add_argument("session_id", help="Session ID")
    show_parser.add_argument("--verbose", "-v", action="store_true")
    
    stats_parser = subparsers.add_parser("stats", help="Show agent statistics")
    stats_parser.add_argument("agent", help="Agent name")
    stats_parser.add_argument("--days", type=int, default=7)
    
    slow_parser = subparsers.add_parser("slow", help="Find slow steps")
    slow_parser.add_argument("--agent", help="Filter by agent")
    slow_parser.add_argument("--threshold", type=float, default=5000)
    
    errors_parser = subparsers.add_parser("errors", help="Find error patterns")
    errors_parser.add_argument("--agent", help="Filter by agent")
    errors_parser.add_argument("--days", type=int, default=7)
    
    compare_parser = subparsers.add_parser("compare", help="Compare sessions")
    compare_parser.add_argument("session_ids", nargs="+", help="Session IDs")
    
    export_parser = subparsers.add_parser("export", help="Export session")
    export_parser.add_argument("session_id", help="Session ID")
    export_parser.add_argument("--output", help="Output file")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    commands = {
        "init": cmd_init, "sessions": cmd_sessions, "show": cmd_show,
        "stats": cmd_stats, "slow": cmd_slow, "errors": cmd_errors,
        "compare": cmd_compare, "export": cmd_export,
    }
    
    commands[args.command](args)

if __name__ == "__main__":
    main()
