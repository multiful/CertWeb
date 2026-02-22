import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config import get_settings

class EmailService:
    @staticmethod
    def send_update_report(report_data: List[Dict]):
        """
        Sends an email report of detected law changes.
        """
        settings = get_settings()
        smtp_host = settings.SMTP_HOST
        smtp_port = settings.SMTP_PORT
        email_user = settings.EMAIL_USER
        email_password = settings.EMAIL_PASSWORD
        
        if not email_user or not email_password:
            print("Email credentials not configured (.env)")
            return False

        message = MIMEMultipart()
        message["From"] = email_user
        message["To"] = email_user  # Sending to admin
        message["Subject"] = "자격증 플랫폼: 법령 개정 및 데이터 업데이트 보고서"

        # Generate HTML content
        html_content = f"""
        <html>
            <body>
                <h2>국가기술자격법령 개정 알림</h2>
                <p>시스템에 의해 감지된 최신 변경 사항입니다. 검토 후 최종 승인이 필요합니다.</p>
                <table border="1" style="border-collapse: collapse; width: 100%;">
                    <thead>
                        <tr style="background-color: #f2f2f2;">
                            <th>종목명</th>
                            <th>변경구분</th>
                            <th>변경 내용</th>
                            <th>적용 시점</th>
                        </tr>
                    </thead>
                    <tbody>
        """
        
        for item in report_data:
            html_content += f"""
                        <tr>
                            <td>{item.get('target_cert')}</td>
                            <td>{item.get('action')}</td>
                            <td>{item.get('change_info')}</td>
                            <td>{item.get('effective_date')}</td>
                        </tr>
            """
            
        html_content += """
                    </tbody>
                </table>
                <p>본 메일은 시스템에 의해 자동 발송되었습니다.</p>
            </body>
        </html>
        """
        
        message.attach(MIMEText(html_content, "html"))

        try:
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                server.login(email_user, email_password)
                server.send_message(message)
            return True
        except Exception as e:
            print(f"Failed to send email: {e}")
            return False

email_service = EmailService()
