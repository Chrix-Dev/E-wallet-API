from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from app.core.config import settings


def _send(to_email: str, subject: str, html: str):
    message = Mail(
        from_email=settings.SENDGRID_SENDER_EMAIL,
        to_emails=to_email,
        subject=subject,
        html_content=html,
    )
    sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
    sg.send(message)


async def send_verification_email(to_email: str, full_name: str, token: str):
    verification_url = f"http://localhost:8000/api/v1/auth/verify?token={token}"
    _send(
        to_email=to_email,
        subject="Verify your Aza-Pay email",
        html=f"""
        <h2>Hi {full_name},</h2>
        <p>Thanks for signing up. Click the link below to verify your email address:</p>
        <a href="{verification_url}">Verify Email</a>
        <p>This link expires in 24 hours.</p>
        <p>If you didn't create an account, ignore this email.</p>
        """
    )


async def send_funding_email(to_email: str, full_name: str, amount: str, balance: str, reference: str):
    _send(
        to_email=to_email,
        subject="Your wallet has been funded",
        html=f"""
        <h2>Hi {full_name},</h2>
        <p>Your wallet has been credited successfully.</p>
        <table>
            <tr><td><b>Amount:</b></td><td>₦{amount}</td></tr>
            <tr><td><b>New Balance:</b></td><td>₦{balance}</td></tr>
            <tr><td><b>Reference:</b></td><td>{reference}</td></tr>
        </table>
        <p>If you did not initiate this transaction, please contact support immediately.</p>
        """
    )


async def send_transfer_sent_email(to_email: str, full_name: str, amount: str, receiver_email: str, reference: str, balance: str):
    _send(
        to_email=to_email,
        subject="Transfer successful",
        html=f"""
        <h2>Hi {full_name},</h2>
        <p>Your transfer was successful.</p>
        <table>
            <tr><td><b>Amount:</b></td><td>₦{amount}</td></tr>
            <tr><td><b>To:</b></td><td>{receiver_email}</td></tr>
            <tr><td><b>Reference:</b></td><td>{reference}</td></tr>
            <tr><td><b>New Balance:</b></td><td>₦{balance}</td></tr>
        </table>
        """
    )


async def send_transfer_received_email(to_email: str, full_name: str, amount: str, sender_email: str, reference: str, balance: str):
    _send(
        to_email=to_email,
        subject="You have received a transfer",
        html=f"""
        <h2>Hi {full_name},</h2>
        <p>You just received a transfer.</p>
        <table>
            <tr><td><b>Amount:</b></td><td>₦{amount}</td></tr>
            <tr><td><b>From:</b></td><td>{sender_email}</td></tr>
            <tr><td><b>Reference:</b></td><td>{reference}</td></tr>
            <tr><td><b>New Balance:</b></td><td>₦{balance}</td></tr>
        </table>
        """
    )


async def send_withdrawal_success_email(to_email: str, full_name: str, amount: str, reference: str, balance: str):
    _send(
        to_email=to_email,
        subject="Withdrawal successful",
        html=f"""
        <h2>Hi {full_name},</h2>
        <p>Your withdrawal has been processed successfully.</p>
        <table>
            <tr><td><b>Amount:</b></td><td>₦{amount}</td></tr>
            <tr><td><b>Reference:</b></td><td>{reference}</td></tr>
            <tr><td><b>Remaining Balance:</b></td><td>₦{balance}</td></tr>
        </table>
        """
    )


async def send_withdrawal_failed_email(to_email: str, full_name: str, amount: str, reference: str, balance: str):
    _send(
        to_email=to_email,
        subject="Withdrawal failed — your balance has been reversed",
        html=f"""
        <h2>Hi {full_name},</h2>
        <p>Unfortunately your withdrawal could not be processed. Your balance has been reversed.</p>
        <table>
            <tr><td><b>Amount:</b></td><td>₦{amount}</td></tr>
            <tr><td><b>Reference:</b></td><td>{reference}</td></tr>
            <tr><td><b>Restored Balance:</b></td><td>₦{balance}</td></tr>
        </table>
        <p>Please try again or contact support if the issue persists.</p>
        """
    )