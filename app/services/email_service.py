from app.tasks.email_tasks import send_otp_email

class EmailService:
    """Service wrapper layer interface dispatching email tasks to Celery brokers."""
    
    @staticmethod
    def send_registration_otp(email: str, code: str) -> None:
        """Dispatches an OTP verification code task for student registrations."""
        send_otp_email.delay(email, code, "registration")

    @staticmethod
    def send_password_reset_otp(email: str, code: str) -> None:
        """Dispatches an OTP code task for account password recoveries."""
        send_otp_email.delay(email, code, "password_reset")

    @staticmethod
    def send_account_deletion_otp(email: str, code: str) -> None:
        """Dispatches an OTP confirmation code task for user deletion validations."""
        send_otp_email.delay(email, code, "account_deletion")
