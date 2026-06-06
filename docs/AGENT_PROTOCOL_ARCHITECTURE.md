# SoulBodyProtocol — Agent Fleet Architecture

## The Fundamental Rule

> **Mark XXXIX never directly invokes a tool. It sends intents to the soul. The soul decides what executes, at what risk level, with what approval requirement. The body just renders the result.**

This document maps how JARVIS's entire agent fleet connects to Mark XXXIX through the SoulBodyProtocol.

---

## 1. Complete Intent Flow Diagram

```
╔══════════════════════════════════════════════════════════════════════╗
║                        USER TYPES COMMAND                           ║
║                     "Research AI safety and save it"                ║
╚══════════════════════════════════╦═══════════════════════════════════╝
                                   ▼
╔══════════════════════════════════════════════════════════════════════╗
║  BODY (Mark XXXIX)                                                   ║
║  ┌─────────────────────────────────────────────────────────────────┐ ║
║  │ 1. Parse user input → extract raw_text                          │ ║
║  │ 2. Create Intent object:                                        │ ║
║  │    { raw_text, user_id, session_id, timestamp, context }        │ ║
║  │ 3. Call protocol.submit_intent(intent)                          │ ║
║  │ 4. Wait for IntentResult via callback/future                    │ ║
║  │ 5. Render result in HUD (speak, display, animate)               │ ║
║  └─────────────────────────────────────────────────────────────────┘ ║
║                                                                      ║
║  ❌ NEVER calls _call_tool() directly                                ║
║  ❌ NEVER calls planner.create_plan() directly                       ║
║  ❌ NEVER calls executor.execute() directly                          ║
║                                                                      ║
║  ✅ ONLY creates Intents and renders results                         ║
╚══════════════════════════════════╦═══════════════════════════════════╝
                                   ▼
╔══════════════════════════════════════════════════════════════════════╗
║  SOUL (JARVIS Agent Fleet)                                           ║
║                                                                      ║
║  ┌──────────────────────────────────────────────────────────────┐    ║
║  │  SOUL ORCHESTRATOR (receives intent)                         │    ║
║  │                                                              │    ║
║  │  Step 1: SAFETY GATE — Pre-flight check                      │    ║
║  │    → asimov.check_command(intent.raw_text)                   │    ║
║  │    → If BLOCKED: return IntentResult(blocked=True, reason)   │    ║
║  │    → If PASS: continue                                       │    ║
║  │                                                              │    ║
║  │  Step 2: CLASSIFY INTENT                                     │    ║
║  │    → Commander agent routes intent type                      │    ║
║  │    → Returns: { selected_agent, confidence, task_type }      │    ║
║  │                                                              │    ║
║  │  Step 3: MEMORY CONTEXT                                      │    ║
║  │    → MemoryCoordinator retrieves relevant memories           │    ║
║  │    → Assembles context for the target agent                  │    ║
║  │                                                              │    ║
║  │  Step 4: AGENT EXECUTION                                     │    ║
║  │    → Routes to appropriate agent(s) based on task_type       │    ║
║  │    → Agent produces: tool_calls[] + response_text            │    ║
║  │                                                              │    ║
║  │  Step 5: SAFETY GATE — Per-tool validation                   │    ║
║  │    → For EACH tool_call:                                     │    ║
║  │      → capability_registry.get_risk_level(tool)              │    ║
║  │      → asimov.check_action(tool, params)                     │    ║
║  │      → If HIGH risk: request approval from body              │    ║
║  │      → If BLOCKED: skip tool, notify user                    │    ║
║  │                                                              │    ║
║  │  Step 6: TOOL EXECUTION                                      │    ║
║  │    → Execute approved tool_calls via embodiment layer        │    ║
║  │    → Collect results                                         │    ║
║  │                                                              │    ║
║  │  Step 7: QA VALIDATION (if code/output generated)            │    ║
║  │    → QA agent validates output quality                       │    ║
║  │    → If FAIL: loop back to agent with feedback               │    ║
║  │    → If PASS: continue                                       │    ║
║  │                                                              │    ║
║  │  Step 8: ASSEMBLE RESULT                                     │    ║
║  │    → Combine agent responses + tool results                  │    ║
║  │    → Generate summary via Writer/Researcher agent            │    ║
║  │    → Return IntentResult to body                             │    ║
║  └──────────────────────────────────────────────────────────────┘    ║
╚══════════════════════════════════╦═══════════════════════════════════╝
                                   ▼
╔══════════════════════════════════════════════════════════════════════╗
║  BODY (Mark XXXIX)                                                   ║
║  ┌─────────────────────────────────────────────────────────────────┐ ║
║  │ 1. Receive IntentResult from protocol                          │ ║
║  │ 2. If blocked: display blocking reason to user                 │ ║
║  │ 3. If approval_needed: show approval dialog, await response     │ ║
║  │ 4. If success: render result in HUD                            │ ║
║  │    → speak(result.summary)                                     │ ║
║  │    → display(result.tool_outputs)                              │ ║
║  │    → animate(result.status)                                    │ ║
║  │ 5. Update task_queue status                                    │ ║
║  └─────────────────────────────────────────────────────────────────┘ ║
╚══════════════════════════════════════════════════════════════════════╝
```

