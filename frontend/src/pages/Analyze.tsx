import { useEffect, useState } from 'react'
import { api, type Relationship } from '../api'
import { Char } from '../components/Char'

const LINES = [['📖', '대화 읽는 중'], ['💔', '사망 시점 추적 중'], ['🔢', '사망 원인 계산 중'], ['🪦', '진단서 발급 중']]

export function Analyze({ target, onDone, onError }: { target: string; onDone: (r: Relationship) => void; onError: (e: string) => void }) {
  const [i, setI] = useState(0)
  useEffect(() => {
    let data: Relationship | null = null, err: string | null = null
    api.relationship(target).then(r => { data = r }).catch(e => { err = String(e) })
    const t = setInterval(() => setI(x => x + 1), 850)
    const check = setInterval(() => {
      if (err) { clearInterval(t); clearInterval(check); onError(err) }
    }, 300)
    const finish = setTimeout(() => {
      const wait = setInterval(() => {
        if (data) { clearInterval(wait); clearInterval(t); clearInterval(check); onDone(data) }
        if (err) { clearInterval(wait) }
      }, 200)
    }, LINES.length * 850 + 400)
    return () => { clearInterval(t); clearInterval(check); clearTimeout(finish) }
  }, [target, onDone, onError])

  return (
    <section className="page an">
      <div className="wrap wrap-narrow">
        <div className="up-char" style={{ marginBottom: 8, width: 110 }}><Char mood="sad" size={110} /></div>
        <div className="up-logo" style={{ fontSize: 34 }}>부검 중입니다…</div>
        <div className="log-box">
          {LINES.map(([ic, t], k) => (
            <div key={t} className={'log-line' + (k < i ? ' done' : k === i ? ' active' : '')}><span className="log-ic">{ic}</span> {t}</div>
          ))}
        </div>
      </div>
    </section>
  )
}
