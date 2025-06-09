import json
import os
import tempfile
import unittest

from ctm_swarm.coordinator import Coordinator


TASKS = {
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


class CoordinatorIntegrationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.tasks_path = os.path.join(self.tmpdir.name, "tasks.json")
        with open(self.tasks_path, "w") as f:
            json.dump(TASKS, f)
        self.coordinator = Coordinator()
        self.coordinator.load_tasks(self.tasks_path)

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def test_parallel_completion_unblocks_dependents(self):
        ready = self.coordinator.pick_tasks(2)
        self.assertEqual({t.id for t in ready}, {"1", "2"})

        for t, agent in zip(ready, ["agentA", "agentB"]):
            self.coordinator.mark_in_progress(t.id, agent)
            self.coordinator.mark_done(t.id, agent)

        next_ready = self.coordinator.pick_tasks(1)
        self.assertEqual(len(next_ready), 1)
        self.assertEqual(next_ready[0].id, "3")

    def test_single_completion_keeps_blocked(self):
        ready = self.coordinator.pick_tasks(1)
        self.coordinator.mark_in_progress(ready[0].id, "agentA")
        self.coordinator.mark_done(ready[0].id, "agentA")
        next_ready = self.coordinator.pick_tasks(1)
        self.assertEqual(len(next_ready), 1)
        self.assertEqual(next_ready[0].id, "2")


if __name__ == "__main__":
    unittest.main()
