"""데모용 카톡 샘플 생성기 (결정적, seed 고정).  python sample/generate.py

김하늘.txt — 6개월 연애의 시작부터 끝까지, 읽어도 말이 되는 대본 기반:
  3/1~3/22 썸 → 3/23 고백 → 4~5월 허니문 → 6/12 첫 싸움·6/14 화해 → 7월 바빠지며 식음 시작
  → 7/20 두 번째 싸움·7/22 미지근한 화해 → 8월 단답·약속 취소·8/23 세 번째 싸움 → 9/2 "시간 갖자"
  → 9/14 정리 → 9/16 상대가 열린 메시지, 내가 답 안 함.
답장 속도·선톡 비율·하루 세션 수는 날짜에 따라 매끄럽게 식는다 (코드가 계산하는 지표가 그걸 잡아내야 하니까).
장면(SCENES)은 시간대가 있고 전체 기간에 한 번만 쓰인다. 분량은 슬롯 채우기 템플릿(TEMPLATES)이 맡는다.
박민수.txt / 이서진.txt — 친구방 (내 평소 답장 속도 baseline용).
"""
from __future__ import annotations

import random
from datetime import datetime, timedelta
from pathlib import Path

random.seed(2026)
OUT = Path(__file__).parent
ME, A, B, C = "고연오", "김하늘", "박민수", "이서진"
SAVED = datetime(2026, 9, 17, 22, 40)
WD = "월화수목금토일"
SLOT_HOURS = {"morning": (7, 9), "day": (11, 14), "afternoon": (15, 18), "evening": (19, 22), "night": (23, 25)}


# ================================================================ 날짜별 온도 파라미터
def lerp(a, b, t):
    return a + (b - a) * max(0.0, min(1.0, t))


def phase(day: datetime) -> dict:
    """하루의 관계 상태. warm: 0(차가움)~1(뜨거움) — 템플릿의 상대 반응을 고른다."""
    d = day.date()
    if d < datetime(2026, 3, 23).date():
        t = (d - datetime(2026, 3, 1).date()).days / 22
        return dict(sessions=lerp(0.9, 2.2, t), a_reply=lerp(9, 3, t), m_reply=lerp(6, 3, t), a_start=0.5, bank="some", warm=lerp(0.7, 0.9, t), greet=0.0)
    if d < datetime(2026, 6, 1).date():
        return dict(sessions=3.6, a_reply=2, m_reply=2, a_start=0.5, bank="honey", warm=1.0, greet=1.0)
    if d < datetime(2026, 7, 1).date():
        return dict(sessions=3.2, a_reply=3, m_reply=2.5, a_start=0.45, bank="honey", warm=0.9, greet=0.9)
    if d < datetime(2026, 8, 1).date():
        t = (d - datetime(2026, 7, 1).date()).days / 30
        return dict(sessions=lerp(2.2, 1.3, t), a_reply=lerp(5, 28, t), m_reply=2.5, a_start=lerp(0.4, 0.28, t), bank="cooling", warm=lerp(0.7, 0.35, t), greet=lerp(0.8, 0.3, t))
    if d < datetime(2026, 9, 1).date():
        t = (d - datetime(2026, 8, 1).date()).days / 30
        return dict(sessions=lerp(1.2, 0.55, t), a_reply=lerp(35, 190, t), m_reply=3, a_start=lerp(0.25, 0.12, t), bank="cold", warm=lerp(0.3, 0.1, t), greet=lerp(0.25, 0.05, t))
    return dict(sessions=0.35, a_reply=320, m_reply=6, a_start=0.1, bank="end", warm=0.05, greet=0.0)


# ================================================================ 장면 (한 번만 쓰임). (은행들, 시간대, 대사)
S = []
def scene(banks, slot, *lines):
    S.append({"banks": set(banks.split()), "slot": slot, "lines": [(l[0], l[2:]) for l in lines]})

