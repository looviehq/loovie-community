"""Task-store lifecycle and singleton tests."""

from __future__ import annotations

import re
import threading
import time

from comfyui_loovie.task_store import TaskState, TaskStore

# ---------------------------------------------------------------------
# Task ID format.
# ---------------------------------------------------------------------


def test_task_id_matches_documented_format() -> None:
    store = TaskStore.get_instance()
    record = store.create_task(prompt="hi", aspect_ratio="1:1", workflow_name="flux-2-klein")
    assert re.match(r"^task_loovie_[0-9a-f]{12}$", record.task_id)


# ---------------------------------------------------------------------
# Lifecycle.
# ---------------------------------------------------------------------


def test_initial_state_is_pending() -> None:
    store = TaskStore.get_instance()
    record = store.create_task(prompt="hi", aspect_ratio="1:1", workflow_name="flux-2-klein")
    assert record.state == TaskState.PENDING


def test_get_task_returns_same_record() -> None:
    store = TaskStore.get_instance()
    record = store.create_task(prompt="x", aspect_ratio="1:1", workflow_name="w")
    fetched = store.get_task(record.task_id)
    assert fetched is record


def test_get_task_returns_none_for_unknown_id() -> None:
    assert TaskStore.get_instance().get_task("task_loovie_nonexistent") is None


def test_update_task_changes_state() -> None:
    store = TaskStore.get_instance()
    record = store.create_task(prompt="x", aspect_ratio="1:1", workflow_name="w")
    store.update_task(record.task_id, state=TaskState.PROCESSING, progress=42)
    assert record.state == TaskState.PROCESSING
    assert record.progress == 42


def test_update_task_on_unknown_id_is_silent_no_op() -> None:
    """Late progress callbacks for a tidied-up task must not crash."""
    TaskStore.get_instance().update_task("task_loovie_gone", state=TaskState.SUCCESS)


def test_update_task_ignores_unknown_attributes() -> None:
    """`hasattr` guard prevents tests/callers from accidentally setting random fields."""
    store = TaskStore.get_instance()
    record = store.create_task(prompt="x", aspect_ratio="1:1", workflow_name="w")
    store.update_task(record.task_id, not_a_real_field="bogus")
    assert not hasattr(record, "not_a_real_field")


# ---------------------------------------------------------------------
# Cleanup.
# ---------------------------------------------------------------------


def test_cleanup_removes_only_terminal_tasks_older_than_cutoff() -> None:
    store = TaskStore.get_instance()
    young_pending = store.create_task(prompt="a", aspect_ratio="1:1", workflow_name="w")
    young_done = store.create_task(prompt="b", aspect_ratio="1:1", workflow_name="w")
    old_done = store.create_task(prompt="c", aspect_ratio="1:1", workflow_name="w")

    # Mark the two non-pending tasks done.
    store.update_task(young_done.task_id, state=TaskState.SUCCESS)
    store.update_task(old_done.task_id, state=TaskState.SUCCESS)

    # Age the old one by rewinding its created_at.
    old_done.created_at = time.time() - 7200  # 2h ago

    removed = store.cleanup_old_tasks(max_age_seconds=3600)
    assert removed == 1
    assert store.get_task(old_done.task_id) is None
    assert store.get_task(young_done.task_id) is not None
    assert store.get_task(young_pending.task_id) is not None


def test_cleanup_does_not_remove_pending_or_processing_tasks() -> None:
    """Even ancient non-terminal tasks survive cleanup, they're still in-flight."""
    store = TaskStore.get_instance()
    ancient_pending = store.create_task(prompt="x", aspect_ratio="1:1", workflow_name="w")
    ancient_pending.created_at = time.time() - 86400  # a day ago

    removed = store.cleanup_old_tasks(max_age_seconds=3600)
    assert removed == 0
    assert store.get_task(ancient_pending.task_id) is not None


# ---------------------------------------------------------------------
# Singleton.
# ---------------------------------------------------------------------


def test_get_instance_returns_same_object_across_calls() -> None:
    assert TaskStore.get_instance() is TaskStore.get_instance()


def test_reset_drops_the_singleton() -> None:
    first = TaskStore.get_instance()
    first.create_task(prompt="x", aspect_ratio="1:1", workflow_name="w")
    TaskStore.reset()
    second = TaskStore.get_instance()
    assert second is not first


def test_singleton_init_is_thread_safe() -> None:
    """Many threads racing on `get_instance` end up with the same instance."""
    TaskStore.reset()
    seen: list[object] = []
    barrier = threading.Barrier(8)

    def grab() -> None:
        barrier.wait()
        seen.append(TaskStore.get_instance())

    threads = [threading.Thread(target=grab) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert all(s is seen[0] for s in seen)
