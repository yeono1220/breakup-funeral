import { useEffect, useMemo, useState } from 'react'
import { api, type Msg, type Relationship } from '../api'
import { MemorialChar } from '../components/Char'
import { fmtDate, fmtMin, fmtShort, fmtTime } from '../components/ui'

const ATTACH_LABEL: Record<string, string> = { secure: '안정형', anxious: '불안형', avoidant: '회피형', fearful: '혼란형' }

export function displayName(name: string, alias: boolean) {
  return alias && name.length > 1 ? name[0] + '○'.repeat(Math.min(2, name.length - 1)) : name
}

export function Diagnosis({ data, persona, alias, onNext }: {
  data: Relationship; persona: { mbti: string | null; attachment: string | null }; alias: boolean; onNext: () => void
}) {
  const t = data.target
  const name = displayName(t, alias)
  const [receipt, setReceipt] = useState<{ msgs: Msg[]; focus: number } | null>(null)
  const [drawn, setDrawn] = useState(false)
  useEffect(() => { const id = setTimeout(() => setDrawn(true), 250); return () => clearTimeout(id) }, [])

  const dead = data.stages.lens === 'breakup'
  const last = data.last_message
  const lastDate = data.range[1]
  const days = Math.max(1, Math.round((new Date(data.range[1]).getTime() - new Date(data.range[0]).getTime()) / 86400000))
  const weeks = data.weekly
  const valid = weeks.filter(w => w.temp != null) as (typeof weeks[number] & { temp: number })[]
  const peak = valid.reduce((a, b) => (b.temp > a.temp ? b : a), valid[0])
  const lastValid = valid[valid.length - 1]

  // ---- 사망 사유 (규칙 기반)
  const reason = useMemo(() => {
    if (data.waiting) return `${data.waiting.age_hours}시간 읽씹 (평소 ${fmtMin(data.waiting.usual_reply_min)} 안에 답하던 사이)`
    const seg = data.stages.segments[data.stages.segments.length - 1]
    if (seg?.stage === 'cutoff') return `${seg.weeks}주째 대화 단절`
    if (data.temperature.top_factor) return `${data.temperature.top_factor.label} ${data.temperature.top_factor.delta_contrib > 0 ? '상승' : '하락'} 중 (온도 ${data.temperature.temp}°)`
    return `온도 ${data.temperature.temp ?? '–'}°`
  }, [data])

  // ---- 사망 원인 % (선톡 / 읽씹 / 대화량)
  const causes = useMemo(() => {
    const starts = data.symmetry.bars.find(b => b.key === 'starts')?.share ?? 0.5
    const comp = data.temperature.components
    const raw = [
      { label: '유저의 과다 선톡', v: Math.max(0, starts - 0.5) * 2, color: 'linear-gradient(90deg,#D96A5E,#E88B80)' },
      { label: '상대의 읽씹 (응답 둔화)', v: comp.R ? 1 - comp.R.value : 0.3, color: 'linear-gradient(90deg,#7C8894,#AEB9C4)' },
      { label: '대화량 급감', v: comp.F ? 1 - comp.F.value : 0.2, color: 'linear-gradient(90deg,#8B7BB8,#B4A7D6)' },
    ]
    const sum = raw.reduce((a, b) => a + b.v, 0) || 1
    return raw.map(r => ({ ...r, pct: Math.round((r.v / sum) * 100) }))
  }, [data])

  // ---- 낙하 곡선 path
  const path = useMemo(() => {
    if (!valid.length) return ''
    const n = weeks.length
    const pts = weeks.map((w, i) => (w.temp == null ? null : [ (i / Math.max(1, n - 1)) * 400, 200 - (w.temp / 100) * 180 ] as [number, number]))
    let d = '', started = false
    pts.forEach(p => { if (!p) return; d += (started ? ' L' : 'M') + p[0].toFixed(1) + ' ' + p[1].toFixed(1); started = true })
    return d
  }, [weeks, valid.length])
  const xOf = (ws: string) => (weeks.findIndex(w => w.week_start === ws) / Math.max(1, weeks.length - 1)) * 100
  const yOf = (temp: number) => ((200 - (temp / 100) * 180) / 210) * 100

  const openReceipt = (id: number) => api.around(id).then(r => setReceipt({ msgs: r.messages, focus: r.focus }))

  // ---- 핵심 사건
  const events = useMemo(() => {
    const out = data.events.map((e, i) => {
      const w = weeks.find(x => x.week_start === e.week_start)
      const f = e.top_factor?.key
      let text = `온도 ${e.delta > 0 ? '+' : ''}${e.delta}° · 주요인 ${e.top_factor?.label ?? '–'}`
      if (f === 'R' && w?.their_med != null) text = `상대 답장 간격이 ${fmtMin(w.their_med)}으로 ${e.direction === 'down' ? '늘어난' : '줄어든'} 시점`
      else if (f === 'F' && w) text = `대화가 하루 ${w.per_day}개로 ${e.direction === 'down' ? '줄어든' : '늘어난'} 시점`
      else if (f === 'I' && w?.my_start_share != null) text = `내가 먼저 말 건 비율 ${Math.round(w.my_start_share * 100)}%`
      const firstDrop = e.direction === 'down' && data.events.findIndex(x => x.direction === 'down') === i
      return { date: e.week_start, up: e.direction === 'up', text, quote: e.evidence_preview[0]?.text as string | undefined, id: e.evidence_ids[0] as number | undefined,
        tag: e.direction === 'up' ? `온도 +${e.delta}° 🌱` : firstDrop ? '마음 정리 시작된 Point' : `온도 ${e.delta}° 📉` }
    })
    if (last) out.push({ date: last.ts.slice(0, 10), up: false, text: `마지막 ${last.sender === t ? '한마디' : '내 메시지'}: “${last.text.slice(0, 40)}”`, quote: undefined as string | undefined, id: last.id as number | undefined,
      tag: dead ? '관계 사망 판정 💀' : data.waiting ? `${data.waiting.age_hours}시간째 답 없음` : '현재' })
    return out
  }, [data, weeks, last, t, dead])

  return (
    <section className="page">
      <div className="wrap">
        <div className="steps-bar">
          <span className="step-pill on">① 사망 진단서</span><span className="step-arrow">→</span>
          <span className="step-pill">② 추모하기</span><span className="step-arrow">→</span>
          <span className="step-pill">③ 공동묘지 안치</span>
        </div>
        <div className="section-gap">
          <div className="memorial">
            {!dead && <div className="alive-banner">⚠️ 아직 숨이 붙어 있어요 — 현재 단계 <b>{data.stages.current_label}</b>, 온도 {data.temperature.temp ?? '–'}°. 장례는 이르지만 부검 결과는 볼 수 있어요.</div>}
            <div className="portrait-frame"><div className="portrait-ribbon" /><MemorialChar size={150} /></div>
            <div className="mem-name">故 {name}</div>
            <div className="mem-target">· 대상: {persona.attachment ? ATTACH_LABEL[persona.attachment] + ' ' : ''}{name}{persona.mbti || persona.attachment ? ` (${[persona.mbti, persona.attachment && ATTACH_LABEL[persona.attachment]].filter(Boolean).join('·')})` : ''} · 함께한 {data.n_messages.toLocaleString()}마디</div>
            <div className="mem-death">
              {fmtDate(lastDate)} {last && <span className="q" onClick={() => openReceipt(last.id)} title="원문 보기">“{last.text.slice(0, 40)}”</span>}<br />
              {last ? '를 끝으로 숨을 거둠' : '마지막 대화'}<br />
              <span className="tiny faint">사유: {reason}</span>
            </div>
            <div className="cert">
              <div className="cert-t">🧾 사망 원인 진단서</div>
              {causes.map(c => (
                <div className="cert-row" key={c.label}>
                  <span className="cr-lbl">{c.label}</span>
                  <div className="cr-track"><div className="cr-fill" style={{ width: drawn ? `${c.pct}%` : 0, background: c.color }} /></div>
                  <span className="cr-val">{c.pct}%</span>
                </div>
              ))}
              <div className="cert-note">선톡 = 대화 시작 중 내가 건 비율({Math.round((data.symmetry.bars.find(b => b.key === 'starts')?.share ?? 0.5) * 100)}%), 읽씹 = 최근 14일 상대 응답성, 대화량 = 평시 대비 최근 빈도. 전부 코드가 셈. 상대 마음이 아니라 관계의 모양.</div>
            </div>
            {receipt && (
              <div className="receipt">
                <div className="row" style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}><span className="tiny muted">🧾 영수증 · 원문</span><button className="btn btn-sm" onClick={() => setReceipt(null)}>닫기</button></div>
                {receipt.msgs.map(m => (
                  <div key={m.id} className={'rc-msg' + (m.id === receipt.focus ? ' focus' : '')}>
                    <div className={'who' + (m.sender === data.me ? ' me' : '')}>{m.sender === t ? name : m.sender}<br />{fmtShort(m.ts)} {m.ts.slice(11, 16)}</div>
                    <div>{m.text}</div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="card">
            <h3>📉 애정도 {dead ? '수직 낙하' : '추이'}</h3>
            <p className="sub">{peak ? <>최고점 <span className="rose-tag">{peak.temp}°</span> ({fmtShort(peak.week_start)} 주) → 지금 <span className="rose-tag">{lastValid?.temp ?? '–'}°</span></> : '표본이 적어요'}</p>
            <div className="freefall">
              <svg className="ff-svg" viewBox="0 0 400 210" preserveAspectRatio="none">
                {[40, 100, 160].map(y => <line key={y} x1="0" y1={y} x2="400" y2={y} stroke="#3B4252" strokeWidth="1" strokeDasharray="4" />)}
                <path d={path} fill="none" stroke="#D96A5E" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"
                  strokeDasharray="1200" strokeDashoffset={drawn ? 0 : 1200} style={{ transition: 'stroke-dashoffset 1.6s ease-out' }} />
                {peak && <circle cx={(xOf(peak.week_start) / 100) * 400} cy={200 - (peak.temp / 100) * 180} r="4" fill="#8FB8A0" />}
                {lastValid && <circle cx={(xOf(lastValid.week_start) / 100) * 400} cy={200 - (lastValid.temp / 100) * 180} r="5" fill="#D96A5E" />}
              </svg>
              {peak && <div className="ff-annot ok" style={{ left: `min(78%, ${xOf(peak.week_start)}%)`, top: `${Math.max(2, yOf(peak.temp) - 14)}%` }}>💚 골든타임 {peak.temp}°</div>}
              {lastValid && <div className="ff-annot" style={{ right: '2%', top: `${Math.min(80, yOf(lastValid.temp) + 4)}%` }}>{dead ? '💀' : '🩺'} {lastValid.temp}°</div>}
            </div>
            <div className="ff-legend"><span>💚 최고점 {peak?.temp ?? '–'}°</span><span>{dead ? '💀 사망' : '🩺 마지막'} {fmtShort(lastDate)}</span><span>⏳ 향년 {days}일</span><span>💬 {data.n_messages.toLocaleString()}마디</span></div>
            <div className="ff-stages">{data.stages.segments.map((s, i) => <span key={i} className="ff-stage">{s.label} {fmtShort(s.start)}~{fmtShort(s.end)}</span>)}</div>
          </div>

          <div className="card">
            <h3>🔍 데이터 피셜 핵심 사건</h3>
            <p className="sub">주간 온도가 10° 이상 움직인 순간들. 눌러서 그 주 원문 보기.</p>
            {events.length === 0 && <div className="muted">큰 사건 없이 잔잔했어요.</div>}
            {events.map((e, i) => (
              <div className="event-item" key={i} onClick={() => e.id && openReceipt(e.id)}>
                <div className="event-date">{e.date.slice(0, 4)}<br />{fmtShort(e.date)}</div>
                <div className={'event-dot' + (e.up ? ' up' : '')} />
                <div className="event-body">
                  <div className="eb-t">{e.text}</div>
                  {e.quote && <div className="eb-q">“{e.quote}”</div>}
                  <div className={'eb-tag' + (e.up ? ' up' : '')}>{e.tag}</div>
                </div>
              </div>
            ))}
          </div>

          <div className="card">
            <h3>🧪 부검 소견 · 썸 신호</h3>
            <p className="sub">{data.signals.title} — {data.signals.desc}</p>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
              <SignalCol who="나" score={data.signals.me.score} parts={data.signals.me.parts} color="#D96A5E" />
              <SignalCol who={name} score={data.signals.them.score} parts={data.signals.them.parts} color="#AEB9C4" />
            </div>
            <ul style={{ marginTop: 12, paddingLeft: 18, fontSize: 13 }} className="muted">{data.signals.facts.map((f, i) => <li key={i}>{f.replace(t, name)}</li>)}</ul>
          </div>

          <button className="btn btn-rose btn-block" style={{ fontSize: 16, padding: 16 }} onClick={onNext}>{dead ? '이제 추모하러 가기 →' : '그래도 미리 보내볼래요 →'}</button>
          <div className="tiny faint" style={{ textAlign: 'center' }}>마지막 대화 {fmtTime(lastDate)} · 온도·신호는 전부 코드 계산, 상대 마음 판정 아님</div>
        </div>
      </div>
    </section>
  )
}

function SignalCol({ who, score, parts, color }: { who: string; score: number | null; parts: { label: string; score: number }[]; color: string }) {
  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}><span className="tiny muted">{who} 쪽 신호</span><span className="pen" style={{ fontSize: 28, color }}>{score ?? '–'}</span></div>
      {parts.map(p => (
        <div key={p.label} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, marginTop: 4 }}>
          <span className="muted" style={{ width: 70 }}>{p.label}</span>
          <div style={{ flex: 1, height: 8, borderRadius: 4, background: '#20242C' }}><div style={{ width: `${p.score}%`, height: '100%', borderRadius: 4, background: color }} /></div>
          <span style={{ width: 26, textAlign: 'right' }}>{p.score}</span>
        </div>
      ))}
    </div>
  )
}
