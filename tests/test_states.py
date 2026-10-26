import pytest

from agent.models.states import AgentState
from agent.orchestrator.state_machine import InvalidStateTransition, StateMachine
from agent.services.workflow_service import (
    WorkflowStateError,
    create_workflow,
    transition_workflow,
)


def test_full_forward_path_is_valid():
    sm = StateMachine()
    path = [
        (AgentState.RECEIVED, AgentState.SEARCHING),
        (AgentState.SEARCHING, AgentState.PROFILE_DISCOVERED),
        (AgentState.PROFILE_DISCOVERED, AgentState.PROFILE_CLASSIFIED),
        (AgentState.PROFILE_CLASSIFIED, AgentState.PROFILE_RESEARCHED),
        (AgentState.PROFILE_RESEARCHED, AgentState.GENERATING),
        (AgentState.GENERATING, AgentState.VALIDATING),
        (AgentState.VALIDATING, AgentState.WAITING_FOR_APPROVAL),
        (AgentState.WAITING_FOR_APPROVAL, AgentState.APPROVED),
        (AgentState.APPROVED, AgentState.EXECUTING),
        (AgentState.EXECUTING, AgentState.DRAFTED),
        (AgentState.DRAFTED, AgentState.VERIFIED),
    ]
    for current, target in path:
        assert sm.can_transition(current, target), f"{current} -> {target} should be valid"
        assert sm.transition(current, target) == target


def test_approval_transition_is_valid():
    sm = StateMachine()
    assert sm.can_transition(AgentState.WAITING_FOR_APPROVAL, AgentState.APPROVED)
    assert sm.transition(AgentState.WAITING_FOR_APPROVAL, AgentState.APPROVED) == AgentState.APPROVED


def test_rejected_to_executing_is_invalid():
    sm = StateMachine()
    assert not sm.can_transition(AgentState.REJECTED, AgentState.EXECUTING)
    with pytest.raises(InvalidStateTransition):
        sm.transition(AgentState.REJECTED, AgentState.EXECUTING)


def test_approval_cannot_be_skipped():
    sm = StateMachine()
    assert not sm.can_transition(AgentState.RECEIVED, AgentState.EXECUTING)
    assert not sm.can_transition(AgentState.GENERATING, AgentState.DRAFTED)
    with pytest.raises(InvalidStateTransition):
        sm.transition(AgentState.RECEIVED, AgentState.EXECUTING)


def test_rejection_requires_approval_gate():
    sm = StateMachine()
    assert not sm.can_transition(AgentState.VALIDATING, AgentState.REJECTED)
    assert not sm.can_transition(AgentState.DRAFTED, AgentState.REJECTED)


def test_terminated_state_has_no_outgoing_edges():
    sm = StateMachine()
    assert not sm.can_transition(AgentState.VERIFIED, AgentState.ERROR)


def test_error_state_is_recoverable():
    sm = StateMachine()
    assert sm.can_transition(AgentState.ERROR, AgentState.RECEIVED)
    assert sm.transition(AgentState.ERROR, AgentState.RECEIVED) == AgentState.RECEIVED


def test_persistent_workflow_transitions(db_session):
    workflow = create_workflow(db_session, workflow_type="SEARCH")
    db_session.commit()

    assert workflow.current_state == "RECEIVED"

    workflow = transition_workflow(db_session, workflow.id, AgentState.SEARCHING)
    assert workflow.current_state == "SEARCHING"

    workflow = transition_workflow(db_session, workflow.id, AgentState.PROFILE_DISCOVERED)
    assert workflow.current_state == "PROFILE_DISCOVERED"

    with pytest.raises(InvalidStateTransition):
        transition_workflow(db_session, workflow.id, AgentState.EXECUTING)

    reloaded = db_session.get(type(workflow), workflow.id)
    assert reloaded.current_state == "PROFILE_DISCOVERED"


def test_transition_unknown_workflow_raises(db_session):
    with pytest.raises(WorkflowStateError):
        transition_workflow(db_session, 9999, AgentState.SEARCHING)