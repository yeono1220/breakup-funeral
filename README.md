# 🪦 이별 장례식 — AI 관계 추모 센터

카톡 대화를 올리면 관계의 **사망 진단서**(마지막 말·사망 사유·사망 원인 %·애정도 낙하·핵심 사건)를 발급하고, 매장 → 헌화 → 진정성 진단서 / 애착유형별 저주 부적 → 공동묘지 → 현실 치료실(X 소환술·레전드 썰·선톡 방지 사이렌)로 보내드립니다.
숫자는 전부 코드가 세고 LLM은 조회·해석만 합니다. 모든 사실엔 원문 영수증이 붙습니다.

## 로컬 실행
```bat
run.bat
```
`.env`에 `ANTHROPIC_API_KEY`(필요 시 `ANTHROPIC_WORKSPACE_ID`) — 없으면 LLM 기능만 템플릿으로 폴백.

## 배포 (푸시 = 자동 배포)
- **프론트: Vercel** — Import Git Repository → Root Directory `frontend` → Framework Vite → Environment Variable `VITE_API_BASE=https://<render-service>.onrender.com`
- **백엔드: Render** — New → Blueprint → 이 repo 선택 (`render.yaml`) → `ANTHROPIC_API_KEY`, `ANTHROPIC_WORKSPACE_ID` 입력
- free 플랜은 15분 유휴 시 잠들고 재시작 시 데이터가 초기화됩니다. 영구 저장은 `render.yaml`의 disk 주석 해제(유료).

## 구조
```
backend/   FastAPI · SQLite · core/(온도·업다운·단계·대칭·신호·사망원인) · coach.py · funeral.py · cemetery.py
frontend/  Vite + React (Upload → Analyze → Diagnosis → Tribute → Cemetery / Tools)
sample/    합성 데이터 생성기 (썸→연애→식음→단절)
docs/SPEC.md  기능명세
```
