"""Soul Orchestrator — JARVIS agent fleet coordinator for Mark XXXIX.

This replaces Mark XXXIX's executor.py with the full JARVIS agent fleet.
It processes Intents through the complete agent pipeline:
  Commander → Memory → Planner → ToolOperator → Engineer → QA → Writer

Principle: The soul decides what executes, at what risk level,
with what approval requirement.

Usage:
    from agent.soul_orchestrator import SoulOrchestrator

    orchestrator = SoulOrchestrator()
    result = orchestrator.process_intent(intent, protocol)
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path
from typing import Any

# Add JARVIS agents to path
JARVIS_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(JARVIS_ROOT))
sys.path.insert(0, str(JARVIS_ROOT / "tools"))

from tools.embodiment.protocol import (
    AgentStep,
    Intent,
    IntentResult,
    IntentStatus,
    RiskLevel,
    ToolCall,
    ToolOutput,
    ApprovalRequest,
)


class SoulOrchestrator:
    """The soul's brain. Routes intents to agents, manages execution.

    This replaces Mark XXXIX's AgentExecutor entirely.
    It uses the JARVIS agent fleet for all reasoning tasks.
    """

    MAX_RETRIES = 3
    MAX_REPLANS = 3

    def __init__(self):
        self._agents = self._load_agents()
        self._tool_modules: dict[str, Any] = {}

    def _load_agents(self) -> dict[str, Any]:
        """Load JARVIS agents from agents/ and tools/agents/."""
        # Import from JARVIS agent system
        from agents import run_agent
        from tools.agents.commander import route_task
        from tools.agents.researcher import research_topic
        from tools.agents.engineer import generate_code
        from tools.agents.planner import create_plan
        from tools.agents.tool_operator import plan_tool_usage
        from tools.agents.memory_coordinator import coordinate_memory

        return {
            "commander": route_task,
            "researcher": research_topic,
            "engineer": generate_code,
            "planner": create_plan,
            "tool_operator": plan_tool_usage,
            "memory_coordinator": coordinate_memory,
            "run_agent": run_agent,
        }

    def process_intent(
        self,
        intent: Intent,
        protocol: Any,  # SoulBodyProtocol
    ) -> IntentResult:
        """Process an intent through the full soul pipeline.

        Steps:
        1. Classify intent type (Commander)
        2. Retrieve memory context (MemoryCoordinator)
        3. Route to primary agent
        4. Agent produces tool_calls
        5. Safety gate per tool (Asimov)
        6. Execute tools (EmbodimentLayer)
        7. QA validate output
        8. Summarize result
        9. Store in memory

        Args:
            intent: The user's intent
            protocol: SoulBodyProtocol for tool execution

        Returns:
            IntentResult with status, summary, and tool outputs
        """
        trace: list[AgentStep] = []
        start_time = time.time()

        try:
            # ── Step 1: Classify Intent ────────────────────────────
            t0 = time.time()
            classification = self._classify_intent(intent.raw_text)
            trace.append(AgentStep(
                agent_name="commander",
                action="classified",
                detail=json.dumps(classification, ensure_ascii=False),
                duration_ms=(time.time() - t0) * 1000,
            ))

            task_type = classification.get("task_type", "research")
            confidence = classification.get("confidence", 0.5)

            # Low confidence → ask for clarification
            if confidence < 0.5:
                return IntentResult(
                    intent_id=intent.intent_id,
                    status=IntentStatus.SUCCESS,
                    summary=(
                        "I'm not sure what you'd like me to do. "
                        "Could you rephrase that, sir?"
                    ),
                    agent_trace=trace,
                    metadata={"classification": classification},
                )

            # ── Step 2: Memory Context ─────────────────────────────
            t0 = time.time()
            memory_ctx = self._retrieve_memory(intent)
            trace.append(AgentStep(
                agent_name="memory_coordinator",
                action="retrieved",
                detail=f"Context keys: {list(memory_ctx.keys())}",
                duration_ms=(time.time() - t0) * 1000,
            ))

            # ── Step 3-4: Route and Plan ───────────────────────────
            t0 = time.time()
            plan = self._plan_execution(
                intent.raw_text, task_type, memory_ctx
            )
            trace.append(AgentStep(
                agent_name=self._agent_for_type(task_type),
                action="planned",
                detail=f"Steps: {len(plan.get('steps', []))}, Tools: {len(plan.get('tool_calls', []))}",
                duration_ms=(time.time() - t0) * 1000,
            ))

            # ── Step 5: Safety Gate Per Tool ───────────────────────
            tool_calls = plan.get("tool_calls", plan.get("steps", []))

            for tc in tool_calls:
                tool_name = tc.get("tool", "")
                params = tc.get("parameters", {})

                approved, reason = protocol._validate_tool(
                    ToolCall(tool=tool_name, params=params)
                )

                if not approved:
                    if "Approval required" in reason:
                        # Need user approval
                        cap = self._get_capability(tool_name)
                        return IntentResult(
                            intent_id=intent.intent_id,
                            status=IntentStatus.APPROVAL_NEEDED,
                            summary="",
                            agent_trace=trace,
                            approval_request=ApprovalRequest(
                                tool_name=tool_name,
                                risk_level=RiskLevel.HIGH,
                                description=reason,
                                parameters=params,
                                capability=tool_name,
                            ),
                        )
                    else:
                        # Blocked by safety
                        return IntentResult(
                            intent_id=intent.intent_id,
                            status=IntentStatus.BLOCKED,
                            summary="",
                            agent_trace=trace,
                            blocking_reason=reason,
                        )

            # ── Step 6: Execute Tools ──────────────────────────────
            tool_outputs: list[ToolOutput] = []

            for tc in tool_calls:
                tool_name = tc.get("tool", "")
                params = tc.get("parameters", {})

                t0 = time.time()
                output = protocol._execute_tool(
                    ToolCall(tool=tool_name, params=params)
                )
                tool_outputs.append(output)
                trace.append(AgentStep(
                    agent_name="embodiment",
                    action="executed",
                    detail=f"{tool_name}: {output.status}",
                    duration_ms=(time.time() - t0) * 1000,
                ))

            # ── Step 7: QA Validation ─────────────────────────────
            t0 = time.time()
            qa_result = self._validate_output(
                intent.raw_text, tool_outputs
            )
            trace.append(AgentStep(
                agent_name="qa",
                action="validated",
                detail=f"Passed: {qa_result.get('passed', False)}",
                duration_ms=(time.time() - t0) * 1000,
            ))

            # ── Step 8: Summarize ─────────────────────────────────
            t0 = time.time()
            summary = self._summarize_result(
                intent.raw_text, tool_outputs, qa_result
            )
            trace.append(AgentStep(
                agent_name="writer",
                action="summarized",
                detail=f"Length: {len(summary)}",
                duration_ms=(time.time() - t0) * 1000,
            ))

            # ── Step 9: Assemble Result ───────────────────────────
            total_ms = (time.time() - start_time) * 1000
            return IntentResult(
                intent_id=intent.intent_id,
                status=IntentStatus.SUCCESS,
                summary=summary,
                tool_outputs=tool_outputs,
                agent_trace=trace,
                metadata={
                    "task_type": task_type,
                    "total_ms": total_ms,
                    "tools_executed": len(tool_outputs),
                },
            )

        except Exception as e:
            return IntentResult(
                intent_id=intent.intent_id,
                status=IntentStatus.FAILED,
                summary="",
                error=f"Soul processing error: {e}",
                agent_trace=trace,
            )

    # ── Agent Helpers ──────────────────────────────────────────────

    def _classify_intent(self, raw_text: str) -> dict:
        """Classify intent type using Commander agent."""
        try:
            return self._agents["commander"](raw_text)
        except Exception:
            return {
                "selected_agent": "researcher",
                "confidence": 0.5,
                "task_type": "research",
                "reasoning": "Default classification",
            }

    def _retrieve_memory(self, intent: Intent) -> dict:
        """Retrieve relevant memories for this intent."""
        try:
            return self._agents["memory_coordinator"](
                intent.raw_text,
                existing_memory=intent.context,
            )
        except Exception:
            return {}

    def _plan_execution(
        self, raw_text: str, task_type: str, memory_ctx: dict
    ) -> dict:
        """Plan execution using the appropriate agent."""
        context_str = json.dumps(memory_ctx, ensure_ascii=False) if memory_ctx else ""

        if task_type == "tool_use":
            return self._agents["tool_operator"](raw_text)
        elif task_type == "coding":
            return self._agents["engineer"](raw_text, context=context_str)
        elif task_type == "research":
            return self._agents["researcher"](raw_text, context=context_str)
        elif task_type == "planning":
            return self._agents["planner"](raw_text)
        else:
            # Default: try tool operator first, fall back to researcher
            plan = self._agents["tool_operator"](raw_text)
            if plan.get("tool_calls"):
                return plan
            return self._agents["researcher"](raw_text, context=context_str)

    def _validate_output(
        self, raw_text: str, tool_outputs: list[ToolOutput]
    ) -> dict:
        """Validate output using QA agent."""
        try:
            # Check if any tools failed
            failed = [o for o in tool_outputs if o.status == "failed"]
            if failed:
                return {
                    "passed": False,
                    "reason": f"{len(failed)} tool(s) failed",
                    "failed_tools": [o.tool_name for o in failed],
                }
            return {"passed": True, "reason": "All tools executed successfully"}
        except Exception:
            return {"passed": True, "reason": "Validation skipped"}

    def _summarize_result(
        self,
        raw_text: str,
        tool_outputs: list[ToolOutput],
        qa_result: dict,
    ) -> str:
        """Summarize the result for the user."""
        try:
            # Use researcher for conversational summary
            outputs_text = "\n".join(
                f"- {o.tool_name}: {str(o.output)[:200]}"
                for o in tool_outputs
                if o.output
            )

            result = self._agents["researcher"](
                f"Summarize this for the user:\n"
                f"Original request: {raw_text}\n"
                f"Results:\n{outputs_text}",
                context="Write a brief, helpful summary. Address user as 'sir'."
            )
            return result.get("summary", "Task completed, sir.")
        except Exception:
            return f"Completed {len(tool_outputs)} steps for: {raw_text[:60]}."

    def _agent_for_type(self, task_type: str) -> str:
        """Map task type to primary agent name."""
        mapping = {
            "tool_use": "tool_operator",
            "coding": "engineer",
            "research": "researcher",
            "planning": "planner",
            "conversational": "researcher",
            "memory": "memory_coordinator",
            "mixed": "orchestrator",
        }
        return mapping.get(task_type, "researcher")

    def _get_capability(self, tool_name: str):
        """Get capability from registry."""
        try:
            from tools.embodiment.capability_registry import get_capability
            return get_capability(tool_name)
        except Exception:
            return None
