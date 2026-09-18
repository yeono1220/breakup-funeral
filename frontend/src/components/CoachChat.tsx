/** 관계 코치 상담 모달. 백엔드 /chat(SSE)에 붙고, 코치가 update_context 툴로 사정을 기록하면
 *  context_updated 이벤트가 와서 onContextUpdated() → 앱이 진단서를 다시 받는다 (분석이 대화에 따라 바뀜).
 *  답변 속 [#msg_id] 영수증은 클릭하면 앞뒤 원문이 열린다. */
import { Fragment, useEffect, useRef, useState } from 'react'
import { api, type Msg } from '../api'
import { Icon } from './Icons'
import { fmtShort, Modal } from './ui'

export type CoachMsg = { role: 'user' | 'assistant'; content: string; sys?: boolean }

const OPENERS = ['우리 언제부터 식었어?', '내가 너무 매달렸나?', '걔가 먼저 연락한 적 있어?']
const HL = /<highlight>[\s\S]*?<\/highlight>/g
const RECEIPT = /\[#(\d+)\]/g
const TOOL_KO: Record<string, string> = {
  get_relationship_brief: '관계 요약', get_timeline: '주별 타임라인', get_reply_stats: '답장 시간', get_slowest_replies: '가장 늦은 답장',
  search_messages: '원문 검색', get_context: '앞뒤 원문', get_period: '그 기간 대화', get_my_style: '내 말투', get_their_style: '상대 말투',
  compare_people: '다른 사람과 비교', list_people: '사람 목록', update_context: '사정 기록',
}

function Receipts({ text, onOpen }: { text: string; onOpen: (id: number) => void }) {
  const parts = text.split(RECEIPT)   // 홀수 인덱스가 msg_id
  return <>{parts.map((p, i) => i % 2 ? <span key={i} className="rcpt" onClick={() => onOpen(+p)} title="원문 보기">[#{p}]</span> : <Fragment key={i}>{p}</Fragment>)}</>
}

export function CoachChat({ name, me, target, msgs, setMsgs, onContextUpdated, onClose }: {
  name: string; me: string; target: string; msgs: CoachMsg[]; setMsgs: (m: CoachMsg[]) => void; onContextUpdated: () => void; onClose: () => void
}) {
  const [v, setV] = useState('')
  const [busy, setBusy] = useState(false)
  const [status, setStatus] = useState<string | null>(null)
  const [receipt, setReceipt] = useState<{ msgs: Msg[]; focus: number } | null>(null)
  const box = useRef<HTMLDivElement>(null)
  useEffect(() => { box.current?.scrollTo({ top: 1e9 }) }, [msgs, busy, status])
  const openReceipt = (id: number) => api.around(id).then(r => setReceipt({ msgs: r.messages, focus: r.focus })).catch(() => {})

  async function send(text?: string) {
    const t = (text ?? v).trim(); if (!t || busy) return
    const hist: CoachMsg[] = [...msgs, { role: 'user', content: t }]
    setMsgs(hist); setV(''); setBusy(true); setStatus('데이터 보는 중')
    let acc = ''
    let updated = false
    const paint = (extra?: CoachMsg) => setMsgs([...hist, { role: 'assistant', content: acc.replace(HL, '').trimEnd() }, ...(extra ? [extra] : [])])
    try {
      const r = await api.chat(hist.filter(m => !m.sys).map(m => ({ role: m.role, content: m.content })))
      if (r.status === 400) throw new Error('서버에 네 데이터가 없어 — 서버가 쉬었다 깨면서 지워졌을 수 있어. 카톡을 다시 올려줘 (내 장례식 → 업로드)')
      if (!r.ok || !r.body) throw new Error(`서버 오류 ${r.status}`)
      const reader = r.body.getReader(); const dec = new TextDecoder(); let buf = ''
      for (;;) {
        const { value, done } = await reader.read(); if (done) break
        buf += dec.decode(value, { stream: true })
        const lines = buf.split('\n\n'); buf = lines.pop() ?? ''
        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const ev = JSON.parse(line.slice(6)) as { delta?: string; error?: string; done?: boolean; text?: string; event?: { context_updated?: unknown; tools?: string[] } }
          if (ev.delta) { acc += ev.delta; setStatus(null); paint() }
          if (ev.event?.tools?.length) { setStatus(ev.event.tools.map(n => TOOL_KO[n] ?? n).join(' · ') + ' 보는 중') }
          if (ev.event?.context_updated) { updated = true; onContextUpdated() }
          if (ev.error) throw new Error(ev.error)
          if (ev.done && ev.text) acc = ev.text
        }
      }
      paint(updated ? { role: 'assistant', content: '↑ 네가 말해준 사정을 기록했어. 진단서·향년·사인·소환술이 그걸 우선해서 다시 계산됐어.', sys: true } : undefined)
    } catch (e) {
      setMsgs([...hist, { role: 'assistant', content: '지금은 코치가 답을 못 해. ' + String(e instanceof Error ? e.message : e).slice(0, 120), sys: true }])
    } finally { setBusy(false); setStatus(null) }
  }

  return (
    <Modal title="관계 코치 상담" onClose={onClose} bodyClass="summon-body coach-body">
      <p className="tiny muted" style={{ marginBottom: 12 }}>카톡 데이터를 보는 코치야 · 숫자엔 <span className="num">[#영수증]</span>이 붙어(누르면 원문) · 사정을 말해주면 진단서가 그걸 우선해서 바뀌어</p>
      <div className="summon-chat" ref={box}>
        {msgs.length === 0 && <div className="rp-msg them">{name}이랑 어떻게 된 건지, 데이터에 없는 사정부터 말해줘도 되고 그냥 물어봐도 돼.</div>}
        {msgs.map((m, i) => (
          m.sys
            ? <div key={i} style={{ fontSize: 11, color: 'var(--rose-soft)', textAlign: 'center', margin: '4px 0 12px' }}>{m.content}</div>
            : <div key={i} className={'rp-msg ' + (m.role === 'user' ? 'me' : 'them')}>{m.role === 'assistant' ? <Receipts text={m.content} onOpen={openReceipt} /> : m.content}{!m.content && busy ? '…' : ''}</div>
        ))}
        {busy && status && <div className="rp-msg them coach-status"><span className="live-dot" />…{status}</div>}
      </div>
      {receipt && (
        <div className="receipt" style={{ maxHeight: 180, marginTop: 8 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}><span className="tiny muted" style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}><Icon name="receipt" size={14} />영수증 · 원문 [#{receipt.focus}]</span><button className="btn btn-sm" onClick={() => setReceipt(null)}>닫기</button></div>
          {receipt.msgs.map(m => (
            <div key={m.id} className={'rc-msg' + (m.id === receipt.focus ? ' focus' : '')}>
              <div className={'who' + (m.sender === me ? ' me' : '')}>{m.sender === target ? name : m.sender === me ? '나' : m.sender}<br />{fmtShort(m.ts)} {m.ts.slice(11, 16)}</div>
              <div>{m.text}</div>
            </div>
          ))}
        </div>
      )}
      {msgs.length === 0 && <div className="summon-quick">{OPENERS.map(q => <button key={q} onClick={() => send(q)}>{q}</button>)}</div>}
      <div className="summon-in"><input value={v} onChange={e => setV(e.target.value)} placeholder="물어보거나, 사정을 말해줘…" onKeyDown={e => { if (e.key === 'Enter' && !e.nativeEvent.isComposing) send() }} disabled={busy} /><button onClick={() => send()} aria-label="보내기" disabled={busy}>↑</button></div>
    </Modal>
  )
}
