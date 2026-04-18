#!/usr/bin/env python3
"""MCP protocol smoke test.

Spawns greenode-mcp-server as a stdio subprocess and walks the basic
MCP handshake:

    initialize → notifications/initialized → tools/list → tools/call

Uses GRN_MCP_SPEC_DIR to avoid network dependency on the docs portal.
Exits 0 on success, non-zero on any failure.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path


EXPECTED_TOOLS = {
    "search_api",
    "call_api",
    "list_k8s_resources",
    "get_pod_logs",
    "get_k8s_events",
    "list_api_versions",
    "manage_k8s_resource",
    "apply_yaml",
}

READ_TIMEOUT = 10.0


async def _send(proc: asyncio.subprocess.Process, msg: dict) -> None:
    assert proc.stdin is not None
    proc.stdin.write((json.dumps(msg) + "\n").encode())
    await proc.stdin.drain()


async def _recv(proc: asyncio.subprocess.Process, expect_id: int | None = None) -> dict:
    assert proc.stdout is not None
    while True:
        try:
            line = await asyncio.wait_for(proc.stdout.readline(), timeout=READ_TIMEOUT)
        except asyncio.TimeoutError as e:
            raise RuntimeError(f"timeout waiting for response id={expect_id}") from e
        if not line:
            raise RuntimeError("server closed stdout without replying")
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue  # skip non-JSON log lines
        if expect_id is None or msg.get("id") == expect_id:
            return msg


def _write_fixture_spec(fixture_dir: Path) -> None:
    fixture_dir.mkdir(parents=True, exist_ok=True)
    (fixture_dir / "vks.json").write_text(json.dumps({
        "openapi": "3.0.0",
        "info": {"title": "VKS API"},
        "paths": {"/v1/clusters": {"get": {"summary": "list clusters"}}},
    }))


async def _handshake(proc: asyncio.subprocess.Process) -> None:
    await _send(proc, {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "smoke-test", "version": "1.0"},
        },
    })
    resp = await _recv(proc, expect_id=1)
    if "result" not in resp:
        raise RuntimeError(f"initialize failed: {resp}")
    server_name = resp["result"].get("serverInfo", {}).get("name")
    if server_name != "greenode-mcp-server":
        raise RuntimeError(f"unexpected server name: {server_name!r}")
    print("OK  initialize")
    await _send(proc, {"jsonrpc": "2.0", "method": "notifications/initialized"})


async def _check_tools_list(proc: asyncio.subprocess.Process) -> None:
    await _send(proc, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    resp = await _recv(proc, expect_id=2)
    tools = resp.get("result", {}).get("tools") or []
    names = {t["name"] for t in tools}
    missing = EXPECTED_TOOLS - names
    if missing:
        raise RuntimeError(f"missing tools: {sorted(missing)}; got {sorted(names)}")
    print(f"OK  tools/list ({len(tools)} tools)")


async def _check_tools_call(proc: asyncio.subprocess.Process) -> None:
    await _send(proc, {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "search_api",
            "arguments": {"query": "cluster"},
        },
    })
    resp = await _recv(proc, expect_id=3)
    content_blocks = resp.get("result", {}).get("content") or []
    if not content_blocks:
        raise RuntimeError(f"search_api returned no content: {resp}")
    text = content_blocks[0].get("text", "")
    if "/v1/clusters" not in text:
        raise RuntimeError(f"search_api result missing fixture path: {text!r}")
    print("OK  tools/call search_api")


async def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="mcp-smoke-"))
    fixture = tmp / "specs"
    _write_fixture_spec(fixture)

    env = {**os.environ, "GRN_MCP_SPEC_DIR": str(fixture)}
    proc = await asyncio.create_subprocess_exec(
        "uv", "run", "greenode-mcp-server",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
        env=env,
    )
    try:
        await _handshake(proc)
        await _check_tools_list(proc)
        await _check_tools_call(proc)
        print("\nAll MCP protocol checks passed.")
        return 0
    except Exception as exc:
        print(f"\nFAIL {exc}", file=sys.stderr)
        return 1
    finally:
        proc.terminate()
        try:
            await asyncio.wait_for(proc.wait(), timeout=5)
        except asyncio.TimeoutError:
            proc.kill()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
