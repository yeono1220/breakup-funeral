import { useEffect, useRef, useState } from 'react'
import { api } from '../api'
import { Modal } from '../components/ui'

const CANNED = ['ㅇㅇ 근데 그건 네 생각이고', '바쁘다니까 자꾸', '미안한데 나 진짜 변한 거 없어', '그때도 말했잖아 ㅎㅎ', '굳이 지금 이걸 물어봐야 돼?', '너 또 이런다 진짜', '나중에 연락할게 (안 함)']

export function Tools({ name }: { name: string }) {
  const [modal, setModal] = useState<'summon' | 'legend' | 'siren' | null>(null)
  return (
    <section className="page">
      <div className="wrap">
        <h2 className="pen" style={{ fontSize: 34, marginBottom: 6, fontWeight: 400 }}>🩹 현실 치료실</h2>
        <p style={{ color: 'var(--text-soft)', fontSize: 14, marginBottom: 24 }}>미련이 스멀스멀 올라올 때, 현실을 직시하게 도와드려요</p>
        <div className="tool-grid">
          <div className="tool" onClick={() => setModal('summon')}><div className="tool-ic">🔮</div><div className="tool-t">X-AI 소환술</div><div className="tool-d">{name} 말투 복제 AI와 가상 대화 · 미련 던지면 팩폭 리턴</div></div>
          <div className="tool" onClick={() => setModal('legend')}><div className="tool-ic">📖</div><div className="tool-t">레전드 썰 매칭</div><div className="tool-d">내 카톡과 유사한 디시·네이트판 레전드 썰로 현타 부여</div></div>
          <div className="tool" onClick={() => setModal('siren')}><div className="tool-ic">🚨</div><div className="tool-t">선톡 방지 비상벨</div><div className="tool-d">새벽에 선톡하고 싶을 때 누르면 사이렌이 울려요</div></div>
        </div>
        <div className="roast" style={{ marginTop: 24 }}>
          <div className="rq">"다시 만나기만 해봐라.<br />인간은 같은 실수를 반복하고,<br />당신은 또 울면서 이 앱을 켜게 될 겁니다."</div>
          <div className="rcap">— 이별 장례식 현실 치료 센터</div>
        </div>
      </div>
      {modal === 'summon' && <Summon name={name} onClose={() => setModal(null)} />}
      {modal === 'legend' && <Legend onClose={() => setModal(null)} />}
      {modal === 'siren' && (
        <div className="siren-modal">
          <div className="siren-emoji">🚨</div>
          <div className="siren-big">멈춰!!!</div>
          <div className="siren-sub">지금 선톡하면 내일 아침 이불킥 200%.<br />그 톡, 3분 뒤에도 보내고 싶으면 그때 보내요.<br /><br />지금은… 폰 내려놓기 🙅</div>
          <button className="siren-btn" onClick={() => setModal(null)}>알았어요… 참을게요</button>
        </div>
      )}
    </section>
  )
}

function Summon({ name, onClose }: { name: string; onClose: () => void }) {
  const [msgs, setMsgs] = useState<{ role: 'user' | 'assistant'; content: string; note?: string }[]>([{ role: 'assistant', content: '…왜 불렀어?' }])
  const [v, setV] = useState('')
  const [busy, setBusy] = useState(false)
  const box = useRef<HTMLDivElement>(null)
  useEffect(() => { box.current?.scrollTo({ top: 1e9 }) }, [msgs])

  async function say(text?: string) {
    const t = (text ?? v).trim(); if (!t || busy) return
    const hist = [...msgs, { role: 'user' as const, content: t }]
    setMsgs(hist); setV(''); setBusy(true)
    try {
      const r = await api.summon(hist.map(m => ({ role: m.role, content: m.content })))
      setMsgs([...hist, { role: 'assistant', content: r.reply, note: r.fallback ? '↑ 데모 응답 · API 키 넣으면 실제 말투로 복제돼요' : '↑ 팩폭 주의 · 실제 카톡 패턴 기반' }])
    } catch {
      setMsgs([...hist, { role: 'assistant', content: CANNED[Math.floor(Math.random() * CANNED.length)], note: '↑ 데모 응답 · API 키 넣으면 실제 말투로 복제돼요' }])
    } finally { setBusy(false) }
  }
  return (
    <Modal title="🔮 X 소환술" onClose={onClose} bodyClass="summon-body">
      <p className="tiny muted" style={{ marginBottom: 10 }}>{name} 말투를 복제한 AI · 미련 던지면 팩폭이 돌아옵니다 · 보내지지 않아요</p>
      <div className="summon-chat" ref={box}>
        {msgs.map((m, i) => (
          <div key={i} style={{ display: 'contents' }}>
            <div className={'rp-msg ' + (m.role === 'user' ? 'me' : 'them')}>{m.content}</div>
            {m.note && <div style={{ fontSize: 11, color: 'var(--rose-soft)', textAlign: 'center', margin: '4px 0 10px' }}>{m.note}</div>}
          </div>
        ))}
        {busy && <div className="rp-msg them">…</div>}
      </div>
      <div className="summon-quick">{['보고 싶어', '우리 다시 만날까?', '그때 왜 그랬어?'].map(q => <button key={q} onClick={() => say(q)}>{q}</button>)}</div>
      <div className="summon-in"><input value={v} onChange={e => setV(e.target.value)} placeholder="미련 섞인 톡을 던져봐요…" onKeyDown={e => e.key === 'Enter' && say()} /><button onClick={() => say()}>↑</button></div>
    </Modal>
  )
}

function Legend({ onClose }: { onClose: () => void }) {
  return (
    <Modal title="📖 레전드 썰 매칭" onClose={onClose}>
      <p className="tiny muted" style={{ marginBottom: 14 }}>당신 카톡 맥락과 유사한 레전드 썰을 찾았어요</p>
      <div className="legend-story"><span className="ls-match">🎯 유사도 98%</span><div className="ls-src">📍 디시인사이드 연애갤 · 추천 4,201</div><div className="ls-body">"6시간마다 답장 오길래 바쁜 줄 알았는데, 알고 보니 게임하면서 딴 사람이랑은 실시간 톡. 나한테만 '바빴어 미안' 시전…"</div><div className="ls-hit">💥 현타 포인트: 바쁜 게 아니라 <b>우선순위에서 밀린 것</b>이었습니다.</div></div>
      <div className="legend-story"><span className="ls-match">🎯 유사도 94%</span><div className="ls-src">📍 네이트판 · 댓글 1,882</div><div className="ls-body">"'나 나중에 연락할게'가 마지막이었음. 그 나중은 6개월째 안 옴. 근데 생일엔 칼같이 '생축' 한 마디…"</div><div className="ls-hit">💥 현타 포인트: '나중에'는 <b>거절의 완곡어법</b>입니다.</div></div>
      <button className="btn btn-block" onClick={onClose}>현실 자각 완료 🫠</button>
    </Modal>
  )
}