---

## 2. Data Models

### Intent (Body → Soul)

```python
@dataclass
class Intent:
    """What the body sends to the soul. Never contains tool calls."""
    intent_id: str                          # UUID
    raw_text: str                           # User's original command
    user_id: str                            # Who issued the command
    session_id: str                         # Current session
    timestamp: float                        # Time created
    context: dict                           # UI state, recent history
    priority: TaskPriority = TaskPriority.NORMAL
    speak_callback: Callable | None = None  # For TTS back to body
    cancel_flag: threading.Event | None = None
```

### IntentResult (Soul → Body)

```python
@dataclass
class IntentResult:
    """What the soul sends back to the body. Never contains raw tool output."""
    intent_id: str                          # Matches the Intent
    status: IntentStatus                    # SUCCESS | BLOCKED | FAILED | APPROVAL_NEEDED
    summary: str                            # Human-readable summary for HUD
    tool_outputs: list[ToolOutput]          # Structured tool results (if any)
    agent_trace: list[AgentStep]            # Which agents ran, what they did
    error: str | None                       # Error message if FAILED
    blocking_reason: str | None             # Why blocked (if BLOCKED)
    approval_request: ApprovalRequest | None  # What needs approval (if APPROVAL_NEEDED)
    metadata: dict                          # Extra data for HUD rendering

@dataclass
class ToolOutput:
    """Structured output from a single tool execution."""
    tool_name: str
    capability: str                         # Registry capability name
    risk_level: RiskLevel
    status: str                             # "completed" | "blocked" | "failed"
    output: Any                             # Tool result data
    execution_time_ms: float

@dataclass
class AgentStep:
    """Trace of what an agent did."""
    agent_name: str
    action: str                             # "routed" | "planned" | "executed" | "validated"
    detail: str
    duration_ms: float

@dataclass
class ApprovalRequest:
    """What needs user approval before execution."""
    tool_name: str
    risk_level: RiskLevel
    description: str
    parameters: dict
    capability: str
```

### IntentStatus

```python
class IntentStatus(Enum):
    SUCCESS = "success"           # Intent completed normally
    BLOCKED = "blocked"           # Safety gate blocked it
    FAILED = "failed"             # Execution failed after retries
    APPROVAL_NEEDED = "approval"  # Waiting for user approval
    CANCELLED = "cancelled"       # User cancelled
```

---

## 3. Agent Routing Rules

### Intent Classification → Agent Mapping

| Intent Type | Pattern Examples | Primary Agent | Supporting Agents |
|---|---|---|---|
| `conversational` | "hello", "hi", "good morning" | **Researcher** (conversation mode) | MemoryCoordinator (context) |
| `research` | "what is X", "tell me about Y" | **Researcher** | MemoryCoordinator, Writer |
| `tool_use` | "open Chrome", "search web", "set volume" | **ToolOperator** → Embodiment Layer | Commander (routing) |
| `planning` | "plan my trip", "create a schedule" | **Planner** | Researcher, ToolOperator |
| `coding` | "write a Python script", "build a project" | **Engineer** | QA (validation), Planner |
| `file_ops` | "save to desktop", "read this file" | **ToolOperator** → file_controller | Safety gate (HIGH risk) |
| `os_control` | "click here", "type this", "press keys" | **ToolOperator** → computer_control | Safety gate (HIGH risk) |
| `memory` | "remember that...", "what did I say about..." | **MemoryCoordinator** | Researcher |
| `mixed` | "research X and save it" | **Orchestrator** (multi-agent) | Planner, Researcher, ToolOperator |
| `error_recovery` | (internal — from error_handler) | **QA Agent** | Engineer (fix generation) |