# ---- 썸
scene("some", "day", "M:어제 잘 들어갔어?", "A:응! 너는?", "M:나도 방금 ㅋㅋ 버스 놓쳐서 걸어옴", "A:헐 거기서 집까지??", "M:30분 걸리더라", "A:미쳤다 ㅋㅋㅋ 다음엔 내가 택시 태워줄게", "M:오 약속", "A:ㅋㅋㅋ 알겠어")
scene("some", "afternoon", "A:오늘 동아리 회의 나와?", "M:응 7시 맞지", "A:ㅇㅇ 나 먼저 가서 자리 잡아놓을게", "M:오 고마워 나 5분 늦을 듯", "A:괜찮아 천천히 와", "M:커피 사갈까", "A:헐 아아 하나만.. 진짜?", "M:ㅇㅇ ㅋㅋ")
scene("some", "evening", "M:너 어제 그 영화 봤다며", "A:봤지 ㅋㅋ 근데 나 중간에 졸았어", "M:그거 재밌다던데", "A:앞부분이 너무 느려서.. 뒤는 괜찮았어", "M:같이 보러 갈 걸 그랬네", "A:다음 거 같이 보자 그럼", "M:ㅇㅋ 뭐 개봉하는지 찾아볼게", "A:ㅎㅎ 응")
scene("some", "evening", "M:야 너 MBTI 뭐야", "A:갑자기? ㅋㅋ ENFP", "M:아 그럴 것 같았어", "A:뭐야 그게 ㅋㅋㅋ 너는", "M:INTJ", "A:헐 진짜 정반대네", "M:그래서 잘 맞는대", "A:ㅎㅎ 누가 그래", "M:인터넷이")
scene("some", "afternoon", "A:오늘 뭐해?", "M:집에서 뒹굴 중", "A:나도 ㅋㅋ 심심하다", "M:나올래?", "A:지금? 어디로", "M:학교 앞 그 카페", "A:ㅋㅋ 좋아 30분 뒤", "M:ㅇㅋ 자리 잡아놓을게")
scene("some", "night", "M:오늘 고마웠어 ㅋㅋ", "A:뭐가~", "M:그냥 다", "A:ㅋㅋㅋ 뭐야 나도 재밌었어", "M:다음엔 내가 살게", "A:그럼 비싼 거 먹어야지", "M:적당히 ㅋㅋ", "A:ㅎㅎ 잘자", "M:잘자")
scene("some", "evening", "A:너 혹시 매운 거 잘 먹어?", "M:보통? 왜", "A:학교 앞에 마라탕 새로 생겼대", "M:오 가보자", "A:내일 어때", "M:내일 수업 4시 끝", "A:그럼 5시!", "M:ㅇㅋ")
scene("some", "night", "M:자?", "A:아니 아직 ㅋㅋ", "M:뭐해", "A:그냥 유튜브", "M:나도", "A:뭐 봐", "M:먹방", "A:이 시간에?? 배고파지겠다", "M:이미 배고픔", "A:ㅋㅋㅋㅋ 참아")
scene("some", "evening", "A:오늘 사진 보내줘 아까 찍은 거", "M:사진", "M:사진", "A:헐 잘 나왔다", "M:네가 잘 나온 거지", "A:ㅎㅎ 뭐래", "A:나도 보내줄게", "A:사진", "M:오 이거 프사 해도 됨?", "A:ㅋㅋㅋ 마음대로")
scene("some", "night", "A:아직 안 자?", "M:응 잠이 안 와", "A:나도", "M:왜", "A:그냥.. 오늘 재밌어서 그런가", "M:나도 그래", "A:ㅎㅎ", "M:내일 또 봐", "A:응 잘자")
scene("some", "night", "M:오늘 너랑 얘기하니까 시간 빨리 감", "A:나도 그랬어", "M:ㅋㅋ", "A:이제 자야지 내일 1교시", "M:헉 미안", "A:아냐 좋았어", "M:잘자", "A:너도")
scene("some", "day", "A:너 오늘 학교 와?", "M:응 2시 수업", "A:나 도서관인데 잠깐 볼래", "M:오 좋아 1시 반?", "A:응 3층 창가", "M:ㅇㅋ 간다")
scene("some", "afternoon", "M:너 커피 뭐 마셔", "A:아아! 왜", "M:그냥 궁금해서", "A:ㅋㅋㅋ 뭐야 너는", "M:라떼", "A:오 의외", "M:왜 ㅋㅋ", "A:아아 마실 것 같이 생겨서", "M:그게 뭔데 ㅋㅋㅋ")
# ---- 허니문
scene("honey", "morning", "M:굿모닝", "A:굿모닝 ☀️ 잘 잤어?", "M:응 꿈에 네가 나옴", "A:헐 뭐하고 있었는데", "M:기억 안 나 ㅋㅋ", "A:ㅋㅋㅋㅋ 그럼 왜 말해", "M:그냥 좋아서")
scene("honey", "afternoon", "A:오늘 저녁 뭐 먹을래", "M:너 먹고 싶은 거", "A:그 말이 제일 어려워 ㅋㅋ", "M:그럼 파스타", "A:오 좋아 저번에 거기?", "M:응 7시에 데리러 갈게", "A:응응 ❤️")
scene("honey", "night", "M:집 도착", "A:오늘 너무 좋았어", "M:나도 ㅋㅋ 사진 보내줘", "A:사진", "A:사진", "M:이거 배경화면 한다", "A:ㅎㅎ 나도 할래", "M:잘자 사랑해", "A:나도 사랑해 잘자 ❤️")
scene("honey", "day", "A:나 지금 수업인데 너무 졸려", "M:ㅋㅋ 몰래 자", "A:앞자리라 안 돼", "M:끝나고 커피 사줄게", "A:헐 고마워", "A:이모티콘", "M:3시 정문?", "A:응!")
scene("honey", "evening", "M:보고싶다", "A:어제 봤잖아 ㅋㅋ", "M:그래도", "A:ㅎㅎ 나도 보고싶어", "M:내일 뭐해", "A:너 만나지", "M:ㅋㅋ 정답")
scene("honey", "day", "A:우리 주말에 바다 갈래?", "M:오 갑자기?", "A:그냥 날씨 좋아서", "M:가자 토요일 첫차", "A:첫차는 좀.. 9시?", "M:ㅇㅋ 9시 ㅋㅋ", "A:김밥 싸갈게", "M:진짜? 너무 좋다")
scene("honey", "afternoon", "M:오늘 몇 시에 끝나", "A:6시", "M:데리러 갈까", "A:응 와줘 ㅎㅎ", "M:정문에서 봐", "A:응 사랑해", "M:나도")
scene("honey", "afternoon", "A:나 오늘 발표 망함 ㅠㅠ", "M:왜 무슨 일이야", "A:중간에 말이 막혔어", "M:그래도 끝까지 했잖아", "A:응.. 근데 창피해", "M:내가 보기엔 잘했을 거야. 저녁에 맛있는 거 먹자", "A:ㅠㅠ 고마워", "M:7시에 갈게")
scene("honey", "evening", "M:너 어제 그거 뭐였지 그 노래", "A:카페에서 나온 거?", "M:응", "A:찾아서 보내줄게", "A:https://youtu.be/dQw4w9WgXcQ", "M:오 이거다", "A:ㅎㅎ 좋지", "M:너 생각나는 노래")
scene("honey", "night", "A:엄마가 너 언제 데려오냐고 물어봄 ㅋㅋ", "M:헐 벌써?", "A:ㅋㅋㅋ 농담 반", "M:긴장된다", "A:우리 엄마 착해", "M:그래도 ㅋㅋ", "A:천천히 하자")
scene("honey", "evening", "A:이모티콘", "M:뭐야 ㅋㅋ", "A:그냥 귀여워서", "M:네가 더 귀여움", "A:ㅎㅎ 오글", "M:사실인데")
scene("honey", "night", "M:오늘 네 친구들 재밌더라", "A:ㅋㅋ 다들 너 좋대", "M:진짜?", "A:응 특히 지수가 ㅋㅋ", "M:다행이다 긴장했어", "A:티 났어 ㅋㅋㅋ", "M:ㅠㅠ", "A:귀여웠어 잘자")
scene("honey", "day", "M:너 지금 어디야", "A:도서관 왜", "M:나 근처인데 뭐 사다줄까", "A:헐 샌드위치.. 되나", "M:ㅇㅋ 10분", "A:사랑해 ㅠㅠ", "M:ㅋㅋ 이럴 때만")
scene("honey", "evening", "A:오늘 비 오는데 우산 있어?", "M:없음 ㅋㅋ", "A:내가 데리러 갈게 어디야", "M:진짜? 도서관 앞", "A:15분만 기다려", "M:너 최고")
scene("honey", "afternoon", "M:우리 다음 주 기념일인데 뭐 하고 싶어", "A:음 한강?", "M:오 좋다 자전거 타자", "A:치킨도!", "M:당연하지", "A:기대돼 ㅎㅎ")
scene("honey", "night", "A:오늘 너무 피곤해서 먼저 잘게", "M:응 푹 자", "A:내일 아침에 톡할게", "M:사랑해", "A:나도 ❤️")
scene("honey", "day", "A:나 머리 잘랐어", "A:사진", "M:헐 잘 어울려", "A:진짜? 너무 짧은가 했는데", "M:아니 딱 좋아", "A:ㅎㅎ 다행")
scene("honey", "evening", "M:오늘 알바 사장님이 또 늦게 보내줌", "A:ㅠㅠ 고생했어", "M:배고파", "A:나 지금 너희 집 근처인데 뭐 사갈까", "M:진짜?? 김밥", "A:ㅋㅋ 알겠어 10분")
scene("honey", "night", "M:자기 전에 목소리 듣고 싶다", "A:전화해 ㅎㅎ", "M:지금 건다", "A:응")
# ---- 6월 안정기 (honey 은행 공유) + 식음
scene("cooling", "morning", "M:굿모닝", "A:응 굿모닝", "M:오늘 뭐해", "A:인턴 출근", "M:몇 시 끝나", "A:7시 넘을 듯", "M:끝나고 잠깐 볼까", "A:오늘은 좀 피곤해서.. 내일 보자", "M:응 알겠어")
scene("cooling", "day", "M:밥 먹었어?", "A:응", "M:뭐 먹었어", "A:회사 근처", "M:ㅋㅋ 뭐", "A:국밥", "M:맛있었어?", "A:그냥")
scene("cooling", "evening", "A:나 오늘 늦게 끝나 먼저 자", "M:몇 시쯤", "A:몰라 11시?", "M:기다릴게", "A:그냥 자", "M:응..")
scene("cooling", "evening", "M:주말에 시간 돼?", "A:토요일은 회사 사람들이랑 약속", "M:일요일은", "A:일요일은 쉬고 싶어", "M:그럼 저녁에 잠깐만", "A:봐서 연락할게")
scene("cooling", "afternoon", "M:오늘 너 생각 많이 났어", "A:ㅎㅎ 나도", "M:진짜?", "A:응 근데 지금 회의 들어가야 해", "M:응 이따 연락해", "A:응")
scene("cooling", "evening", "M:사진", "M:이거 너랑 갔던 데 아니야?", "A:오 맞네", "M:또 가자", "A:그래 언젠가")
scene("cooling", "night", "M:자?", "A:아니", "M:뭐해", "A:누워있어", "M:통화할까", "A:오늘은 목 아파서.. 내일", "M:알겠어 잘자", "A:잘자")
scene("cooling", "evening", "A:오늘 회식이라 늦어", "M:응 술 많이 마시지 마", "A:ㅇㅇ", "M:끝나면 톡해", "A:응")
scene("cooling", "afternoon", "M:요즘 바빠?", "A:응 좀", "M:힘들겠다", "A:괜찮아", "M:내가 뭐 해줄 거 없어?", "A:없어 고마워")
scene("cooling", "night", "M:오늘 하루 어땠어", "A:그냥 똑같았어", "M:무슨 일 있었어?", "A:아니 그냥 피곤", "M:주말에 푹 쉬자 같이", "A:응 봐서")
scene("cooling", "day", "A:점심 뭐 먹어", "M:너 생각하면서 김밥 ㅋㅋ", "A:ㅋㅋ", "M:너는", "A:아직 회의 중")
scene("cooling", "evening", "M:오늘 영화 볼래? 그 새로 나온 거", "A:오늘? 음..", "M:저녁 8시", "A:다음에 보자 오늘은 좀", "M:응 알겠어")
scene("cooling", "night", "M:잘자 사랑해", "A:응 잘자")
# ---- 8월 차가움
scene("cold", "day", "M:뭐해", "A:일", "M:밥은", "A:먹었어", "M:응.. 이따 연락해", "A:ㅇㅇ")
scene("cold", "afternoon", "M:오늘 볼 수 있어?", "A:오늘은 힘들 것 같아", "M:내일은", "A:봐서", "M:알겠어")
scene("cold", "evening", "M:사진", "M:이거 웃기지 않아 ㅋㅋ", "A:ㅋㅋ")
scene("cold", "afternoon", "M:나 오늘 시험 잘 봤어", "A:오 잘했네", "M:저녁에 축하해줘 ㅋㅋ", "A:오늘 약속 있어", "M:누구랑", "A:회사", "M:응")
scene("cold", "night", "M:요즘 우리 얘기 별로 안 하는 것 같아", "A:바빠서 그래", "M:그래도..", "A:미안", "M:아니야")
scene("cold", "night", "M:자?", "A:응 잘게")
scene("cold", "day", "M:주말에 뭐해", "A:쉬려고", "M:같이 쉬자", "A:혼자 있고 싶어", "M:응")
scene("cold", "evening", "M:저번에 갔던 카페 없어졌더라", "A:아 그래?", "M:응 아쉽다 우리 자주 갔는데", "A:그러게")
scene("cold", "evening", "M:오늘 회사 어땠어", "A:그냥", "M:힘들었어?", "A:ㅇㅇ", "M:푹 쉬어", "A:응")
scene("cold", "night", "M:잘자", "A:잘자")
scene("cold", "day", "M:점심은 먹었어?", "A:응")
# ---- 9월 단절
scene("end", "evening", "M:잘 지내?", "A:응", "M:나는 그냥 그래", "A:..")
scene("end", "evening", "M:밥은 잘 먹고 다녀?", "A:응 너도")
scene("end", "evening", "M:그때 얘기 좀 할 수 있을까", "A:지금은 좀", "M:알겠어")

