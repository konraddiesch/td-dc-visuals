#!/usr/bin/env python3
"""
MCP server for TouchDesigner .chan file analysis.

Provides Claude Code with tools to analyze and plot .chan files
(performance channel recordings from TouchDesigner).

Protocol: JSON-RPC 2.0 over stdio (MCP stdio transport).

Tools:
  - chan_info        — list channels, duration, sample count
  - chan_analyze     — per-channel stats (global max, local min, mean, etc.)
  - chan_plot        — generate a plot and return the file path
  - chan_list        — find .chan files relative to the project root
"""

import json
import os
import sys
import subprocess
from pathlib import Path

# ── helpers ──────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parent.parent  # tools/ is one level in


def _msg(obj: dict):
    """Write a JSON-RPC message to stdout (MCP transport)."""
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


def _err(msg: str):
    """Write a log message to stderr (visible in Claude Code MCP logs)."""
    print(f"[chan_mcp] {msg}", file=sys.stderr, flush=True)


def _chan_files():
    """Yield .chan file paths from visuals/ and tools/."""
    for pattern in ["**/*.chan", "../**/*.chan"]:
        for p in PROJECT_ROOT.glob(pattern):
            if p.suffix == ".chan":
                yield p.resolve()


# ── tool implementations ─────────────────────────────────────────────────

def tool_chan_list(args: dict) -> dict:
    """List all .chan files found in the project."""
    files = sorted(set(_chan_files()))
    if not files:
        return {"content": [{"type": "text", "text": "No .chan files found."}]}

    lines = [f"Found {len(files)} .chan file(s):\n"]
    for f in files:
        rel = f.relative_to(PROJECT_ROOT)
        size = f.stat().st_size
        lines.append(f"  {rel}  ({size // 1024} KB)")
    return {"content": [{"type": "text", "text": "\n".join(lines)}]}


def tool_chan_info(args: dict) -> dict:
    """Print channel count, duration, and channel names of a .chan file."""
    fpath = _resolve_path(args.get("file", ""))
    if not fpath:
        return {"content": [{"type": "text", "text": f"File not found: {args.get('file')}"}]}

    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "tools" / "plot_chan.py"), "--summary", str(fpath)],
        capture_output=True, text=True, timeout=30, cwd=PROJECT_ROOT,
    )
    text = result.stdout.strip() or result.stderr.strip() or "No output"
    return {"content": [{"type": "text", "text": text}]}


def tool_chan_analyze(args: dict) -> dict:
    """Run full statistical analysis (global max, local min, mean, etc.)."""
    fpath = _resolve_path(args.get("file", ""))
    if not fpath:
        return {"content": [{"type": "text", "text": f"File not found: {args.get('file')}"}]}

    cmd = [sys.executable, str(PROJECT_ROOT / "tools" / "chan_stats.py"), str(fpath)]
    channels = args.get("channels")
    if channels:
        cmd.extend(["--channel"] + channels)
    if args.get("peak_distance"):
        cmd.extend(["--peak-distance", str(args["peak_distance"])])

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60, cwd=PROJECT_ROOT)
    text = result.stdout.strip() or result.stderr.strip() or "No output"
    return {"content": [{"type": "text", "text": text}]}


def tool_chan_plot(args: dict) -> dict:
    """Generate a plot of .chan channels and save to a PNG."""
    fpath = _resolve_path(args.get("file", ""))
    if not fpath:
        return {"content": [{"type": "text", "text": f"File not found: {args.get('file')}"}]}

    output = args.get("output") or str(
        PROJECT_ROOT / "tools" / f"{fpath.stem}_plot.png"
    )

    cmd = [
        sys.executable, str(PROJECT_ROOT / "tools" / "plot_chan.py"),
        str(fpath), "--output", output,
    ]
    channels = args.get("channels")
    if channels:
        cmd.extend(["--channels"] + channels)
    if args.get("window"):
        cmd.extend(["--window", str(args["window"])])

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120, cwd=PROJECT_ROOT)
    if result.returncode != 0:
        return {"content": [{"type": "text", "text": (result.stderr or result.stdout or f"Exit code {result.returncode}").strip()}]}

    rel = Path(output).relative_to(PROJECT_ROOT)
    return {
        "content": [
            {"type": "text", "text": f"Plot saved to {output}\n"},
        ]
    }


