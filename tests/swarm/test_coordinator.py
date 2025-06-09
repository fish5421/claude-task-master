import json
import os
import tempfile
import unittest

from ctm_swarm.coordinator import Coordinator


SAMPLE_TASKS = {
    "tasks": [
        {
            "id": "1",
            "dependencies": [],
            "priority": "high",
            "createdAt": "2024-01-01T00:00:00Z",
            "impactSet": ["A"],
            "status": "pending",
        },
        {
            "id": "2",
            "dependencies": ["1"],
            "priority": "medium",
            "createdAt": "2024-01-02T00:00:00Z",
            "impactSet": ["B"],
            "status": "pending",
        },
    ]
}


class CoordinatorTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.tasks_path = os.path.join(self.tmpdir.name, "tasks.json")
        with open(self.tasks_path, "w") as f:
            json.dump(SAMPLE_TASKS, f)
        self.coordinator = Coordinator()
        self.coordinator.load_tasks(self.tasks_path)

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def test_pick_highest_priority(self):
        tasks = self.coordinator.pick_tasks(1)
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0].id, "1")

    def test_pick_reserves_paths(self):
        self.coordinator.pick_tasks(1)
        self.assertIn("A", self.coordinator.locked_paths)

    def test_mark_done_unlocks_dependents(self):
        tasks = self.coordinator.pick_tasks(1)
        self.coordinator.mark_in_progress(tasks[0].id, "agent")
        self.coordinator.mark_done(tasks[0].id, "agent")
        self.assertNotIn("A", self.coordinator.locked_paths)
        ready = self.coordinator.pick_tasks(1)
        self.assertEqual(len(ready), 1)
        self.assertEqual(ready[0].id, "2")

    def test_conflicting_paths_blocked(self):
        data = {
            "tasks": [
                {
                    "id": "1",
                    "dependencies": [],
                    "priority": "high",
                    "createdAt": "2024-01-01T00:00:00Z",
                    "impactSet": ["X"],
                    "status": "pending",
                },
                {
                    "id": "2",
                    "dependencies": [],
                    "priority": "high",
                    "createdAt": "2024-01-01T00:00:01Z",
                    "impactSet": ["X"],
                    "status": "pending",
                },
            ]
        }
        with open(self.tasks_path, "w") as f:
            json.dump(data, f)
        self.coordinator.load_tasks(self.tasks_path)
        ready = self.coordinator.pick_tasks(2)
        self.assertEqual(len(ready), 1)

    def test_partial_completion_keeps_blocked(self):
        data = {
            "tasks": [
                {
                    "id": "1",
                    "dependencies": [],
                    "priority": "high",
                    "createdAt": "2024-01-01T00:00:00Z",
                    "impactSet": ["A"],
                    "status": "pending",
                },
                {
                    "id": "2",
                    "dependencies": [],
                    "priority": "high",
                    "createdAt": "2024-01-01T00:00:01Z",
                    "impactSet": ["B"],
                    "status": "pending",
                },
                {
                    "id": "3",
                    "dependencies": ["1", "2"],
                    "priority": "medium",
                    "createdAt": "2024-01-02T00:00:00Z",
                    "impactSet": ["C"],
                    "status": "pending",
                },
            ]
        }
        with open(self.tasks_path, "w") as f:
            json.dump(data, f)
        self.coordinator.load_tasks(self.tasks_path)
        ready = self.coordinator.pick_tasks(1)
        self.coordinator.mark_in_progress(ready[0].id, "agent")
        self.coordinator.mark_done(ready[0].id, "agent")
        next_ready = self.coordinator.pick_tasks(1)
        self.assertEqual(len(next_ready), 1)
        self.assertEqual(next_ready[0].id, "2")

    def test_events_and_flush(self):
        tasks = self.coordinator.pick_tasks(1)
        from io import StringIO
        import contextlib

        buf = StringIO()
        with contextlib.redirect_stdout(buf):
            self.coordinator.mark_in_progress(tasks[0].id, "agent")
            self.coordinator.mark_done(tasks[0].id, "agent")
        output = buf.getvalue().splitlines()
        self.assertEqual(output[0], json.dumps({"event": "TASK_STARTED", "task_id": "1", "agent_id": "agent"}))
        self.assertEqual(output[1], json.dumps({"event": "TASK_DONE", "task_id": "1", "agent_id": "agent", "success": True}))
        with open(self.tasks_path) as f:
            data = json.load(f)
        task_dict = {t["id"]: t for t in data["tasks"]}
        self.assertEqual(task_dict["1"]["status"], "done")

    def test_mark_done_twice_errors(self):
        tasks = self.coordinator.pick_tasks(1)
        self.coordinator.mark_in_progress(tasks[0].id, "agent")
        self.coordinator.mark_done(tasks[0].id, "agent")
        with self.assertRaises(ValueError):
            self.coordinator.mark_done(tasks[0].id, "agent")


if __name__ == "__main__":
    unittest.main()
