import { useCallback, useEffect, useState } from 'react'
import { api, type Amulet, type Persona, type Relationship } from './api'
import { ToastProvider, useToast } from './components/ui'
import { CoachChat, type CoachMsg } from './components/CoachChat'
import { Icon } from './components/Icons'
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
  const [jump, setJump] = useState<'persona' | undefined>(undefined)
  const [pair, setPair] = useState<{ me: string; target: string } | null>(null)
  const [data, setData] = useState<Relationship | null>(null)
  const [persona, setPersona] = useState<Persona>({ mbti: null, attachment: null, note: null })
  const [buriedKind, setBuriedKind] = useState<'chrys' | 'curse'>('chrys')
  const [amulet, setAmulet] = useState<Amulet | null>(null)
  const [coachOpen, setCoachOpen] = useState(false)
  const [coachMsgs, setCoachMsgs] = useState<CoachMsg[]>([])   // 페이지를 옮겨도 상담은 이어진다

  // 이전 세션 복원
  useEffect(() => {
    api.targets().then(t => { if (t.me && t.target) { setPair({ me: t.me, target: t.target }); api.persona(t.target).then(setPersona).catch(() => {}); setPage('analyze') } }).catch(() => {})
  }, [])

  const go = (p: Page) => {
    if ((p === 'diagnosis' || p === 'tribute') && !data) { toast('먼저 카톡을 올려 진단서를 발급받아요'); setPage('upload'); return }
    setPage(p); window.scrollTo(0, 0)
  }
  const start = (me: string, target: string) => { setJump(undefined); setPair({ me, target }); api.persona(target).then(setPersona).catch(() => {}); setPage('analyze') }
  const onDone = useCallback((r: Relationship) => { setData(r); if (pair) api.persona(pair.target).then(setPersona).catch(() => {}); setPage('diagnosis'); window.scrollTo(0, 0) }, [pair])
  // 코치가 사정을 기록하면 진단서(향년·사인·단계)를 새 컨텍스트로 다시 받는다
  const refresh = useCallback(() => {
    if (!pair) return
    api.relationship(pair.target).then(setData).catch(() => {})
    api.persona(pair.target).then(setPersona).catch(() => {})
  }, [pair])
  const onError = useCallback((e: string) => { toast('분석 실패: ' + e.slice(0, 80)); setPage('upload') }, [toast])

  const alias = persona.alias ?? persona.note === 'alias'
  const name = pair ? displayName(pair.target, alias) : ''
  const startIso = data ? (data.user_context?.started_at ? data.user_context.started_at + 'T00:00:00' : data.user_context?.suggested_start ? data.user_context.suggested_start + 'T00:00:00' : data.range[0]) : ''
  const endIso = data ? (data.user_context?.ended_at ? data.user_context.ended_at + 'T00:00:00' : data.range[1]) : ''
  const days = data ? Math.max(1, Math.round((new Date(endIso).getTime() - new Date(startIso).getTime()) / 86400000)) : null
  // 비문: 마지막 말이 의미 있으면 인용, 아니면 부적 사자성어 → 이별 사유 → 사망 원인 1위 순
  const lastText = data?.last_message?.text?.trim() ?? ''
  const meaningful = lastText.length >= 4 && !/^(사진|이모티콘|동영상)/.test(lastText)
  const epitaph = !data ? null
    : meaningful ? `"${lastText.slice(0, 30)}"`
    : buriedKind === 'curse' && amulet ? `${amulet.hanja.replace(/\n/g, ' ')} — ${amulet.reading}`
    : data.user_context?.ending_label ? `${data.user_context.ending_label}으로 떠나보냄`
    : data.causes?.causes?.[0] ? `사인: ${data.causes.causes[0].label}` : `향년 ${days}일`
  const navOn = page === 'cemetery' ? 'cemetery' : page === 'tools' ? 'tools' : 'funeral'

  return (
    <>
      <div className="topbar">
        <div className="brand" onClick={() => go('upload')}><span className="logo"><Icon name="tomb" size={18} /> 이별 장례식</span><span className="tag">AI 관계 추모 센터</span></div>
        <div className="nav">
          <a className={navOn === 'funeral' ? 'on' : ''} onClick={() => go(data ? 'diagnosis' : 'upload')}>내 장례식</a>
          <a className={navOn === 'cemetery' ? 'on' : ''} onClick={() => go('cemetery')}>공동묘지</a>
          <a className={navOn === 'tools' ? 'on' : ''} onClick={() => go('tools')}>현실 치료실</a>
        </div>
      </div>
      {page === 'upload' && <Upload onStart={start} jumpTo={jump} />}
      {page === 'analyze' && pair && <Analyze target={pair.target} onDone={onDone} onError={onError} />}
      {page === 'diagnosis' && data && <Diagnosis data={data} persona={persona} alias={alias} onNext={() => go('tribute')} onEditContext={() => { setJump('persona'); setPage('upload'); window.scrollTo(0, 0) }} onCoach={() => setCoachOpen(true)} />}
      {page === 'tribute' && data && <Tribute data={data} name={name} portrait={persona.portrait ?? null} onBack={() => go('diagnosis')} onNext={() => go('cemetery')} onBuried={setBuriedKind} onAmulet={setAmulet} />}
      {page === 'cemetery' && <Cemetery myEpitaph={epitaph} myKind={buriedKind} myDays={days} myHanja={amulet ? amulet.hanja.replace(/\n/g, ' ') : null} />}
      {page === 'tools' && <Tools name={name || '그 사람'} onCoach={pair ? () => setCoachOpen(true) : undefined} />}
      {coachOpen && <CoachChat name={name || '그 사람'} msgs={coachMsgs} setMsgs={setCoachMsgs} onContextUpdated={refresh} onClose={() => setCoachOpen(false)} />}
    </>
  )
}