# ── routing ──────────────────────────────────────────────────────────────

TOOLS = {
    "chan_list": {
        "description": "Find all .chan files in the project (recursive search). No arguments needed.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
        "handler": tool_chan_list,
    },
    "chan_info": {
        "description": "Quick overview of a .chan file: channel count, names, duration.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file": {
                    "type": "string",
                    "description": "Path to .chan file (absolute or relative to project root)",
                }
            },
            "required": ["file"],
        },
        "handler": tool_chan_info,
    },
    "chan_analyze": {
        "description": "Per-channel statistics: global max, local min between first/last peak, mean, median, std dev, variance. Leading/trailing zeros are trimmed.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file": {
                    "type": "string",
                    "description": "Path to .chan file",
                },
                "channels": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Specific channels to analyze (default: all)",
                },
                "peak_distance": {
                    "type": "integer",
                    "description": "Minimum sample distance between peaks (default: 5)",
                },
            },
            "required": ["file"],
        },
        "handler": tool_chan_analyze,
    },
    "chan_plot": {
        "description": "Generate a matplotlib plot of .chan channels, saved as PNG.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file": {
                    "type": "string",
                    "description": "Path to .chan file",
                },
                "channels": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Channels to plot (default: all)",
                },
                "output": {
                    "type": "string",
                    "description": "Output PNG path (default: tools/<filename>_plot.png)",
                },
                "window": {
                    "type": "integer",
                    "description": "Only plot last N samples (e.g. 600 = 10s)",
                },
            },
            "required": ["file"],
        },
        "handler": tool_chan_plot,
    },
}


def _resolve_path(raw: str) -> Path | None:
    """Resolve a file path — try absolute, then relative to project root."""
    p = Path(raw)
    if p.is_absolute():
        return p if p.exists() else None
    # relative → try from project root
    p2 = PROJECT_ROOT / raw
    if p2.exists():
        return p2
    # try from visuals/
    p3 = PROJECT_ROOT / "visuals" / raw
    return p3 if p3.exists() else None


# ── JSON-RPC 2.0 stdio loop ─────────────────────────────────────────────

def main():
    _err("chan_mcp server starting...")
    initialized = False

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError as e:
            _err(f"Invalid JSON: {e}")
            continue

        req_id = req.get("id")
        method = req.get("method")
        params = req.get("params", {})

        # ── initialization ──
        if method == "initialize":
            _msg({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "chan-tools", "version": "1.0.0"},
                },
            })
            initialized = True
            continue

        if method == "notifications/initialized":
            _err("initialized notification received")
            continue

        if not initialized:
            _msg({
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32000, "message": "Server not initialized"},
            })
            continue

        # ── tools/list ──
        if method == "tools/list":
            tool_list = []
            for name, t in TOOLS.items():
                tool_list.append({
                    "name": name,
                    "description": t["description"],
                    "inputSchema": t["inputSchema"],
                })
            _msg({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"tools": tool_list},
            })
            continue

        # ── tools/call ──
        if method == "tools/call":
            name = params.get("name", "")
            arguments = params.get("arguments", {})
            tool = TOOLS.get(name)
            if not tool:
                _msg({
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32601, "message": f"Unknown tool: {name}"},
                })
                continue
            try:
                result = tool["handler"](arguments)
                _msg({"jsonrpc": "2.0", "id": req_id, "result": result})
            except Exception as e:
                _err(f"Tool {name} error: {e}")
                _msg({
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32603, "message": str(e)},
                })
            continue

        # ── shutdown ──
        if method == "shutdown":
            _msg({"jsonrpc": "2.0", "id": req_id, "result": None})
            break

        if method == "exit":
            break

        _err(f"Unknown method: {method}")


if __name__ == "__main__":
    main()