# ================================================================ 슬롯 채우기 템플릿 (분량 담당). warm에 따라 상대 반응이 달라진다
FOOD = ["김치찌개", "돈까스", "마라탕", "샌드위치", "학식", "떡볶이", "국밥", "파스타", "초밥", "치킨", "라면", "쌀국수", "제육"]
PLACE = ["도서관", "카페", "집", "학교", "강의실", "버스", "지하철", "편의점", "헬스장"]
ACT = ["과제", "팀플", "알바", "시험공부", "빨래", "청소", "산책", "넷플릭스", "운동"]
SHOW = ["그 드라마", "어제 그 예능", "그 유튜브", "그 애니", "새로 나온 영화"]
WEATHER = [("비 온다", "헐 우산 챙겼어? 내가 갈까", "ㅋㅋ 그러게 우산 챙겨"), ("미쳤다 더워", "ㅋㅋ 그러니까 나 지금 녹는 중", "응 진짜 덥다"),
           ("춥다 갑자기", "옷 따뜻하게 입었어? ㅠ", "ㅋㅋ 그러게"), ("날씨 진짜 좋다", "이런 날은 너랑 산책해야 되는데", "응 좋더라"), ("바람 개많이 불어", "머리 다 망가졌어 ㅋㅋㅋ", "ㅋㅋ 그러게")]

