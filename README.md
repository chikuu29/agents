agent/
├── core/
│   ├── orchestrator.py      # main loop, context, LLM call
│   ├── skill_router.py      # scoring & dispatch
│   ├── sub_agent.py         # spawn / join sub-agents
│   └── context_store.py     # short + long-term memory
├── skills/
│   ├── base_skill.py        # abstract Skill class
│   ├── code_skill.py
│   ├── data_skill.py
│   └── web_skill.py
├── mcp/
│   ├── dispatcher.py        # JSON-RPC builder + caller
│   ├── registry.py          # MCP server manifest store
│   ├── stdio_transport.py   # subprocess MCP transport
│   └── sse_transport.py     # HTTP SSE transport
└── main.py