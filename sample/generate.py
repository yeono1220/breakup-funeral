"""샘플 데이터 생성기: 썸(3월) → 연애(4~7월) → 식음(7~8월) → 단절(8~9월) 시나리오 + 친구방 2개.
카톡 Windows PC 내보내기 포맷으로 sample/*.txt 생성. 결정적(seed 고정).

python sample/generate.py
"""
from __future__ import annotations

import random
from datetime import datetime, timedelta
from pathlib import Path

random.seed(7)
OUT = Path(__file__).parent
ME, A, B, C = "고연오", "김하늘", "박민수", "이서진"
SAVED = datetime(2026, 9, 17, 22, 40)
WD = "월화수목금토일"

# ---------------------------------------------------------------- phrase pools
ME_OPEN = ["뭐해", "밥 먹었어?", "오늘 뭐함", "자?", "야", "심심하다", "오늘 날씨 미쳤다", "과제 하기 싫다 ㅋㅋ", "지금 뭐하고 있어"]
A_OPEN = ["뭐해요?", "오늘 뭐했어?", "밥은?", "나 지금 카페 왔는데 사람 너무 많아", "헐 나 방금 웃긴 거 봄", "오늘 진짜 피곤하다"]
ME_MID = ["ㅋㅋㅋㅋ", "ㅋㅋ 뭐야", "아 진짜?", "ㅇㅇ", "나도", "헐", "그건 좀 ㅋㅋ", "오 좋다", "그래서?", "아 몰라 ㅋㅋ",
          "야 그거 봤어?", "나 배고파", "언제 볼래", "주말에 시간 돼?", "그거 재밌어?", "나 지금 도서관", "ㅋㅋㅋ 인정", "ㄱㄱ", "웅", "오케이"]
A_MID_WARM = ["ㅎㅎ 진짜?", "웅웅", "나도 그거 봤어!", "아 맞다 그거", "진짜 웃겨 ㅋㅋㅋ", "오늘 너 생각났어", "언제 시간 돼?", "주말에 볼래?",
              "나 이거 먹고 있어 사진", "헐 대박", "그러게~", "오 좋아 좋아", "밥 잘 챙겨 먹어", "너 진짜 웃긴 듯 ㅋㅋ", "궁금해 더 말해줘", "어디야?"]
A_MID_COLD = ["ㅇㅇ", "응", "그래", "ㅋㅋ", "나중에", "바빠", "몰라", "음", "그렇구나", "지금 좀 바쁨", "나중에 얘기하자", "응 알겠어", "ㅇㅋ"]
A_CLOSE = ["잘자~", "나 잘게", "굿나잇", "내일 봐", "응 잘자", "ㅂㅂ"]
ME_CLOSE = ["잘자", "굿나잇", "낼 봐", "ㅂㅂ", "응 잘자 ㅋㅋ"]
DATING_ME = ["굿모닝", "잘 잤어?", "보고싶다", "오늘 몇 시에 끝나", "저녁 뭐 먹을래", "데리러 갈까", "사랑해", "오늘 너무 좋았어", "집 도착", "잘자 사랑해"]
DATING_A = ["굿모닝 ☀️", "잘 잤어 ㅎㅎ", "나도 보고싶어", "6시!", "떡볶이", "응 와줘", "나도 사랑해", "나도 ㅎㅎ 오늘 최고였어", "도착했어~", "잘자 ❤️"]
FIGHT = [(ME, "어제 왜 연락 안 했어"), (A, "바빴어"), (ME, "하루 종일?"), (A, "응 과제 있었다고 했잖아"), (ME, "그래도 한 번은 할 수 있잖아"),
         (A, "지금 그거 때문에 화난 거야?"), (ME, "서운하다고"), (A, "미안 근데 나도 힘들어"), (ME, "알겠어"), (A, "…"), (ME, "미안 내가 예민했다"), (A, "응")]
B_ME = ["야 과제 했냐", "ㅋㅋㅋㅋ 뭐냐 그게", "오늘 학식 뭐임", "피시방 ㄱ?", "아 시험 망함", "ㅇㅇ", "ㄱㄱ", "낼 봄", "ㅋㅋ 인정", "몰라 그냥 하자"]
B_B = ["ㄴㄴ", "ㅋㅋㅋ", "돈까스", "ㄱ", "나도", "ㅇㅋ", "몇 시", "야 그 교수 미쳤냐", "과제 언제까지지", "ㅋㅋㅋㅋㅋ", "나 지금 감"]
C_ME = ["언니 뭐해", "ㅋㅋㅋ 진짜?", "그거 어디서 샀어", "나 요즘 너무 바쁘다", "다음 주에 밥 먹자", "ㅇㅇ 알겠어", "ㅎㅎ 고마워"]
C_C = ["일하지 ㅠ", "응 진짜야 ㅋㅋ", "올리브영!", "힘내 ㅠㅠ", "좋아 언제?", "오키", "밥 잘 챙겨 먹고", "연오야 잘 지내?"]


