"""Generated actor classes for CADL SoS definition."""

from __future__ import annotations

from cadl.codegen.runtime_support import ActorBase, AutonomyLevel


class ResidentActor(ActorBase):
    """Actor: RESIDENT (role=student_living_alone, autonomy=high)."""

    ROLE = "student_living_alone"
    AUTONOMY = AutonomyLevel.HIGH

    def __init__(self) -> None:
        super().__init__(actor_id="RESIDENT", role=self.ROLE)
        self.state: dict = {}


class HomeRobotActor(ActorBase):
    """Actor: HOME_ROBOT (role=reminder_and_observer, autonomy=low)."""

    ROLE = "reminder_and_observer"
    AUTONOMY = AutonomyLevel.LOW

    def __init__(self) -> None:
        super().__init__(actor_id="HOME_ROBOT", role=self.ROLE)
        self.state: dict = {}


class EmployerActor(ActorBase):
    """Actor: EMPLOYER (role=part_time_employer, autonomy=high)."""

    ROLE = "part_time_employer"
    AUTONOMY = AutonomyLevel.HIGH

    def __init__(self) -> None:
        super().__init__(actor_id="EMPLOYER", role=self.ROLE)
        self.state: dict = {}