### Routing Decision Matrix

```python
ROUTING_RULES = {
    # Intent Type → (Primary Agent, Risk Gate, Max Retries)
    "conversational": ("researcher",    RiskLevel.LOW,    0),
    "research":       ("researcher",    RiskLevel.LOW,    2),
    "tool_use":       ("tool_operator", RiskLevel.MEDIUM, 3),
    "planning":       ("planner",       RiskLevel.LOW,    2),
    "coding":         ("engineer",      RiskLevel.HIGH,   3),
    "file_ops":       ("tool_operator", RiskLevel.HIGH,   2),
    "os_control":     ("tool_operator", RiskLevel.HIGH,   2),
    "memory":         ("memory_coordinator", RiskLevel.LOW, 1),
    "mixed":          ("orchestrator",  RiskLevel.MEDIUM, 3),
}
```

### Capability → Agent Mapping (which agent can use which tools)

| Capability | Risk | Agents Allowed |
|---|---|---|
| `voice_io` | LOW | Researcher, Writer (for TTS output) |
| `app_launcher` | LOW | ToolOperator |
| `screen_vision` | LOW | ToolOperator, QA |
| `browser_navigation` | MEDIUM | ToolOperator |
| `file_operations` | HIGH | ToolOperator (approval required) |
| `os_control` | HIGH | ToolOperator (approval required) |
| `system_settings` | LOW | ToolOperator |
| `code_generation` | HIGH | Engineer (approval required) |
| `project_builder` | HIGH | Engineer (approval required) |
| `web_search` | LOW | Researcher, ToolOperator |
| `youtube` | LOW | Researcher, ToolOperator |
| `weather` | LOW | Researcher |
| `flight_search` | LOW | Researcher |
| `messaging` | HIGH | ToolOperator (approval required) |
| `reminders` | LOW | ToolOperator |
| `game_updater` | MEDIUM | ToolOperator |
| `desktop_control` | LOW | ToolOperator |
| `file_processor` | MEDIUM | ToolOperator, Engineer |

---

## 4. Safety Gate Integration at Each Step

```
INTENT LIFECYCLE — SAFETY CHECKPOINTS
═══════════════════════════════════════

  CHECKPOINT 1: Pre-flight (on intent submission)
  ┌─────────────────────────────────────────────────┐
  │ asimov.check_command(intent.raw_text)            │
  │ → Blocks: harm keywords, dangerous commands      │
  │ → Blocks: vague commands (Second Law)            │
  │ → Blocks: commands targeting SAGE itself          │
  │ → PASS: continue to routing                      │
  │ → FAIL: return IntentResult(BLOCKED) immediately │
  └─────────────────────────────────────────────────┘
                    ▼ (if PASS)
  CHECKPOINT 2: Agent routing confidence
  ┌─────────────────────────────────────────────────┐
  │ Commander agent returns confidence score         │
  │ → confidence < 0.5: ask user for clarification   │
  │ → confidence >= 0.5: proceed to agent            │
  │ → This prevents misrouting dangerous intents     │
  └─────────────────────────────────────────────────┘
                    ▼ (if confident)
  CHECKPOINT 3: Per-tool validation (before EACH tool call)
  ┌─────────────────────────────────────────────────┐
  │ For each tool_call in agent's output:            │
  │                                                   │
  │ 3a. capability_registry.get_risk_level(tool)     │
  │     → LOW: auto-execute, log only                │
  │     → MEDIUM: execute + notify user              │
  │     → HIGH: require explicit approval            │
  │                                                   │
  │ 3b. asimov.check_action(action_type, target)     │
  │     → First Law: absolute block                  │
  │     → Third Law: block + allow override          │
  │     → Second Law: implicit (execute unless blocked)│
  │                                                   │
  │ 3c. If approval_required:                        │
  │     → Return IntentResult(APPROVAL_NEEDED)       │
  │     → Body shows approval dialog                 │
  │     → User approves → re-submit with approval    │
  │     → User denies → skip tool, continue plan     │
  └─────────────────────────────────────────────────┘
                    ▼ (if approved)
  CHECKPOINT 4: Post-execution validation
  ┌─────────────────────────────────────────────────┐
  │ QA agent validates output:                       │
  │ → Did the tool produce expected output?          │
  │ → Did it introduce regressions?                  │
  │ → Did it violate any safety constraints?         │
  │ → If FAIL: loop back to agent with feedback      │
  │ → If PASS: continue to next tool or summarize    │
  └─────────────────────────────────────────────────┘
                    ▼
  CHECKPOINT 5: Final output validation
  ┌─────────────────────────────────────────────────┐
  │ Orchestrator validates complete result:          │
  │ → All tools executed successfully?               │
  │ → Output matches user intent?                    │
  │ → No safety violations in final output?          │
  │ → If FAIL: replan or report error                │
  │ → If PASS: assemble IntentResult                 │
  └─────────────────────────────────────────────────┘
```

