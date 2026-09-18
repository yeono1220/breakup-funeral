import { useCallback, useRef, useState } from 'react'
import { api, type Amulet, type Relationship } from '../api'
import { Portrait } from '../components/Portrait'
import { BurnRitual } from '../components/BurnRitual'
import { GrassField } from '../components/GrassField'
import { Modal, useToast, fmtMin } from '../components/ui'

const CURSES = ['읽씹하던 그 손가락,\n앞으로 오타만 나거라', '너의 모든 소개팅에\n어색한 침묵이 깃들기를', '새 연애 3일 만에\n전 애인 얘기 튀어나와라', '너의 인스타 스토리\n조회수 평생 한 자리수', "'바빴어'라는 변명,\n네 인생 최고 히트작 되거라"]

export function Tribute({ data, name, portrait, onBack, onNext, onBuried }: { data: Relationship; name: string; portrait: string | null; onBack: () => void; onNext: () => void; onBuried: (kind: 'chrys' | 'curse') => void }) {
  const toast = useToast()
  const [lidTop, setLidTop] = useState(-58)
  const [closed, setClosed] = useState(false)
  const [dragging, setDragging] = useState(false)
  const [soil, setSoil] = useState(false)
  const [showFlowers, setShowFlowers] = useState(false)
  const [thrown, setThrown] = useState<string[]>([])
  const [flying, setFlying] = useState<string | null>(null)
  const [modal, setModal] = useState<'flower' | 'curse' | null>(null)
  const startY = useRef(0)

  const closeLid = useCallback(() => {
    setClosed(true); setDragging(false); setLidTop(58)
    setTimeout(() => setSoil(true), 400)
    setTimeout(() => setShowFlowers(true), 1100)
    toast('관을 덮었어요 🪦')
  }, [toast])

  const onDown = (e: React.PointerEvent) => { if (closed) return; setDragging(true); startY.current = e.clientY; (e.target as Element).setPointerCapture?.(e.pointerId) }
  const onMove = (e: React.PointerEvent) => {
    if (!dragging || closed) return
    const nt = Math.min(58, Math.max(-58, -58 + (e.clientY - startY.current)))
    setLidTop(nt)
    if (nt >= 48) closeLid()
  }
  const onUp = () => { if (!dragging) return; setDragging(false); if (lidTop < 48) setLidTop(-58) }

  function throwFlower(emoji: string) {
    setFlying(null); requestAnimationFrame(() => setFlying(emoji))
    setTimeout(() => { setThrown(x => [...x, emoji]); setFlying(null) }, 900)
    toast('헌화했어요 💐')
  }

  const title = !closed ? '잘 보내드릴게요' : thrown.length ? '편히 잠들기를' : '이제 꽃을 놓아주세요'
  const desc = !closed ? '관 뚜껑을 잡고 아래로 덮어주세요' : thrown.length ? '꽃을 더 놓거나, 아래에서 인사를 남겨요' : '골라서 던지면 무덤 위에 놓여요'

  return (
    <section className="page">
      <div className="wrap wrap-narrow">
        <div className="steps-bar">
          <span className="step-pill">① 사망 진단서</span><span className="step-arrow">→</span>
          <span className="step-pill on">② 추모하기</span><span className="step-arrow">→</span>
          <span className="step-pill">③ 공동묘지 안치</span>
        </div>
        <h2 className="pen" style={{ fontSize: 34, textAlign: 'center', marginBottom: 6, fontWeight: 400 }}>{title}</h2>
        <p style={{ textAlign: 'center', color: 'var(--text-soft)', fontSize: 14, marginBottom: 20 }}>{desc}</p>

        <div className="grave-scene">
          <GrassField />
          <div className="pit">
            <div className="pit-wall" />
            <div className="pit-portrait"><Portrait src={portrait} size={96} gray /></div>
            <div className={'coffin-lid' + (dragging ? ' dragging' : '') + (closed ? ' closed' : '')} style={{ top: lidTop }}
              onPointerDown={onDown} onPointerMove={onMove} onPointerUp={onUp} onPointerCancel={onUp}>
              <svg width="240" height="70" viewBox="0 0 240 70"><path d="M16 8 L224 8 L232 34 L224 62 L16 62 L8 34 Z" fill="#B98A5E" stroke="#7A5B3A" strokeWidth="3" strokeLinejoin="round" /><path d="M120 14 L120 56 M60 34 L180 34" stroke="#7A5B3A" strokeWidth="2.5" /><path d="M104 26 L136 26 L128 42 L112 42 Z" fill="#8A6642" stroke="#7A5B3A" strokeWidth="2" /></svg>
              {!closed && <div className="lid-hint">⬇ 잡고 아래로 덮기</div>}
            </div>
            <div className="soil-cover" style={{ height: soil ? '100%' : 0 }} />
          </div>
          {thrown.length > 0 && (
            <div className="mound-final">
              <svg width="260" height="130" viewBox="0 0 260 130"><path d="M20 120 Q80 40 130 42 Q180 40 240 120 Z" fill="#6B8F4E" stroke="#54733C" strokeWidth="3" strokeLinejoin="round" /><path d="M60 96 q6 -9 12 0 M108 78 q6 -9 12 0 M156 92 q6 -9 12 0 M196 104 q6 -9 12 0" stroke="#54733C" strokeWidth="2.5" fill="none" strokeLinecap="round" /><rect x="118" y="20" width="24" height="46" rx="4" fill="#AEB9C4" stroke="#7C8894" strokeWidth="3" /><path d="M118 34 L142 34" stroke="#7C8894" strokeWidth="2.5" /><text x="130" y="30" fontSize="10" textAnchor="middle" fill="#7C8894">RIP</text></svg>
              <div className="thrown-flowers">{thrown.map((f, i) => <span key={i}>{f}</span>)}</div>
            </div>
          )}
          {flying && <div className="flying-flower fly">{flying}</div>}
        </div>

        {showFlowers && (
          <div className="flower-bar">
            <div className="fb-label">🌸 헌화할 꽃을 골라 던져주세요</div>
            <div className="flower-choices">
              {[['🌼', '국화'], ['🌹', '장미'], ['🥀', '시든 꽃'], ['💐', '꽃다발']].map(([e, l]) => (
                <button key={e} className="flower-choice" onClick={() => throwFlower(e)}>{e}<span>{l}</span></button>
              ))}
            </div>
          </div>
        )}

        {thrown.length > 0 && (
          <div>
            <div className="bury-done">🕊️ 편히 잠들었습니다 · 헌화해주셔서 고마워요</div>
            <p style={{ textAlign: 'center', color: 'var(--text-soft)', fontSize: 14, margin: '20px 0 16px' }}>마지막으로, 어떤 인사를 남길까요?</p>
            <div className="tribute-grid">
              <div className="tribute chrys" onClick={() => { setModal('flower'); onBuried('chrys') }}>
                <div className="ti">🌼</div><div className="tt">진정성 진단서</div><div className="tp">차분한 추모</div>
                <div className="td">데이터 근거로 쓴<br />팩폭 위로 진단서를 받아요</div>
                <div className="price">무료</div>
              </div>
              <div className="tribute curse" onClick={() => { setModal('curse'); onBuried('curse') }}>
                <div className="ti">📜</div><div className="tt">매운맛 저주 부적</div><div className="tp">화끈한 작별</div>
                <div className="td">🔮 애착유형별 사자성어 부적<br />+ 카톡 패턴 맞춤 저주 한 줄</div>
                <div className="price">🔥 유료 · 크레딧</div>
              </div>
            </div>
            <div className="next-row">
              <button className="btn" style={{ flex: 1 }} onClick={onBack}>← 진단서로</button>
              <button className="btn btn-rose" style={{ flex: 1 }} onClick={onNext}>공동묘지에 안치 →</button>
            </div>
          </div>
        )}
      </div>

      {modal === 'flower' && <FlowerModal data={data} name={name} onClose={() => setModal(null)} />}
      {modal === 'curse' && <CurseModal onClose={() => setModal(null)} />}
    </section>
  )
}

