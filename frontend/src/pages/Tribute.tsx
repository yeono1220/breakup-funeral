import { useCallback, useRef, useState } from 'react'
import { api, type Amulet, type Relationship } from '../api'
import { Portrait } from '../components/Portrait'
import { BurnRitual } from '../components/BurnRitual'
import { GrassField } from '../components/GrassField'
import { RitualBar } from '../components/RitualBar'
import { Icon } from '../components/Icons'
import { Modal, useToast, fmtMin } from '../components/ui'

const CURSES = ['읽씹하던 그 손가락,\n앞으로 오타만 나거라', '너의 모든 소개팅에\n어색한 침묵이 깃들기를', '새 연애 3일 만에\n전 애인 얘기 튀어나와라', '너의 인스타 스토리\n조회수 평생 한 자리수', "'바빴어'라는 변명,\n네 인생 최고 히트작 되거라"]

/* 추모 카드 2장: 국화 쪽을 살짝 넓게. 모바일은 1열 (index.css .tribute-grid 의 미디어쿼리와 동일 분기점) */
const TRIBUTE_GRID_CSS = '.tribute-grid.tg-asym{grid-template-columns:1.2fr .8fr}@media (max-width:560px){.tribute-grid.tg-asym{grid-template-columns:1fr}}'

export function Tribute({ data, name, portrait, onBack, onNext, onGoStep, onBuried, onAmulet }: { data: Relationship; name: string; portrait: string | null; onBack: () => void; onNext: () => void; onGoStep?: (i: number) => void; onBuried: (kind: 'chrys' | 'curse') => void; onAmulet?: (a: Amulet) => void }) {
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
    toast('관을 덮었어')
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
    toast('헌화했어')
  }

  const title = !closed ? '잘 보내줄게' : thrown.length ? '편히 잠들기를' : '이제 꽃을 놓아줘'
  const desc = !closed ? '관 뚜껑을 잡고 아래로 덮어줘' : thrown.length ? '꽃을 더 놓거나, 아래에서 인사를 남겨' : '골라서 던지면 무덤 위에 놓여'

  return (
    <section className="page">
      <style>{TRIBUTE_GRID_CSS}</style>
      <div className="wrap wrap-narrow">
        <RitualBar current={thrown.length > 0 ? 2 : 1} onGo={onGoStep} />
        <h2 className="page-title reveal" style={{ textAlign: 'center', marginBottom: 8, ['--i' as any]: 1 }}>{title}</h2>
        <p className="reveal" style={{ textAlign: 'center', color: 'var(--text-soft)', fontSize: 14, marginBottom: 20, ['--i' as any]: 2 }}>{desc}</p>

        <div className="grave-scene reveal" style={{ ['--i' as any]: 3 }}>
          <GrassField />
          <div className="pit">
            <div className="pit-wall" />
            <div className="pit-portrait"><Portrait src={portrait} size={96} gray /></div>
            <div className={'coffin-lid' + (dragging ? ' dragging' : '') + (closed ? ' closed' : '')} style={{ transform: 'translateY(' + (lidTop + 58) + 'px)' }}
              onPointerDown={onDown} onPointerMove={onMove} onPointerUp={onUp} onPointerCancel={onUp}>
              <svg width="240" height="70" viewBox="0 0 240 70">
                {/* 뚜껑 판: 좌우 비대칭, 살짝 휜 변 */}
                <path d="M17 9 L223 7.5 Q233 34 224.5 62.5 L15.5 61.5 Q7 33 17 9 Z" fill="#B98A5E" stroke="#7A5B3A" strokeWidth="3" strokeLinejoin="round" />
                <path d="M17 9 L223 7.5 Q233 34 224.5 62.5 L15.5 61.5 Q7 33 17 9 Z" fill="none" stroke="#7A5B3A" strokeWidth="1.2" opacity=".5" transform="translate(1.2 1)" />
                {/* 십자 홈: 두 겹 선(굵은 반투명 + 얇은 진한) */}
                <path d="M120 14.5 Q121 35 119.5 55.5 M61 34.5 Q120 33 179 35" stroke="#7A5B3A" strokeWidth="4" opacity=".25" fill="none" strokeLinecap="round" />
                <path d="M120 14.5 Q121 35 119.5 55.5 M61 34.5 Q120 33 179 35" stroke="#7A5B3A" strokeWidth="2" fill="none" strokeLinecap="round" />
                <path d="M104.5 26 L136 25.5 L128.5 42.5 L112 42 Z" fill="#8A6642" stroke="#7A5B3A" strokeWidth="2" strokeLinejoin="round" />
              </svg>
              {!closed && <div className="lid-hint">↓ 잡고 아래로 덮기</div>}
            </div>
            <div className={'soil-cover' + (soil ? ' on' : '')} />
          </div>
          {thrown.length > 0 && (
            <div className="mound-final">
              <svg width="260" height="130" viewBox="0 0 260 130">
                {/* 봉분: 정상이 살짝 왼쪽으로 치우친 비대칭 곡선 */}
                <path d="M18 121 Q72 38 126 43 Q184 42 242 120 Z" fill="#6B8F4E" stroke="#54733C" strokeWidth="3" strokeLinejoin="round" />
                <path d="M58 97 q6 -9 13 -1 M107 79 q5 -8 12 -1 M158 92 q7 -10 12 -1 M197 105 q5 -8 11 0" stroke="#54733C" strokeWidth="2.5" fill="none" strokeLinecap="round" />
                <path d="M118 22 Q130 17 142.5 21.5 L142 66.5 L118.5 66 Z" fill="#AEB9C4" stroke="#7C8894" strokeWidth="3" strokeLinejoin="round" />
                <path d="M119 34.5 Q130 33.5 141.5 34.5" stroke="#7C8894" strokeWidth="2.5" fill="none" strokeLinecap="round" />
                <text x="130" y="30" fontSize="10" textAnchor="middle" fill="#7C8894">RIP</text>
              </svg>
              <div className="thrown-flowers">{thrown.map((f, i) => <span key={i}>{f}</span>)}</div>
            </div>
          )}
          {flying && <div className="flying-flower fly">{flying}</div>}
        </div>

        {showFlowers && (
          <div className="flower-bar">
            <div className="fb-label">꽃을 골라 던져줘</div>
            <div className="flower-choices">
              {[['🌼', '국화'], ['🌹', '장미'], ['🥀', '시든 꽃'], ['💐', '꽃다발']].map(([e, l]) => (
                <button key={e} className="flower-choice" onClick={() => throwFlower(e)}>{e}<span>{l}</span></button>
              ))}
            </div>
          </div>
        )}

        {thrown.length > 0 && (
          <div>
            <div className="bury-done reveal" style={{ ['--i' as any]: 0 }}>편히 잠들었어. 꽃 고마워</div>
            <p className="reveal" style={{ textAlign: 'center', color: 'var(--text-soft)', fontSize: 14, margin: '20px 0 16px', ['--i' as any]: 1 }}>마지막으로 어떤 인사를 남길까</p>
            <div className="tribute-grid tg-asym">
              <div className="tribute chrys reveal" style={{ ['--i' as any]: 2 }} onClick={() => { setModal('flower'); onBuried('chrys') }}>
                <div className="ti" style={{ color: 'var(--chrys)' }}><Icon name="flower" size={24} /></div><div className="tt">진정성 진단서</div><div className="tp">차분한 추모</div>
                <div className="td">데이터 근거로 쓴<br />팩폭 위로 진단서를 받아</div>
                <div className="tiny faint" style={{ marginTop: 12 }}>무료</div>
              </div>
              <div className="tribute curse reveal" style={{ ['--i' as any]: 3 }} onClick={() => { setModal('curse'); onBuried('curse') }}>
                <div className="ti" style={{ color: 'var(--rose-deep)' }}><Icon name="scroll" size={24} /></div><div className="tt">매운맛 저주 부적</div><div className="tp">화끈한 작별</div>
                <div className="td">애착유형별 사자성어 부적<br />+ 카톡 패턴 맞춤 저주 한 줄</div>
                <div className="tiny faint" style={{ marginTop: 12 }}>유료 · 크레딧</div>
              </div>
            </div>
            <div className="next-row reveal" style={{ ['--i' as any]: 4 }}>
              <button className="btn" style={{ flex: 1 }} onClick={onBack}>← 진단서로</button>
              <button className="btn btn-rose" style={{ flex: 1 }} onClick={onNext}>발인 · 공동묘지로 →</button>
            </div>
          </div>
        )}
      </div>

      {modal === 'flower' && <FlowerModal data={data} name={name} onClose={() => setModal(null)} />}
      {modal === 'curse' && <CurseModal onClose={() => setModal(null)} onAmulet={onAmulet} />}
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
    <Modal title="국화꽃 헌화" onClose={onClose}>
      <p className="tiny muted" style={{ marginBottom: 8 }}>꽃 하나 골라줘. 진단서를 써줄게</p>
      <div className="flower-pick">{['🌼', '🌸', '🥀'].map(f => <div key={f} className="flower-opt press" onClick={pick}>{f}</div>)}</div>
      {busy && <div className="muted tiny">진단서 쓰는 중…</div>}
      {text && (
        <div className="result-card card reveal" style={{ borderColor: 'var(--chrys-deep)' }}>
          <div style={{ color: 'var(--chrys)', display: 'flex', justifyContent: 'center' }}><Icon name="flower" size={40} /></div>
          <div className="diagnosis"><div className="dh">진정성 있는 팩폭 진단</div>{text}</div>
        </div>
      )}
    </Modal>
  )
}

