# core/mcp_dispatcher.py
import asyncio, json
from pathlib import Path

class AsyncMCPDispatcher:
    def __init__(self, registry_path: str = "config/mcp_registry.json"):
        cfg = json.loads(Path(registry_path).read_text())
        self.registry = cfg["servers"]
        self._procs: dict[str, asyncio.subprocess.Process] = {}
        self._tool_cache: dict[str, list] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    async def _proc(self, server: str) -> asyncio.subprocess.Process:
        if server not in self._procs:
            cfg = self.registry[server]
            self._procs[server] = await asyncio.create_subprocess_exec(
                *cfg["cmd"],
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
            )
            self._locks[server] = asyncio.Lock()
        return self._procs[server]

    async def _rpc(self, server: str, method: str, params: dict) -> dict:
        proc = await self._proc(server)
        req = json.dumps({"jsonrpc": "2.0", "id": 1,
                          "method": method, "params": params}) + "\n"
        async with self._locks[server]:   # one call at a time per server
            proc.stdin.write(req.encode())
            await proc.stdin.drain()
            line = await proc.stdout.readline()
        return json.loads(line)

    async def get_tool_definitions(self, server_names: list[str]) -> list[dict]:
        async def fetch_one(name):
            if name not in self._tool_cache:
                resp = await self._rpc(name, "tools/list", {})
                self._tool_cache[name] = resp.get("result", {}).get("tools", [])
            return [
                {
                    "name": f"{name}__{t['name']}",
                    "description": t["description"],
                    "input_schema": t["inputSchema"],
                }
                for t in self._tool_cache[name]
            ]

        results = await asyncio.gather(*[fetch_one(n) for n in server_names])
        return [tool for sublist in results for tool in sublist]

    async def call(self, prefixed_name: str, params: dict) -> dict:
        server, tool = prefixed_name.split("__", 1)
        resp = await self._rpc(server, "tools/call",
                               {"name": tool, "arguments": params})
        return resp.get("result", {})

    async def close(self):
        for proc in self._procs.values():
            proc.stdin.close()
            await proc.wait()