import { useEffect, useRef, useState } from 'react'
import { api, type Legends } from '../api'
import { Modal } from '../components/ui'
import { Icon } from '../components/Icons'

const CANNED = ['ㅇㅇ 근데 그건 네 생각이고', '바쁘다니까 자꾸', '미안한데 나 진짜 변한 거 없어', '그때도 말했잖아 ㅎㅎ', '굳이 지금 이걸 물어봐야 돼?', '너 또 이런다 진짜', '나중에 연락할게 (안 함)']

/* 도구 카드: 소환술 카드를 크게, 좁은 화면에선 한 열 */
const GRID_CSS = `
.tool-grid.tg-hero{grid-template-columns:1.4fr 1fr 1fr;}
.tool-grid.tg-hero .tool.hero{text-align:left;display:flex;flex-direction:column;justify-content:flex-end;min-height:180px;}
.tool-grid.tg-hero .tool.hero .tool-ic{justify-content:flex-start;margin-bottom:auto;padding-bottom:16px;}
.tool-grid.tg-hero .tool.hero .tool-t{font-size:20px;}
.tool-grid.tg-hero .tool.hero .tool-d{font-size:13px;}
@media (max-width:700px){.tool-grid.tg-hero{grid-template-columns:1fr;}.tool-grid.tg-hero .tool.hero{min-height:0;}}
`

export function Tools({ name, onCoach }: { name: string; onCoach?: () => void }) {
  const [modal, setModal] = useState<'summon' | 'legend' | 'siren' | null>(null)
  return (
    <section className="page">
      <style>{GRID_CSS}</style>
      <div className="wrap">
        <h2 className="page-title reveal" style={{ ['--i' as any]: 0, display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}><Icon name="bandage" size={18} />현실 치료실</h2>
        <p className="reveal" style={{ ['--i' as any]: 1, color: 'var(--text-soft)', fontSize: 14, marginBottom: 24 }}>미련이 스멀스멀 올라올 때, 현실을 보게 도와줄게</p>
        <div className="tool-grid tg-hero">
          <div className="tool hero reveal" style={{ ['--i' as any]: 2 }} onClick={() => setModal('summon')}><div className="tool-ic"><Icon name="ghost" size={40} /></div><div className="tool-t">X-AI 소환술</div><div className="tool-d">{name} 말투를 흉내 낸 AI랑 가상 대화 · 미련 던지면 팩폭이 돌아와</div></div>
          <div className="tool reveal" style={{ ['--i' as any]: 3 }} onClick={() => setModal('legend')}><div className="tool-ic"><Icon name="search" size={32} /></div><div className="tool-t">레전드 썰 매칭</div><div className="tool-d">내 카톡이랑 비슷한 디시·네이트판 레전드 썰로 현타 주기</div></div>
          {onCoach && <div className="tool reveal" style={{ ['--i' as any]: 4 }} onClick={onCoach}><div className="tool-ic"><Icon name="receipt" size={32} /></div><div className="tool-t">관계 코치 상담</div><div className="tool-d">데이터 보는 코치한테 묻기 · 사정을 말하면 진단서가 그걸 우선해</div></div>}
          <div className="tool reveal" style={{ ['--i' as any]: 5 }} onClick={() => setModal('siren')}><div className="tool-ic">🚨</div><div className="tool-t">선톡 방지 비상벨</div><div className="tool-d">새벽에 선톡하고 싶을 때 누르면 사이렌이 울려</div></div>
        </div>
        <div className="roast reveal" style={{ ['--i' as any]: 5, marginTop: 44 }}>
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
          <div className="siren-sub">지금 선톡하면 내일 아침 이불킥 200%.<br />3분 뒤에도 보내고 싶으면 그때 보내.<br /><br />지금은 폰 내려놔</div>
          <button className="siren-btn" onClick={() => setModal(null)}>알았어… 참을게</button>
        </div>
      )}
    </section>
  )
}

const NOTE_DEMO = '↑ 지금은 예시 답변이야'
const NOTE_REAL = '↑ 실제 카톡 패턴으로 만든 답이야'

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
      const bubbles = r.bubbles && r.bubbles.length ? r.bubbles : [r.reply]
      const note = r.fallback ? NOTE_DEMO : NOTE_REAL
      // 상대가 실제로 그러듯 버블을 하나씩 띄운다 (마지막 버블에만 주석)
      for (let i = 0; i < bubbles.length; i++) {
        if (i) await new Promise(res => setTimeout(res, 500 + Math.min(1200, bubbles[i].length * 60)))
        const last = i === bubbles.length - 1
        setMsgs([...hist, ...bubbles.slice(0, i + 1).map((b, j) => ({ role: 'assistant' as const, content: b, note: last && j === i ? note : undefined }))])
      }
    } catch {
      setMsgs([...hist, { role: 'assistant', content: CANNED[Math.floor(Math.random() * CANNED.length)], note: NOTE_DEMO }])
    } finally { setBusy(false) }
  }
  return (
    <Modal title="X 소환술" onClose={onClose} bodyClass="summon-body">
      <p className="tiny muted" style={{ marginBottom: 12 }}>{name} 말투를 흉내 낸 AI야 · 미련 던지면 팩폭이 돌아와 · 진짜로 보내지진 않아</p>
      <div className="summon-chat" ref={box}>
        {msgs.map((m, i) => (
          <div key={i} style={{ display: 'contents' }}>
            <div className={'rp-msg ' + (m.role === 'user' ? 'me' : 'them')}>{m.content}</div>
            {m.note && <div style={{ fontSize: 11, color: 'var(--rose-soft)', textAlign: 'center', margin: '4px 0 12px' }}>{m.note}</div>}
          </div>
        ))}
        {busy && <div className="rp-msg them">…</div>}
      </div>
      <div className="summon-quick">{['보고 싶어', '우리 다시 만날까?', '그때 왜 그랬어?'].map(q => <button key={q} onClick={() => say(q)}>{q}</button>)}</div>
      <div className="summon-in"><input value={v} onChange={e => setV(e.target.value)} placeholder="미련 섞인 톡을 던져봐…" onKeyDown={e => { if (e.key === 'Enter' && !e.nativeEvent.isComposing) say() }} /><button onClick={() => say()} aria-label="보내기">↑</button></div>
    </Modal>
  )
}

