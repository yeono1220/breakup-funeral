import { useEffect, useState } from 'react'
import { api, type Candidate, type Ending, type Sender } from '../api'
import { DrawPad } from '../components/DrawPad'
import { Char } from '../components/Char'
import { Icon } from '../components/Icons'
import { useToast } from '../components/ui'

type Step = 'drop' | 'me' | 'target' | 'persona' | 'portrait'
const MBTI = ['ISTJ', 'ISFJ', 'INFJ', 'INTJ', 'ISTP', 'ISFP', 'INFP', 'INTP', 'ESTP', 'ESFP', 'ENFP', 'ENTP', 'ESTJ', 'ESFJ', 'ENFJ', 'ENTJ']
const ATTACH = [
  { key: 'secure', label: '안정형', d: '연락·거리 둘 다 편안' },
  { key: 'anxious', label: '불안형', d: '답장 늦으면 초조' },
  { key: 'avoidant', label: '회피형', d: '가까워지면 거리 둠' },
  { key: 'fearful', label: '혼란형', d: '당기다 밀다 반복' },
]
const ENDINGS: { key: Ending; label: string; d: string }[] = [
  { key: 'ghosted', label: '잠수·읽씹', d: '답이 끊기면서 끝남' },
  { key: 'dumped', label: '차였어', d: '상대가 끝냄' },
  { key: 'dumper', label: '내가 끝냈어', d: '내가 정리함' },
  { key: 'faded', label: '자연소멸', d: '서서히 멀어짐' },
  { key: 'mutual', label: '합의 이별', d: '같이 정리함' },
  { key: 'ongoing', label: '아직 안 끝남', d: '썸/연애 진행 중' },
]

