import { useEffect, useState } from 'react'
import { api, type CemeteryData, type Comment, type Tomb } from '../api'
import { Modal, useToast } from '../components/ui'

export function Cemetery({ myEpitaph, myKind, myDays, myHanja }: { myEpitaph: string | null; myKind: 'curse' | 'chrys'; myDays: number | null; myHanja: string | null }) {
  const toast = useToast()
  const [data, setData] = useState<CemeteryData | null>(null)
  const [guest, setGuest] = useState<Tomb | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const load = () => api.cemetery().then(setData).catch(e => setErr(String(e)))
  useEffect(() => { load() }, [])

  async function hwa(t: Tomb) {
    if (t.flowered) { toast('이미 헌화했어요 🤍'); return }
    try {
      const r = await api.flower(t.id)
      setData(d => d && { ...d, tombs: d.tombs.map(x => x.id === t.id ? { ...x, flowers: r.flowers, flowered: true } : x), top: d.top.map(x => x.id === t.id ? { ...x, flowers: r.flowers } : x) })
      toast(r.already ? '이미 헌화했어요 🤍' : '헌화했어요 💐')
    } catch { toast('헌화 실패') }
  }
  async function bury() {
    if (!myEpitaph) { toast('먼저 진단서를 발급받아요'); return }
    try {
      const r = await api.bury({ epitaph: myEpitaph, kind: myKind, days: myDays, hanja: myKind === 'curse' ? myHanja : null })
      toast(r.existed ? '이미 안치돼 있어요 🪦' : '내 관계도 안치됐어요 🪦'); load()
    } catch { toast('안치 실패') }
  }

  return (
    <section className="page">
      <div className="wrap">
        <div className="cemetery-head">
          <h2 className="pen" style={{ fontSize: 34, fontWeight: 400 }}>🪦 공동묘지</h2>
          <div className="live-count"><span className="live-dot" />조문객 {data?.visitors ?? '…'}명 · 로그인 없이 헌화·방명록</div>
        </div>
        <p style={{ color: 'var(--text-soft)', fontSize: 14, marginBottom: 20 }}>떠나보낸 관계들이 잠든 곳 · 헌화는 묘비당 한 번, 방명록은 익명</p>
        {err && <div className="ctx-banner">공동묘지 서버에 연결 못 했어요 ({err.slice(0, 60)})</div>}
        {data && (
          <>
            <div className="legend-top">
              <div className="lt-h">🏆 전설의 묘지 TOP 3</div>
              {data.top.map((t, i) => (
                <div className="legend-row" key={t.id}><div className={'legend-rank r' + (i + 1)}>{i + 1}</div><div className="legend-body"><div className="lb-t">{t.epitaph}</div><div className="lb-m">묘비 #{t.id} · {t.kind === 'curse' ? `📜 저주봉인${t.hanja ? ` · ${t.hanja}` : ''}` : '🌼 헌화'}{t.days ? ` · 향년 ${t.days}일` : ''}</div></div><div className="legend-stat">💐 {t.flowers.toLocaleString()}</div></div>
              ))}
            </div>
            <div className="tomb-grid">
              {data.tombs.map(t => (
                <div className={'tomb' + (t.mine ? ' mine' : '')} key={t.id}>
                  <div className="tomb-top"><span className="tomb-icon">🪦</span><span className="tomb-id">묘비 #{t.id}{t.mine ? ' · 내 관계' : ''}{t.days ? ` · 향년 ${t.days}일` : ''}</span><span className={'tomb-badge ' + t.kind}>{t.kind === 'curse' ? '📜 저주봉인' : '🌼 헌화'}</span></div>
                  <div className="tomb-epitaph">{t.epitaph}</div>
                  {t.hanja && <div className="tiny" style={{ color: '#E8CE9E', marginTop: -6, marginBottom: 8 }}>符 {t.hanja}</div>}
                  <div className="tomb-meta"><span className={t.flowered ? 'hit' : ''} onClick={() => hwa(t)}>💐 <b>{t.flowers.toLocaleString()}</b></span><span onClick={() => setGuest(t)}>💬 {t.comments}</span></div>
                </div>
              ))}
            </div>
          </>
        )}
        <button className="btn btn-block" style={{ marginTop: 18 }} onClick={bury}>＋ 내 관계 여기 안치하기</button>
        <div className="tiny faint" style={{ marginTop: 8, textAlign: 'center' }}>지금은 이 컴퓨터의 서버에 저장돼요. 배포하면 모두가 같은 묘지를 봐요.</div>
      </div>
      {guest && <GuestModal tomb={guest} onClose={() => { setGuest(null); load() }} />}
    </section>
  )
}

function GuestModal({ tomb, onClose }: { tomb: Tomb; onClose: () => void }) {
  const toast = useToast()
  const [items, setItems] = useState<Comment[]>([])
  const [v, setV] = useState('')
  const [busy, setBusy] = useState(false)
  useEffect(() => { api.comments(tomb.id).then(r => setItems(r.comments)).catch(() => {}) }, [tomb.id])
  const add = async () => {
    if (!v.trim() || busy) return
    setBusy(true)
    try { const r = await api.addComment(tomb.id, v); setItems([{ id: Date.now(), nick: r.nick + ' (나)', text: r.text, created: '' }, ...items]); setV(''); toast('위로를 남겼어요 🤍') }
    catch { toast('등록 실패') } finally { setBusy(false) }
  }
  return (
    <Modal title={`💬 조문 방명록 · 묘비 #${tomb.id}`} onClose={onClose}>
      <div className="tomb-epitaph" style={{ minHeight: 0, marginBottom: 12 }}>{tomb.epitaph}</div>
      {items.length === 0 && <div className="muted tiny" style={{ marginBottom: 8 }}>첫 조문객이 되어주세요.</div>}
      {items.map(c => <div className="guestbook" key={c.id}><div className="gb-name">{c.nick}</div><div className="gb-text">{c.text}</div></div>)}
      <div className="summon-in" style={{ marginTop: 12 }}><input value={v} onChange={e => setV(e.target.value)} placeholder="위로 한마디 남기기… (익명)" onKeyDown={e => e.key === 'Enter' && add()} /><button onClick={add} disabled={busy}>↑</button></div>
    </Modal>
  )
}
