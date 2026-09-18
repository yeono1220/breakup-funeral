import { useEffect, useState } from 'react'
import { Modal, useToast } from '../components/ui'

export type Tomb = { id: number; epitaph: string; kind: 'curse' | 'chrys'; flowers: number; comments: number; mine?: boolean }
const SEED: Tomb[] = [
  { id: 108, epitaph: '"바쁘다며 스토리는 1분마다 올리던 그대"', kind: 'curse', flowers: 142, comments: 38 },
  { id: 109, epitaph: '"읽씹 6시간, 답장은 \'ㅇㅇ\' 두 글자"', kind: 'chrys', flowers: 88, comments: 12 },
  { id: 110, epitaph: '"나만 좋아했던 것 같은 6개월"', kind: 'curse', flowers: 231, comments: 54 },
  { id: 111, epitaph: '"먼저 좋다 해놓고 먼저 식은 사람"', kind: 'chrys', flowers: 67, comments: 9 },
]
const LS = 'funeral.tombs'

export function loadTombs(): Tomb[] {
  try { const v = localStorage.getItem(LS); if (v) return JSON.parse(v) } catch {}
  return SEED
}
export function saveTombs(t: Tomb[]) { try { localStorage.setItem(LS, JSON.stringify(t)) } catch {} }

export function Cemetery({ myEpitaph, myKind }: { myEpitaph: string | null; myKind: 'curse' | 'chrys' }) {
  const toast = useToast()
  const [tombs, setTombs] = useState<Tomb[]>(loadTombs)
  const [guest, setGuest] = useState<number | null>(null)
  const [hit, setHit] = useState<Set<number>>(new Set())
  useEffect(() => saveTombs(tombs), [tombs])

  function hwa(id: number) {
    if (hit.has(id)) return
    setTombs(ts => ts.map(t => (t.id === id ? { ...t, flowers: t.flowers + 1 } : t)))
    setHit(h => new Set(h).add(id)); toast('헌화했어요 💐')
  }
  function bury() {
    if (!myEpitaph) { toast('먼저 진단서를 발급받아요'); return }
    if (tombs.some(t => t.mine && t.epitaph === myEpitaph)) { toast('이미 안치돼 있어요 🪦'); return }
    const id = Math.max(...tombs.map(t => t.id)) + 1
    setTombs(ts => [{ id, epitaph: myEpitaph, kind: myKind, flowers: 0, comments: 0, mine: true }, ...ts]); toast('내 관계도 안치됐어요 🪦')
  }

  return (
    <section className="page">
      <div className="wrap">
        <div className="cemetery-head">
          <h2 className="pen" style={{ fontSize: 34, fontWeight: 400 }}>🪦 공동묘지</h2>
          <div className="live-count"><span className="live-dot" />실시간 조문객 142명</div>
        </div>
        <p style={{ color: 'var(--text-soft)', fontSize: 14, marginBottom: 20 }}>떠나보낸 관계들이 잠든 곳 · 헌화하고 위로를 남겨요</p>
        <div className="legend-top">
          <div className="lt-h">🏆 전설의 묘지 TOP 3</div>
          {[['3년 연애 후 "우리 잠깐 시간을 갖자" → 잠수', '묘비 #77 · 📜 저주봉인', '💐 2,914', 'r1'], ['청첩장 돌리기 3주 전 파혼', '묘비 #12 · 📜 저주봉인', '💐 2,105', 'r2'], ['200일 선물 주고 그날 밤 환승 발각', '묘비 #203 · 🌼 헌화', '💐 1,888', 'r3']].map(([t, m, s, r], i) => (
            <div className="legend-row" key={i}><div className={'legend-rank ' + r}>{i + 1}</div><div className="legend-body"><div className="lb-t">{t}</div><div className="lb-m">{m}</div></div><div className="legend-stat">{s}</div></div>
          ))}
        </div>
        <div className="tomb-grid">
          {tombs.map(t => (
            <div className={'tomb' + (t.mine ? ' mine' : '')} key={t.id}>
              <div className="tomb-top"><span className="tomb-icon">🪦</span><span className="tomb-id">묘비 #{t.id}{t.mine ? ' · 내 관계' : ''}</span><span className={'tomb-badge ' + t.kind}>{t.kind === 'curse' ? '📜 저주봉인' : '🌼 헌화'}</span></div>
              <div className="tomb-epitaph">{t.epitaph}</div>
              <div className="tomb-meta"><span className={hit.has(t.id) ? 'hit' : ''} onClick={() => hwa(t.id)}>💐 <b>{t.flowers}</b></span><span onClick={() => setGuest(t.id)}>💬 {t.comments}</span></div>
            </div>
          ))}
        </div>
        <button className="btn btn-block" style={{ marginTop: 18 }} onClick={bury}>＋ 내 관계 여기 안치하기</button>
      </div>
      {guest != null && <GuestModal onClose={() => setGuest(null)} />}
    </section>
  )
}

function GuestModal({ onClose }: { onClose: () => void }) {
  const toast = useToast()
  const [items, setItems] = useState([['익명의 조문객', '저도 똑같이 당했어요… 힘내세요 🥺'], ['익명의 조문객', '읽씹은 답장이 맞습니다. 잘 보내주세요'], ['익명의 조문객', '당신의 앞날을 빕니다 🙏']])
  const [v, setV] = useState('')
  const add = () => { if (!v.trim()) return; setItems([['나', v], ...items]); setV(''); toast('위로를 남겼어요 🤍') }
  return (
    <Modal title="💬 조문 방명록" onClose={onClose}>
      {items.map(([n, t], i) => <div className="guestbook" key={i}><div className="gb-name">{n}</div><div className="gb-text">{t}</div></div>)}
      <div className="summon-in" style={{ marginTop: 12 }}><input value={v} onChange={e => setV(e.target.value)} placeholder="위로 한마디 남기기…" onKeyDown={e => e.key === 'Enter' && add()} /><button onClick={add}>↑</button></div>
    </Modal>
  )
}
