

Librariesanthropic       # async client built-in
aiosqlite       # async SQLite
chromadb        # has AsyncHttpClient / AsyncEphemeralClient
aiofiles        # async file I/O for SKILL.md patching
pyyaml          # frontmatter parse (sync is fine, done once at startup)
httpx           # async HTTP for SSE MCP transport
pydantic        # schema validation

agent/
├── skills/
│   ├── code/
│   │   └── SKILL.md
│   ├── data/
│   │   └── SKILL.md
│   ├── web/
│   │   └── SKILL.md
│   └── file/
│       └── SKILL.md
├── mcp_servers/
│   ├── file_mcp.py
│   └── db_mcp.py
├── core/
│   ├── skill_loader.py
│   ├── skill_registry.py
│   ├── orchestrator.py
│   ├── mcp_dispatcher.py
│   └── sub_agent.py
├── config/
│   └── mcp_registry.json
└── main.py