---

## 5. Error Handling Flow Across Soul-Body Boundary

### Current Mark XXXIX Error Flow (WRONG — body handles everything)

```
executor.execute() → _call_tool() fails → error_handler.analyze_error()
  → RETRY: retry same tool
  → SKIP: skip step
  → REPLAN: replan remaining steps
  → ABORT: return error to user
```

### New Protocol-Mediated Error Flow (CORRECT — soul handles, body renders)

```
╔══════════════════════════════════════════════════════════════╗
║  SOUL: Tool execution fails                                  ║
║                                                              ║
║  1. ERROR_CLASSIFICATION                                     ║
║     → QA agent analyzes failure                              ║
║     → Classifies: TRANSIENT | LOGIC | SAFETY | RESOURCE      ║
║                                                              ║
║  2. RECOVERY DECISION                                        ║
║     ┌────────────────────────────────────────────────────┐   ║
║     │ TRANSIENT (network timeout, temp lock):            │   ║
║     │   → Retry same tool (max 2 attempts)              │   ║
║     │   → Report to body: "Retrying, sir..."            │   ║
║     ├────────────────────────────────────────────────────┤   ║
║     │ LOGIC (wrong parameters, wrong tool):              │   ║
║     │   → Engineer agent generates fix                   │   ║
║     │   → Or Planner agent creates alternative approach  │   ║
║     │   → Report to body: "Trying alternative, sir..."  │   ║
║     ├────────────────────────────────────────────────────┤   ║
║     │ SAFETY (blocked by Asimov):                        │   ║
║     │   → NEVER retry — it will be blocked again        │   ║
║     │   → Report to body: blocking reason                │   ║
║     │   → Suggest safe alternative if possible           │   ║
║     ├────────────────────────────────────────────────────┤   ║
║     │ RESOURCE (timeout, out of memory):                 │   ║
║     │   → Simplify the task                              │   ║
║     │   → Reduce scope and retry                         │   ║
║     │   → Report to body: "Simplified approach, sir..." │   ║
║     └────────────────────────────────────────────────────┘   ║
║                                                              ║
║  3. REPLAN (after max retries per step)                      ║
║     → Orchestrator requests new plan from Planner            ║
║     → Uses completed steps + failure context                 ║
║     → Max 3 replan attempts total                            ║
║                                                              ║
║  4. FINAL FAILURE                                            ║
║     → After all retries + replans exhausted                  ║
║     → QA agent generates failure report                      ║
║     → Return IntentResult(FAILED, error=report)              ║
║                                                              ║
║  5. BODY RECEIVES                                            ║
║     → Renders error message in HUD                           ║
║     → speak(error.user_message)                              │
║     → Updates task_queue status to FAILED                     │
╚══════════════════════════════════════════════════════════════╝
```

### Error Classification by QA Agent

