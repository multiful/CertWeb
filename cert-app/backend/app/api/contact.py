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
            logger.error(
                "[SMTP] 환경변수 미설정 — EMAIL_USER=%r, SMTP_HOST=%r. "
                "Render 대시보드 > Environment에 EMAIL_USER / EMAIL_PASSWORD / "
                "SMTP_HOST / SMTP_PORT / CONTACT_EMAIL 값을 추가하세요.",
                settings.EMAIL_USER,
                settings.SMTP_HOST,
            )
            return

        logger.info(
            "[SMTP] 메일 발송 시도: host=%s port=%d user=%s → admin=%s, user=%s",
            settings.SMTP_HOST,
            settings.SMTP_PORT,
            settings.EMAIL_USER,
            settings.CONTACT_EMAIL or settings.EMAIL_USER,
            sender_email,
        )

        to_admin = f"발신자: {name} ({sender_email})\n\n{message}"
        to_user = (
            f"{name}님, 문의해 주셔서 감사합니다.\n\n"
            "문의가 접수되었습니다. 검토 후 입력해 주신 이메일로 빠른 시일 내에 답변 드리겠습니다.\n\n"
            "— CertFinder"
        )

        if settings.SMTP_PORT == 465:
            server = smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15)
        else:
            server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15)
            server.ehlo()
            server.starttls()
            server.ehlo()

        server.login(settings.EMAIL_USER, settings.EMAIL_PASSWORD)

        admin_email = settings.CONTACT_EMAIL or settings.EMAIL_USER
        _send_one(server, settings.EMAIL_USER, admin_email, f"[CertFinder 문의] {subject}", to_admin)
        _send_one(server, settings.EMAIL_USER, sender_email, "[CertFinder] 문의 접수 완료", to_user)

        server.quit()
        logger.info("[SMTP] 발송 완료: admin(%s) + user(%s)", admin_email, sender_email)
    except smtplib.SMTPAuthenticationError as e:
        logger.error("[SMTP] 인증 실패 — 앱 비밀번호 또는 계정 SMTP 허용 설정을 확인하세요: %s", e)
    except smtplib.SMTPConnectError as e:
        logger.error("[SMTP] 연결 실패 — host=%s port=%d: %s", settings.SMTP_HOST, settings.SMTP_PORT, e)
    except Exception as e:
        import traceback
        logger.error("[SMTP] 발송 실패: %s\n%s", e, traceback.format_exc())

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