def tone(warm: float) -> str:
    r = random.random()
    return "hot" if r < warm - 0.15 else "mid" if r < warm + 0.35 else "cold"

def pick(t: str, hot, mid, cold) -> str:
    return random.choice({"hot": hot, "mid": mid, "cold": cold}[t])

def t_lunch(w):  # 점심 (M 시작)
    f, t = random.choice(FOOD), tone(w)
    a1 = pick(t, [f"{f}! 너는?", f"{f} 먹었어 ㅎㅎ 너는"], [f"{f}", f"{f} 먹음"], ["먹었어", "응"])
    m2 = random.choice(["나 편의점 ㅋㅋ", "나 아직", "나 라면 ㅋㅋ"]) if t != "cold" else random.choice(["뭐 먹었어?", "맛있었어?"])
    a2 = pick(t, ["또 편의점이야? 저녁은 내가 사줄게", "ㅠㅠ 밥 좀 제대로 먹어", "저녁 같이 먹자 그럼"], ["ㅋㅋ 그렇구나", "응 맛있게 먹어"], [f"{f}", "그냥"])
    m3 = pick(t, ["헐 좋아 7시?", "ㅎㅎ 알겠어"], ["응 ㅋㅋ", "너도 맛있게 먹어"], ["응", "그렇구나"])
    return "day", [("M", random.choice(["점심 뭐 먹었어", "밥 먹었어?", "점심 먹었어"])), ("A", a1), ("M", m2), ("A", a2), ("M", m3)]

def t_where(w):  # 어디야 (M 시작)
    p, t = random.choice(PLACE), tone(w)
    a = pick(t, [f"{p}! 왜 보고싶어? ㅎㅎ", f"{p}인데 너 올래?"], [f"{p}", f"{p}이야"], [f"{p}", "밖"])
    if t == "hot":
        return random.choice(["day", "afternoon"]), [("M", random.choice(["어디야", "지금 어디"])), ("A", a), ("M", random.choice(["ㅋㅋ 응 보고싶어", "나 근처인데 갈게"])), ("A", random.choice(["빨리 와 ㅎㅎ", "ㅋㅋ 귀여워 기다릴게"])), ("M", "10분")]
    if t == "mid":
        return random.choice(["day", "afternoon"]), [("M", random.choice(["어디야", "지금 어디"])), ("A", a), ("M", random.choice(["끝나면 연락해", "오 나도 이따 갈게"])), ("A", random.choice(["응 알겠어", "ㅇㅋ"]))]
    return random.choice(["day", "afternoon"]), [("M", random.choice(["어디야", "지금 어디"])), ("A", a), ("M", random.choice(["나 근처인데 잠깐 볼래", "끝나면 연락해"])), ("A", random.choice(["오늘은 좀", "봐서", "응"]))]