```python
class ErrorClassification(Enum):
    TRANSIENT = "transient"    # Network timeout, temp file lock, race condition
    LOGIC = "logic"            # Wrong tool, wrong parameters, wrong approach
    SAFETY = "safety"          # Blocked by Asimov (NEVER retry)
    RESOURCE = "resource"      # Timeout, memory, disk space
    UNKNOWN = "unknown"        # Default to replan

ERROR_RECOVERY_MAP = {
    ErrorClassification.TRANSIENT:  {"action": "retry",    "max_attempts": 2, "delay_ms": 2000},
    ErrorClassification.LOGIC:      {"action": "replan",   "max_attempts": 3, "use_engineer": True},
    ErrorClassification.SAFETY:     {"action": "abort",    "max_attempts": 0, "suggest_alternative": True},
    ErrorClassification.RESOURCE:   {"action": "simplify", "max_attempts": 2, "reduce_scope": True},
    ErrorClassification.UNKNOWN:    {"action": "replan",   "max_attempts": 2},
}
```

---

## 6. Task Queue → Orchestrator Mapping

### Current Mark XXXIX TaskQueue

```python
# Mark XXXIX task_queue.py — body-side task management
class TaskQueue:
    def submit(goal, priority, speak, on_complete) -> task_id
    def cancel(task_id) -> bool
    def get_status(task_id) -> dict
    # Internally creates AgentExecutor, calls executor.execute(goal)
```

### New Protocol-Mediated TaskQueue

```python
class ProtocolTaskQueue:
    """Body-side queue that submits intents to the soul, not directly to executor."""
    
    def __init__(self, protocol: SoulBodyProtocol):
        self._protocol = protocol
        self._tasks: dict[str, Task] = {}
        self._lock = threading.Lock()
    
    def submit(
        self,
        goal: str,
        priority: TaskPriority = TaskPriority.NORMAL,
        speak: Callable | None = None,
        on_complete: Callable | None = None,
    ) -> str:
        """Submit a goal as an Intent to the soul."""
        task_id = str(uuid.uuid4())[:8]
        
        # Create Intent from goal
        intent = Intent(
            intent_id=task_id,
            raw_text=goal,
            user_id="current_user",
            session_id=self._session_id,
            timestamp=time.time(),
            context=self._get_context(),
            priority=priority,
            speak_callback=speak,
        )
        
        # Store task for tracking
        task = Task(
            priority=priority.value,
            created_at=time.time(),
            task_id=task_id,
            goal=goal,
            status=TaskStatus.PENDING,
            speak=speak,
            on_complete=on_complete,
        )
        with self._lock:
            self._tasks[task_id] = task
        
        # Submit to soul via protocol — NOT directly to executor
        future = self._protocol.submit_intent(
            intent,
            on_result=lambda result: self._handle_result(task_id, result),
            on_approval=lambda req: self._handle_approval(task_id, req, speak),
        )
        
        return task_id
    
    def _handle_result(self, task_id: str, result: IntentResult):
        """Called when soul returns a result."""
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return
            
            if result.status == IntentStatus.SUCCESS:
                task.status = TaskStatus.COMPLETED
                task.result = result.summary
            elif result.status == IntentStatus.BLOCKED:
                task.status = TaskStatus.FAILED
                task.error = f"Blocked: {result.blocking_reason}"
            elif result.status == IntentStatus.FAILED:
                task.status = TaskStatus.FAILED
                task.error = result.error
            elif result.status == IntentStatus.CANCELLED:
                task.status = TaskStatus.CANCELLED
        
        # Notify user via speak
        if task.speak:
            if task.status == TaskStatus.COMPLETED:
                task.speak(result.summary)
            elif task.status == TaskStatus.FAILED:
                task.speak(f"Task failed, sir. {task.error}")
        
        # Fire callback
        if task.on_complete and task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
            try:
                task.on_complete(task_id, task.result or task.error)
            except Exception as e:
                print(f"[ProtocolTaskQueue] on_complete error: {e}")
    
    def _handle_approval(self, task_id: str, req: ApprovalRequest, speak: Callable):
        """Called when soul needs user approval for a high-risk tool."""
        if speak:
            speak(f"I need your approval to use {req.tool_name}. {req.description}")
        # Body shows approval dialog, user responds, protocol continues
```

### Mapping Table

