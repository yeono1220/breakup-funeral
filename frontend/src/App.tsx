import { useCallback, useEffect, useState } from 'react'
import { api, type Persona, type Relationship } from './api'
import { ToastProvider, useToast } from './components/ui'
import { Analyze } from './pages/Analyze'
import { Cemetery } from './pages/Cemetery'
import { Diagnosis, displayName } from './pages/Diagnosis'
import { Tools } from './pages/Tools'
import { Tribute } from './pages/Tribute'
import { Upload } from './pages/Upload'

type Page = 'upload' | 'analyze' | 'diagnosis' | 'tribute' | 'cemetery' | 'tools'

export default function App() {
  return <ToastProvider><Shell /></ToastProvider>
}

function Shell() {
  const toast = useToast()
  const [page, setPage] = useState<Page>('upload')
  const [pair, setPair] = useState<{ me: string; target: string } | null>(null)
  const [data, setData] = useState<Relationship | null>(null)
  const [persona, setPersona] = useState<Persona>({ mbti: null, attachment: null, note: null })
  const [buriedKind, setBuriedKind] = useState<'chrys' | 'curse'>('chrys')

  // 이전 세션 복원
  useEffect(() => {
    api.targets().then(t => { if (t.me && t.target) { setPair({ me: t.me, target: t.target }); api.persona(t.target).then(setPersona).catch(() => {}); setPage('analyze') } }).catch(() => {})
  }, [])

  const go = (p: Page) => {
    if ((p === 'diagnosis' || p === 'tribute') && !data) { toast('먼저 카톡을 올려 진단서를 발급받아요'); setPage('upload'); return }
    setPage(p); window.scrollTo(0, 0)
  }
  const start = (me: string, target: string) => { setPair({ me, target }); api.persona(target).then(setPersona).catch(() => {}); setPage('analyze') }
  const onDone = useCallback((r: Relationship) => { setData(r); setPage('diagnosis'); window.scrollTo(0, 0) }, [])
  const onError = useCallback((e: string) => { toast('분석 실패: ' + e.slice(0, 80)); setPage('upload') }, [toast])

  const alias = persona.note === 'alias'
  const name = pair ? displayName(pair.target, alias) : ''
  const epitaph = data?.last_message ? `"${data.last_message.text.slice(0, 30)}" — 향년 ${Math.max(1, Math.round((new Date(data.range[1]).getTime() - new Date(data.range[0]).getTime()) / 86400000))}일` : null
  const navOn = page === 'cemetery' ? 'cemetery' : page === 'tools' ? 'tools' : 'funeral'

  return (
    <>
      <div className="topbar">
        <div className="brand" onClick={() => go('upload')}><span className="logo">🪦 이별 장례식</span><span className="tag">AI 관계 추모 센터</span></div>
        <div className="nav">
          <a className={navOn === 'funeral' ? 'on' : ''} onClick={() => go(data ? 'diagnosis' : 'upload')}>내 장례식</a>
          <a className={navOn === 'cemetery' ? 'on' : ''} onClick={() => go('cemetery')}>공동묘지</a>
          <a className={navOn === 'tools' ? 'on' : ''} onClick={() => go('tools')}>현실 치료실</a>
        </div>
      </div>
      {page === 'upload' && <Upload onStart={start} />}
      {page === 'analyze' && pair && <Analyze target={pair.target} onDone={onDone} onError={onError} />}
      {page === 'diagnosis' && data && <Diagnosis data={data} persona={persona} alias={alias} onNext={() => go('tribute')} />}
      {page === 'tribute' && data && <Tribute data={data} name={name} onBack={() => go('diagnosis')} onNext={() => go('cemetery')} onBuried={setBuriedKind} />}
      {page === 'cemetery' && <Cemetery myEpitaph={epitaph} myKind={buriedKind} />}
      {page === 'tools' && <Tools name={name || '그 사람'} />}
    </>
  )
}
