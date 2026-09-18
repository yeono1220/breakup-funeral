import { useEffect, useState } from 'react'
import { api, type Candidate, type Sender } from '../api'
import { Char } from '../components/Char'
import { useToast } from '../components/ui'

type Step = 'drop' | 'me' | 'target' | 'persona'
const MBTI = ['ISTJ', 'ISFJ', 'INFJ', 'INTJ', 'ISTP', 'ISFP', 'INFP', 'INTP', 'ESTP', 'ESFP', 'ENFP', 'ENTP', 'ESTJ', 'ESFJ', 'ENFJ', 'ENTJ']
const ATTACH = [
  { key: 'secure', label: '안정형', d: '연락·거리 둘 다 편안' },
  { key: 'anxious', label: '불안형', d: '답장 늦으면 초조' },
  { key: 'avoidant', label: '회피형', d: '가까워지면 거리 둠' },
  { key: 'fearful', label: '혼란형', d: '당기다 밀다 반복' },
]

export function Upload({ onStart }: { onStart: (me: string, target: string) => void }) {
  const toast = useToast()
  const [step, setStep] = useState<Step>('drop')
  const [drag, setDrag] = useState(false)
  const [busy, setBusy] = useState(false)
  const [senders, setSenders] = useState<Sender[]>([])
  const [me, setMe] = useState<string | null>(null)
  const [cands, setCands] = useState<Candidate[]>([])
  const [target, setTarget] = useState<string | null>(null)
  const [mbti, setMbti] = useState<string | null>(null)
  const [attach, setAttach] = useState<string | null>(null)
  const [alias, setAlias] = useState(true)

  useEffect(() => { api.senders().then(r => { setSenders(r.senders); if (r.me) setMe(r.me) }).catch(() => {}) }, [])

  async function ingest(run: () => Promise<{ added: number; senders: Sender[] }>) {
    setBusy(true)
    try {
      const r = await run()
      if (!r.senders.length) { toast('카톡 내보내기 파일이 아닌 것 같아 😅'); return }
      setSenders(r.senders); setStep('me')
      toast(`${r.added.toLocaleString()}개 메시지를 읽었어요`)
    } catch (e) { toast('업로드 실패: ' + String(e).slice(0, 60)) } finally { setBusy(false) }
  }

  async function pickMe(name: string) {
    setMe(name); await api.setMe(name)
    const t = await api.targets()
    setCands(t.candidates.filter(c => c.name !== name)); setStep('target')
  }

  async function pickTarget(name: string) {
    setTarget(name); await api.setTarget(name)
    const p = await api.persona(name).catch(() => null)
    if (p) { setMbti(p.mbti); setAttach(p.attachment) }
    setStep('persona')
  }

  async function finish() {
    if (!me || !target) return
    await api.setPersona({ person: target, mbti, attachment: attach, note: alias ? 'alias' : null })
    onStart(me, target)
  }

  return (
    <section className="page up">
      <div className="wrap wrap-narrow">
        <div className="up-logo">이별, 잘 보내드립니다</div>
        <div className="up-tag">카톡을 올리면 이 관계의 사망 진단서를 발급해드려요.<br />애도하고, 저주하고, 떠나보내세요.</div>
        <div className="up-char"><Char mood="smile" size={190} /></div>

        {step === 'drop' && (
          <>
            <label className={'dropzone' + (drag ? ' on' : '')}
              onDragOver={e => { e.preventDefault(); setDrag(true) }} onDragLeave={() => setDrag(false)}
              onDrop={e => { e.preventDefault(); setDrag(false); ingest(() => api.upload(Array.from(e.dataTransfer.files))) }}>
              <svg width="38" height="38" viewBox="0 0 38 38" fill="none"><path d="M19 5 L19 24 M11 16 L19 24 L27 16" stroke="#6B7484" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" /><path d="M8 30 L30 30" stroke="#6B7484" strokeWidth="2" strokeLinecap="round" /></svg>
              <p>{busy ? '읽는 중…' : '카톡 대화 파일(.txt) 드래그 & 드롭'}</p>
              <span>또는 눌러서 업로드 · 상대 방 1개 + 친구 방 2~3개 (비교 기준용)</span>
              <input type="file" multiple accept=".txt" onChange={e => e.target.files && ingest(() => api.upload(Array.from(e.target.files!)))} />
            </label>
            <div className="up-alt">
              <button className="btn" disabled title="곧 지원" onClick={() => toast('OCR은 곧 지원해요')}>📷 카톡 캡처로 분석 (OCR)</button>
              <button className="btn btn-rose" disabled={busy} onClick={() => ingest(async () => { await api.clear(); return api.loadSample() })}>✨ 샘플로 보기</button>
            </div>
            {senders.length > 0 && <button className="btn btn-block" style={{ maxWidth: 520, margin: '12px auto 0', display: 'block' }} onClick={() => setStep('me')}>이미 올린 데이터로 계속 →</button>}
            <div className="up-note">🔒 원문은 이 컴퓨터에만 저장돼요 · 이름은 가명 처리할 수 있어요</div>
            <details className="up-note" style={{ maxWidth: 520, margin: '10px auto 0' }}>
              <summary style={{ cursor: 'pointer' }}>카톡에서 내보내는 법</summary>
              PC: 대화방 → ≡ → 대화 내용 → 내보내기 · Android: ≡ → 설정 → 대화 내용 내보내기 → 텍스트만 · iOS: ≡ → 설정 → 대화 내용 내보내기
            </details>
          </>
        )}

        {step === 'me' && (
          <div className="card" style={{ textAlign: 'left' }}>
            <h3>이 중에 누가 당신인가요?</h3>
            <div className="pick-grid">
              {senders.map(s => (
                <button key={s.sender} className={'pick' + (me === s.sender ? ' on' : '')} onClick={() => pickMe(s.sender)}>
                  <div className="pn">{s.sender}</div><div className="pm">{s.n.toLocaleString()}개</div>
                </button>
              ))}
            </div>
          </div>
        )}

        {step === 'target' && (
          <div className="card" style={{ textAlign: 'left' }}>
            <h3>누구를 보내드릴까요?</h3>
            <div className="pick-grid">
              {cands.map(c => (
                <button key={c.name} className="pick" onClick={() => pickTarget(c.name)}>
                  <div className="pn">{c.name}</div><div className="pm">{c.messages.toLocaleString()}개 · {c.one_on_one ? '1:1' : '단톡'}</div>
                </button>
              ))}
            </div>
            <div className="up-note" style={{ textAlign: 'left' }}>나머지 방은 "평소의 나" 기준(baseline)으로만 써요.</div>
          </div>
        )}

        {step === 'persona' && (
          <div className="card" style={{ textAlign: 'left' }}>
            <h3>故 {target}은(는) 어떤 사람이었나요?</h3>
            <p className="sub">몰라도 돼요. 입력값은 통계엔 안 쓰이고, 영정·X 소환술 말투에만 반영돼요.</p>
            <div className="field-label">MBTI</div>
            <div className="mbti-grid">
              {MBTI.map(m => <button key={m} className={'pick' + (mbti === m ? ' on' : '')} onClick={() => setMbti(mbti === m ? null : m)}>{m}</button>)}
            </div>
            <div className="field-label">애착 유형</div>
            <div className="pick-grid">
              {ATTACH.map(a => (
                <button key={a.key} className={'pick' + (attach === a.key ? ' on' : '')} onClick={() => setAttach(attach === a.key ? null : a.key)}>
                  <div className="pn">{a.label}</div><div className="pm">{a.d}</div>
                </button>
              ))}
            </div>
            <div style={{ margin: '16px 0 6px' }}>
              <label className="toggle"><input type="checkbox" checked={alias} onChange={e => setAlias(e.target.checked)} /> 상대 이름을 가명으로 표시</label>
            </div>
            <button className="btn btn-rose btn-block" style={{ marginTop: 10 }} onClick={finish}>부검 시작 →</button>
          </div>
        )}
      </div>
    </section>
  )
}