| Mark XXXIX Component | JARVIS Soul Component | Protocol Role |
|---|---|---|
| `TaskQueue.submit(goal)` | `Orchestrator.receive_intent(intent)` | Body creates Intent, soul receives |
| `AgentExecutor.execute(goal)` | `Orchestrator.route_and_execute(intent)` | Soul routes, executes, returns |
| `planner.create_plan(goal)` | `Planner.create_plan(intent + context)` | Soul's planner (with memory context) |
| `executor._call_tool(tool, params)` | `EmbodimentLayer.execute(tool_call)` | Soul dispatches through safety gate |
| `error_handler.analyze_error()` | `QA Agent.classify_error(failure)` | Soul's QA classifies errors |
| `executor._summarize(goal, steps)` | `Writer Agent.summarize(intent, results)` | Soul's Writer generates summary |
| `task_queue.get_status(id)` | `protocol.get_status(intent_id)` | Body queries via protocol |

---

## 7. Protocol Method Signatures

### SoulBodyProtocol — The Interface

```python
class SoulBodyProtocol:
    """
    The single interface between Mark XXXIX body and JARVIS soul.
    
    Principle: Body never calls tools directly. Body creates Intents.
    Soul receives Intents, routes to agents, validates safety, executes,
    and returns IntentResults.
    """
    
    def __init__(
        self,
        orchestrator: "JARVISEncoder",      # JARVIS agent fleet
        safety_gate: "AsimovGate",           # asimov.py + capability_registry
        embodiment: "EmbodimentLayer",       # tools/embodiment/
        memory: "MemoryStore",               # memory layer
    ):
        self._orchestrator = orchestrator
        self._safety = safety_gate
        self._embodiment = embodiment
        self._memory = memory
    
    # ── Core Flow ──────────────────────────────────────────────────
    
    def submit_intent(
        self,
        intent: Intent,
        on_result: Callable[[IntentResult], None] | None = None,
        on_approval: Callable[[ApprovalRequest], None] | None = None,
    ) -> Future[IntentResult]:
        """
        Submit an intent for processing.
        
        The body calls this method. It NEVER calls tools directly.
        
        Flow:
        1. Pre-flight safety check (asimov.check_command)
        2. Route to appropriate agent via Commander
        3. Agent produces tool_calls
        4. Per-tool safety validation
        5. Execute approved tools
        6. QA validates output
        7. Assemble and return IntentResult
        
        Args:
            intent: The user's intent (never contains tool calls)
            on_result: Callback when intent completes
            on_approval: Callback when approval is needed
        
        Returns:
            Future that resolves to IntentResult
        """
        pass
    
    def cancel_intent(self, intent_id: str) -> bool:
        """Cancel a running intent. Body calls this on user cancel."""
        pass
    
    def get_status(self, intent_id: str) -> IntentResult | None:
        """Get current status of an intent. Body polls or subscribes."""
        pass
    
    def request_approval(
        self,
        intent_id: str,
        tool_call_id: str,
        approved: bool,
    ) -> None:
        """Body responds to an approval request from the soul."""
        pass
    
    # ── Soul-Side Methods (called by orchestrator, not body) ──────
    
    def _validate_safety(self, intent: Intent) -> tuple[bool, str]:
        """Pre-flight safety check. Soul calls this first."""
        return self._safety.check_command(intent.raw_text)
    
    def _validate_tool(self, tool_call: ToolCall) -> tuple[bool, str]:
        """Per-tool safety check. Soul calls this for each tool."""
        cap = self._safety.get_capability(tool_call.tool)
        if cap and cap.approval_required:
            return False, f"Approval required for {tool_call.tool}"
        return self._safety.check_action(tool_call.tool, str(tool_call.params))
    
    def _execute_tool(self, tool_call: ToolCall) -> ToolOutput:
        """Execute a single tool through the embodiment layer."""
        return self._embodiment.execute(tool_call)
    
    def _store_memory(self, intent: Intent, result: IntentResult):
        """Store intent/result in memory for future context."""
        self._memory.store(
            category="interactions",
            key=intent.intent_id,
            value={
                "intent": intent.raw_text,
                "status": result.status.value,
                "summary": result.summary,
                "timestamp": intent.timestamp,
            }
        )
```

### Embodiment Layer — Tool Execution

