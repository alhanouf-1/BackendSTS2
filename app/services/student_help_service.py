import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from app.models.help_ticket import HelpTicket, TicketStatus
from app.repositories.help_ticket_repository import HelpTicketRepository
from app.tasks.email_tasks import send_email

class StudentHelpService:
    """Orchestrates technical support tickets submission and dispatching administrative alerts."""

    @staticmethod
    async def create_ticket(
        db: AsyncSession,
        student_id: uuid.UUID,
        subject: str,
        description: str
    ) -> HelpTicket:
        # Enforce VARCHAR(100) validation limit
        if len(subject) > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ticket subject exceeds the strict 100-character limit."
            )

        ticket_repo = HelpTicketRepository(db)
        ticket = HelpTicket(
            student_id=student_id,
            subject=subject,
            description=description,
            status=TicketStatus.OPEN
        )
        await ticket_repo.create(ticket)
        await db.flush()

        # Dispatch async background email alert to administrative corporate support
        support_email = "support@sts-platform.com"
        email_body = (
            f"NEW SUPPORT TICKET DISPATCHED:\n\n"
            f"Ticket ID: {ticket.id}\n"
            f"Student ID: {student_id}\n"
            f"Subject: {subject}\n"
            f"Description: {description}\n"
        )
        send_email.delay(support_email, f"Support Ticket Filed: {subject[:30]}", email_body)

        return ticket