def t_doing(w):  # 뭐해 (A 시작)
    act, t = random.choice(ACT), tone(w)
    a2 = pick(t, [f"오 {act} 힘내! 끝나고 뭐해", "ㅎㅎ 나는 너 생각하고 있었지", "나 심심해 놀아줘"], ["ㅋㅋ 그렇구나", "나도 그거 해야 되는데"], ["응", "ㅇㅇ"])
    if t == "cold":
        return random.choice(["afternoon", "evening"]), [("A", random.choice(["뭐해", "바빠?"])), ("M", f"{act} 중"), ("A", a2), ("M", random.choice(["너는 뭐해", "왜 무슨 일 있어?"])), ("A", random.choice(["그냥", "아니 그냥 물어봤어"]))]
    m2 = random.choice(["ㅋㅋ 끝나고 볼래?", "이따 통화할까", "너는 뭐해"])
    a3 = {"ㅋㅋ 끝나고 볼래?": pick(t, ["좋아 몇 시?", "응 기다릴게 ㅎㅎ"], ["음 오늘은 좀 피곤한데", "봐서 연락할게"], ["x"]),
          "이따 통화할까": pick(t, ["응 전화해 ㅎㅎ", "좋아 목소리 듣고 싶었어"], ["응 이따", "ㅋㅋ 그래"], ["x"]),
          "너는 뭐해": pick(t, ["너 생각 ㅎㅎ", "누워서 너 기다리는 중"], ["그냥 누워있어", "유튜브"], ["x"])}[m2]
    return random.choice(["afternoon", "evening", "night"]), [("A", random.choice(["뭐해?", "뭐해", "바빠?"])), ("M", f"{act} 중"), ("A", a2), ("M", m2), ("A", a3)]

def t_show(w):  # 봤어? (M 시작)
    sh, t = random.choice(SHOW), tone(w)
    if t == "cold":
        return random.choice(["evening", "night"]), [("M", f"{sh} 봤어?"), ("A", random.choice(["아니", "안 봄"])), ("M", "재밌더라 한번 봐"), ("A", random.choice(["응", "ㅇㅇ"]))]
    a = pick(t, ["봤지!! 마지막에 미쳤어", "아직 ㅠ 같이 볼래?"], ["봤어 ㅋㅋ", "아직"], ["x"])
    if "아직" in a:
        return random.choice(["evening", "night"]), [("M", f"{sh} 봤어?"), ("A", a), ("M", random.choice(["오 주말에 같이 보자", "스포 안 할게 ㅋㅋ"])), ("A", pick(t, ["좋아 ㅎㅎ 팝콘은 내가", "약속!"], ["응 ㅋㅋ", "그래"], ["x"]))]
    return random.choice(["evening", "night"]), [("M", f"{sh} 봤어?"), ("A", a), ("M", "중간에 그 장면 진짜 ㅋㅋㅋ"), ("A", pick(t, ["ㅋㅋㅋㅋ 나도 거기서 소리 질렀어", "그치 그 장면 최고"], ["ㅋㅋ 인정", "그러게"], ["x"]))]

def t_weather(w):
    wx, hot, mid = random.choice(WEATHER); t = tone(w)
    a = pick(t, [hot], [mid], ["ㅇㅇ", "응"])
    m2 = pick(t, ["ㅋㅋ 이따 봐", "너도 조심해"], ["ㅋㅋ", "감기 조심"], ["응"])
    return random.choice(["day", "afternoon"]), [("M", wx), ("A", a), ("M", m2)] + ([("A", pick(t, ["너도 ❤️", "응 이따 봐 ㅎㅎ"], ["응", "ㅇㅋ"], ["x"]))] if t != "cold" else [])

def t_plan(w):  # 주말 계획 (M 시작)
    day, what, t = random.choice(["토요일", "일요일", "금요일 저녁", "내일"]), random.choice(["영화", "한강", "그 카페", "전시", "맛집", "드라이브"]), tone(w)
    if t == "hot":
        return random.choice(["afternoon", "evening"]), [("M", f"{day}에 시간 돼?"), ("A", random.choice(["당연히 되지 ㅎㅎ 뭐 할까", "나 그날 하루 비워놨어"])), ("M", f"{what} 어때"), ("A", random.choice([f"좋아!! {what} 가자", "ㅎㅎ 기대된다 몇 시에 볼까"])), ("M", random.choice(["2시 정문?", "점심부터 같이 먹자"])), ("A", "응 ❤️")]
    if t == "mid":
        return random.choice(["afternoon", "evening"]), [("M", f"{day}에 시간 돼?"), ("A", random.choice(["음 저녁엔 될 듯", "그날 뭐 하려고?"])), ("M", f"{what} 어때"), ("A", random.choice(["응 알겠어 봐서 연락할게", "ㅇㅋ 저녁에"])), ("M", "응")]
    return random.choice(["afternoon", "evening"]), [("M", f"{day}에 시간 돼?"), ("A", random.choice(["그날 약속 있어", "쉬고 싶어", "봐서"])), ("M", random.choice(["그럼 저녁이라도", "알겠어..", "요즘 계속 바쁘네"])), ("A", random.choice(["다음에", "미안", "응"]))]

def t_tired(w):  # 상대가 피곤 (A 시작)
    t = tone(w)
    a2 = pick(t, ["ㅠㅠ 고마워 목소리 들으니까 낫다", "너 보면 풀릴 것 같아", "안아줘 ㅠ"], ["응 고마워", "ㅎㅎ 응"], ["응", "ㅇㅇ"])
    a3 = pick(t, ["응 잘자 사랑해", "너도 푹 자 ❤️"], ["응 잘자", "잘자"], ["ㅇㅇ", "응"])
    return random.choice(["evening", "night"]), [("A", random.choice(["아 오늘 진짜 피곤해", "일 너무 많다", "나 오늘 완전 방전"])), ("M", random.choice(["고생했어 ㅠㅠ", "무슨 일 있었어?", "내가 맛있는 거 사줄게"])), ("A", a2), ("M", random.choice(["푹 쉬어", "일찍 자", "내일은 좀 나을 거야"])), ("A", a3)]

def t_photo(w):  # 사진 (M 시작)
    t = tone(w)
    a = pick(t, ["헐 뭐야 귀여워 ㅋㅋㅋ", "어디야 여기?? 나도 가고 싶어", "너 잘 나왔다"], ["ㅋㅋ 뭐야", "오 어디야"], ["ㅋㅋ", "응"])
    m3 = "다음에 같이 오자" if "어디" in a else pick(t, ["ㅋㅋㅋ 너 주려고 찍음", "ㅎㅎ"], ["ㅋㅋㅋ", "그치"], ["응"])
    return random.choice(["day", "afternoon", "evening"]), [("M", "사진"), ("M", random.choice(["이거 봐 ㅋㅋ", "지금 여기", "너 생각나서"])), ("A", a), ("M", m3)]

