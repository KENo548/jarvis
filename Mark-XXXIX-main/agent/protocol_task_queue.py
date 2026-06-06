"""Protocol Task Queue — Body-side queue using SoulBodyProtocol.

This replaces task_queue.py with a protocol-mediated queue that
submits intents to the soul instead of calling executor directly.

Principle: The body renders. The soul decides. The protocol connects.

Usage:
    from agent.protocol_task_queue import ProtocolTaskQueue

    queue = ProtocolTaskQueue(protocol)
    task_id = queue.submit("Research AI safety and save it")
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Any

from tools.embodiment.protocol import (
    Intent,
    IntentResult,
    IntentStatus,
    SoulBodyProtocol,
    TaskPriority,
)


class TaskStatus(Enum):
    """Task status for body-side tracking."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(order=True)
class Task:
    """Body-side task record."""
    priority: int
    created_at: float = field(compare=False)
    task_id: str = field(compare=False)
    goal: str = field(compare=False)
    status: TaskStatus = field(compare=False, default=TaskStatus.PENDING)
    result: Any = field(compare=False, default=None)
    error: str = field(compare=False, default="")
    speak: Any = field(compare=False, default=None)
    on_complete: Any = field(compare=False, default=None)
    cancel_flag: threading.Event = field(compare=False, default_factory=threading.Event)


class ProtocolTaskQueue:
    """Body-side queue that submits intents to the soul.

    This replaces the old TaskQueue which called executor.execute() directly.
    Now it creates Intents and submits them via SoulBodyProtocol.
    """

    def __init__(self, protocol: SoulBodyProtocol):
        self._protocol = protocol
        self._tasks: dict[str, Task] = {}
        self._lock = threading.Lock()
        self._running = True
        self._session_id = str(uuid.uuid4())[:8]

    def submit(
        self,
        goal: str,
        priority: TaskPriority = TaskPriority.NORMAL,
        speak: Callable | None = None,
        on_complete: Callable | None = None,
    ) -> str:
        """Submit a goal as an Intent to the soul.

        The body NEVER calls executor directly. It creates an Intent
        and submits it via the protocol.

        Args:
            goal: What the user wants done
            priority: Task priority
            speak: TTS callback
            on_complete: Callback when done

        Returns:
            Task ID for tracking
        """
        task_id = str(uuid.uuid4())[:8]

        # Create body-side task record
        task = Task(
            priority=priority.value,
            created_at=time.time(),
            task_id=task_id,
            goal=goal,
            speak=speak,
            on_complete=on_complete,
        )

        with self._lock:
            self._tasks[task_id] = task

        # Create Intent (body's ONLY job besides rendering)
        intent = Intent(
            raw_text=goal,
            user_id="current_user",
            session_id=self._session_id,
            timestamp=time.time(),
            context={},
            priority=priority,
            speak_callback=speak,
            cancel_flag=task.cancel_flag,
        )

        # Submit to soul via protocol (NEVER call tools directly)
        future = self._protocol.submit_intent(
            intent,
            on_result=lambda result: self._handle_result(task_id, result),
        )

        # Update status
        with self._lock:
            task.status = TaskStatus.RUNNING

        if speak:
            speak("Processing your request, sir.")

        return task_id

    def cancel(self, task_id: str) -> bool:
        """Cancel a running task."""
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return False
            if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
                return False

            task.cancel_flag.set()
            task.status = TaskStatus.CANCELLED

        # Also cancel in protocol
        self._protocol.cancel_intent(task_id)
        return True

    def get_status(self, task_id: str) -> dict | None:
        """Get task status."""
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return None
            return {
                "task_id": task.task_id,
                "goal": task.goal,
                "status": task.status.value,
                "result": task.result,
                "error": task.error,
            }

    def get_all_statuses(self) -> list[dict]:
        """Get all task statuses."""
        with self._lock:
            return [
                {
                    "task_id": t.task_id,
                    "goal": t.goal[:50],
                    "status": t.status.value,
                }
                for t in self._tasks.values()
            ]

    def pending_count(self) -> int:
        """Count pending tasks."""
        with self._lock:
            return sum(1 for t in self._tasks.values() if t.status == TaskStatus.PENDING)

    def _handle_result(self, task_id: str, result: IntentResult):
        """Handle result from soul.

        This is the callback from the protocol when the soul finishes.
        The body renders the result here.
        """
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
                task.error = result.error or "Unknown error"
            elif result.status == IntentStatus.CANCELLED:
                task.status = TaskStatus.CANCELLED
            elif result.status == IntentStatus.APPROVAL_NEEDED:
                # Body shows approval dialog, then continues
                task.status = TaskStatus.RUNNING
                return

        # Render result via speak (body's ONLY job besides creating Intents)
        if task.speak:
            if task.status == TaskStatus.COMPLETED:
                task.speak(result.summary or "Task completed, sir.")
            elif task.status == TaskStatus.FAILED:
                task.speak(f"Task failed, sir. {task.error}")

        # Fire callback
        if task.on_complete and task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
            try:
                task.on_complete(task_id, task.result or task.error)
            except Exception as e:
                print(f"[ProtocolTaskQueue] on_complete error: {e}")

        print(f"[ProtocolTaskQueue] {task.status.value}: [{task_id}] {task.goal[:60]}")


# ── Module-level singleton ────────────────────────────────────────

_queue: ProtocolTaskQueue | None = None
_queue_lock = threading.Lock()


def get_protocol_queue(protocol: SoulBodyProtocol) -> ProtocolTaskQueue:
    """Get or create the protocol task queue singleton."""
    global _queue
    with _queue_lock:
        if _queue is None:
            _queue = ProtocolTaskQueue(protocol)
        return _queue
