import uuid
import heapq
from typing import Dict, List, Any, Optional
from datetime import datetime
from soif_timeline import SoifTimeline
from trix_router import TrixRouter

class DartrixScheduler:
    """
    DartrixScheduler v1.0: Core kernel task orchestrator.
    Manages task prioritization, routing via TrixRouter, and logging via SoifTimeline.
    """
    
    PRIORITY_MAP = {
        "CRITICAL": 0,
        "HIGH": 1,
        "MEDIUM": 2,
        "LOW": 3
    }
    
    AGENT_MAP = {
        "WANKEL": 0,
        "LEON": 1,
        "SONIA": 2
    }

    def __init__(self, timeline: SoifTimeline, router: TrixRouter):
        self.timeline = timeline
        self.router = router
        # Priority queue stores (priority_val, agent_val, task_id, task_dict)
        self._queue: List[tuple] = []

    def schedule(self, task: Dict[str, Any]) -> str:
        """
        Schedules a task by pushing it to the priority queue and logging the event.
        Task should contain: 'priority', 'agent_type', 'payload'.
        """
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        priority = task.get("priority", "LOW").upper()
        agent_type = task.get("agent_type", "SONIA").upper()
        
        # Map strings to integers for min-heap (lower value = higher priority)
        p_val = self.PRIORITY_MAP.get(priority, 3)
        a_val = self.AGENT_MAP.get(agent_type, 2)
        
        # Store metadata in the task object
        task["id"] = task_id
        task["scheduled_at"] = datetime.utcnow().isoformat() + "Z"
        
        # Log scheduling event
        self.timeline.log_event({
            "module": "DartrixScheduler",
            "type": "TASK_SCHEDULED",
            "napięcie": 0.3,
            "mode": "PLANNING",
            "details": {
                "task_id": task_id,
                "priority": priority,
                "agent_type": agent_type
            }
        })
        
        heapq.heappush(self._queue, (p_val, a_val, task_id, task))
        return task_id

    def get_queue(self) -> List[Dict[str, Any]]:
        """
        Returns all queued tasks sorted by priority and agent type.
        """
        sorted_queue = sorted(self._queue)
        return [item[3] for item in sorted_queue]

    def run_tick(self, adapters: Dict[str, Any]) -> Optional[str]:
        """
        Executes a single tick: pops the highest priority task, 
        queries TrixRouter, and dispatches to the specified adapter.
        """
        if not self._queue:
            return None
            
        # Pop highest priority (lowest tuple values)
        p_val, a_val, task_id, task = heapq.heappop(self._queue)
        
        # Query TrixRouter for routing decision
        route = f"/kernel/dispatch/{task.get('agent_type', 'generic').lower()}"
        self.router.process_pipeline(task_id, route, cached=False)
        
        # Determine adapter (simulated dispatch)
        agent_type = task.get("agent_type", "SONIA").upper()
        adapter = adapters.get(agent_type)
        
        # Log Execution
        self.timeline.log_event({
            "module": "DartrixScheduler",
            "type": "TASK_EXECUTED",
            "napięcie": 0.8,
            "mode": "EXECUTION",
            "details": {
                "task_id": task_id,
                "route": route,
                "adapter": str(adapter)
            }
        })
        
        # Simulate reflection/completion
        result = "success"
        if adapter:
            # If adapter was a callable/class, we'd invoke it here
            pass

        self.timeline.log_event({
            "module": "DartrixScheduler",
            "type": "TASK_REFLECTED",
            "napięcie": 0.45,
            "mode": "COOLDOWN",
            "details": {
                "task_id": task_id,
                "status": result,
                "completion_time": datetime.utcnow().isoformat() + "Z"
            }
        })
        
        return task_id

if __name__ == "__main__":
    # Integration demonstration
    tl = SoifTimeline()
    tr = TrixRouter(tl)
    scheduler = DartrixScheduler(tl, tr)
    
    # Schedule diverse tasks
    scheduler.schedule({"priority": "LOW", "agent_type": "SONIA", "payload": "background_sync"})
    scheduler.schedule({"priority": "CRITICAL", "agent_type": "WANKEL", "payload": "emergency_shutdown"})
    scheduler.schedule({"priority": "HIGH", "agent_type": "LEON", "payload": "data_analysis"})
    
    # Check queue sorting
    print("Queued tasks (sorted):")
    for t in scheduler.get_queue():
        print(f"- {t['id']}: {t['priority']} | {t['agent_type']}")
        
    # Run a tick
    executed_id = scheduler.run_tick(adapters={"WANKEL": "PrimaryCore", "LEON": "NeuralEngine"})
    print(f"\nTick processed task: {executed_id}")
