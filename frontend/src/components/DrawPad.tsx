import { useEffect, useRef, useState } from 'react'

/** 그림판: X 얼굴을 마우스/터치로 그리거나 이미지를 불러온다. onChange에 PNG data URL. */
const COLORS = ['#334155', '#D96A5E', '#F4A9A0', '#70bbfd', '#F0C64A', '#58a618']
const SIZES = [3, 7, 14]
const W = 300

export function DrawPad({ value, onChange }: { value?: string | null; onChange: (dataUrl: string | null) => void }) {
  const ref = useRef<HTMLCanvasElement>(null)
  const [color, setColor] = useState(COLORS[0])
  const [size, setSize] = useState(SIZES[1])
  const [eraser, setEraser] = useState(false)
  const drawing = useRef(false)
  const last = useRef<[number, number] | null>(null)
  const history = useRef<ImageData[]>([])

  const ctx = () => ref.current!.getContext('2d')!

  useEffect(() => {
    const c = ctx()
    c.fillStyle = '#ffffff'; c.fillRect(0, 0, W, W)
    if (value) { const img = new Image(); img.onload = () => c.drawImage(img, 0, 0, W, W); img.src = value }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const pos = (e: React.PointerEvent) => {
    const r = ref.current!.getBoundingClientRect()
    return [((e.clientX - r.left) / r.width) * W, ((e.clientY - r.top) / r.height) * W] as [number, number]
  }
  const down = (e: React.PointerEvent) => {
    history.current.push(ctx().getImageData(0, 0, W, W)); if (history.current.length > 20) history.current.shift()
    drawing.current = true; last.current = pos(e); (e.target as Element).setPointerCapture(e.pointerId); move(e)
  }
  const move = (e: React.PointerEvent) => {
    if (!drawing.current) return
    const c = ctx(); const p = pos(e); const l = last.current ?? p
    c.lineCap = 'round'; c.lineJoin = 'round'; c.lineWidth = eraser ? size * 3 : size
    c.strokeStyle = eraser ? '#ffffff' : color
    c.beginPath(); c.moveTo(l[0], l[1]); c.lineTo(p[0], p[1]); c.stroke()
    last.current = p
  }
  const up = () => { if (!drawing.current) return; drawing.current = false; last.current = null; onChange(ref.current!.toDataURL('image/png')) }
  const undo = () => { const h = history.current.pop(); if (h) { ctx().putImageData(h, 0, 0); onChange(ref.current!.toDataURL('image/png')) } }
  const clear = () => { history.current.push(ctx().getImageData(0, 0, W, W)); const c = ctx(); c.fillStyle = '#fff'; c.fillRect(0, 0, W, W); onChange(null) }
  const load = (f: File) => {
    const img = new Image()
    img.onload = () => {
      const c = ctx(); c.fillStyle = '#fff'; c.fillRect(0, 0, W, W)
      const s = Math.max(W / img.width, W / img.height); const w = img.width * s, h = img.height * s
      c.drawImage(img, (W - w) / 2, (W - h) / 2, w, h); onChange(ref.current!.toDataURL('image/png'))
    }
    img.src = URL.createObjectURL(f)
  }

  return (
    <div className="drawpad">
      <canvas ref={ref} width={W} height={W} onPointerDown={down} onPointerMove={move} onPointerUp={up} onPointerCancel={up} />
      <div className="dp-tools">
        <div className="dp-row">
          {COLORS.map(c => <button key={c} className={'dp-color' + (!eraser && color === c ? ' on' : '')} style={{ background: c }} onClick={() => { setColor(c); setEraser(false) }} aria-label={c} />)}
          <button className={'dp-btn' + (eraser ? ' on' : '')} onClick={() => setEraser(e => !e)}>지우개</button>
        </div>
        <div className="dp-row">
          {SIZES.map(s => <button key={s} className={'dp-btn' + (size === s ? ' on' : '')} onClick={() => setSize(s)}><i style={{ width: s + 4, height: s + 4 }} /></button>)}
          <button className="dp-btn" onClick={undo}>되돌리기</button>
          <button className="dp-btn" onClick={clear}>전부 지우기</button>
          <label className="dp-btn">사진 불러오기<input type="file" accept="image/*" hidden onChange={e => e.target.files?.[0] && load(e.target.files[0])} /></label>
        </div>
      </div>
    </div>
  )
}