def kdate(d: datetime) -> str:
    return f"--------------- {d.year}년 {d.month}월 {d.day}일 {WD[d.weekday()]}요일 ---------------"


def ktime(d: datetime) -> str:
    ap = "오전" if d.hour < 12 else "오후"
    h = d.hour % 12 or 12
    return f"[{ap} {h}:{d.minute:02d}]"


def write_room(name: str, title: str, msgs: list[tuple[datetime, str, str]]):
    msgs.sort(key=lambda x: x[0])
    lines = [f"{title} 님과 카카오톡 대화", f"저장한 날짜 : {SAVED:%Y-%m-%d %H:%M:%S}", ""]
    cur = None
    for ts, who, text in msgs:
        if cur != ts.date():
            cur = ts.date(); lines.append(kdate(ts))
        lines.append(f"[{who}] {ktime(ts)} {text}")
    (OUT / f"{name}.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(msgs)


def jitter(minutes: float, spread: float = 0.6) -> float:
    return max(0.3, random.lognormvariate(0, spread) * minutes)


def session(day: datetime, starter: str, other: str, n: int, my_reply: float, their_reply: float,
            my_pool, their_pool, close_pool_me, close_pool_a, hour_range=(10, 24), late=False, opener=None) -> list:
    h = random.randint(*hour_range) % 24
    if late and random.random() < 0.5:
        h = random.choice([0, 1, 2])
    t = day.replace(hour=h, minute=random.randint(0, 59))
    if h < 4:
        t += timedelta(days=1)
    out, who = [], starter
    pool = {ME: my_pool, other: their_pool}
    first = opener if opener else random.choice(ME_OPEN if starter == ME else A_OPEN if other == A else pool[starter])
    out.append((t, who, first))
    for _ in range(n - 1):
        nxt = other if who == ME else ME
        t += timedelta(minutes=jitter(my_reply if nxt == ME else their_reply))
        # 연속 발화 20%
        if random.random() < 0.2:
            nxt = who
            t += timedelta(minutes=random.uniform(0.2, 1.5))
        who = nxt
        out.append((t, who, random.choice(pool[who])))
    # 종결
    if random.random() < 0.7:
        t += timedelta(minutes=jitter(my_reply))
        ender = random.choice([ME, other])
        out.append((t, ender, random.choice(close_pool_me if ender == ME else close_pool_a)))
    return out


def gen_A() -> list:
    msgs = []
    d0 = datetime(2026, 3, 1)
    for i in range(0, 200):
        day = d0 + timedelta(days=i)
        # ---- 썸 (3/1 ~ 4/12): 빈도 상승, 응답 빠름, 시작 균형
        if day < datetime(2026, 4, 13):
            k = i / 42
            n_sess = 1 if random.random() < 0.3 + k * 0.6 else (2 if random.random() < 0.4 else 1)
            if random.random() < 0.15 and i < 10:
                continue
            for _ in range(n_sess):
                starter = ME if random.random() < 0.52 else A
                msgs += session(day, starter, A, int(6 + k * 14 + random.randint(-2, 4)), 3, 8,
                                ME_MID, A_MID_WARM, ME_CLOSE, A_CLOSE, late=(k > 0.5))
            if day == datetime(2026, 3, 14):
                msgs.append((day.replace(hour=23, minute=41), A, "오늘 너무 재밌었어 ㅎㅎ 보고싶다"))
                msgs.append((day.replace(hour=23, minute=42), ME, "나도"))
                msgs.append((day.replace(hour=23, minute=42, second=30), ME, "ㅋㅋㅋㅋ 뭐야 갑자기"))
                msgs.append((day.replace(hour=23, minute=44), A, "그냥 ㅎㅎ 잘자"))
        # ---- 연애 (4/13 ~ 7/12): 고빈도, 인사 어휘
        elif day < datetime(2026, 7, 13):
            if day == datetime(2026, 4, 13):
                msgs += [(day.replace(hour=22, minute=10), ME, "우리 오늘부터 1일이다"), (day.replace(hour=22, minute=11), A, "ㅎㅎ 응 ❤️")]
            msgs.append((day.replace(hour=random.choice([7, 8, 9]), minute=random.randint(0, 59)), random.choice([ME, A]), random.choice(["굿모닝", "잘 잤어?", "굿모닝 ☀️", "일어났어?"])))
            for _ in range(random.choice([2, 2, 3])):
                starter = ME if random.random() < 0.5 else A
                msgs += session(day, starter, A, random.randint(8, 18), 2.5, 4, ME_MID + DATING_ME, A_MID_WARM + DATING_A, ME_CLOSE, A_CLOSE, hour_range=(11, 23))
            msgs.append((day.replace(hour=random.choice([23, 0]), minute=random.randint(0, 59)) + (timedelta(days=1) if random.random() < 0.3 else timedelta()), random.choice([ME, A]), random.choice(["잘자 사랑해", "잘자 ❤️", "굿나잇", "낼 봐 잘자"])))
        # ---- 식음 (7/13 ~ 8/23): 빈도 하락, A 응답 둔화, 내가 먼저 말 걺
        elif day < datetime(2026, 8, 24):
            k = (i - 134) / 42  # 0→1
            if day == datetime(2026, 7, 25):
                t = day.replace(hour=22, minute=3)
                for who, text in FIGHT:
                    t += timedelta(minutes=jitter(2 if who == ME else 25, 0.5)); msgs.append((t, who, text))
                continue
            if random.random() < 0.15 + k * 0.35:
                continue
            starter = ME if random.random() < 0.6 + k * 0.3 else A
            msgs += session(day, starter, A, max(3, int(12 - k * 9 + random.randint(-2, 2))), 2.5, 30 + k * 200,
                            ME_MID + ["보고싶다", "요즘 바빠?", "주말에 볼 수 있어?"], A_MID_WARM if random.random() > k else A_MID_COLD, ME_CLOSE, A_CLOSE, hour_range=(12, 23))
            if random.random() < 0.5 - k * 0.4:
                msgs.append((day.replace(hour=8, minute=random.randint(0, 59)), random.choice([ME, ME, A]), "굿모닝"))
        # ---- 단절 (8/24 ~): 7일 침묵 후 저빈도
        else:
            if day < datetime(2026, 9, 1):
                continue
            if random.random() < 0.7:
                continue
            msgs += session(day, ME, A, random.randint(2, 4), 3, 400, ["잘 지내?", "그때 얘기 좀 할 수 있을까", "응", "알겠어"], ["응", "지금은 좀", "나중에", "미안"], ["응"], ["응"], hour_range=(20, 23))
    # 마지막: A가 열린 메시지를 보냈고 내가 답 안 함 (답장 대기 데모용)
    msgs.append((datetime(2026, 9, 16, 21, 12), A, "우리 한 번 만나서 얘기할까?"))
    return msgs


def gen_B() -> list:
    msgs, d0 = [], datetime(2026, 3, 1)
    for i in range(200):
        day = d0 + timedelta(days=i)
        if random.random() < 0.45:
            continue
        msgs += session(day, random.choice([ME, B]), B, random.randint(3, 9), 45, 60, B_ME, B_B, ["ㅂㅂ", "ㅇㅋ"], ["ㅇㅋ", "ㄱ"], hour_range=(11, 23))
    return msgs


def gen_C() -> list:
    msgs, d0 = [], datetime(2026, 3, 1)
    for i in range(200):
        day = d0 + timedelta(days=i)
        if random.random() < 0.8:
            continue
        msgs += session(day, random.choice([ME, C, C]), C, random.randint(3, 7), 90, 40, C_ME, C_C, ["ㅎㅎ 응", "고마워"], ["응응", "잘 지내"], hour_range=(12, 22))
    msgs.append((datetime(2026, 9, 15, 19, 30), C, "연오야 다음 주 토요일 시간 돼? 밥 사줄게"))
    return msgs


if __name__ == "__main__":
    for f in OUT.glob("*.txt"):
        if f.stem in ("pc", "android", "ios"):
            continue
        f.unlink()
    n1 = write_room("김하늘", A, gen_A())
    n2 = write_room("박민수", B, gen_B())
    n3 = write_room("이서진", C, gen_C())
    print(f"김하늘 {n1} / 박민수 {n2} / 이서진 {n3} messages")
