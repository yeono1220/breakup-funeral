# HANDOFF — 이별 장례식 (breakup-funeral) 새 세션용 컨텍스트

> 새 대화 첫 메시지에 이 파일을 통째로 붙이거나 "docs/HANDOFF.md 읽고 시작해"라고 하면 됨. 2026-09-19 기준.

## 0. 한 줄
카톡 대화 txt를 올리면 관계의 **사망 진단서**를 발급하고 → 매장 → 진정성 진단서 / 애착유형별 저주 부적 → 공동묘지 → 현실 치료실(X 소환술·레전드 썰·사이렌)로 보내는 웹앱. BYPP 해커톤 출품. 1인 개발(고연오, 카톡 이름 `고연오`), Claude Code로 개발.

- 서비스: https://breakup-funeral.vercel.app
- 백엔드: https://breakup-funeral-api.onrender.com (`/health`, `/llm_check` 진단)
- GitHub: https://github.com/yeono1220/breakup-funeral (main, push = Vercel/Render 자동 배포)
- 로컬 경로: `C:\Users\user\kakao-coach` (홈 폴더 자체가 다른 git repo라 헷갈리지 말 것 — kakao-coach 안에서만 git)
- 명세: `docs/SPEC.md` · 제출서 초안: `docs/SUBMISSION.md` (Demo Market 피드백 칸 비어 있음)

## 1. 스택 / 파일 맵
```
backend/                FastAPI + SQLite, Python 3.12 (.venv), uvicorn
  main.py               라우트 전부 (upload, me/target/persona, relationship, compare, messages, chat(SSE), first_insight,
                        summon, eulogy, curse, legends, cemetery(폴백), health, llm_check)
  parser.py             카톡 txt 3종(PC/Android/iOS) 파싱, saved_at, media 플래그
  db.py                 SQLite (messages, settings), DATA_DIR env → 없으면 backend/data → /tmp
  relationship.py       build(): 온도·주간·사건·단계·대칭·편향·답장대기·신호·마지막 메시지 조립 / candidates / compare
  core/
    sessions.py         6시간 공백 세션, 1:1 방 추출(relationship_messages), other_messages
    temperature.py      온도 지수(R F I Q T E, 가중치 공개), weekly_series, updown_events(±10°, 주 20건 이상)
    stages.py           썸/연애/일상/식음/단절 규칙 감지 + smooth
    symmetry.py         대칭 바 5개, my_bias(baseline 대비), waiting_reply(열린 메시지만)
    signals.py          썸/이별 신호: baseline 모드(내 다른 방 대비) or relative 모드(둘 사이 비교, 합 100); retro()로 이별 렌즈 문구
    causes.py           사망 원인: 전성기 4주 vs 말기 4주 비교 6항목 + 침묵(사용자가 끝났다면 오늘 기준)
    textfeat.py         질문/종결형/인사/감정 정규식
    replies.py          답장 페어·중앙값
  coach.py              관계 코치(툴 유즈 11개, SYSTEM_RULES, 매 턴 관계 요약 카드 주입, [#msg_id] 영수증 규칙) — 프론트 UI는 현재 없음
  funeral.py            X 소환술(summon_system), 진정성 진단서(eulogy), 부적(curse: AMULETS + 맞춤 한 줄), 레전드 썰(legends_for: web_search 툴)
  cemetery.py           공동묘지 백엔드 폴백(SQLite). 실제 운영은 Supabase
  stats.py              구버전 통계(코치 툴 일부가 사용)
frontend/               Vite + React + TS. envDir='..' (루트 .env 공유, VITE_* 만 노출)
  src/App.tsx           페이지 상태 머신 upload→analyze→diagnosis→tribute→cemetery / tools, persona/amulet 보관
  src/pages/            Upload(드롭·나/상대·MBTI·애착·이별방식·상황·시작/종료일·영정 그림판), Analyze, Diagnosis, Tribute(매장·부적·BurnRitual), Cemetery(Supabase 어댑터), Tools(소환술·레전드·사이렌)
  src/components/       Char(마스코트=나, 테루테루보즈), Portrait(X 얼굴), DrawPad, GrassField, BurnRitual, Icons(14종), ui(Modal/Toast/fmt/useCountUp/smoothPath)
  src/cemeteryStore.ts  Supabase 있으면 직접, 없으면 백엔드 /cemetery
  src/api.ts            BASE = VITE_API_BASE || '/api'(Vite 프록시→8000), 타입 전부
  src/index.css         디자인 시스템 전체(토큰·유틸·컴포넌트) ~600줄
supabase/schema.sql     tombs/flowers/guestbook + RLS + RPC(flower, visitors, my_flowers) + 시드 (이미 적용됨)
sample/generate.py      합성 데이터(썸→연애→식음→단절) 생성 → sample/*.txt (샘플로 보기용)
tests/run_core.py       core 지표 눈검사 스크립트 (유닛테스트 아님) / tests/check_key.py 키 점검
render.yaml, frontend/vercel.json, run.bat, README.md
```