export function Upload({ onStart, jumpTo }: { onStart: (me: string, target: string) => void; jumpTo?: 'persona' }) {
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
  const [ending, setEnding] = useState<Ending | null>(null)
  const [context, setContext] = useState('')
  const [endedAt, setEndedAt] = useState('')
  const [startedAt, setStartedAt] = useState('')
  const [portrait, setPortrait] = useState<string | null>(null)

  useEffect(() => {
    api.senders().then(r => { setSenders(r.senders); if (r.me) setMe(r.me) }).catch(() => {})
    if (jumpTo === 'persona') {
      api.targets().then(t => { if (t.me && t.target) { setMe(t.me); pickTarget(t.target) } }).catch(() => {})
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  async function ingest(run: () => Promise<{ added: number; senders: Sender[] }>) {
    setBusy(true)
    try {
      const r = await run()
      if (!r.senders.length) { toast('카톡 내보내기 파일이 아닌 것 같아'); return }
      setSenders(r.senders); setStep('me')
      toast(`${r.added.toLocaleString()}개 메시지를 읽었어`)
    } catch (e) { toast('업로드에 실패했어: ' + String(e).slice(0, 60)) } finally { setBusy(false) }
  }

  async function pickMe(name: string) {
    setMe(name); await api.setMe(name)
    const t = await api.targets()
    setCands(t.candidates.filter(c => c.name !== name)); setStep('target')
  }

  async function pickTarget(name: string) {
    setTarget(name); await api.setTarget(name)
    const p = await api.persona(name).catch(() => null)
    if (p) { setMbti(p.mbti); setAttach(p.attachment); setEnding(p.ending ?? null); setContext(p.context ?? ''); setEndedAt(p.ended_at ?? ''); setStartedAt(p.started_at ?? ''); setAlias(p.alias ?? true); setPortrait(p.portrait ?? null) }
    setStep('persona')
  }

  async function savePersona() {
    if (!target) return
    await api.setPersona({ person: target, mbti, attachment: attach, ending, context: context || null, ended_at: endedAt || null, started_at: startedAt || null, alias, portrait: portrait ?? undefined })
  }
  async function toPortrait() { await savePersona(); setStep('portrait') }
  async function finish() {
    if (!me || !target) return
    await savePersona()
    onStart(me, target)
  }

  // 단계 순서 지정용: JSX에서 style={{['--i' as any]: n}}
  const at = (n: number) => ({ ['--i' as any]: n })

  return (
    <section className="page up">
      <div className="wrap wrap-narrow">
        <div className="up-logo reveal" style={at(0)}>이별, 잘 보내줄게</div>
        <div className="up-tag reveal" style={at(1)}>카톡을 올리면 이 관계의 사망 진단서를 발급해줄게.<br />애도하고, 저주하고, 떠나보내.</div>
        <div className="fade-in" style={at(2)}><div className="up-char"><Char mood="smile" size={190} /></div></div>

        {step === 'drop' && (
          <>
            <label className={'dropzone reveal' + (drag ? ' on' : '')} style={at(3)}
              onDragOver={e => { e.preventDefault(); setDrag(true) }} onDragLeave={() => setDrag(false)}
              onDrop={e => { e.preventDefault(); setDrag(false); ingest(() => api.upload(Array.from(e.dataTransfer.files))) }}>
              <Icon name="upload" size={36} className="muted" />
              <p>{busy ? '읽는 중…' : '카톡 대화 파일(.txt) 드래그 & 드롭'}</p>
              <span>또는 눌러서 올려줘 · 그 사람과의 1:1 대화방이면 충분해</span>
              <input type="file" multiple accept=".txt" onChange={e => e.target.files && ingest(() => api.upload(Array.from(e.target.files!)))} />
            </label>
            <div className="up-alt reveal" style={at(4)}>
              <button className="btn btn-rose" disabled={busy} onClick={() => ingest(async () => { await api.clear(); return api.loadSample() })}>샘플로 먼저 볼래</button>
            </div>
            {senders.length > 0 && <button className="btn btn-block reveal" style={{ ...at(5), maxWidth: 520, margin: '12px auto 0', display: 'block' }} onClick={() => setStep('me')}>이미 올린 데이터로 계속 →</button>}
            <div className="up-note reveal" style={at(6)}>원문은 이 컴퓨터에만 남아. 이름은 가려줄 수 있어.</div>
            <details className="up-note reveal" style={{ ...at(7), maxWidth: 520, margin: '8px auto 0' }}>
              <summary style={{ cursor: 'pointer' }}>카톡에서 내보내는 법</summary>
              PC: 대화방 → ≡ → 대화 내용 → 내보내기 · Android: ≡ → 설정 → 대화 내용 내보내기 → 텍스트만 · iOS: ≡ → 설정 → 대화 내용 내보내기
            </details>
          </>
        )}

        {step === 'me' && (
          <div className="card reveal" style={{ textAlign: 'left' }}>
            <h3>이 중에 누가 너야?</h3>
            <div className="pick-grid">
              {senders.map((s, k) => (
                <button key={s.sender} className={'pick reveal' + (me === s.sender ? ' on' : '')} style={at(k + 1)} onClick={() => pickMe(s.sender)}>
                  <div className="pn">{s.sender}</div><div className="pm">{s.n.toLocaleString()}개</div>
                </button>
              ))}
            </div>
          </div>
        )}

        {step === 'target' && (
          <div className="card reveal" style={{ textAlign: 'left' }}>
            <h3>누구를 보내줄까?</h3>
            <div className="pick-grid">
              {cands.map((c, k) => (
                <button key={c.name} className="pick reveal" style={at(k + 1)} onClick={() => pickTarget(c.name)}>
                  <div className="pn">{c.name}</div><div className="pm">{c.messages.toLocaleString()}개 · {c.one_on_one ? '1:1' : '단톡'}</div>
                </button>
              ))}
            </div>
            <div className="up-note" style={{ textAlign: 'left' }}>나머지 방은 평소의 나를 아는 데만 써.</div>
          </div>
        )}

        {step === 'persona' && (
          <div className="card reveal" style={{ textAlign: 'left' }}>
            <h3>故 {target}, 어떤 사람이었어?</h3>
            <p className="sub">몰라도 돼. 여기 적는 건 통계엔 안 쓰고, 영정·X 소환술 말투에만 반영돼.</p>
            <div className="field-label reveal" style={at(1)}>MBTI</div>
            <div className="mbti-grid reveal" style={at(2)}>
              {MBTI.map(m => <button key={m} className={'pick' + (mbti === m ? ' on' : '')} onClick={() => setMbti(mbti === m ? null : m)}>{m}</button>)}
            </div>
            <div className="field-label reveal" style={at(3)}>애착 유형</div>
            <div className="pick-grid reveal" style={at(4)}>
              {ATTACH.map(a => (
                <button key={a.key} className={'pick' + (attach === a.key ? ' on' : '')} onClick={() => setAttach(attach === a.key ? null : a.key)}>
                  <div className="pn">{a.label}</div><div className="pm">{a.d}</div>
                </button>
              ))}
            </div>
            <div className="field-label reveal" style={at(5)}>어떻게 끝났어? <span className="faint">— 데이터 판정보다 이걸 우선해</span></div>
            <div className="chips reveal" style={at(6)}>
              {ENDINGS.map(e => (
                <button key={e.key} className={'pick' + (ending === e.key ? ' on' : '')} onClick={() => setEnding(ending === e.key ? null : e.key)} title={e.d}>{e.label}</button>
              ))}
            </div>
            <div className="field-label reveal" style={at(7)}>상황 설명 <span className="faint">(선택) — 회피형이라 데이터만 보면 썸처럼 보이는 경우처럼, 코치·소환술·진단서가 이 맥락을 참고해</span></div>
            <textarea className="ctx reveal" style={at(8)} value={context} onChange={e => setContext(e.target.value)} placeholder="예: 3주 전에 '나중에 연락할게' 하고 잠수. 원래 연락 뜸한 회피형이라 데이터로는 안 끝난 것처럼 보임" />
            <div className="field-label reveal" style={at(9)}>썸(관계) 시작일 · 헤어진 날 <span className="faint">(선택) — 향년은 이 사이로 계산해. 카톡은 사귀기 전부터 했을 수 있으니까</span></div>
            <div className="row reveal" style={{ ...at(10), display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              <input className="date" type="date" value={startedAt} onChange={e => setStartedAt(e.target.value)} title="썸 시작일" />
              <span className="faint" style={{ alignSelf: 'center' }}>~</span>
              <input className="date" type="date" value={endedAt} onChange={e => setEndedAt(e.target.value)} title="헤어진 날" />
            </div>
            <div className="tiny faint reveal" style={{ ...at(11), marginTop: 8 }}>비워두면 데이터가 감지한 첫 썸/연애 구간부터 계산해. 진단서에서 나중에 바꿀 수도 있어.</div>
            <div className="reveal" style={{ ...at(12), margin: '16px 0 8px' }}>
              <label className="toggle"><input type="checkbox" checked={alias} onChange={e => setAlias(e.target.checked)} /> 상대 이름을 가명으로 표시</label>
            </div>
            <button className="btn btn-rose btn-block reveal" style={{ ...at(13), marginTop: 12 }} onClick={toPortrait}>다음: 영정 준비 →</button>
          </div>
        )}

        {step === 'portrait' && (
          <div className="card reveal" style={{ textAlign: 'left' }}>
            <h3>영정 사진을 준비해줘</h3>
            <p className="sub">故 {target}의 얼굴을 그려도 되고, 사진을 불러와도 돼. 이 컴퓨터에만 남아. 건너뛰면 익명 실루엣.</p>
            <div className="reveal" style={at(1)}><DrawPad value={portrait} onChange={setPortrait} /></div>
            <div className="next-row reveal" style={at(2)}>
              <button className="btn" style={{ flex: 1 }} onClick={() => setStep('persona')}>← 이전</button>
              <button className="btn btn-rose" style={{ flex: 2 }} onClick={finish}>{portrait ? '부검 시작 →' : '건너뛰고 부검 시작 →'}</button>
            </div>
          </div>
        )}
      </div>
    </section>
  )
}
