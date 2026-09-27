"""Typed explicit state machine governing Aegis agent execution transitions."""

from typing import List, Optional
from pydantic import BaseModel, Field

from aegis.errors import AegisError
from aegis.models import AgentState


class StateTransition(BaseModel):
    from_state: AgentState
    to_state: AgentState
    reason: str
    turn: int


VALID_TRANSITIONS: dict[AgentState, set[AgentState]] = {
    AgentState.IDLE: {AgentState.PLAN, AgentState.ABORTED, AgentState.BLOCKED},
    AgentState.PLAN: {AgentState.IMPLEMENT, AgentState.FAILED, AgentState.ABORTED, AgentState.BLOCKED},
    AgentState.IMPLEMENT: {AgentState.IMPLEMENT, AgentState.VERIFY, AgentState.FAILED, AgentState.ABORTED, AgentState.BLOCKED},
    AgentState.VERIFY: {AgentState.COMPLETE, AgentState.DIAGNOSE, AgentState.FAILED, AgentState.ABORTED, AgentState.BLOCKED},
    AgentState.DIAGNOSE: {AgentState.IMPLEMENT, AgentState.FAILED, AgentState.ABORTED, AgentState.BLOCKED},
    AgentState.COMPLETE: {AgentState.COMMIT, AgentState.FAILED},
    AgentState.COMMIT: set(),
    AgentState.FAILED: set(),
    AgentState.ABORTED: set(),
    AgentState.BLOCKED: set(),
}


class StateMachine:
    """Enforces deterministic, fail-closed state lifecycle transitions."""

    def __init__(self, initial_state: AgentState = AgentState.IDLE):
        self._current_state = initial_state
        self.transitions: list[StateTransition] = []
        self.turn: int = 0

    @property
    def current_state(self) -> AgentState:
        return self._current_state

    def is_terminal(self) -> bool:
        return self._current_state in (
            AgentState.COMPLETE,
            AgentState.COMMIT,
            AgentState.FAILED,
            AgentState.ABORTED,
            AgentState.BLOCKED,
        )

    def transition(self, to_state: AgentState, reason: str = "") -> None:
        """Transitions to target state if permitted by lifecycle rules, else raises AegisError."""
        allowed = VALID_TRANSITIONS.get(self._current_state, set())
        if to_state not in allowed:
            raise AegisError(
                f"Invalid state transition from {self._current_state.value} to {to_state.value}. "
                f"Reason: {reason}. Allowed target states: {[s.value for s in allowed]}"
            )

        self.transitions.append(StateTransition(
            from_state=self._current_state,
            to_state=to_state,
            reason=reason,
            turn=self.turn,
        ))
        self._current_state = to_state