const STATIC: Legends = { stories: [
  { title: '6시간마다 답장, 알고 보니 딴 사람이랑은 실시간', source: '디시 연애갤 (예시)', url: '', summary: '바쁜 줄 알았던 상대가 다른 사람과는 실시간으로 대화하고 있었고, 나한테만 "바빴어 미안"이 반복됐다는 글.', match_points: ['답장 간격이 점점 벌어짐'], similarity: 0, hit: '바쁜 게 아니라 우선순위에서 밀린 것이었습니다.' },
  { title: '"나중에 연락할게"가 마지막', source: '네이트판 (예시)', url: '', summary: '"나중에 연락할게" 이후 6개월째 연락이 없지만 생일엔 짧은 축하 메시지만 왔다는 글.', match_points: ['마지막 메시지 후 장기 침묵'], similarity: 0, hit: "'나중에'는 거절의 완곡어법입니다." },
], fallback: true }

function Legend({ onClose }: { onClose: () => void }) {
  const [data, setData] = useState<Legends | null>(null)
  const [busy, setBusy] = useState(true)
  const load = (refresh = false) => { setBusy(true); api.legends(refresh).then(setData).catch(() => setData(STATIC)).finally(() => setBusy(false)) }
  useEffect(() => { load(false) }, [])
  const shown = data && data.stories.length ? data : (data ? STATIC : null)
  return (
    <Modal title="레전드 썰 매칭" onClose={onClose}>
      <p className="tiny muted" style={{ marginBottom: 16 }}>
        {busy ? '네이트판·디시·더쿠를 뒤지는 중… (10~30초 걸려)' : shown?.fallback ? `실시간 검색이 안 돼서 예시 썰을 보여줄게${data?.reason ? ` (${data.reason.slice(0, 60)})` : ''}` : `내 카톡 기준으로 비슷한 실제 썰을 찾았어${data?.cached ? ' · 아까 찾아둔 결과야' : ''}`}
      </p>
      {busy && <div className="legend-story"><div className="ls-body muted" style={{ display: 'flex', gap: 8, alignItems: 'flex-start' }}><Icon name="search" size={16} className="faint" /><span>내 데이터(이별 방식 · 상대 애착유형 · 답장 패턴 · 마지막 메시지)로 검색어를 만들어서 진짜 글을 찾는 중…</span></div></div>}
      {!busy && data && !data.fallback && (data.queries?.length || data.basis) && (
        <div className="tiny muted" style={{ marginBottom: 12, lineHeight: 1.6 }}>
          {data.basis && <div>근거: {[data.basis.attachment && `상대 ${data.basis.attachment}`, data.basis.ending].filter(Boolean).join(' · ') || '내 카톡 패턴'}</div>}
          {data.queries?.length ? <div>검색어: {data.queries.slice(0, 4).map(q => `"${q}"`).join(' · ')}</div> : null}
        </div>
      )}
      {!busy && shown?.stories.map((s, i) => (
        <div className="legend-story reveal" style={{ ['--i' as any]: i }} key={i}>
          {s.similarity > 0 && <span className="ls-match">유사도 <span className="num">{s.similarity}%</span></span>}
          <div className="ls-src">출처 · {s.source}{s.url && <> · <a href={s.url} target="_blank" rel="noreferrer" style={{ color: 'var(--rose-soft)' }}>원문 보기 ↗</a></>}</div>
          <div className="ls-body"><b style={{ color: 'var(--text)' }}>{s.title}</b><br />{s.summary}</div>
          {s.match_points?.length > 0 && <div className="tiny muted" style={{ marginTop: 8 }}>겹치는 점: {s.match_points.join(' · ')}</div>}
          {s.hit && <div className="ls-hit"><span style={{ color: 'var(--text-soft)' }}>현타 포인트 · </span>{s.hit}</div>}
        </div>
      ))}
      <div className="next-row">
        <button className="btn" style={{ flex: 1 }} disabled={busy} onClick={() => load(true)}>다시 검색</button>
        <button className="btn btn-rose" style={{ flex: 1 }} onClick={onClose}>현실 자각 완료</button>
      </div>
    </Modal>
  )
}