def t_class(w):  # 수업/팀플 (M 시작)
    t = tone(w)
    a = pick(t, ["나도 ㅠ 끝나고 커피 마시자", "힘내 이따 봐 ❤️", "나 지금 몰래 톡하는 중 ㅋㅋ"], ["나도 회의 중", "ㅋㅋ 힘내"], ["응", "바빠 이따"])
    return "day", [("M", random.choice(["수업 너무 지루하다", "이 교수 진짜 ㅋㅋ", "팀플 미친 것 같아"])), ("A", a), ("M", pick(t, ["ㅋㅋ 끝나면 톡할게", "응 이따 봐"], ["응 이따", "ㅇㅋ"], ["응"]))]

def t_night(w):  # 밤 (M 시작)
    t = tone(w)
    if t == "cold":
        return "night", [("M", random.choice(["자?", "아직 안 자?"])), ("A", random.choice(["응 잘게", "졸려"])), ("M", "응 잘자")]
    a = pick(t, ["응 너 기다렸어 ㅎㅎ", "아직! 뭐해"], ["아니 아직", "응 자려고"], ["x"])
    m2 = random.choice(["그냥 목소리 듣고 싶어서", "보고싶다", "오늘 고생했어"]) if "뭐해" in a else random.choice(["보고싶다", "오늘 고생했어", "잘자 사랑해"])
    a2 = pick(t, ["나도 보고싶어 잘자 ❤️", "내일 보자 잘자 사랑해", "전화해 ㅎㅎ"], ["응 잘자", "잘자~"], ["x"])
    return "night", [("M", random.choice(["자?", "아직 안 자?"])), ("A", a), ("M", m2), ("A", a2)]

T_ME = [t_lunch, t_where, t_show, t_weather, t_plan, t_photo, t_class, t_night]   # 내가 먼저 거는 템플릿
T_A = [t_doing, t_tired]                                                          # 상대가 먼저 거는 템플릿
GM = [[("M", "굿모닝"), ("A", "굿모닝 ☀️")], [("A", "일어났어?"), ("M", "방금 ㅋㅋ")], [("A", "굿모닝~"), ("M", "잘 잤어?"), ("A", "응!")], [("M", "잘 잤어?"), ("A", "응 너는")], [("M", "굿모닝"), ("A", "응 굿모닝")]]
GN = [[("M", "잘자 사랑해"), ("A", "잘자 ❤️")], [("A", "나 잘게 잘자"), ("M", "응 잘자")], [("M", "굿나잇"), ("A", "굿나잇 ㅎㅎ")], [("A", "잘자 내일 봐"), ("M", "응 사랑해")], [("M", "잘자"), ("A", "응 잘자")]]

# ================================================================ 사건 (날짜 고정). (시, 분, 대사, 이후 조용히?)
def ev(*lines):
    return [(l[0], l[2:]) for l in lines]

