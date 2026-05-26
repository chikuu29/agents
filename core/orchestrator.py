# core/orchestrator.py
import asyncio
from anthropic import AsyncAnthropic

class AsyncOrchestrator:
    def __init__(self, registry, dispatcher, brain, reflection):
        self.registry   = registry
        self.dispatcher = dispatcher
        self.brain      = brain
        self.reflection = reflection
        self.client     = AsyncAnthropic()

    async def run(self, user_message: str) -> str:
        # 1. Route skill
        skill_name, _ = await self.registry.route(user_message)
        skill = self.registry.get(skill_name)

        # 2. Parallel: fetch tools + recall memory
        tools, memory_ctx = await asyncio.gather(
            self.dispatcher.get_tool_definitions(skill.mcp_servers),
            self.brain.recall(user_message, skill_name),
        )

        system_prompt = f"""
You are an AI agent. Follow the skill instructions below exactly.

{skill.full_content}

{memory_ctx}

Session context:
{self.brain.working.summary()}
"""
        messages = self.brain.working.messages() + [
            {"role": "user", "content": user_message}
        ]

        collected_tools: list[str] = []
        trace_parts: list[str] = [f"USER: {user_message}"]

        # 3. Async agentic loop
        while True:
            response = await self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                system=system_prompt,
                tools=tools,
                messages=messages,
            )

            if response.stop_reason == "tool_use":
                messages.append({"role": "assistant", "content": response.content})

                # Fire all tool calls concurrently
                tool_blocks = [b for b in response.content if b.type == "tool_use"]
                results = await asyncio.gather(*[
                    self.dispatcher.call(b.name, b.input)
                    for b in tool_blocks
                ])

                tool_results = []
                for block, result in zip(tool_blocks, results):
                    collected_tools.append(block.name)
                    trace_parts.append(f"TOOL {block.name}: {str(result)[:300]}")
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": str(result),
                    })
                messages.append({"role": "user", "content": tool_results})

            else:
                final = next(
                    b.text for b in response.content if b.type == "text"
                )
                self.brain.working.add("user", user_message)
                self.brain.working.add("assistant", final)

                # Fire-and-forget reflection — does NOT block the response
                asyncio.create_task(
                    self.reflection.reflect(
                        intent=user_message,
                        skill_used=skill_name,
                        tools_called=collected_tools,
                        full_trace="\n".join(trace_parts),
                        final_result=final,
                        success=True,
                    )
                )
                return final