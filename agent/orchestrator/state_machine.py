from agent.models.states import AgentState

VALID_TRANSITIONS: dict[AgentState, set[AgentState]] = {
    AgentState.RECEIVED: {AgentState.SEARCHING, AgentState.ERROR},
    AgentState.SEARCHING: {
        AgentState.PROFILE_DISCOVERED,
        AgentState.PROFILE_CLASSIFIED,
        AgentState.PROFILE_RESEARCHED,
        AgentState.ERROR,
    },
    AgentState.PROFILE_DISCOVERED: {AgentState.PROFILE_CLASSIFIED, AgentState.ERROR},
    AgentState.PROFILE_CLASSIFIED: {AgentState.PROFILE_RESEARCHED, AgentState.ERROR},
    AgentState.PROFILE_RESEARCHED: {AgentState.GENERATING, AgentState.ERROR},
    AgentState.GENERATING: {AgentState.VALIDATING, AgentState.ERROR},
    AgentState.VALIDATING: {
        AgentState.WAITING_FOR_APPROVAL,
        AgentState.GENERATING,
        AgentState.ERROR,
    },
    AgentState.WAITING_FOR_APPROVAL: {AgentState.APPROVED, AgentState.REJECTED},
    AgentState.APPROVED: {AgentState.EXECUTING},
    AgentState.EXECUTING: {AgentState.DRAFTED, AgentState.ERROR},
    AgentState.DRAFTED: {AgentState.VERIFIED, AgentState.ERROR},
    AgentState.VERIFIED: set(),
    AgentState.REJECTED: {AgentState.RECEIVED, AgentState.ERROR},
    AgentState.ERROR: {AgentState.RECEIVED},
}


class InvalidStateTransition(Exception):
    def __init__(self, current: AgentState, target: AgentState) -> None:
        self.current = current
        self.target = target
        super().__init__(f"Invalid state transition: {current.value} -> {target.value}")


class StateMachine:
    @staticmethod
    def _coerce(state) -> AgentState:
        if isinstance(state, AgentState):
            return state
        return AgentState(state)

    def can_transition(self, current, target) -> bool:
        current_state = self._coerce(current)
        target_state = self._coerce(target)
        return target_state in VALID_TRANSITIONS.get(current_state, set())

    def transition(self, current, target) -> AgentState:
        current_state = self._coerce(current)
        target_state = self._coerce(target)
        if not self.can_transition(current_state, target_state):
            raise InvalidStateTransition(current_state, target_state)
        return target_state