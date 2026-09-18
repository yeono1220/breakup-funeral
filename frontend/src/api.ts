const BASE = '/api'

async function j<T>(r: Response): Promise<T> {
  if (!r.ok) throw new Error(`${r.status} ${await r.text()}`)
  return r.json()
}

export const api = {
  loadSample: () => fetch(`${BASE}/load_sample`, { method: 'POST' }).then(j<{ added: number; senders: Sender[] }>),
  upload: (files: File[]) => {
    const fd = new FormData()
    files.forEach(f => fd.append('files', f))
    return fetch(`${BASE}/upload`, { method: 'POST', body: fd }).then(j<{ added: number; senders: Sender[] }>)
  },
  senders: () => fetch(`${BASE}/senders`).then(j<{ senders: Sender[]; me: string | null }>),
  setMe: (me: string) => fetch(`${BASE}/me`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ me }) }).then(j),
  setTarget: (target: string) => fetch(`${BASE}/target`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ target }) }).then(j),
  targets: () => fetch(`${BASE}/targets`).then(j<{ me: string; target: string | null; candidates: Candidate[] }>),
  relationship: (p: string) => fetch(`${BASE}/relationship/${encodeURIComponent(p)}`).then(j<Relationship>),
  compare: (a: string, b: string) => fetch(`${BASE}/compare?a=${encodeURIComponent(a)}&b=${encodeURIComponent(b)}`).then(j<Compare>),
  around: (id: number) => fetch(`${BASE}/messages/around/${id}`).then(j<{ messages: Msg[]; focus: number }>),
  clear: () => fetch(`${BASE}/data`, { method: 'DELETE' }).then(j),
  chat: (messages: { role: string; content: string }[]) =>
    fetch(`${BASE}/chat`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ messages }) }),
  persona: (person: string) => fetch(`${BASE}/persona/${encodeURIComponent(person)}`).then(j<Persona>),
  setPersona: (p: Persona & { person: string }) => fetch(`${BASE}/persona`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(p) }).then(j),
  summon: (messages: { role: string; content: string }[]) =>
    fetch(`${BASE}/summon`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ messages }) }).then(j<{ reply: string; fallback?: boolean }>),
  eulogy: () => fetch(`${BASE}/eulogy`).then(j<{ text: string; fallback?: boolean }>),
  curse: () => fetch(`${BASE}/curse`).then(j<Amulet>),
  lastMessage: () => fetch(`${BASE}/last_message`).then(j<{ message: Msg | null }>),
}

export type Ending = 'ghosted' | 'dumped' | 'dumper' | 'faded' | 'mutual' | 'ongoing'
export type Persona = {
  mbti: string | null; attachment: string | null
  ending?: Ending | null; context?: string | null; ended_at?: string | null; started_at?: string | null
  alias?: boolean; portrait?: string | null; ending_label?: string | null; note?: string | null
}
export type Amulet = { hanja: string; reading: string; meaning: string; attachment: string | null; attachment_label: string; line: string; text: string; fallback?: boolean }

export type Sender = { sender: string; n: number }
export type Candidate = { name: string; messages: number; one_on_one: boolean }
export type Msg = { id: number; room: string; sender: string; text: string; ts: string }
export type Component = { label: string; value: number; weight: number; contrib: number }
export type Week = {
  week_start: string; temp: number | null; components: Record<string, Component>
  n: number; per_day: number; their_med: number | null; my_med: number | null; my_start_share: number | null; greetings: number
}
export type Event = {
  week_start: string; temp: number; delta: number; direction: 'up' | 'down'
  top_factor: { key: string; label: string; delta_contrib: number } | null
  evidence_ids: number[]; evidence_preview: { id: number; sender: string; text: string; ts: string }[]; title: string | null
}
export type Segment = { stage: string; label: string; start: string; end: string; weeks: number; confidence: number }
export type Relationship = {
  me: string; target: string; n_messages: number; range: [string, string]
  temperature: { temp: number | null; delta_week: number | null; components: Record<string, Component>; top_factor: { label: string; delta_contrib: number; direction: string } | null; sparse: boolean; n_window: number }
  weekly: Week[]; events: Event[]
  stages: { segments: Segment[]; current_stage: string; current_label: string; lens: string; data_lens?: string; data_label?: string }
  symmetry: { bars: { key: string; label: string; me: number; them: number; share: number | null }[]; reply: { my_median_min: number | null; their_median_min: number | null } }
  bias: { reply_speed: { to_target_min: number | null; to_others_min: number | null; times_faster: number | null }; length: { to_target: number; to_others: number; times: number | null }; kkk: { to_target: number; to_others: number; times: number | null }; questions: { times: number | null }; late_night: { with_target: number; with_others: number }; baseline_people: number }
  waiting: { msg_id: number; text: string; ts: string; age_hours: number; reason: string; usual_reply_min: number | null; times_slower: number | null } | null
  signals: { verdict: 'mutual' | 'me_only' | 'them_only' | 'friends'; title: string; desc: string
    me: { score: number | null; parts: { label: string; score: number; weight: number }[] }
    them: { score: number | null; parts: { label: string; score: number; weight: number }[] }
    facts: string[]; n_baseline_people: number; low_confidence: boolean }
  last_message: Msg | null
  causes?: { causes: { key: string; label: string; pct: number; evidence: string }[]; note: string | null
    peak: { from: string; to: string; n: number; per_day: number } | null; last: { from: string; to: string; n: number; per_day: number } | null; overlap: number; silence_days: number }
  user_context?: { ending: Ending | null; ending_label: string | null; context: string | null; ended_at: string | null; started_at: string | null; suggested_start: string | null; overrides_stage: boolean }
}
export type Compare = { a: string; b: string; rows: Record<string, null | { n_messages: number; temp: number | null; my_reply_min: number | null; their_reply_min: number | null; my_start_share: number | null; my_chars_share: number | null; my_avg_len: number; my_kkk: number; late_night: number }> }