```python
class EmbodimentLayer:
    """
    Executes tool calls through registered capabilities.
    Never called by body — only by soul via protocol.
    """
    
    def __init__(self, registry: CapabilityRegistry):
        self._registry = registry
        self._implementations: dict[str, Callable] = {}
    
    def execute(self, tool_call: ToolCall) -> ToolOutput:
        """
        Execute a single tool call.
        
        1. Look up capability in registry
        2. Check risk level
        3. Load implementation module
        4. Execute with parameters
        5. Return structured output
        """
        cap = self._registry.get(tool_call.tool)
        if not cap:
            raise ValueError(f"Unknown capability: {tool_call.tool}")
        
        impl = self._load_implementation(cap.implementation)
        start = time.time()
        
        try:
            result = impl(**tool_call.params)
            return ToolOutput(
                tool_name=tool_call.tool,
                capability=cap.name,
                risk_level=cap.risk,
                status="completed",
                output=result,
                execution_time_ms=(time.time() - start) * 1000,
            )
        except Exception as e:
            return ToolOutput(
                tool_name=tool_call.tool,
                capability=cap.name,
                risk_level=cap.risk,
                status="failed",
                output=None,
                execution_time_ms=(time.time() - start) * 1000,
            )
    
    def _load_implementation(self, module_name: str) -> Callable:
        """Lazy-load tool implementation from tools/embodiment/."""
        if module_name not in self._implementations:
            # Import from tools/embodiment/<module_name>
            pass
        return self._implementations[module_name]
```

### JARVIS Orchestrator — Agent Fleet Manager

```python
class JARVISEncoder:
    """
    The soul's brain. Routes intents to agents, manages execution.
    Replaces Mark XXXIX's executor.py entirely.
    """
    
    def __init__(self):
        self._agents = {
            "commander": CommanderAgent(),
            "planner": PlannerAgent(),
            "engineer": EngineerAgent(),
            "researcher": ResearcherAgent(),
            "tool_operator": ToolOperatorAgent(),
            "memory_coordinator": MemoryCoordinatorAgent(),
            "qa": QAAgent(),
            "writer": WriterAgent(),
        }
        self._max_retries = 3
        self._max_replans = 3
    
    def process_intent(
        self,
        intent: Intent,
        protocol: SoulBodyProtocol,
    ) -> IntentResult:
        """
        Full intent processing pipeline.
        
        1. Classify intent type
        2. Retrieve memory context
        3. Route to primary agent
        4. Agent produces tool_calls
        5. Validate each tool_call via safety gate
        6. Execute tools
        7. Validate output via QA
        8. Summarize result
        9. Store in memory
        """
        trace = []
        
        # Step 1: Classify
        classification = self._agents["commander"].route(intent.raw_text)
        trace.append(AgentStep("commander", "classified", classification["task_type"], 0))
        
        # Step 2: Memory context
        memory_ctx = self._agents["memory_coordinator"].retrieve(
            intent.raw_text, intent.context
        )
        
        # Step 3-6: Route and execute
        primary = classification["selected_agent"]
        agent = self._agents[primary]
        
        plan = agent.execute(intent.raw_text, context=memory_ctx)
        trace.append(AgentStep(primary, "planned", str(plan), 0))
        
        # Step 5: Safety gate per tool
        for tool_call in plan.get("tool_calls", []):
            approved, reason = protocol._validate_tool(tool_call)
            if not approved:
                if "Approval required" in reason:
                    return IntentResult(
                        intent_id=intent.intent_id,
                        status=IntentStatus.APPROVAL_NEEDED,
                        summary="",
                        tool_outputs=[],
                        agent_trace=trace,
                        error=None,
                        blocking_reason=None,
                        approval_request=ApprovalRequest(
                            tool_name=tool_call.tool,
                            risk_level=tool_call.risk,
                            description=reason,
                            parameters=tool_call.params,
                            capability=tool_call.tool,
                        ),
                        metadata={},
                    )
                else:
                    return IntentResult(
                        intent_id=intent.intent_id,
                        status=IntentStatus.BLOCKED,
                        summary="",
                        tool_outputs=[],
                        agent_trace=trace,
                        error=None,
                        blocking_reason=reason,
                        approval_request=None,
                        metadata={},
                    )
        
        # Step 6: Execute tools
        tool_outputs = []
        for tool_call in plan.get("tool_calls", []):
            output = protocol._execute_tool(tool_call)
            tool_outputs.append(output)
        
        # Step 7: QA validation
        qa_result = self._agents["qa"].validate(intent.raw_text, tool_outputs)
        if not qa_result["passed"]:
            # Retry logic here
            pass
        
        # Step 8: Summarize
        summary = self._agents["writer"].summarize(
            intent.raw_text, tool_outputs, qa_result
        )
        
        # Step 9: Memory
        result = IntentResult(
            intent_id=intent.intent_id,
            status=IntentStatus.SUCCESS,
            summary=summary,
            tool_outputs=tool_outputs,
            agent_trace=trace,
            error=None,
            blocking_reason=None,
            approval_request=None,
            metadata={},
        )
        protocol._store_memory(intent, result)
        
        return result
```

