import { useEffect, useState } from 'react'
import type { CemeteryData, Comment, Tomb } from '../api'
import { store, usingSupabase } from '../cemeteryStore'
import { Modal, useToast } from '../components/ui'
import { Icon } from '../components/Icons'

/* 묘비 그리드: 자동 채움 + '내 관계' 묘비는 두 칸 (한 열뿐일 땐 span 해제) */
const GRID_CSS = `
.tomb-grid.tg-flow{grid-template-columns:repeat(auto-fill,minmax(260px,1fr));}
.tomb-grid.tg-flow .tomb.span2{grid-column:span 2;}
@media (max-width:600px){.tomb-grid.tg-flow{grid-template-columns:1fr;}.tomb-grid.tg-flow .tomb.span2{grid-column:auto;}}
`

export function Cemetery({ myEpitaph, myKind, myDays, myHanja }: { myEpitaph: string | null; myKind: 'curse' | 'chrys'; myDays: number | null; myHanja: string | null }) {
  const toast = useToast()
  const [data, setData] = useState<CemeteryData | null>(null)
  const [guest, setGuest] = useState<Tomb | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const load = () => store.list().then(setData).catch(e => setErr(String(e)))
  useEffect(() => { load() }, [])

  async function hwa(t: Tomb) {
    if (t.flowered) { toast('이미 헌화했어'); return }
    try {
      const r = await store.flower(t.id)
      setData(d => d && { ...d, tombs: d.tombs.map(x => x.id === t.id ? { ...x, flowers: r.flowers, flowered: true } : x), top: d.top.map(x => x.id === t.id ? { ...x, flowers: r.flowers } : x) })
      toast(r.already ? '이미 헌화했어' : '헌화했어')
    } catch { toast('헌화 실패') }
  }
  async function bury() {
    if (!myEpitaph) { toast('먼저 진단서부터 받자'); return }
    try {
      const r = await store.bury({ epitaph: myEpitaph, kind: myKind, days: myDays, hanja: myKind === 'curse' ? myHanja : null })
      toast(r.existed ? '이미 안치돼 있어' : '내 관계도 안치했어'); load()
    } catch { toast('안치 실패') }
  }

  const mineIdx = data ? data.tombs.findIndex(t => t.mine) : -1

  return (
    <section className="page">
      <style>{GRID_CSS}</style>
      <div className="wrap">
        <div className="cemetery-head reveal" style={{ ['--i' as any]: 0 }}>
          <h2 className="page-title" style={{ display: 'flex', alignItems: 'center', gap: 8 }}><Icon name="tomb" size={18} />공동묘지</h2>
          <div className="live-count"><span className="live-dot" />{data?.visitors != null ? <>다녀간 조문객 <span className="num">{data.visitors}</span>명 · </> : null}로그인 없이 헌화·방명록</div>
        </div>
        <p className="reveal" style={{ ['--i' as any]: 1, color: 'var(--text-soft)', fontSize: 14, marginBottom: 20 }}>떠나보낸 관계들이 잠든 곳 · 헌화는 묘비당 한 번, 방명록은 익명</p>
        {err && <div className="ctx-banner">공동묘지 서버에 연결 못 했어 ({err.slice(0, 60)})</div>}
        {data && (
          <>
            <div className="legend-top reveal" style={{ ['--i' as any]: 2 }}>
              <div className="lt-h">전설의 묘지 TOP 3</div>
              {data.top.map((t, i) => (
                <div className="legend-row" key={t.id}><div className={'legend-rank r' + (i + 1)}>{i + 1}</div><div className="legend-body"><div className="lb-t">{t.epitaph}</div><div className="lb-m">묘비 #{t.id} · {t.kind === 'curse' ? '저주봉인' : '헌화'}{t.hanja && <span className="legend-amulet">符 {t.hanja}</span>}{t.days ? ` · 향년 ${t.days}일` : ''}</div></div><div className="legend-stat">💐 <span className="num">{t.flowers.toLocaleString()}</span></div></div>
              ))}
            </div>
            <div className="tomb-grid tg-flow">
              {data.tombs.map((t, i) => (
                <div
                  className={'tomb reveal' + (t.mine ? ' mine' : '') + (t.hanja ? ' has-amulet' : '') + (i === mineIdx ? ' span2' : '')}
                  style={{ ['--i' as any]: Math.min(i, 8) + 3 }}
                  key={t.id}
                >
                  {t.hanja && <MiniAmulet hanja={t.hanja} />}
                  <div className="tomb-top">
                    <span className="tomb-icon" style={{ display: 'inline-flex', color: 'var(--text-soft)' }}><Icon name="tomb" size={20} /></span>
                    <span className="tomb-id">묘비 #{t.id}{t.mine ? ' · 내 관계' : ''}{t.days ? ` · 향년 ${t.days}일` : ''}</span>
                    {!t.hanja && <span className={'tomb-badge ' + t.kind}>{t.kind === 'curse' ? '저주봉인' : '헌화'}</span>}
                  </div>
                  <div className="tomb-epitaph">{t.epitaph}</div>
                  <div className="tomb-meta">
                    <span className={t.flowered ? 'hit' : ''} onClick={() => hwa(t)}>💐 <b className="num">{t.flowers.toLocaleString()}</b></span>
                    <span onClick={() => setGuest(t)}><Icon name="comment" size={14} /><span className="num" style={{ fontWeight: 400 }}>{t.comments}</span></span>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
        <button className="btn btn-block" style={{ marginTop: 40 }} onClick={bury}>내 관계 여기 안치하기</button>
        <div className="tiny faint" style={{ marginTop: 8, textAlign: 'center' }}>{usingSupabase ? '모두가 같은 묘지를 봐. 로그인 없이 헌화하고 한마디 남길 수 있어' : '지금은 내 컴퓨터에만 저장돼'}</div>
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
  useEffect(() => { store.comments(tomb.id).then(r => setItems(r.comments)).catch(() => {}) }, [tomb.id])
  const add = async () => {
    if (!v.trim() || busy) return
    setBusy(true)
    try { const r = await store.addComment(tomb.id, v); setItems([{ id: Date.now(), nick: r.nick + ' (나)', text: r.text, created: '' }, ...items]); setV(''); toast('한마디 남겼어') }
    catch { toast('등록 실패') } finally { setBusy(false) }
  }
  return (
    <Modal title={`조문 방명록 · 묘비 #${tomb.id}`} onClose={onClose}>
      <div className="tomb-epitaph" style={{ minHeight: 0, marginBottom: 12 }}>{tomb.epitaph}</div>
      {items.length === 0 && <div className="muted tiny" style={{ marginBottom: 8 }}>첫 조문객이 돼 줘</div>}
      {items.map((c, i) => <div className="guestbook reveal" style={{ ['--i' as any]: Math.min(i, 6) }} key={c.id}><div className="gb-name">{c.nick}</div><div className="gb-text">{c.text}</div></div>)}
      <div className="summon-in" style={{ marginTop: 12 }}><input value={v} onChange={e => setV(e.target.value)} placeholder="위로 한마디 남기기… (익명)" onKeyDown={e => e.key === 'Enter' && add()} /><button onClick={add} disabled={busy} aria-label="남기기">↑</button></div>
    </Modal>
  )
}

/** 묘비 카드 모서리에 꽂힌 미니 부적. 공백/줄바꿈으로 나뉜 구절은 세로 열로. */
function MiniAmulet({ hanja }: { hanja: string }) {
  const cols = hanja.split(/\s+/).filter(Boolean).slice(0, 2)
  return (
    <div className={"tomb-amulet" + (hanja.replace(/\s/g, "").length > 4 ? " long" : "")} title={hanja}>
      <div className="ta-hanja">{cols.map((c, i) => <span key={i}>{c}</span>)}</div>
      <div className="ta-seal">封</div>
    </div>
  )
}