function templateEulogy(data: Relationship, name: string) {
  const r = data.symmetry.reply
  const b = data.bias
  const w = data.waiting
  const lines = [
    `${name}은(는) 나쁜 사람이 아니라, 맞지 않는 사람이었어요.`,
    r.their_median_min != null ? `평소 ${fmtMin(r.their_median_min)} 안에 답하던 사람이 ${w ? `${w.age_hours}시간째 답이 없는 건` : '느려진 건'} 미움이 아니라 무관심의 신호였고, 무관심은 설득으로 바뀌지 않아요.` : '',
    b.reply_speed.times_faster && b.reply_speed.times_faster > 1.5 ? `당신은 이 사람에게만 평소보다 ${b.reply_speed.times_faster}배 빨리 답했어요. 지금 슬픈 건 그 사람을 잃어서가 아니라, 쏟은 마음이 아까워서예요.` : '지금 슬픈 건 그 사람을 잃어서가 아니라, 쏟은 마음이 아까워서예요.',
    '그 마음, 당신은 다시 채울 수 있어요. 오늘은 여기까지. 잘 보내주세요. 🕊️',
  ]
  return lines.filter(Boolean).join(' ')
}

function FlowerModal({ data, name, onClose }: { data: Relationship; name: string; onClose: () => void }) {
  const [text, setText] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  async function pick() {
    setBusy(true)
    try { const r = await api.eulogy(); setText(r.text) } catch { setText(templateEulogy(data, name)) } finally { setBusy(false) }
  }
  return (
    <Modal title="🌼 국화꽃 헌화" onClose={onClose}>
      <p className="tiny muted" style={{ marginBottom: 6 }}>헌화할 꽃을 골라요 · 잔잔한 추모 BGM ♪</p>
      <div className="flower-pick">{['🌼', '🌸', '🥀'].map(f => <div key={f} className="flower-opt" onClick={pick}>{f}</div>)}</div>
      {busy && <div className="muted tiny">진단서 쓰는 중…</div>}
      {text && (
        <div className="result-card card" style={{ borderColor: 'var(--chrys-deep)' }}>
          <div className="chrys-flower">🌼</div>
          <div className="diagnosis"><div className="dh">🌼 진정성 있는 팩폭 진단</div>{text}</div>
        </div>
      )}
    </Modal>
  )
}