function CurseModal({ onClose, onAmulet }: { onClose: () => void; onAmulet?: (a: Amulet) => void }) {
  const toast = useToast()
  const [am, setAm] = useState<Amulet | null>(null)
  const [busy, setBusy] = useState(false)
  const [ritual, setRitual] = useState(false)
  const [shown, setShown] = useState(false)   // 의식 끝난 뒤 모달 안에 부적 남김
  async function burn() {
    setRitual(true); setBusy(true); setShown(false)
    try { const a = await api.curse(); setAm(a); onAmulet?.(a) }
    catch { setAm({ hanja: '已讀無視\n永劫回歸', reading: '이독무시 영겁회귀', meaning: '읽씹은 돌고 돌아 네게로 돌아오리라', attachment: null, attachment_label: '유형 미상', line: CURSES[Math.floor(Math.random() * CURSES.length)].replace('\n', ' '), text: '' }) }
    finally { setBusy(false) }
  }
  return (
    <>
      <Modal title="매운맛 저주 부적" onClose={onClose}>
        <p className="tiny muted" style={{ marginBottom: 12 }}>애착유형에 맞는 사자성어를 부적에 새기고, 상대 카톡 패턴으로 맞춤 저주 한 줄을 덧붙여. 소리 나니까 볼륨 조심</p>
        <button className="btn btn-rose btn-block" onClick={burn} disabled={busy}>{busy ? '부적 태우는 중…' : shown ? '한 번 더 태우기' : '저주 부적 태우기'}</button>
        {am && shown && (
          <div style={{ marginTop: 8 }}>
            <div className="amulet" style={{ animation: 'pop var(--dur-3) var(--ease-spring) both' }}>
              <div className="am-head">{am.attachment_label} · X 저주 부적</div>
              <div className="am-hanja">{am.hanja.split('\n').map((col, i) => <span key={i}>{col}</span>)}</div>
              <div className="am-read">{am.reading}</div>
              <div className="am-mean">{am.meaning}</div>
              <div className="am-line">“{am.line}”</div>
              <div className="am-seal">封</div>
            </div>
            {am.fallback && <div className="tiny muted" style={{ textAlign: 'center', marginTop: 8 }}>맞춤 한 줄은 지금 예시로 넣었어</div>}
            <button className="btn btn-block" style={{ marginTop: 16 }} onClick={() => toast('부적 PNG 저장은 곧 돼')}>부적 PNG로 저장·공유</button>
          </div>
        )}
      </Modal>
      {ritual && <BurnRitual amulet={am} loading={busy} onClose={() => { setRitual(false); setShown(true) }} />}
    </>
  )
}
