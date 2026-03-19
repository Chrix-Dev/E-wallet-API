from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from app.core.config import settings


async def send_verification_email(to_email: str, full_name: str, token: str):
    verification_url = f"http://localhost:8000/api/v1/auth/verify?token={token}"

    message = Mail(
        from_email=settings.SENDGRID_SENDER_EMAIL,
        to_emails=to_email,
        subject="Verify your E-Wallet email",
        html_content=f"""
        <h2>Hi {full_name},</h2>
        <p>Thanks for signing up. Click the link below to verify your email address:</p>
        <a href="{verification_url}">Verify Email</a>
        <p>This link expires in 24 hours.</p>
        <p>If you didn't create an account, ignore this email.</p>
        """
    )

    sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
    sg.send(message)