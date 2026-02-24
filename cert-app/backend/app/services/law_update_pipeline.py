import os
from typing import List, Dict
import json
from app.utils.ai import client as openai_client
from app.services.email_service import email_service
from app.services.vector_service import vector_service
from sqlalchemy.orm import Session

# Note: In a production environment, you would use PyPDF2 or Unstructured
# For this script, we assume the content is extracted or provided via string if file is not readable
try:
    import PyPDF2
except ImportError:
    PyPDF2 = None


class LawUpdatePipeline:
    """법령/자격증 업데이트 파이프라인. OpenAI 클라이언트는 app.utils.ai 싱글톤 사용."""

    def __init__(self):
        self.openai_client = openai_client

    def extract_from_pdf(self, pdf_path: str) -> str:
        """Extract text from PDF."""
        if not os.path.exists(pdf_path):
            return ""
        
        text = ""
        if PyPDF2:
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                for page in reader.pages:
                    text += page.extract_text()
        else:
            # Fallback or error
            print("PyPDF2 not installed. Cannot parse PDF.")
        return text

    def analyze_changes_with_llm(self, text: str) -> List[Dict]:
        """Use LLM to identify specific certification changes."""
        prompt = f"""
        당신은 국가기술자격법 전문가입니다. 아래의 법령 개정안 텍스트를 분석하여 자격증 변경 사항을 추출하세요.
        추출할 정보:
        1. action: [신설, 통합, 폐지, 명칭변경, 과목개편] 중 하나
        2. target_cert: 자격증 명칭
        3. change_info: 구체적인 변경 내용
        4. effective_date: 적용 시점 (YYYY-MM-DD 형식으로 추측)

        JSON 리스트 형식으로만 답변하세요.
        내용:
        {text[:4000]} # Limit to first 4k chars for prompt safety
        """
        
        response = self.openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        # Expecting {"changes": [...]}
        return result.get("changes", [])

    def process_updates(self, db: Session, pdf_path: str = None):
        """Main pipeline execution."""
        print("Starting Law Update Pipeline...")
        
        # 1. Get raw text
        raw_text = ""
        if pdf_path:
            raw_text = self.extract_from_pdf(pdf_path)
        
        if not raw_text:
            print("No text found to analyze.")
            return

        # 2. Analyze with LLM
        changes = self.analyze_changes_with_llm(raw_text)
        print(f"Detected {len(changes)} changes.")

        # 3. Send Report to Admin
        email_sent = email_service.send_update_report(changes)
        if email_sent:
            print("Update report sent to admin.")

        # 4. Upsert to Vector DB for RAG
        for change in changes:
            vector_service.upsert_vector_data(
                db,
                qual_id=None, # In real logic, match name to ID first
                name=change.get('target_cert', 'Unknown'),
                content=json.dumps(change, ensure_ascii=False),
                metadata=change
            )
        
        print("Pipeline finished.")

law_update_pipeline = LawUpdatePipeline()
