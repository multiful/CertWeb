
### 백엔드 구조

```text
backend/
├── app/
│   ├── api/            # 라우터 (엔드포인트 정의)
│   │   ├── v1/         # API 버전 관리
│   │   │   ├── api.py  # 라우터 통합
│   │   │   └── endpoints/
│   │   │       ├── certs.py
│   │   │       └── users.py
│   ├── core/           # 설정 및 보안 (공통)
│   │   ├── config.py   # .env 관리
│   │   └── security.py # JWT, 인증 관련
│   ├── db/             # 데이터베이스 연결 관리
│   │   ├── base.py     # 모든 모델 Import (Alembic용)
│   │   └── session.py  # Engine 및 Session 생성
│   ├── models/         # SQLAlchemy 모델 (도메인별 분리)
│   │   ├── cert.py
│   │   └── user.py
│   ├── schemas/        # Pydantic 스키마 (Request/Response 모델)
│   │   ├── cert.py
│   │   └── user.py
│   ├── services/       # 비즈니스 로직 (CRUD 상위 계층)
│   │   └── cert_service.py # 단순 DB 작업을 넘어선 복합 로직
│   └── crud/           # 순수 DB 접근 로직
│       ├── crud_cert.py
│       └── crud_user.py
├── alembic/            # DB 마이그레이션 관리 (필수)
├── tests/              # Pytest 유닛 및 통합 테스트
├── main.py
└── .env.example
```
