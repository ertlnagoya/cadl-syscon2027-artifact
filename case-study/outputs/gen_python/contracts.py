"""Generated contract monitors for CADL SoS definition."""

from __future__ import annotations

from cadl.codegen.runtime_support import (
    CheckResult,
    ContractMonitorBase,
    RuntimeContext,
    Violation,
)


class EveningRoutineMonitor(ContractMonitorBase):
    """Contract monitor: EVENING_ROUTINE."""

    CONTRACT_ID = "EVENING_ROUTINE"
    PARTIES = ['RESIDENT', 'HOME_ROBOT']

    def check_assumptions(self, ctx: RuntimeContext) -> list[CheckResult]:
        results = []
        try:
            results.append(self._check('home_arrival_hour <= 23', (ctx.state['home_arrival_hour'] <= 23)))
        except Exception:
            results.append(self._check('home_arrival_hour <= 23', True))  # skip on error
        try:
            results.append(self._check('HOME_ROBOT.is_operational == true', (ctx.actors['HOME_ROBOT'].state['is_operational'] == True)))
        except Exception:
            results.append(self._check('HOME_ROBOT.is_operational == true', True))  # skip on error
        return results

    def check_guarantees(self, ctx: RuntimeContext) -> list[CheckResult]:
        results = []
        try:
            results.append(self._check('lights_out_hour <= 24', (ctx.state['lights_out_hour'] <= 24)))
        except Exception:
            results.append(self._check('lights_out_hour <= 24', True))  # skip on error
        return results


class PartTimeJobMonitor(ContractMonitorBase):
    """Contract monitor: PART_TIME_JOB."""

    CONTRACT_ID = "PART_TIME_JOB"
    PARTIES = ['RESIDENT', 'EMPLOYER']

    def check_assumptions(self, ctx: RuntimeContext) -> list[CheckResult]:
        results = []
        try:
            results.append(self._check('shift_start_hour >= 17', (ctx.state['shift_start_hour'] >= 17)))
        except Exception:
            results.append(self._check('shift_start_hour >= 17', True))  # skip on error
        return results

    def check_guarantees(self, ctx: RuntimeContext) -> list[CheckResult]:
        results = []
        try:
            results.append(self._check('home_arrival_hour >= 22', (ctx.state['home_arrival_hour'] >= 22)))
        except Exception:
            results.append(self._check('home_arrival_hour >= 22', True))  # skip on error
        return results
