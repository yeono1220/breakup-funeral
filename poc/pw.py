"""PrintWindow 기반 오프스크린 캡처 + PostMessage 클릭 유틸 (PoC 공용)."""
import ctypes, time
from ctypes import wintypes
from PIL import Image
u, g = ctypes.windll.user32, ctypes.windll.gdi32
u.SetProcessDPIAware()

class BMI(ctypes.Structure):
    _fields_ = [("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG), ("biHeight", wintypes.LONG),
                ("biPlanes", wintypes.WORD), ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
                ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", wintypes.LONG), ("biYPelsPerMeter", wintypes.LONG),
                ("biClrUsed", wintypes.DWORD), ("biClrImportant", wintypes.DWORD)]

def capture(hwnd, path=None):
    r = wintypes.RECT(); u.GetWindowRect(hwnd, ctypes.byref(r))
    w, h = r.right - r.left, r.bottom - r.top
    hdc = u.GetWindowDC(hwnd); mdc = g.CreateCompatibleDC(hdc)
    bmp = g.CreateCompatibleBitmap(hdc, w, h); g.SelectObject(mdc, bmp)
    u.PrintWindow(hwnd, mdc, 2)
    bmi = BMI(ctypes.sizeof(BMI), w, -h, 1, 32, 0, 0, 0, 0, 0, 0)
    buf = ctypes.create_string_buffer(w * h * 4)
    g.GetDIBits(mdc, bmp, 0, h, buf, ctypes.byref(bmi), 0)
    img = Image.frombuffer("RGBA", (w, h), buf, "raw", "BGRA", 0, 1).convert("RGB")
    g.DeleteObject(bmp); g.DeleteDC(mdc); u.ReleaseDC(hwnd, hdc)
    if path: img.save(path)
    return img

def window_rect(hwnd):
    r = wintypes.RECT(); u.GetWindowRect(hwnd, ctypes.byref(r))
    return r.left, r.top, r.right, r.bottom

def post_click(hwnd, wx, wy):
    """창 좌상단 기준 (wx, wy)에 클릭 메시지 전송. 포커스/z-order 안 건드림."""
    l, t, _, _ = window_rect(hwnd)
    pt = wintypes.POINT(l + wx, t + wy)
    u.ScreenToClient(hwnd, ctypes.byref(pt))
    lp = (pt.y << 16) | (pt.x & 0xFFFF)
    u.PostMessageW(hwnd, 0x0200, 0, lp)          # WM_MOUSEMOVE
    u.PostMessageW(hwnd, 0x0201, 1, lp)          # WM_LBUTTONDOWN
    time.sleep(0.05)
    u.PostMessageW(hwnd, 0x0202, 0, lp)          # WM_LBUTTONUP

def find_kakao_windows():
    from pywinauto import Desktop
    return [w for w in Desktop(backend="uia").windows() if "EVA_" in (w.element_info.class_name or "")]
