"""Unit tests for typed explicit state machine."""

import pytest
from aegis.errors import AegisError
from aegis.models import AgentState
from aegis.state import StateMachine


def test_valid_state_transitions():
    sm = StateMachine(AgentState.IDLE)
    assert sm.current_state == AgentState.IDLE

    sm.transition(AgentState.PLAN, reason="Task started")
    assert sm.current_state == AgentState.PLAN

    sm.transition(AgentState.IMPLEMENT, reason="Plan ready")
    assert sm.current_state == AgentState.IMPLEMENT

    sm.transition(AgentState.VERIFY, reason="Testing implementation")
    assert sm.current_state == AgentState.VERIFY

    sm.transition(AgentState.COMPLETE, reason="Tests passed")
    assert sm.current_state == AgentState.COMPLETE
    assert sm.is_terminal() is True


def test_diagnose_and_repair_transitions():
    sm = StateMachine(AgentState.VERIFY)
    sm.transition(AgentState.DIAGNOSE, reason="Verification failed")
    assert sm.current_state == AgentState.DIAGNOSE

    sm.transition(AgentState.IMPLEMENT, reason="Applying fix")
    assert sm.current_state == AgentState.IMPLEMENT


def test_invalid_state_transition_raises():
    sm = StateMachine(AgentState.IDLE)
    with pytest.raises(AegisError):
        sm.transition(AgentState.COMPLETE, reason="Cannot jump from IDLE to COMPLETE")
