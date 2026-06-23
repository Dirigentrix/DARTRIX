import time
from typing import Dict, Any, List
from soif_timeline import SoifTimeline
from trix_router import TrixRouter
from dartrix_kernel_scheduler import DartrixScheduler

class AgentCoreLoop:
    """
    AgentCoreLoop v1.0: Manages the lifecycle of autonomous agents.
    Iteratively fetches tasks from the DartrixScheduler and processes them.
    """
    def __init__(self, timeline: SoifTimeline, scheduler: DartrixScheduler):
        self.timeline = timeline
        self.scheduler = scheduler
        self.running = False
        self.iteration_count = 0

    def start(self, adapters: Dict[str, Any], max_iterations: int = 10):
        """
        Starts the loop. Processes up to max_iterations.
        """
        self.running = True
        self.timeline.log_event({
            "module": "AgentCoreLoop",
            "type": "LOOP_STARTED",
            "napięcie": 0.2,
            "mode": "ACTIVE",
            "details": {"max_iterations": max_iterations}
        })

        while self.running and self.iteration_count < max_iterations:
            self.iteration_count += 1
            task_id = self.scheduler.run_tick(adapters)
            
            if not task_id:
                # No tasks to process, idle tension
                self.timeline.log_event({
                    "module": "AgentCoreLoop",
                    "type": "LOOP_IDLE",
                    "napięcie": 0.05,
                    "mode": "IDLE",
                    "details": {"iteration": self.iteration_count}
                })
                time.sleep(1)
            else:
                self.timeline.log_event({
                    "module": "AgentCoreLoop",
                    "type": "LOOP_ITERATION",
                    "napięcie": 0.6,
                    "mode": "ACTIVE",
                    "details": {
                        "iteration": self.iteration_count,
                        "processed_task": task_id
                    }
                })
            
            # Short pulse delay
            time.sleep(0.5)

        self.stop()

    def stop(self):
        """
        Gracefully shuts down the core loop.
        """
        self.running = False
        self.timeline.log_event({
            "module": "AgentCoreLoop",
            "type": "LOOP_STOPPED",
            "napięcie": 0.1,
            "mode": "INACTIVE",
            "details": {"total_iterations": self.iteration_count}
        })

if __name__ == "__main__":
    # Integration Test
    tl = SoifTimeline()
    tr = TrixRouter(tl)
    ds = DartrixScheduler(tl, tr)
    loop = AgentCoreLoop(tl, ds)

    # Mock adapters
    system_adapters = {"WANKEL": "Active", "LEON": "Active", "SONIA": "Active"}

    # Schedule some sample load
    ds.schedule({"priority": "HIGH", "agent_type": "WANKEL", "payload": "init_system"})
    ds.schedule({"priority": "MEDIUM", "agent_type": "SONIA", "payload": "check_comms"})

    # Run for 5 iterations
    loop.start(system_adapters, max_iterations=5)
EOF