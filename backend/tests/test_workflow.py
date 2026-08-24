from app.tickets.enums import TicketStatus
from app.workflows.service import WorkflowService


def test_happy_path_transitions() -> None:
    workflow = WorkflowService()
    workflow.assert_can_transition(TicketStatus.NEW, TicketStatus.ASSIGNED)
    workflow.assert_can_transition(TicketStatus.ASSIGNED, TicketStatus.IN_PROGRESS)
    workflow.assert_can_transition(TicketStatus.IN_PROGRESS, TicketStatus.RESOLVED)
    workflow.assert_can_transition(TicketStatus.RESOLVED, TicketStatus.CLOSED)


def test_terminal_states_have_no_exits() -> None:
    workflow = WorkflowService()
    for status in (TicketStatus.CLOSED, TicketStatus.CANCELLED, TicketStatus.REJECTED):
        assert not workflow.can_transition(status, TicketStatus.IN_PROGRESS)
