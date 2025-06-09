from __future__ import annotations

import heapq
import json
import os
from dataclasses import dataclass
import dataclasses
from typing import Dict, List, Optional


PRIORITY_ORDER = {
    "high": 0,
    "medium": 1,
    "low": 2,
}


@dataclass
class Task:
    id: str
    dependencies: List[str]
    priority: str
    createdAt: str
    impactSet: List[str]
    status: str = "pending"
    agent: Optional[str] = None


class Coordinator:
    def __init__(self) -> None:
        self.tasks: Dict[str, Task] = {}
        self.dependents: Dict[str, List[str]] = {}
        self.blocked_count: Dict[str, int] = {}
        self.ready_heap: List[tuple] = []
        self.locked_paths: set[str] = set()
        self.tasks_path: str = ""

    def load_tasks(self, path: str) -> None:
        self.tasks_path = path
        with open(path, "r") as f:
            data = json.load(f)
        self.tasks = {}
        self.dependents = {}
        for raw in data.get("tasks", []):
            task = Task(
                id=str(raw["id"]),
                dependencies=[str(d) for d in raw.get("dependencies", [])],
                priority=raw.get("priority", "medium"),
                createdAt=raw.get("createdAt", ""),
                impactSet=raw.get("impactSet", []),
                status=raw.get("status", "pending"),
            )
            self.tasks[task.id] = task
            for dep in task.dependencies:
                self.dependents.setdefault(dep, []).append(task.id)

        self._recalculate_blocked()
        self._build_ready_heap()

    def _recalculate_blocked(self) -> None:
        self.blocked_count = {}
        for task in self.tasks.values():
            count = 0
            for dep in task.dependencies:
                dep_task = self.tasks.get(dep)
                if dep_task and dep_task.status != "done":
                    count += 1
            self.blocked_count[task.id] = count

    def _build_ready_heap(self) -> None:
        self.ready_heap = []
        for task in self.tasks.values():
            if task.status == "pending" and self.blocked_count.get(task.id, 0) == 0:
                priority = PRIORITY_ORDER.get(task.priority, 1)
                heapq.heappush(
                    self.ready_heap, (priority, task.createdAt, task.id)
                )
        heapq.heapify(self.ready_heap)

    def pick_tasks(self, n: int) -> List[Task]:
        picked: List[Task] = []
        skipped: List[tuple] = []
        while self.ready_heap and len(picked) < n:
            item = heapq.heappop(self.ready_heap)
            task = self.tasks[item[2]]
            if any(p in self.locked_paths for p in task.impactSet):
                skipped.append(item)
                continue
            self.locked_paths.update(task.impactSet)
            picked.append(task)
        for item in skipped:
            heapq.heappush(self.ready_heap, item)
        return picked

    def mark_in_progress(self, task_id: str, agent_id: str) -> None:
        task = self.tasks.get(task_id)
        if not task:
            raise KeyError(f"Task {task_id} does not exist")
        if task.status != "pending":
            raise ValueError(f"Task {task_id} is not pending")
        task.status = "in-progress"
        task.agent = agent_id
        self._flush()
        self._emit_event("TASK_STARTED", task_id, agent_id)

    def mark_done(self, task_id: str, agent_id: str, success: bool = True) -> None:
        task = self.tasks.get(task_id)
        if not task:
            raise KeyError(f"Task {task_id} does not exist")
        if task.status == "done":
            raise ValueError(f"Task {task_id} already marked done")
        task.status = "done"
        task.agent = agent_id
        for p in task.impactSet:
            self.locked_paths.discard(p)
        for dep_id in self.dependents.get(task_id, []):
            self.blocked_count[dep_id] = max(0, self.blocked_count.get(dep_id, 1) - 1)
            dep_task = self.tasks[dep_id]
            if dep_task.status == "pending" and self.blocked_count[dep_id] == 0:
                priority = PRIORITY_ORDER.get(dep_task.priority, 1)
                heapq.heappush(
                    self.ready_heap, (priority, dep_task.createdAt, dep_task.id)
                )
        self._flush()
        self._emit_event("TASK_DONE", task_id, agent_id, success)

    def _flush(self) -> None:
        if not self.tasks_path:
            return
        tmp = self.tasks_path + ".tmp"
        data = {
            "tasks": [dataclasses.asdict(t) for t in self.tasks.values()]
        }
        with open(tmp, "w") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, self.tasks_path)

    def _emit_event(self, event: str, task_id: str, agent_id: str, success: bool | None = None) -> None:
        payload = {"event": event, "task_id": task_id, "agent_id": agent_id}
        if success is not None:
            payload["success"] = success
        print(json.dumps(payload), flush=True)
