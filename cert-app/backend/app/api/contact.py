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

def _send_one(server: smtplib.SMTP, from_addr: str, to_addr: str, subject: str, body: str):
    msg = MIMEMultipart()
    msg["From"] = from_addr
    msg["To"] = to_addr
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))
    server.send_message(msg)


def send_email_task(name: str, sender_email: str, subject: str, message: str):
    try:
        if not settings.EMAIL_USER or not settings.EMAIL_PASSWORD:
            logger.warning("SMTP credentials not set. Simulating email send.")
            logger.info(f"Mock email from {name} <{sender_email}>: {subject}")
            return

        to_admin = f"발신자: {name} ({sender_email})\n\n{message}"
        to_user = (
            f"{name}님, 문의해 주셔서 감사합니다.\n\n"
            "문의가 접수되었습니다. 검토 후 입력해 주신 이메일로 빠른 시일 내에 답변 드리겠습니다.\n\n"
            "— CertFinder"
        )

        if settings.SMTP_PORT == 465:
            server = smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT)
        else:
            server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT)
            server.starttls()

        server.login(settings.EMAIL_USER, settings.EMAIL_PASSWORD)

        # 1) 관리자에게 문의 내용 전달
        admin_email = settings.CONTACT_EMAIL or settings.EMAIL_USER
        _send_one(
            server,
            settings.EMAIL_USER,
            admin_email,
            f"[CertFinder 문의] {subject}",
            to_admin,
        )

        # 2) 사용자에게 접수 확인 메일 발송 (문의 접수 완료 알림)
        _send_one(
            server,
            settings.EMAIL_USER,
            sender_email,
            "[CertFinder] 문의 접수 완료",
            to_user,
        )

        server.quit()
        logger.info(f"Contact email sent: admin + confirmation to {sender_email}")
    except Exception as e:
        import traceback
        logger.error(f"Failed to send contact email: {e}\n{traceback.format_exc()}")

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