---

## 8. Implementation Phases

### Phase 1: Protocol Foundation
1. Create `SoulBodyProtocol` class with `submit_intent()` and `IntentResult`
2. Create `Intent` and `IntentResult` data models
3. Create `ApprovalRequest` model
4. Mark XXXIX body creates Intent instead of calling executor directly

### Phase 2: Safety Gate Integration
1. Wire `asimov.check_command()` as pre-flight gate
2. Wire `capability_registry` for per-tool risk checks
3. Implement approval flow (body shows dialog, protocol continues)
4. Map all existing tools to capabilities

### Phase 3: Agent Routing
1. Wire Commander agent as intent classifier
2. Map intent types to agent routing rules
3. Implement memory context retrieval
4. Wire each JARVIS agent to handle its intent types

### Phase 4: Tool Dispatch
1. Create EmbodimentLayer that loads from capability_registry
2. Replace Mark XXXIX's `_call_tool()` with protocol-mediated dispatch
3. Implement tool output collection and structuring

### Phase 5: Error Handling
1. Replace error_handler.py with QA Agent classification
2. Implement retry/replan/simplify logic in soul
3. Wire error reporting back through IntentResult

### Phase 6: Body Simplification
1. Simplify executor.py to thin Intent creator
2. Simplify task_queue.py to use protocol.submit_intent()
3. Remove direct planner.py calls from body
4. Keep only UI rendering in body

---

## 9. Key Architectural Decisions

| Decision | Choice | Reasoning |
|---|---|---|
| Who routes intents? | Soul (Commander agent) | Body should not know about agent types |
| Who validates safety? | Soul (both gates) | Body cannot be trusted to enforce safety |
| Who handles errors? | Soul (QA agent) | Error recovery is a reasoning task |
| Who summarizes results? | Soul (Writer agent) | Summary generation is an agent task |
| Body's only job | Create Intents, render results | Thin body = secure body |
| Approval flow | Soul → body → soul | Body shows UI, soul decides what to do |
| Memory storage | Soul-side | Memory belongs to the mind, not the body |

---

## 10. Migration Path

### What Gets Deleted from Mark XXXIX
- `executor._call_tool()` → replaced by `EmbodimentLayer.execute()`
- `executor._run_generated_code()` → replaced by `EngineerAgent` + safety gate
- `executor._inject_context()` → replaced by `MemoryCoordinator`
- `executor._summarize()` → replaced by `WriterAgent`
- `planner.create_plan()` → replaced by `PlannerAgent` (soul-side)
- `planner.replan()` → replaced by `Orchestrator.replan()` (soul-side)
- `error_handler.analyze_error()` → replaced by `QA Agent.classify_error()`
- `error_handler.generate_fix()` → replaced by `EngineerAgent.generate_fix()`

### What Stays in Mark XXXIX
- `task_queue.py` → refactored to use `ProtocolTaskQueue`
- `executor.py` → simplified to Intent creator + renderer
- UI rendering (HUD, speak, animations)
- User interaction (approval dialogs, confirmations)

### What Gets Created
- `tools/embodiment/protocol.py` — SoulBodyProtocol class
- `tools/embodiment/intent.py` — Intent, IntentResult, ToolOutput models
- `tools/embodiment/embodiment_layer.py` — Tool execution via capabilities
- `agents/orchestrator/protocol_handler.py` — Soul-side intent processing

---

*Architecture version: 1.0*
*Principle: The body renders. The soul decides. The protocol connects.*
