"""Generated runtime orchestrator for LivingAloneAdjusted."""

from __future__ import annotations

from cadl.codegen.runtime_support import RuntimeContext

from .actors import ResidentActor, HomeRobotActor, EmployerActor
from .contracts import EveningRoutineMonitor, PartTimeJobMonitor


class LivingAloneAdjustedRuntime:
    """Runtime orchestrator for SoS: LivingAloneAdjusted."""

    def __init__(self) -> None:
        self.ctx = RuntimeContext()

        # Actors
        self.resident = ResidentActor()
        self.ctx.register_actor(self.resident)
        self.home_robot = HomeRobotActor()
        self.ctx.register_actor(self.home_robot)
        self.employer = EmployerActor()
        self.ctx.register_actor(self.employer)

        # Contract monitors
        self.evening_routine_monitor = EveningRoutineMonitor()
        self.part_time_job_monitor = PartTimeJobMonitor()

    def run_monitor_cycle(self) -> list:
        """Run all contract monitors and return violations."""
        all_violations = []
        all_violations.extend(self.evening_routine_monitor.run_checks(self.ctx))
        all_violations.extend(self.part_time_job_monitor.run_checks(self.ctx))
        for v in all_violations:
            self.ctx.record_violation(v)
        return all_violations

    def get_protocols(self) -> list:
        """Return all protocol executors."""
        return []

    def create_event_loop(self):
        """Create an EventLoop bound to this runtime."""
        from cadl.codegen.runtime_support import EventLoop
        return EventLoop(self)