EVENTS: dict[str, list] = {
    "2026-03-14": [(21, 40, ev("A:오늘 진짜 재밌었어", "M:나도", "A:ㅎㅎ 근데 너 아까 왜 웃었어", "M:네가 웃어서", "A:뭐야 그게 ㅋㅋㅋ", "M:그냥 그렇다고", "A:..나 지금 좀 설렌 것 같은데", "M:나도", "A:ㅎㅎ 잘자", "M:잘자"), False)],
    "2026-03-23": [(20, 5, ev("M:오늘 할 말이 있어", "A:응? 뭔데", "M:만나서 하려다가 못 참겠어서", "A:ㅋㅋ 뭔데", "M:우리 사귀자", "A:...", "A:나 지금 소리 질렀어", "M:그래서 답은", "A:당연히 응이지 바보야", "M:ㅋㅋㅋㅋ 오늘부터 1일", "A:1일 ❤️"), False)],
    "2026-04-18": [(22, 30, ev("A:아까 그 여자애 누구야", "M:동아리 후배 왜", "A:되게 친해 보이길래", "M:그냥 후배야 ㅋㅋ", "A:ㅋㅋ 하지 마", "M:미안 신경 쓰였어?", "A:조금..", "M:앞으로 조심할게. 내 눈엔 너밖에 안 보여", "A:오글 ㅋㅋㅋ 알겠어", "M:진심인데", "A:ㅎㅎ 알아 잘자"), True)],
    "2026-05-05": [(11, 0, ev("A:오늘 어린이날인데 우리도 어린이 하자", "M:ㅋㅋㅋ 뭐 하게", "A:놀이공원!", "M:가자 지금 준비할게", "A:30분 뒤 정문", "M:ㅇㅋ"), False),
                   (23, 10, ev("M:다리 아파 죽겠다", "A:ㅋㅋㅋ 나도", "M:근데 너무 좋았어", "A:사진", "A:사진", "A:우리 잘 나왔지", "M:응 이거 인생샷", "A:ㅎㅎ 잘자 사랑해", "M:사랑해"), True)],
    "2026-06-12": [(23, 50, ev("M:어디야", "M:연락이 안 되네", "M:자?"), True)],
    "2026-06-13": [(1, 40, ev("A:미안 폰 가방에 있었어", "M:지금 몇 신데", "A:친구들이랑 있었어", "M:한 번은 볼 수 있잖아", "A:정신없었어 미안", "M:나 걱정했어", "A:알겠어 미안하다고", "M:그렇게 말하니까 더 서운하다", "A:...", "M:됐어 자"), True),
                   (14, 20, ev("M:아직 화났어?", "A:화난 건 아닌데", "M:그럼", "A:그냥 좀 답답해. 나도 친구 만날 수 있잖아", "M:그건 당연하지. 연락이 안 돼서 그런 거야", "A:알아.. 나중에 얘기하자", "M:응"), True)],
    "2026-06-14": [(20, 15, ev("M:어제는 미안해. 네가 친구 만나는 게 문제가 아니라 아무 말 없이 4시간 동안 연락이 안 돼서 무서웠어. 근데 그걸 화로 말한 건 내 잘못이야.", "A:나도 미안해. 폰 확인 안 한 건 내 잘못 맞아. 다음부턴 늦게 끝날 것 같으면 미리 말할게", "M:고마워", "A:우리 이런 걸로 싸우지 말자", "M:응 사랑해", "A:나도 사랑해. 내일 만나서 안아줘", "M:ㅋㅋ 당연하지"), True)],
    "2026-07-01": [(0, 0, ev("M:100일 축하해", "A:헐 12시 딱 맞춰서 ㅋㅋㅋ", "M:당연하지", "A:나도 축하해 ❤️ 내일 선물 있어", "M:나도 있어", "A:ㅎㅎ 기대된다 잘자"), False),
                   (21, 30, ev("A:선물 너무 좋았어", "A:사진", "M:네가 준 것도 매일 쓸게", "A:ㅎㅎ 200일도 이렇게 하자", "M:당연하지"), True)],
    "2026-07-20": [(22, 10, ev("M:요즘 왜 이렇게 무심해", "A:무심한 게 아니라 바쁜 거야", "M:바쁜 건 알아. 근데 톡 하나 보내는 데 1분도 안 걸리잖아", "A:인턴 끝나면 진짜 아무것도 하기 싫어", "M:나한테 톡하는 게 '아무것도'에 들어가?", "A:그런 뜻이 아니잖아", "M:그럼 무슨 뜻인데", "A:지금 이 얘기 하기 싫어", "M:알겠어"), True)],
    "2026-07-21": [],   # 침묵
    "2026-07-22": [(21, 0, ev("A:그저께는 미안. 나도 요즘 내가 좀 그런 거 알아", "M:나도 몰아붙여서 미안", "A:인턴 끝나면 괜찮아질 거야", "M:응 기다릴게", "A:고마워", "M:사랑해", "A:응 나도"), True)],
    "2026-08-15": [(17, 30, ev("A:오늘 못 갈 것 같아 미안", "M:왜?", "A:너무 피곤해서..", "M:일주일 전부터 잡은 건데", "A:미안 다음 주에 보자", "M:응"), True)],
    "2026-08-23": [(21, 45, ev("M:우리 요즘 왜 이래", "A:뭐가", "M:한 달 동안 두 번 봤어. 톡도 내가 먼저 안 하면 없고", "A:...", "M:나 혼자 연애하는 것 같아", "A:나도 노력하고 있어", "M:어디에서?", "A:그렇게 말하면 나도 할 말 없어", "M:그냥 솔직하게 말해줘. 마음이 식었어?", "A:모르겠어", "M:...", "A:우리 좀 생각해보자", "M:알겠어"), True)],
    "2026-08-24": [], "2026-08-25": [], "2026-08-26": [],
    "2026-09-02": [(22, 20, ev("A:우리 시간 좀 갖자", "M:얼마나", "A:모르겠어", "M:그게 헤어지자는 말이랑 뭐가 달라", "A:다르지.. 나도 정리가 필요해", "M:알겠어. 기다릴게"), True)],
    "2026-09-03": [], "2026-09-04": [], "2026-09-05": [],
    "2026-09-06": [(23, 30, ev("M:나 그동안 많이 생각했어. 네가 바빠지면서 내가 더 매달렸고 그게 너한테 부담이었던 것 같아. 미안해. 근데 나는 아직 너를 좋아하고, 이대로 끝내고 싶지 않아. 네가 준비되면 얘기하자."), True)],
    "2026-09-07": [(13, 10, ev("A:고마워. 조금만 더 시간 줘"), True)],
    "2026-09-08": [], "2026-09-09": [], "2026-09-10": [], "2026-09-11": [],
    "2026-09-12": [(21, 0, ev("M:잘 지내?"), True)],
    "2026-09-13": [],
    "2026-09-14": [(19, 40, ev("A:미안. 나 마음이 정리된 것 같아", "M:...", "M:그래", "A:정말 미안해", "M:네 잘못 아니야", "A:너 좋은 사람이야", "M:그 말은 하지 마"), True)],
    "2026-09-15": [(20, 30, ev("M:네 물건 어떻게 할까", "A:버려도 돼", "M:그건 못 하겠어", "A:그럼 나중에 받을게"), True)],
    "2026-09-16": [(21, 12, ev("A:우리 한 번 만나서 얘기할까?"), True)],   # 내가 답 안 한 열린 메시지
}

# ================================================================ 엔진
def kdate(d: datetime) -> str:
    return f"--------------- {d.year}년 {d.month}월 {d.day}일 {WD[d.weekday()]}요일 ---------------"


def ktime(d: datetime) -> str:
    return f"[{'오전' if d.hour < 12 else '오후'} {d.hour % 12 or 12}:{d.minute:02d}]"


def write_room(name: str, title: str, msgs: list) -> int:
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


def play(lines: list, t: datetime, a_reply: float, m_reply: float, other: str = A) -> list:
    """대사를 실제 시각으로 펼친다. 같은 사람 연속 발화는 1분 안, 화자가 바뀔 때 답장 지연."""
    out, prev = [], None
    for who, text in lines:
        name = ME if who == "M" else other
        if prev is not None:
            t += timedelta(seconds=random.randint(10, 70)) if prev == name else timedelta(minutes=jitter(m_reply if name == ME else a_reply))
        out.append((t, name, text)); prev = name
    return out


def slot_time(day: datetime, slot: str) -> datetime:
    lo, hi = SLOT_HOURS[slot]
    h = random.randint(lo, hi)
    return day.replace(hour=h % 24, minute=random.randint(0, 59)) + (timedelta(days=1) if h >= 24 else timedelta())


