"""텍스트 피처: 질문/ㅋㅋ/이모지/열린 메시지/인사 판정. 전부 정규식, LLM 없음."""
from __future__ import annotations

import re

RE_KKK = re.compile(r"[ㅋㅎ]{2,}")
RE_YY = re.compile(r"[ㅠㅜ]{2,}")
RE_EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿⭐⭕‼⁉〰〽㊗㊙]")
RE_URL = re.compile(r"https?://\S+")
RE_QUESTION = re.compile(r"\?|[뭐머]\s*(해|하|함|야|임|지)|언제|어디|왜|어때|어떄|할래|갈래|볼래|먹을래|될까|할까|갈까|볼까|가능|있어\s*$|없어\s*$|있음\?|맞[아지]\s*$|아냐\s*$|응\?|진짜\?")
RE_REQUEST = re.compile(r"해줘|해주라|줄래|보내줘|알려줘|확인해|부탁|해야[돼되]|가자|하자|보자|만나|나와")
RE_GREETING = re.compile(r"잘\s*자|굿나잇|굿밤|좋은\s*꿈|굿모닝|좋은\s*아침|잘\s*잤|일어났|출근|퇴근|다녀올게|도착|집\s*왔|밥\s*먹었")
RE_CLOSER = re.compile(r"^(?:[ㅋㅎㅠㅜ]+|ㅇㅇ|ㅇㅋ|오케이|오키|옼|넵|넹|네|응|웅|엉|ㅇ|굿|ㄱㄱ|ok|okay|ㅂㅂ|바이|잘\s*자|굿나잇|굿밤|좋은\s*꿈|수고|고생|땡큐|고마워|감사|ㅎㅇ|안녕|ㅇㅋㅇㅋ|알겠어|알겠|알써|알았어|ㅇㅋ\S*)[!~.\s]*$")
RE_EMOTION = re.compile(r"보고\s*싶|좋아해|좋아|사랑|미안|서운|섭섭|화나|짜증|싫|고마워|행복|설레|보고파|그리워|외로|힘들|슬퍼|우울|기뻐|최고")
RE_SENT_END = re.compile(r"(요|임|함|음|다|야|지|네|죠|어|아|해|워|게|래|까|냐|니|나)[.!?~ㅋㅎ]*$")

MEDIA = {"사진", "이모티콘", "동영상", "음성메시지", "파일"}


def is_media(text: str) -> bool:
    t = text.strip()
    return t in MEDIA or (t.startswith("사진 ") and t.endswith("장"))


def is_question(text: str) -> bool:
    return bool(RE_QUESTION.search(text))


def is_open_message(text: str) -> tuple[bool, str]:
    """상대 마지막 메시지가 '답을 기다리는' 메시지인가. (열림 여부, 이유)"""
    t = text.strip()
    if not t:
        return False, ""
    if is_media(t):
        return t in ("사진", "동영상") or t.startswith("사진 "), "사진/영상 보냄"
    if RE_CLOSER.match(t):
        return False, "종결형"
    if "?" in t:
        return True, "물음표"
    if RE_QUESTION.search(t):
        return True, "질문 표현"
    if RE_REQUEST.search(t):
        return True, "요청/제안"
    if RE_URL.search(t):
        return True, "링크 공유"
    if RE_EMOTION.search(t):
        return True, "감정 표현"
    if len(t) >= 15:
        return True, "긴 메시지"
    return False, "짧은 서술"


def kkk_len(text: str) -> int:
    return sum(len(x) for x in RE_KKK.findall(text))


def has_kkk(text: str) -> bool:
    return bool(RE_KKK.search(text))


def has_emoji(text: str) -> bool:
    return bool(RE_EMOJI.search(text))


def is_greeting(text: str) -> bool:
    return bool(RE_GREETING.search(text))


def has_emotion(text: str) -> bool:
    return bool(RE_EMOTION.search(text))
