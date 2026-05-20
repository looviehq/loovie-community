"""In-memory task store.

Tracks the lifecycle of generation requests:

    pending -> processing -> success
                          -> failed

Task ids are opaque to the client (`task_loovie_<12hex>`) and the store
is thread-safe so the route handlers (create/read) and monitor threads
(update) can share state without coordination.
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("comfyui_loovie.task_store")


class TaskState(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"


@dataclass
class TaskRecord:
    """Observable state of a single generation task."""

    task_id: str
    prompt: str
    aspect_ratio: str
    workflow_name: str
    state: TaskState = TaskState.PENDING
    comfy_prompt_id: str | None = None
    result_url: str | None = None
    error_message: str | None = None
    fail_code: str | None = None
    created_at: float = field(default_factory=time.time)
    completed_at: float | None = None
    progress: int = 0
    progress_step: int = 0
    progress_total: int = 0
    current_node: str | None = None


def _generate_task_id() -> str:
    return f"task_loovie_{uuid.uuid4().hex[:12]}"


class _InMemoryTaskStore:
    """Process-local dict-backed implementation."""

    def __init__(self) -> None:
        self._tasks: dict[str, TaskRecord] = {}
        self._lock = threading.Lock()

    def create_task(
        self,
        *,
        prompt: str,
        aspect_ratio: str,
        workflow_name: str,
    ) -> TaskRecord:
        record = TaskRecord(
            task_id=_generate_task_id(),
            prompt=prompt,
            aspect_ratio=aspect_ratio,
            workflow_name=workflow_name,
        )
        with self._lock:
            self._tasks[record.task_id] = record
            if len(self._tasks) % 50 == 0:
                self._cleanup_locked(max_age_seconds=3600)
        return record

    def get_task(self, task_id: str) -> TaskRecord | None:
        with self._lock:
            return self._tasks.get(task_id)

    def update_task(self, task_id: str, **kwargs: object) -> None:
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return
            for key, value in kwargs.items():
                if hasattr(task, key):
                    setattr(task, key, value)

    def cleanup_old_tasks(self, max_age_seconds: float = 3600) -> int:
        with self._lock:
            return self._cleanup_locked(max_age_seconds=max_age_seconds)

    def _cleanup_locked(self, *, max_age_seconds: float) -> int:
        cutoff = time.time() - max_age_seconds
        expired = [
            tid
            for tid, t in self._tasks.items()
            if t.state in (TaskState.SUCCESS, TaskState.FAILED) and t.created_at < cutoff
        ]
        for tid in expired:
            del self._tasks[tid]
        return len(expired)


class TaskStore:
    """Facade exposing a process-wide singleton instance."""

    _instance: _InMemoryTaskStore | None = None
    _init_lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> _InMemoryTaskStore:
        if cls._instance is None:
            with cls._init_lock:
                if cls._instance is None:
                    cls._instance = _InMemoryTaskStore()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Drop the singleton (used by tests)."""
        cls._instance = None
