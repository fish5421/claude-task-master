# CTM Swarm Coordinator

The CTM Swarm is a set of utilities that allow multiple agents to work on a single
Task Master project. The `Coordinator` is responsible for orchestrating which tasks
are ready to be worked on and ensuring that agents do not step on each other's work.

## Coordinator Responsibilities

- **Dependency Tracking** – tasks are only made available when all of their
  dependencies are marked `done`.
- **Priority Queue** – ready tasks are ordered by priority and creation time.
- **Conflict Lock** – while a task is active its `impactSet` paths are locked so
  no other task can modify the same files.
- **State Flush** – task state is written back to `tasks.json` atomically.
- **Event Hook** – JSON events are printed when tasks start and finish.

## Usage Example

```python
from ctm_swarm.coordinator import Coordinator

c = Coordinator()
c.load_tasks("/path/to/tasks.json")
ready = c.pick_tasks(1)
if ready:
    task = ready[0]
    c.mark_in_progress(task.id, "agent-1")
    # ...work on the task...
    c.mark_done(task.id, "agent-1")
```
