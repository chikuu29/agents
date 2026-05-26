# core/orchestrator.py
"""
Async orchestrator — the main agentic loop.

Routes user intent to a skill, recalls relevant memory,
runs an LLM agentic tool-use loop, then triggers reflection.
"""

import asyncio
import time
import structlog
from opentelemetry import trace

from core.llm.base import BaseLLM

logger = structlog.get_logger(__name__)
tracer = trace.get_tracer(__name__)


class AsyncOrchestrator:
    def __init__(self, registry, dispatcher, brain, reflection, llm: BaseLLM):
        self.registry   = registry
        self.dispatcher = dispatcher
        self.brain      = brain
        self.reflection = reflection
        self.llm        = llm

    async def run(self, user_message: str) -> str:
        with tracer.start_as_current_span("orchestrator.run") as span:
            span.set_attribute("user.message", user_message[:200])
            request_start = time.perf_counter()

            # 1. Route skill
            with tracer.start_as_current_span("skill.routing"):
                skill_name, confidence = await self.registry.route(user_message)
                skill = self.registry.get(skill_name)
                span.set_attribute("skill.name", skill_name)
                span.set_attribute("skill.confidence", confidence)
                logger.info(
                    "orchestrator.skill_routed",
                    skill=skill_name,
                    confidence=round(confidence, 3),
                )

            # 2. Parallel: fetch tools + recall memory
            with tracer.start_as_current_span("parallel.tools_and_memory"):
                tools, memory_ctx = await asyncio.gather(
                    self.dispatcher.get_tool_definitions(skill.mcp_servers),
                    self.brain.recall(user_message, skill_name),
                )
                logger.debug(
                    "orchestrator.context_loaded",
                    tool_count=len(tools),
                    memory_length=len(memory_ctx),
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
            loop_iteration = 0

            # 3. Async agentic loop
            while True:
                loop_iteration += 1
                with tracer.start_as_current_span(f"llm.call.{loop_iteration}") as llm_span:
                    llm_start = time.perf_counter()

                    response = await self.llm.chat(
                        messages=messages,
                        system=system_prompt,
                        tools=tools,
                        max_tokens=4096,
                    )

                    llm_duration = time.perf_counter() - llm_start
                    llm_span.set_attribute("llm.provider", self.llm.provider_name)
                    llm_span.set_attribute("llm.duration_ms", round(llm_duration * 1000))
                    llm_span.set_attribute("llm.tokens.input", response.usage.input_tokens)
                    llm_span.set_attribute("llm.tokens.output", response.usage.output_tokens)

                    logger.info(
                        "orchestrator.llm_call",
                        iteration=loop_iteration,
                        provider=self.llm.provider_name,
                        duration_ms=round(llm_duration * 1000),
                        input_tokens=response.usage.input_tokens,
                        output_tokens=response.usage.output_tokens,
                        stop_reason=response.stop_reason,
                    )

                if response.stop_reason == "tool_use":
                    # Append assistant message in provider-specific format
                    messages.append(self.llm.format_assistant_message(response))

                    # Fire all tool calls concurrently
                    with tracer.start_as_current_span("tools.execute") as tool_span:
                        tool_span.set_attribute(
                            "tools.names",
                            [tc.name for tc in response.tool_calls],
                        )
                        results = await asyncio.gather(*[
                            self.dispatcher.call(tc.name, tc.input)
                            for tc in response.tool_calls
                        ])

                    tool_results = []
                    for tc, result in zip(response.tool_calls, results):
                        collected_tools.append(tc.name)
                        trace_parts.append(f"TOOL {tc.name}: {str(result)[:300]}")
                        tool_results.append(
                            self.llm.format_tool_result(tc.id, str(result))
                        )
                        logger.debug(
                            "orchestrator.tool_result",
                            tool=tc.name,
                            result_preview=str(result)[:200],
                        )
                    messages.append({"role": "user", "content": tool_results})

                else:
                    final = response.text or ""
                    self.brain.working.add("user", user_message)
                    self.brain.working.add("assistant", final)

                    total_duration = time.perf_counter() - request_start
                    span.set_attribute("total.duration_ms", round(total_duration * 1000))
                    span.set_attribute("total.tool_calls", len(collected_tools))
                    span.set_attribute("total.llm_iterations", loop_iteration)

                    logger.info(
                        "orchestrator.completed",
                        duration_ms=round(total_duration * 1000),
                        llm_iterations=loop_iteration,
                        tools_called=collected_tools,
                        response_preview=final[:150],
                    )

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