def flip(lines: list) -> list:
    return [("A" if w == "M" else "M", t) for w, t in lines]


def greet_lines(pool: list, p: dict) -> list:
    lines = random.choice(pool)
    want_a = random.random() < p["a_start"]
    return flip(lines) if (lines[0][0] == "A") != want_a else lines


def day_sessions(day: datetime, p: dict, used_scenes: set, used_slots: set) -> list:
    out = []
    n = int(p["sessions"]) + (1 if random.random() < p["sessions"] % 1 else 0)
    for _ in range(n):
        want_a = random.random() < p["a_start"]
        avail = [i for i, sc in enumerate(S) if p["bank"] in sc["banks"] and i not in used_scenes and sc["slot"] not in used_slots and (sc["lines"][0][0] == "A") == want_a]
        if avail and random.random() < 0.5:
            i = random.choice(avail); used_scenes.add(i)
            slot, lines = S[i]["slot"], S[i]["lines"]
        else:
            pool = T_A if want_a else T_ME
            for _try in range(6):
                slot, lines = random.choice(pool)(p["warm"])
                if slot not in used_slots:
                    break
            else:
                continue
        used_slots.add(slot)
        out += play(lines, slot_time(day, slot), p["a_reply"], p["m_reply"])
    return out


def gen_A() -> list:
    msgs, used_scenes = [], set()
    d0 = datetime(2026, 3, 1)
    for i in range(0, 200):
        day = d0 + timedelta(days=i)
        key = day.strftime("%Y-%m-%d")
        p = phase(day)
        used_slots: set = set()
        quiet = False
        if key in EVENTS:
            if not EVENTS[key]:
                continue   # 침묵일
            for h, m, lines, q in EVENTS[key]:
                msgs += play(lines, day.replace(hour=h, minute=m), max(2, p["a_reply"] / 3), max(1, p["m_reply"] / 2))
                slot = next((s for s, (lo, hi) in SLOT_HOURS.items() if lo <= (h if h >= 7 else h + 24) <= hi), "night")
                used_slots.add(slot)
                quiet = quiet or q
            if quiet:
                continue   # 싸움·이별 사건이 있는 날은 그 대화가 전부
        if p["bank"] == "end" and random.random() > p["sessions"]:
            continue
        if random.random() < p["greet"] and "morning" not in used_slots:
            msgs += play(greet_lines(GM, p), slot_time(day, "morning"), p["a_reply"], p["m_reply"]); used_slots.add("morning")
        msgs += day_sessions(day, p, used_scenes, used_slots)
        if random.random() < p["greet"] * 0.85 and "night" not in used_slots and not quiet:
            msgs += play(greet_lines(GN, p), slot_time(day, "night"), p["a_reply"], p["m_reply"])
    return msgs


# ---------------------------------------------------------------- 친구방 (baseline)
B_ME = ["야 과제 했냐", "ㅋㅋㅋㅋ 뭐냐 그게", "오늘 학식 뭐임", "피시방 ㄱ?", "아 시험 망함", "ㅇㅇ", "ㄱㄱ", "낼 봄", "ㅋㅋ 인정", "몰라 그냥 하자", "몇 시에 옴", "나 지금 도서관"]
B_B = ["ㄴㄴ", "ㅋㅋㅋ", "돈까스", "ㄱ", "나도", "ㅇㅋ", "몇 시", "야 그 교수 미쳤냐", "과제 언제까지지", "ㅋㅋㅋㅋㅋ", "나 지금 감", "배고프다"]
C_ME = ["언니 뭐해", "ㅋㅋㅋ 진짜?", "그거 어디서 샀어", "나 요즘 너무 바쁘다", "다음 주에 밥 먹자", "ㅇㅇ 알겠어", "ㅎㅎ 고마워", "언니 나 요즘 힘들어"]
C_C = ["일하지 ㅠ", "응 진짜야 ㅋㅋ", "올리브영!", "힘내 ㅠㅠ", "좋아 언제?", "오키", "밥 잘 챙겨 먹고", "연오야 잘 지내?", "무슨 일 있어? 언니한테 말해"]


def chat_pool(day: datetime, other: str, n: int, my_reply: float, their_reply: float, my_pool, their_pool, hours) -> list:
    t = day.replace(hour=random.randint(*hours), minute=random.randint(0, 59))
    who = random.choice([ME, other]); out = [(t, who, random.choice(my_pool if who == ME else their_pool))]
    for _ in range(n - 1):
        nxt = other if who == ME else ME
        t += timedelta(minutes=jitter(my_reply if nxt == ME else their_reply))
        who = nxt; out.append((t, who, random.choice(my_pool if who == ME else their_pool)))
    return out


def gen_B() -> list:
    msgs, d0 = [], datetime(2026, 3, 1)
    for i in range(200):
        day = d0 + timedelta(days=i)
        if random.random() < 0.45:
            continue
        msgs += chat_pool(day, B, random.randint(3, 9), 45, 60, B_ME, B_B, (11, 23))
    return msgs


def gen_C() -> list:
    msgs, d0 = [], datetime(2026, 3, 1)
    for i in range(200):
        day = d0 + timedelta(days=i)
        if random.random() < 0.8:
            continue
        msgs += chat_pool(day, C, random.randint(3, 7), 90, 40, C_ME, C_C, (12, 22))
    msgs.append((datetime(2026, 9, 15, 19, 30), C, "연오야 다음 주 토요일 시간 돼? 밥 사줄게"))
    return msgs


if __name__ == "__main__":
    for f in OUT.glob("*.txt"):
        f.unlink()
    n1 = write_room("김하늘", A, gen_A())
    n2 = write_room("박민수", B, gen_B())
    n3 = write_room("이서진", C, gen_C())
    print(f"김하늘 {n1} / 박민수 {n2} / 이서진 {n3} messages")