function CurseModal({ onClose }: { onClose: () => void }) {
  const toast = useToast()
  const [am, setAm] = useState<Amulet | null>(null)
  const [busy, setBusy] = useState(false)
  const [ritual, setRitual] = useState(false)
  const [shown, setShown] = useState(false)   // 의식 끝난 뒤 모달 안에 부적 남김
  async function burn() {
    setRitual(true); setBusy(true); setShown(false)
    try { setAm(await api.curse()) }
    catch { setAm({ hanja: '已讀無視\n永劫回歸', reading: '이독무시 영겁회귀', meaning: '읽씹은 돌고 돌아 네게로 돌아오리라', attachment: null, attachment_label: '유형 미상', line: CURSES[Math.floor(Math.random() * CURSES.length)].replace('\n', ' '), text: '' }) }
    finally { setBusy(false) }
  }
  return (
    <>
      <Modal title="📜 매운맛 저주 부적" onClose={onClose}>
        <p className="tiny muted" style={{ marginBottom: 12 }}>🔮 애착유형별 사자성어가 부적에 박히고, 상대 카톡 패턴으로 맞춤 저주 한 줄을 덧붙여요 · 🔊 소리 나요</p>
        <button className="btn btn-rose btn-block" onClick={burn} disabled={busy}>{busy ? '부적 태우는 중…' : shown ? '🔥 한 번 더 태우기' : '🔥 저주 부적 태우기'}</button>
        {am && shown && (
          <div style={{ marginTop: 8 }}>
            <div className="amulet">
              <div className="am-head">{am.attachment_label} · X 저주 부적</div>
              <div className="am-hanja">{am.hanja.split('\n').map((col, i) => <span key={i}>{col}</span>)}</div>
              <div className="am-read">{am.reading}</div>
              <div className="am-mean">{am.meaning}</div>
              <div className="am-line">“{am.line}”</div>
              <div className="am-seal">封</div>
            </div>
            {am.fallback && <div className="tiny muted" style={{ textAlign: 'center', marginTop: 8 }}>맞춤 한 줄은 데모 문구 (API 키 확인)</div>}
            <button className="btn btn-block" style={{ marginTop: 16 }} onClick={() => toast('저주 부적 PNG 저장은 곧 지원 📜')}>🖼️ 부적 PNG로 저장·공유</button>
          </div>
        )}
      </Modal>
      {ritual && <BurnRitual amulet={am} loading={busy} onClose={() => { setRitual(false); setShown(true) }} />}
    </>
  )
}
