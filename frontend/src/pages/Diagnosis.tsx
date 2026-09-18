import { useEffect, useMemo, useState, type CSSProperties } from 'react'
const useS = useState
import { api, type Msg, type Relationship } from '../api'
import { Portrait } from '../components/Portrait'
import type { Persona } from '../api'
import { fmtDate, fmtMin, fmtShort, fmtTime, smoothPath, useCountUp } from '../components/ui'
import { Icon } from '../components/Icons'
import { RitualBar } from '../components/RitualBar'

const ATTACH_LABEL: Record<string, string> = { secure: '안정형', anxious: '불안형', avoidant: '회피형', fearful: '혼란형' }

export function displayName(name: string, alias: boolean) {
  return alias && name.length > 1 ? name[0] + '○'.repeat(Math.min(2, name.length - 1)) : name
}

// 제목 왼쪽 14px 아이콘용 — .card h3 / .cert-t 에 inline 으로만 얹는다
const H_ROW: CSSProperties = { display: 'flex', alignItems: 'center', gap: 8 }
const order = (n: number) => ({ ['--i' as string]: n } as CSSProperties)

export function Diagnosis({ data, persona, alias, verdict, onNext, onEditContext, onCoach }: {
  data: Relationship; persona: Persona; alias: boolean; verdict?: string | null; onNext: () => void; onEditContext?: () => void; onCoach?: () => void
}) {
  const t = data.target
  const name = displayName(t, alias)
  const [receipt, setReceipt] = useState<{ msgs: Msg[]; focus: number } | null>(null)
  const [drawn, setDrawn] = useState(false)
  useEffect(() => { const id = setTimeout(() => setDrawn(true), 250); return () => clearTimeout(id) }, [])

  const uc = data.user_context
  const dead = data.stages.lens === 'breakup'
  const last = data.last_message
  const lastDate = uc?.ended_at ? uc.ended_at + 'T00:00:00' : data.range[1]
  const [startedAt, setStartedAt] = useS<string | null>(uc?.started_at ?? null)
  const [editStart, setEditStart] = useS(false)
  const [autopsy, setAutopsy] = useS(false)   // 차트·사건·신호는 접어두고 판결부터
  useEffect(() => { setStartedAt(uc?.started_at ?? null) }, [uc?.started_at])   // 코치 상담으로 시작일이 바뀌면 따라간다
  const startIso = startedAt ? startedAt + 'T00:00:00' : (uc?.suggested_start ? uc.suggested_start + 'T00:00:00' : data.range[0])
  const days = Math.max(1, Math.round((new Date(lastDate).getTime() - new Date(startIso).getTime()) / 86400000))
  const knownBefore = Math.round((new Date(startIso).getTime() - new Date(data.range[0]).getTime()) / 86400000)
  const saveStart = async (v: string) => { setStartedAt(v || null); setEditStart(false); await api.setPersona({ person: t, mbti: persona.mbti, attachment: persona.attachment, ending: persona.ending ?? null, context: persona.context ?? null, ended_at: persona.ended_at ?? null, started_at: v || null, alias }) }
  // 차트 창: 관계 시작일(월요일 기준)부터. 그 전 알고 지낸 기간은 x축에서 제외 (짧은 관계가 오른쪽에 압축되는 문제)
  const startWeek = (() => { const d = new Date(startIso); d.setHours(0, 0, 0, 0); d.setDate(d.getDate() - ((d.getDay() + 6) % 7)); return d.toISOString().slice(0, 10) })()
  const weeksAll = data.weekly
  const weeksFrom = weeksAll.filter(w => w.week_start >= startWeek)
  const weeks = weeksFrom.length >= 4 ? weeksFrom : weeksAll
  const valid = weeks.filter(w => w.temp != null) as (typeof weeks[number] & { temp: number })[]
  const gaps = weeks.map((w, i) => (w.temp == null ? i : -1)).filter(i => i >= 0)
  const peak = valid.reduce((a, b) => (b.temp > a.temp ? b : a), valid[0])
  const lastValid = valid[valid.length - 1]

  // ---- 카운트업 (표현만: 계산값은 위 그대로)
  const daysShown = useCountUp(days)
  const peakShown = useCountUp(peak?.temp ?? 0)
  const lastShown = useCountUp(lastValid?.temp ?? 0)

  // ---- 사망 사유 (규칙 기반)
  const reason = useMemo(() => {
    if (uc?.ending_label) return `${uc.ending_label}${uc.context ? ` — ${uc.context.slice(0, 60)}${uc.context.length > 60 ? '…' : ''}` : ''}${data.waiting ? ` · 마지막 메시지에 ${data.waiting.age_hours}시간째 무응답` : ''}`
    if (data.waiting) return `${data.waiting.age_hours}시간 읽씹 (평소 ${fmtMin(data.waiting.usual_reply_min)} 안에 답하던 사이)`
    const seg = data.stages.segments[data.stages.segments.length - 1]
    if (seg?.stage === 'cutoff') return `${seg.weeks}주째 대화 단절`
    if (data.temperature.top_factor) return `${data.temperature.top_factor.label} ${data.temperature.top_factor.delta_contrib > 0 ? '상승' : '하락'} 중 (온도 ${data.temperature.temp}°)`
    return `온도 ${data.temperature.temp ?? '–'}°`
  }, [data, uc])

  // ---- 사망 원인 (백엔드: 전성기 4주 vs 말기 4주 비교) — 막대는 단색
  const COLORS: Record<string, string> = {
    their_reply: 'var(--ghost-line)', my_reply: 'var(--rose)', volume: '#8B7BB8',
    my_start: '#E9998E', their_effort: '#C9B268', silence: 'var(--ink)',
  }
  const causes = (data.causes?.causes ?? []).map(c => ({ ...c, color: COLORS[c.key] ?? 'var(--rose)' }))

  // ---- 낙하 곡선 path (Catmull-Rom → cubic bezier)
  const path = useMemo(() => {
    if (!valid.length) return ''
    const n = weeks.length
    // 빈 주는 건너뛰고 유효한 점만 이어서 선이 끊기지 않게 (빈 주는 옅은 띠로 따로 표시)
    const pts = weeks.map((w, i) => (w.temp == null ? null : [ (i / Math.max(1, n - 1)) * 400, 200 - (w.temp / 100) * 180 ] as [number, number])).filter((q): q is [number, number] => !!q)
    return smoothPath(pts, 0.5, [8, 200])
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
      else if (f === 'C') text = e.direction === 'down' ? '대화 없는 날이 늘어난 시점' : '다시 매일 연락하던 시점'
      else if (f === 'L') text = e.direction === 'down' ? '상대 답장이 짧아진 시점' : '상대 답장이 길어진 시점'
      const firstDrop = e.direction === 'down' && data.events.findIndex(x => x.direction === 'down') === i
      return { date: e.week_start, up: e.direction === 'up', text, quote: e.evidence_preview[0]?.text as string | undefined, id: e.evidence_ids[0] as number | undefined,
        tag: e.direction === 'up' ? `온도 +${e.delta}°` : firstDrop ? '마음 정리가 시작된 지점' : `온도 ${e.delta}°` }
    })
    if (last) out.push({ date: last.ts.slice(0, 10), up: false, text: `마지막 ${last.sender === t ? '한마디' : '내 메시지'}: “${last.text.slice(0, 40)}”`, quote: undefined as string | undefined, id: last.id as number | undefined,
      tag: dead ? '관계 사망 판정' : data.waiting ? `${data.waiting.age_hours}시간째 답 없음` : '현재' })
    return out
  }, [data, weeks, last, t, dead])

  const dashStyle: CSSProperties = { transition: 'stroke-dashoffset calc(var(--dur-4) * 1.8) var(--ease-out)' }

  return (
    <section className="page">
      <div className="wrap">
        <RitualBar current={0} />
        <div className="section-gap">
          {/* 판결: 처음 보는 사람이 3초 안에 "그래서 결론이 뭔데"를 잡게 */}
          <div className="verdict fade-in">
            <div className="tiny muted">판결</div>
            <div className="verdict-title">{verdict ?? (last && last.text.length >= 4 && !/^(사진|이모티콘|동영상|파일:|https?:)/.test(last.text) ? `“${last.text.slice(0, 30)}”` : `${name}과의 ${days}일`)}</div>
            <div className="verdict-line">
              {causes[0] && <span>사인 1위 <b>{causes[0].label}</b> <span className="num">{causes[0].pct}%</span></span>}
              <span>향년 <b className="num">{days}</b>일</span>
              <span>{uc?.ending_label ? <b>{uc.ending_label}</b> : <>지금 <b>{data.stages.current_label}</b></>}</span>
            </div>
          </div>
          <div className="memorial fade-in">
            {!dead && <div className="alive-banner" style={{ textAlign: 'left' }}>기록상으론 아직 숨이 붙어 있어. 지금 단계는 <b>{data.stages.current_label}</b>, 온도는 {data.temperature.temp ?? '–'}°. 이미 끝난 사이라면 <a style={{ textDecoration: 'underline', cursor: 'pointer' }} onClick={onEditContext}>어떻게 끝났는지 알려줘</a>. 그쪽을 우선할게.</div>}
            {uc?.overrides_stage && <div className="ctx-banner" style={{ textAlign: 'left' }}>네가 말해준 대로 봤어: <b>{uc.ending_label}</b>.{data.stages.data_label ? ` 기록만 보면 '${data.stages.data_label}'이야. 회피형처럼 원래 연락이 뜸하면 이렇게 보이기도 해.` : ''}</div>}
            {uc?.context && (
              <div className="told-card" style={{ textAlign: 'left' }}>
                <div className="tiny muted" style={{ marginBottom: 4 }}>네가 말해준 사정 · 진단서는 이걸 우선해
                  {(uc.started_at || uc.ended_at) && <span className="faint"> · {uc.started_at ?? '?'} ~ {uc.ended_at ?? '?'}</span>}</div>
                {uc.context.split('\n').filter(Boolean).map((l, i) => <div key={i} style={{ fontSize: 13, lineHeight: 1.5 }}>· {l}</div>)}
                {onCoach && <a className="tiny" style={{ cursor: 'pointer', textDecoration: 'underline dotted', color: 'var(--rose-deep)' }} onClick={onCoach}>더 말해주기 →</a>}
              </div>
            )}
            <div className="portrait-frame"><div className="portrait-ribbon" /><Portrait src={persona.portrait} size={150} /></div>
            <div className="mem-name">故 {name}</div>
            <div className="mem-target">· 대상: {persona.attachment ? ATTACH_LABEL[persona.attachment] + ' ' : ''}{name}{persona.mbti || persona.attachment ? ` (${[persona.mbti, persona.attachment && ATTACH_LABEL[persona.attachment]].filter(Boolean).join('·')})` : ''} · 함께한 {data.n_messages.toLocaleString()}마디</div>
            <div className="mem-death">
              {fmtDate(lastDate)} {last && <span className="q" onClick={() => openReceipt(last.id)} title="원문 보기">“{last.text.slice(0, 40)}”</span>}<br />
              {last ? (uc?.ended_at ? '를 남기고 떠남' : '를 끝으로 숨을 거둠') : '마지막 대화'}<br />
              <span className="tiny faint">사유: {reason}</span>
            </div>
            <div className="cert">
              <div className="cert-t" style={H_ROW}><Icon name="receipt" size={14} />사망 원인 진단서</div>
              {data.causes?.note && <div className="ctx-banner" style={{ marginBottom: 12 }}>{data.causes.note}</div>}
              {causes.map(c => (
                <div key={c.key} style={{ marginBottom: 12 }}>
                  <div className="cert-row" style={{ marginBottom: 4 }}>
                    <span className="cr-lbl">{c.label}</span>
                    <div className="cr-track"><div className="cr-fill" style={{ ['--p' as string]: drawn ? c.pct / 100 : 0, background: c.color } as CSSProperties} /></div>
                    <span className="cr-val num">{c.pct}%</span>
                  </div>
                  <div className="tiny faint" style={{ paddingLeft: 2 }}>{c.evidence}</div>
                </div>
              ))}
              {causes.length === 0 && <div className="muted tiny">대화가 너무 적어서 원인까진 못 짚었어.</div>}
              {data.causes?.peak && data.causes.last && (
                <div className="cert-note">
                  가장 뜨거웠던 {fmtShort(data.causes.peak.from)}~{fmtShort(data.causes.peak.to)}엔 하루 {data.causes.peak.per_day}마디였어. 마지막 {fmtShort(data.causes.last.from)}~{fmtShort(data.causes.last.to)}엔 하루 {data.causes.last.per_day}마디.
                  {data.causes.silence_days >= 3 ? ` 그 뒤로 ${data.causes.silence_days}일은 조용했어.` : ''}
                  {' '}상대 마음이 아니라, 대화의 모양을 본 거야.
                </div>
              )}
            </div>
            {receipt && (
              <div className="receipt">
                <div className="row" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}><span className="tiny muted" style={H_ROW}><Icon name="receipt" size={14} />영수증 · 원문</span><button className="btn btn-sm" onClick={() => setReceipt(null)}>닫기</button></div>
                {receipt.msgs.map(m => (
                  <div key={m.id} className={'rc-msg' + (m.id === receipt.focus ? ' focus' : '')}>
                    <div className={'who' + (m.sender === data.me ? ' me' : '')}>{m.sender === t ? name : m.sender}<br />{fmtShort(m.ts)} {m.ts.slice(11, 16)}</div>
                    <div>{m.text}</div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {!autopsy && <button className="btn btn-block reveal" style={order(0)} onClick={() => setAutopsy(true)}>부검 기록 펼치기 · 애정도 추이 / 핵심 사건 / 이별 신호</button>}
          {autopsy && <>
          <div className="card reveal" style={order(0)}>
            <h3 style={H_ROW}><Icon name="trend-down" size={14} />애정도 {dead ? '수직 낙하' : '추이'}</h3>
            <p className="sub">{peak ? <>최고점 <span className="rose-tag num">{peakShown}°</span> ({fmtShort(peak.week_start)} 주) → 지금 <span className="rose-tag num">{lastValid ? lastShown : '–'}°</span></> : '대화가 너무 적어'}</p>
            <div className="freefall">
              <svg className="ff-svg" viewBox="0 0 400 210" preserveAspectRatio="none">
                {gaps.map(i => { const n = Math.max(1, weeks.length - 1); const w = 400 / n; return <rect key={'g' + i} x={(i / n) * 400 - w / 2} y="8" width={w} height="192" fill="var(--text-faint)" opacity=".07" /> })}
                {/* 격자: 중앙 50° 한 줄만 */}
                <line x1="0" y1="110" x2="400" y2="110" stroke="var(--line)" strokeWidth="1" strokeDasharray="4 5" />
                {/* 펜 자국: 굵고 옅은 밑선 + 얇고 진한 윗선 */}
                <path d={path} fill="none" stroke="var(--rose-deep)" strokeOpacity=".2" strokeWidth="6" strokeLinecap="round" strokeLinejoin="round"
                  strokeDasharray="1200" strokeDashoffset={drawn ? 0 : 1200} style={dashStyle} />
                <path d={path} fill="none" stroke="var(--rose-deep)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
                  strokeDasharray="1200" strokeDashoffset={drawn ? 0 : 1200} style={dashStyle} />
                {peak && <ellipse cx={(xOf(peak.week_start) / 100) * 400} cy={200 - (peak.temp / 100) * 180} rx="4.3" ry="3.8" fill="var(--ok)" />}
                {lastValid && <ellipse cx={(xOf(lastValid.week_start) / 100) * 400} cy={200 - (lastValid.temp / 100) * 180} rx="5.2" ry="4.7" fill="var(--rose-deep)" />}
              </svg>
              {peak && <div className="ff-annot ok" style={{ left: `min(78%, ${xOf(peak.week_start)}%)`, top: `${Math.max(2, yOf(peak.temp) - 14)}%` }}>골든타임 {peak.temp}°</div>}
              {lastValid && <div className="ff-annot" style={{ right: '2%', top: `${Math.min(80, yOf(lastValid.temp) + 4)}%` }}>{dead ? '사망' : '지금'} {lastValid.temp}°</div>}
            </div>
            <div className="ff-legend" style={{ justifyContent: 'flex-start' }}>
              <span>최고점 <span className="num">{peak?.temp ?? '–'}°</span></span>
              <span>{dead ? '사망' : '마지막'} {fmtShort(lastDate)}</span>
              <span title="썸/관계 시작일부터 셌어" style={H_ROW}><Icon name="clock" size={14} />향년 <span className="num">{daysShown}</span>일 {knownBefore > 7 && <span className="faint">(카톡은 {knownBefore}일 전부터)</span>} <a style={{ cursor: 'pointer', textDecoration: 'underline dotted' }} onClick={() => setEditStart(v => !v)}>시작일</a></span>
              <span style={H_ROW}><Icon name="comment" size={14} />{data.n_messages.toLocaleString()}마디</span>
            </div>
            {editStart && (
              <div className="row" style={{ display: 'flex', gap: 8, alignItems: 'center', marginTop: 12, flexWrap: 'wrap' }}>
                <span className="tiny muted">썸/관계 시작일</span>
                <input className="date" type="date" defaultValue={startedAt ?? uc?.suggested_start ?? data.range[0].slice(0, 10)} onChange={e => saveStart(e.target.value)} />
                {uc?.suggested_start && <button className="btn btn-sm" onClick={() => saveStart(uc.suggested_start!)}>추천: {fmtShort(uc.suggested_start)}</button>}
                <button className="btn btn-sm" onClick={() => saveStart('')}>첫 카톡부터</button>
              </div>
            )}
            <div className="ff-stages" style={{ justifyContent: 'flex-start' }}>{data.stages.segments.filter(sg => sg.end >= startWeek).map((s, i) => <span key={i} className="ff-stage">{s.label} {fmtShort(s.start)}~{fmtShort(s.end)}</span>)}</div>
          </div>

          <div className="card reveal" style={order(1)}>
            <h3 style={H_ROW}><Icon name="search" size={14} />데이터 피셜 핵심 사건</h3>
            <p className="sub">온도가 크게 움직인 주들이야. 누르면 그 주 대화가 열려.</p>
            {events.length === 0 && <div className="muted">큰 사건 없이 잔잔했어.</div>}
            {events.length > 0 && (
              <div style={{ position: 'relative' }}>
                {/* 타임라인 세로선: 날짜(72) + gap(12) + 점 중심(6) */}
                <div aria-hidden style={{ position: 'absolute', left: 89.5, top: 16, bottom: 16, width: 1, background: 'var(--line)' }} />
                {events.map((e, i) => (
                  <div className="event-item" key={i} onClick={() => e.id && openReceipt(e.id)}>
                    <div className="event-date">{e.date.slice(0, 4)}<br />{fmtShort(e.date)}</div>
                    <div className={'event-dot' + (e.up ? ' up' : '')} style={{ position: 'relative' }} />
                    <div className="event-body">
                      <div className="eb-t">{e.text}</div>
                      {e.quote && <div className="eb-q">“{e.quote}”</div>}
                      <div className={'eb-tag' + (e.up ? ' up' : '')}>{e.tag}</div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="card reveal" style={order(2)}>
            <h3 style={H_ROW}><Icon name="flask" size={14} />부검 소견 · {dead ? '이별 신호' : '썸 신호'}</h3>
            <p className="sub"><b style={{ color: 'var(--text)' }}>{data.signals.title}</b> — {data.signals.desc}</p>
            <div className="tiny faint" style={{ marginBottom: 12 }}>{data.signals.mode === 'relative' ? '둘 사이를 나란히 놓고 본 거야' : '평소 내 다른 대화들과 비교했어'}</div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
              <SignalCol who="나" score={data.signals.me.score} parts={data.signals.me.parts} color="var(--rose-deep)" />
              <SignalCol who={name} score={data.signals.them.score} parts={data.signals.them.parts} color="var(--ghost-line)" />
            </div>
            <ul style={{ marginTop: 12, paddingLeft: 18, fontSize: 13, lineHeight: 1.6 }} className="muted">{data.signals.facts.map((f, i) => <li key={i}>{f.replace(t, name)}</li>)}</ul>
          </div>

          </>}
          <div className="reveal" style={order(3)}>
            <button className="btn btn-rose btn-block" style={{ fontSize: 16, padding: 16 }} onClick={onNext}>{dead ? '이제 추모하러 가기 →' : '그래도 미리 보내볼래 →'}</button>
            {onCoach && <button className="btn btn-block" style={{ marginTop: 10 }} onClick={onCoach}>코치와 상담하기 · 사정을 말하면 진단서가 바뀌어</button>}
            <div className="tiny faint" style={{ textAlign: 'center', marginTop: 12 }}>마지막 대화 {fmtTime(lastDate)}</div>
          </div>
        </div>
      </div>
    </section>
  )
}

function SignalCol({ who, score, parts, color, empty }: { who: string; score: number | null; parts: { label: string; score: number }[]; color: string; empty?: string }) {
  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}><span className="tiny muted">{who} 쪽 신호</span><span className="num" style={{ fontSize: 24, color }}>{score ?? '–'}</span></div>
      {empty && <div className="tiny faint">{empty}</div>}
      {parts.map(p => (
        <div key={p.label} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, marginTop: 8 }}>
          <span className="muted" style={{ width: 70 }}>{p.label}</span>
          <div style={{ flex: 1, height: 8, borderRadius: 'var(--r-pill)', background: 'var(--panel3)', overflow: 'hidden' }}><div style={{ width: '100%', height: '100%', borderRadius: 'var(--r-pill)', background: color, transformOrigin: 'left', transform: `scaleX(${p.score / 100})` }} /></div>
          <span className="num" style={{ width: 26, textAlign: 'right' }}>{p.score}</span>
        </div>
      ))}
    </div>
  )
}
