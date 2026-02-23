from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import BaseModel, EmailStr
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
from app.api.deps import check_rate_limit
from app.config import get_settings

router = APIRouter(prefix="/contact", tags=["contact"])
logger = logging.getLogger(__name__)
settings = get_settings()

class ContactRequest(BaseModel):
    name: str
    email: EmailStr
    subject: str
    message: str

def send_email_task(name: str, sender_email: str, subject: str, message: str):
    try:
        if not settings.EMAIL_USER or not settings.EMAIL_PASSWORD:
            logger.warning("SMTP credentials not set. Simulating email send.")
            logger.info(f"Mock email from {name} <{sender_email}>: {subject}")
            return
            
        msg = MIMEMultipart()
        msg['From'] = settings.EMAIL_USER
        msg['To'] = "rlaehdrb2485@naver.com"
        msg['Subject'] = f"[CertFinder 문의] {subject}"
        
        body = f"발신자: {name} ({sender_email})\n\n{message}"
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        # Select appropriate SMTP class based on port
        if settings.SMTP_PORT == 465:
            server = smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT)
        else:
            server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT)
            server.starttls()
            
        server.login(settings.EMAIL_USER, settings.EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        logger.info(f"Successfully sent contact email from {sender_email}")
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"Failed to send email: {e}\n{error_trace}")

@router.post("")
async def submit_contact(
    request: ContactRequest,
    background_tasks: BackgroundTasks,
    _: None = Depends(check_rate_limit)
):
    """Submit a contact/help request."""
    # Run in background to not block the API response
    background_tasks.add_task(
        send_email_task,
        name=request.name,
        sender_email=request.email,
        subject=request.subject,
        message=request.message
    )
    return {"message": "문의가 성공적으로 접수되었습니다."}
