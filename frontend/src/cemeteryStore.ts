/** 공동묘지 저장소 어댑터: Supabase(env 있으면, 영구·공유) → 없으면 백엔드 /cemetery. */
import { createClient, type SupabaseClient } from '@supabase/supabase-js'
import { api, anonId, type CemeteryData, type Comment, type Tomb } from './api'

const URL_ = (import.meta.env.VITE_SUPABASE_URL as string | undefined) || ''
const KEY = (import.meta.env.VITE_SUPABASE_ANON_KEY as string | undefined) || ''
let sb: SupabaseClient | null = null
export const usingSupabase = !!(URL_ && KEY)
if (usingSupabase) sb = createClient(URL_, KEY)

const nick = (anon: string) => { let h = 0; for (const ch of anon) h = (h * 31 + ch.charCodeAt(0)) >>> 0; return `익명의 조문객 #${(h % 900) + 100}` }

export const store = {
  async list(): Promise<CemeteryData> {
    if (!sb) return api.cemetery()
    const anon = anonId()
    const [{ data: rows, error }, { data: mine }, { data: vis }] = await Promise.all([
      sb.from('tombs').select('id, epitaph, kind, days, hanja, owner, flowers, created_at, guestbook(count)').order('created_at', { ascending: false }),
      sb.rpc('my_flowers', { p_anon: anon }),
      sb.rpc('visit', { p_anon: anon }),   // 방문 기록 + 실제 조문객 수 (같은 브라우저는 1명)
    ])
    if (error) throw error
    const flowered = new Set<number>((mine as number[] | null) ?? [])
    const tombs: Tomb[] = (rows ?? []).map(r => ({
      id: r.id, epitaph: r.epitaph, kind: r.kind, days: r.days, hanja: r.hanja, flowers: r.flowers,
      comments: (r.guestbook as unknown as { count: number }[] | null)?.[0]?.count ?? 0,
      mine: r.owner === anon, flowered: flowered.has(r.id), created: r.created_at,
    }))
    return { tombs, top: [...tombs].sort((a, b) => b.flowers - a.flowers).slice(0, 3), visitors: (vis as number | null) ?? null }
  },
  async bury(b: { epitaph: string; kind: 'chrys' | 'curse'; days?: number | null; hanja?: string | null }) {
    if (!sb) return api.bury(b)
    const anon = anonId()
    const { data: ex } = await sb.from('tombs').select('id').eq('owner', anon).eq('epitaph', b.epitaph).maybeSingle()
    if (ex) return { id: ex.id as number, existed: true }
    const { data, error } = await sb.from('tombs').insert({ epitaph: b.epitaph.slice(0, 120), kind: b.kind, days: b.days ?? null, hanja: b.hanja ?? null, owner: anon }).select('id').single()
    if (error) throw error
    return { id: data.id as number, existed: false }
  },
  async flower(id: number) {
    if (!sb) return api.flower(id)
    const { data, error } = await sb.rpc('flower', { p_tomb: id, p_anon: anonId() })
    if (error) throw error
    const row = (data as { flowers: number; already: boolean }[] | null)?.[0]
    return { flowers: row?.flowers ?? 0, already: row?.already ?? false }
  },
  async comments(id: number): Promise<{ comments: Comment[] }> {
    if (!sb) return api.comments(id)
    const { data, error } = await sb.from('guestbook').select('id, nick, text, created_at').eq('tomb_id', id).order('id', { ascending: false }).limit(100)
    if (error) throw error
    return { comments: (data ?? []).map(r => ({ id: r.id, nick: r.nick, text: r.text, created: r.created_at })) }
  },
  async addComment(id: number, text: string) {
    if (!sb) return api.addComment(id, text)
    const anon = anonId(); const n = nick(anon)
    const { error } = await sb.from('guestbook').insert({ tomb_id: id, anon, nick: n, text: text.trim().slice(0, 200) })
    if (error) throw error
    return { nick: n, text: text.trim().slice(0, 200) }
  },
}