## 2. 실행 / 환경
- 로컬: `run.bat` (백엔드 8000 + Vite 5173 + 브라우저). 수동: `.venv\Scripts\python -m uvicorn main:app --app-dir backend --port 8000` (**--reload는 Windows에서 꼬임, 코드 바꾸면 수동 재시작**), `cd frontend && npm run dev`.
- 루트 `.env`(gitignore): `ANTHROPIC_API_KEY`(sk-ant-api03…, 워크스페이스 미지정 키라 `ANTHROPIC_WORKSPACE_ID`=wrkspc_… 필요), `CLAUDE_MODEL=claude-opus-5`, `VITE_API_BASE`(로컬은 비움), `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`.
- Render: Blueprint(render.yaml), rootDir backend, free 플랜(15분 유휴 시 슬립 → 첫 요청 50초, 재시작 시 SQLite 초기화). 환경변수 대시보드에 ANTHROPIC 2개 입력됨(`/llm_check` call: ok 확인). 안 잠들게 하려면 cron-job.org로 `/health` 10분 핑(사용자가 설정 중이었음).
- Vercel: Root Directory `frontend`, env 3개 반영 확인됨.
- Supabase: 프로젝트 `aphzbhaqocvlrujftxij`, schema.sql 적용됨. 테스트 흔적: tombs id 8("rest test tomb"), guestbook id 1 — 대시보드에서 삭제 필요(anon 키로는 삭제 불가).
- 모델 호출 규칙: Opus 5는 adaptive thinking 기본 → **max_tokens 넉넉히(4000+)** 안 그러면 텍스트가 비어 폴백됨. 용도별 `output_config.effort` (소환술 medium/부적 low/진단서 medium/코치 high/레전드 medium). 텍스트 블록만 추출(`b.type == "text"`).

## 3. 제품 원칙 (SPEC 1장)
1. LLM은 세지 않는다 — 숫자·시간·비율은 코드. 2. 영수증 — 사실엔 msg_id. 3. 나 중심 — 상대 마음 단정 금지, "대화의 모양"만. 4. 투명한 지수. 5. 정직한 데이터 흐름("전부 로컬" 금지). 6. 엔진 하나, 렌즈 셋(썸/연애중/이별). + 사용자가 알려준 이별 컨텍스트(ending/context/started_at/ended_at)가 데이터 판정을 덮어씀.

