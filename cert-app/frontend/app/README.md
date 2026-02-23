# React + TypeScript + Vite

This template provides a minimal setup to get React working in Vite with HMR and some ESLint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Babel](https://babeljs.io/) (or [oxc](https://oxc.rs) when used in [rolldown-vite](https://vite.dev/guide/rolldown)) for Fast Refresh
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/) for Fast Refresh

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the ESLint configuration

If you are developing a production application, we recommend updating the configuration to enable type-aware lint rules:

```js
export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      // Other configs...

      // Remove tseslint.configs.recommended and replace with this
      tseslint.configs.recommendedTypeChecked,
      // Alternatively, use this for stricter rules
      tseslint.configs.strictTypeChecked,
      // Optionally, add this for stylistic rules
      tseslint.configs.stylisticTypeChecked,

      // Other configs...
    ],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
      // other options...
    },
  },
])
```

You can also install [eslint-plugin-react-x](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-x) and [eslint-plugin-react-dom](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-dom) for React-specific lint rules:

```js
// eslint.config.js
import reactX from 'eslint-plugin-react-x'
import reactDom from 'eslint-plugin-react-dom'

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      // Other configs...
      // Enable lint rules for React
      reactX.configs['recommended-typescript'],
      // Enable lint rules for React DOM
      reactDom.configs.recommended,
    ],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
      // other options...
    },
  },
])
```

# 🎨 CertFinder Frontend
### React + TypeScript 기반 고성능 자격증 분석 플랫폼 UI

---

## 🏗 프로젝트 구조 (Project Structure)

```text
frontend/
├── src/
│   ├── components/
│   │   ├── layout/     # Header(UserMenu), Layout, Sidebar
│   │   ├── common/     # CertLogo 등 공통 UI 요소
│   │   └── ui/         # shadcn/ui 기반 원자적 컴포넌트
│   ├── pages/          # 도메인별 메인 페이지 (Home, Cert, Job, MyPage 등)
│   ├── hooks/          # 인증(useAuth), 데이터 Fetching(useCerts) 커스텀 훅
│   ├── lib/            # 코어 라이브러리 설정 (API, Supabase, Router)
│   ├── types/          # 전역 TypeScript 인터페이스 및 타입 정의
│   ├── App.tsx         # 메인 어플리케이션 엔트리
│   └── index.css       # 글로벌 스타일 및 가변 디자인 토큰
├── public/             # favicon, robots.txt 등 정적 자산
├── tailwind.config.js  # 테마 및 다크모드 설정
└── vite.config.ts      # 빌드 최적화 설정
```

---

## 💎 주요 사용자 경험 (UX) 특장점

1.  **Glassmorphism UI**: 다크 모드 기반의 세련된 디자인과 부드러운 애니메이션(Framer Motion/Tailwind)을 적용했습니다.
2.  **Custom Router Path**: Simple Client-side Routing을 구현하여 페이지 전환 시 압도적인 속도를 제공합니다.
3.  **Real-time Feedback**: Sonner를 활용한 즉각적인 토스트 알림으로 사용자 상호작용을 강화했습니다.
4.  **Responsive Layout**: 모바일-퍼스트 전략으로 다양한 기기에서 최적화된 화면을 제공합니다.

---

## 🛠 실행 방법 (Installation)

1.  의존성 설치: `npm install`
2.  환경 변수 설정: `.env` 파일 작성 (VITE_API_BASE_URL, VITE_SUPABASE_URL 등)
3.  개발 서버 실행: `npm run dev`
