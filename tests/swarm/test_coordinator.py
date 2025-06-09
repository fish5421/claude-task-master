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


if __name__ == "__main__":
    unittest.main()