## 4. 디자인 시스템 (마지막 패스 c8e4b91)
- 팔레트: 한지 아이보리 `--bg #F6F1EA`, 패널 #FFF/#F4EEE5, 잉크 #2B2622, 로즈 #D96A5E/#B9463B, 국화 #9C7C1E, ok #4F8A5E.
- 모션 토큰 `--ease-out/--ease-spring/--ease-in`, `--dur-1~4`; 등장 `.reveal` + `--i` stagger, `.fade-in`, press scale(.98); `prefers-reduced-motion` 블록 있음; transform만 애니(관 뚜껑 translateY, 흙 scaleY, 막대 scaleX).
- 모서리 6/12/20(+999). 그라데이션·그림자는 부적·불·잔디·모달·영정만. 카드는 `.paper` 하단선 + body 노이즈.
- 이모지 허용: 💐(헌화) 🔮(부적) 🚨(사이렌) 꽃 선택 4종, 의식 불꽃. 나머지는 `Icons.tsx`.
- 손글씨(Nanum Pen)는 `故 이름`·비문·부적만. Black Han Sans는 사이렌·명언만. UI 카피 반말 통일(진정성 진단서만 편지체 존댓말).
- 마스코트 = 나. X = 사용자가 그린/올린 초상화(없으면 빈 종이+?).

## 5. 프롬프트 위치 (고도화 대상)
| 기능 | 파일 | 현재 방식 |
|---|---|---|
| X 소환술 | `funeral.py: summon_system()` | 상대 말투 통계 + 최근 실제 메시지 25개 + "내 말→상대 반응" 페어 15개, 규칙 5개, 후처리 `_clean_reply`(마지막 한 줄만, 메타 단어 필터). effort medium |
| 진정성 진단서 | `funeral.py: eulogy()` | `_facts()`(코드 계산 사실 목록) + 이별 컨텍스트 + 규칙(5~6문장, 숫자 2개 이상, 마음 단정 금지, 놓아주기로 끝). 폴백 `template_eulogy` |
| 저주 부적 | `funeral.py: curse()` + `AMULETS` | 애착유형→사자성어 고정(밈 1순위) + LLM 한 줄(20자, 패턴 하나 필수, 예시 1개) |
| 레전드 썰 | `funeral.py: legends_for()` | web_search_20260209 (allowed_domains 커뮤니티 14개, KR), JSON 강제, pause_turn 이어받기, 사용된 쿼리 수집·표시, 상대별 캐시(`settings legends:<target>`) |
| 관계 코치 | `coach.py` | SYSTEM_RULES 7개 + 렌즈 톤 + 툴 11개 + 관계 요약 카드 + 이별 컨텍스트 주입. **프론트 UI 없음(장례식 개편 때 제거됨)**, `/chat` SSE는 살아 있음 |
| 답장 초안(F9.1) | — | **미구현** (`/draft_reply` 501). SPEC의 "말투 재현 규격" 참고 |

## 6. 알려진 이슈 / 미완 (중요도 순)
1. **멀티유저 안전 아님** — 백엔드 상태(me/target/persona/메시지)가 서버 전역 SQLite `settings` 하나. 공개 URL에 동시 접속자가 2명이면 서로 덮어씀. 데모/지인 테스트는 "한 번에 한 명"이거나 세션 키(쿠키/헤더)로 격리 필요. 최우선.
2. **보안 무방비** — `DELETE /data` 누구나, CORS `*`, 인증·rate limit 없음 → 공개 URL에서 LLM 키 소모 가능.
3. Render free 슬립/데이터 초기화(위 참조).
4. 코치 채팅 UI 부재(백엔드만), 답장 초안 미구현, 부적 PNG 저장 미구현(토스트만), OCR 버튼은 숨김, 카톡 PC 자동 내보내기 커넥터 PoC만(`poc/`), X 장례식(F13.2) P2 리마인드, 피드백 루프(F12: 앱 내 👍👎) 미구현.
5. 프라이버시 고지 UI 없음(상대 원문 일부가 LLM으로 전송됨을 화면에 안 알림). 업로드 삭제 버튼 없음(API만).
6. 테스트: 유닛테스트 0. 통계 임계값(온도 가중치, 단계 규칙, 사건 20건, 신호 55/42·58)은 합성 샘플 + 사용자 본인 데이터 1건으로만 튜닝.
7. 리허설(F9.2) 미구현 — 소환술이 그 역할을 대신.

