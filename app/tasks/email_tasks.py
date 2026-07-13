import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from celery.utils.log import get_task_logger
from app.config.celery import celery_app
from app.config.settings import settings

logger = get_task_logger(__name__)

@celery_app.task(name="app.tasks.email_tasks.send_otp_email")
def send_otp_email(email: str, otp_code: str, purpose: str) -> bool:
    """
    Asynchronous Celery task for delivering OTP codes.
    Logs email details and falls back to print statements if SMTP credentials are unset.
    """
    logger.info(f"Dispatching OTP code {otp_code} to {email} for purpose: {purpose}")
    
    subject = f"STS Platform - Account Verification Code"
    body = f"""
    Hello,

    Your verification code is: {otp_code}

    This code is valid for 5 minutes. If you did not request this action, please secure your account credentials.

    Sincerely,
    The STS Team
    """

    # If SMTP settings are missing, mock-log the action for local development environment ease
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        logger.warn(
            f"SMTP configuration is missing. MOCK EMAIL DISPATCH COMPLETE:\n"
            f"--------------------------------------------------\n"
            f"TO: {email}\n"
            f"SUBJECT: {subject}\n"
            f"BODY: {body}\n"
            f"--------------------------------------------------"
        )
        return True

    try:
        msg = MIMEMultipart()
        msg["From"] = settings.SMTP_FROM
        msg["To"] = email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT)
        server.starttls()
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.sendmail(settings.SMTP_FROM, email, msg.as_string())
        server.quit()
        
        logger.info(f"Email notification successfully delivered to {email}")
        return True
    except Exception as e:
        logger.error(f"Failed to deliver email message to {email}. Error: {str(e)}")
        # Raise error to trigger Celery retry mechanism
        raise e

@celery_app.task(
    name="app.tasks.email_tasks.send_email",
    bind=True,
    max_retries=3,
    retry_backoff=True,
    default_retry_delay=60
)
def send_email(self, email: str, subject: str, body: str) -> bool:
    """
    General purpose background email dispatch worker with retry constraints.
    """
    logger.info(f"Dispatching email to {email} with subject: {subject}")
    
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        logger.warn(
            f"SMTP configuration is missing. MOCK EMAIL DISPATCH COMPLETE:\n"
            f"--------------------------------------------------\n"
            f"TO: {email}\n"
            f"SUBJECT: {subject}\n"
            f"BODY: {body}\n"
            f"--------------------------------------------------"
        )
        return True

    try:
        msg = MIMEMultipart()
        msg["From"] = settings.SMTP_FROM
        msg["To"] = email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT)
        server.starttls()
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.sendmail(settings.SMTP_FROM, email, msg.as_string())
        server.quit()
        
        logger.info(f"Email successfully delivered to {email}")
        return True
    except Exception as e:
        logger.error(f"Failed to deliver email to {email}. Error: {str(e)}")
        raise self.retry(exc=e, countdown=60)
