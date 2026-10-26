from sqlalchemy.orm import Session

from agent.models.states import AgentState
from agent.orchestrator.state_machine import StateMachine
from database.models import Workflow


class WorkflowStateError(Exception):
    pass


def create_workflow(
    db: Session,
    workflow_type: str,
    context: dict | None = None,
    initial_state: AgentState = AgentState.RECEIVED,
) -> Workflow:
    workflow = Workflow(
        workflow_type=workflow_type,
        current_state=initial_state.value,
        context=context,
    )
    db.add(workflow)
    db.flush()
    return workflow


def get_workflow(db: Session, workflow_id: int) -> Workflow | None:
    return db.get(Workflow, workflow_id)


def transition_workflow(db: Session, workflow_id: int, target_state: AgentState) -> Workflow:
    workflow = get_workflow(db, workflow_id)
    if workflow is None:
        raise WorkflowStateError(f"Workflow {workflow_id} not found")
    new_state = StateMachine().transition(AgentState(workflow.current_state), target_state)
    workflow.current_state = new_state.value
    db.add(workflow)
    db.commit()
    db.refresh(workflow)
    return workflow