## 7. 작업 시 함정 (이 환경 특유)
- Bash heredoc에 한글/백슬래시 들어간 파이썬을 넣으면 깨짐 → 패치는 `Write`로 .py 파일 만들고 실행.
- 콘솔 cp949 → `PYTHONIOENCODING=utf-8`; curl -d에 한글 JSON은 파일로.
- uvicorn `--reload` 금지(고아 프로세스가 8000 점유 → PowerShell로 python 프로세스 kill).
- Vite는 루트 `.env` 읽음(envDir '..'); env 바꾸면 dev 서버 재시작.
- Claude 브라우저 패널은 GitHub 로그인 팝업이 열려 있으면 이동 불가(사용자가 닫아야 함).
- 사용자 실데이터: `backend/data/uploads/`(gitignore). 내용은 열어보지 말고 수치만.

## 8. 냉정한 평가 — 부족한 것
- **깊이보다 폭**: 기능 8개 중 진짜 완성도는 부검·부적·공동묘지 3개. 나머지는 "돌아가는 목업"에 가깝다(레전드 폴백 문구, PNG 저장 없음, 소환술 대화가 한 줄 답만).
- **프롬프트는 규칙 나열형**: 예시(few-shot)는 소환술만 있고, 진단서·부적·레전드는 "하지 마" 목록으로 통제. 출력 품질 측정 도구가 없어서 좋아졌는지 나빠졌는지 모른다. 소환술의 추론 누출은 원인(effort/포맷)을 안 잡고 후처리로 덮었다.
- **말투 재현 검증 없음**: SPEC의 "블라인드 테스트(본인이 못 구분하면 성공)"를 한 번도 안 했다.
- **통계의 근거 부족**: 온도 가중치·임계값은 감으로 정했고 검증 데이터가 1건. "코드가 계산한다"는 건 재현 가능하다는 뜻이지 맞다는 뜻이 아니다.
- **심사 기준 대비**: "피드백 받고 개선" 증거가 앱 안에 없다(F12 미구현). 개발 중 셀프 피드백 8건은 커밋에 남았지만 외부 사용자 피드백은 0.
- **엔지니어링 부채**: main.py 350줄에 라우트 전부, 문자열 패치 누적으로 코드 결이 고르지 않음, CSS 단일 파일, 모바일/접근성 미검증.

## 9. 프롬프트 고도화 백로그 (다음 세션 제안 순서)
1. **평가셋 먼저**: 사용자 본인 데이터로 소환술 20턴·진단서 5개·부적 10개를 뽑아 `docs/evals/`에 저장하고 좋/나쁨 라벨. 이게 없으면 나머지는 감.
2. 소환술: (a) 유사 상황 검색 기반 few-shot(지금은 최근 25개 고정 → 사용자 입력과 비슷한 과거 내 메시지 뒤의 상대 답을 골라 넣기), (b) 길이·ㅋㅋ·마침표 분포에서 **샘플링**해 답 길이를 지정, (c) 출력 후 스타일 검증(길이/ㅋㅋ/존댓말) 불일치 시 1회 재생성, (d) 여러 버블로 쪼개기.
3. 진정성 진단서: 구조 템플릿(관찰→인정→놓아주기) + 인용 사실 3개 강제 + 금지어 목록 + 길이 상한. 폴백 템플릿과 A/B.
4. 부적 한 줄: 예시 5개 이상 + "유치함 점수" 자기검열 + 상대 top_words에서 반드시 1개 사용.
5. 레전드 썰: 쿼리 생성 단계와 검색 단계 분리(쿼리 3개를 먼저 JSON으로 → 각각 검색), 유사도 근거를 데이터 필드명으로 명시.
6. 코치 채팅 UI 복구(현실 치료실에 "코치에게 묻기" 탭) — 백엔드 툴 유즈는 완성돼 있음.
7. 답장 초안(F9.1) — SPEC "말투 재현 규격" 그대로 구현.
