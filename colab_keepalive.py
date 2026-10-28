"""Colab 탭이 유휴로 끊기지 않게 주기적으로 '사용 중' 신호를 보낸다 (Windows).

- 대상: 창 제목에 --title 문자열이 들어간 Colab 브라우저 창 하나
- 동작: 창을 앞으로 → 페이지 가운데에서 살짝 스크롤 후 되돌림 → Shift 한 번 → 원래 창으로 복귀
  셀을 클릭하거나 글자를 입력하지 않으므로 노트북 내용은 바뀌지 않는다.
- 사용자가 PC를 쓰는 중(최근 --idle-min 분 안에 입력)이면 건너뛴다.
- 실행 중에는 Windows 절전·화면 꺼짐을 막는다.
- 종료: Ctrl+Alt+Q (어느 창에서든), 콘솔에서 Ctrl+C, 또는 마우스를 화면 왼쪽 위 구석으로.

준비: Colab 탭을 브라우저의 '별도 창'으로 떼어 두고 그 창에서 Colab 탭이 활성 탭이어야 한다
(창 제목은 활성 탭 제목만 보인다). 최소화는 해도 된다.

    python colab_keepalive.py --title "내노트북이름"   # 5분 간격
    python colab_keepalive.py --dry-run               # 창 찾기·유휴 시간만 출력, 조작 안 함
"""
import argparse
import ctypes
from ctypes import wintypes
import datetime as dt
import random
import threading
import time

import pyautogui
import pygetwindow

ES_CONTINUOUS, ES_SYSTEM_REQUIRED, ES_DISPLAY_REQUIRED = 0x80000000, 0x00000001, 0x00000002
MOD_ALT, MOD_CONTROL, MOD_NOREPEAT = 0x0001, 0x0002, 0x4000
WM_HOTKEY, WM_QUIT = 0x0312, 0x0012
VK_Q = 0x51
user32, kernel32 = ctypes.windll.user32, ctypes.windll.kernel32


class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [('cbSize', ctypes.c_uint), ('dwTime', ctypes.c_uint)]


def idle_seconds():
    info = LASTINPUTINFO()
    info.cbSize = ctypes.sizeof(info)
    user32.GetLastInputInfo(ctypes.byref(info))
    return (kernel32.GetTickCount() - info.dwTime) / 1000


def listen_hotkey(stop):
    """Global Ctrl+Alt+Q. RegisterHotKey binds to the calling thread, so it owns its own message loop."""
    if not user32.RegisterHotKey(None, 1, MOD_CONTROL | MOD_ALT | MOD_NOREPEAT, VK_Q):
        print('⚠ Ctrl+Alt+Q 등록 실패(다른 프로그램이 사용 중). 콘솔 Ctrl+C로 종료하세요', flush=True)
        return
    msg = wintypes.MSG()
    try:
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            if msg.message == WM_HOTKEY:
                stop.set()
                break
    finally:
        user32.UnregisterHotKey(None, 1)


def find_window(title):
    matches = [w for w in pygetwindow.getWindowsWithTitle(title) if ' - Colab' in w.title]
    return matches[0] if matches else None


def bring_front(window):
    if window.isMinimized:
        window.restore()
    try:
        window.activate()
    except pygetwindow.PyGetWindowException:
        # Windows foreground lock: a minimize/restore cycle is allowed to take focus
        window.minimize()
        window.restore()
    time.sleep(0.8)


def poke(window):
    previous = pygetwindow.getActiveWindow()
    was_minimized = window.isMinimized
    bring_front(window)
    x = window.left + window.width // 2
    y = window.top + int(window.height * 0.6)
    pyautogui.moveTo(x, y, duration=0.3)
    pyautogui.scroll(-3)
    time.sleep(0.5)
    pyautogui.scroll(3)
    pyautogui.press('shift')
    if was_minimized:
        window.minimize()
    if previous is not None and previous != window:
        try:
            previous.activate()
        except pygetwindow.PyGetWindowException:
            pass


def main():
    parser = argparse.ArgumentParser(description='Colab 유휴 끊김 방지')
    parser.add_argument('--title', default=' - Colab', help='대상 창 제목에 들어간 문자열 (기본: 첫 Colab 창)')
    parser.add_argument('--every-min', type=float, default=5)
    parser.add_argument('--idle-min', type=float, default=3, help='이 시간 이상 입력이 없을 때만 조작')
    parser.add_argument('--every-sec', type=float, help='--every-min 대신 초 단위 (테스트용)')
    parser.add_argument('--idle-sec', type=float, help='--idle-min 대신 초 단위 (테스트용)')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    every_sec = args.every_sec if args.every_sec is not None else args.every_min * 60
    idle_sec = args.idle_sec if args.idle_sec is not None else args.idle_min * 60
    jitter = min(20, every_sec * 0.1)
    stop = threading.Event()
    threading.Thread(target=listen_hotkey, args=(stop,), daemon=True).start()
    kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED)
    print(f'대상 창: "{args.title}" · {every_sec:.0f}초 간격 · 사용자 유휴 {idle_sec:.0f}초 이상일 때만', flush=True)
    print('종료: Ctrl+Alt+Q (어느 창에서든) / 이 창에서 Ctrl+C / 마우스를 화면 왼쪽 위 구석으로', flush=True)
    try:
        while not stop.is_set():
            now = dt.datetime.now().strftime('%H:%M:%S')
            window = find_window(args.title)
            idle = idle_seconds()
            if window is None:
                print(f'{now} 대상 Colab 창 없음 — 탭을 별도 창으로 떼고 활성 탭으로 두세요', flush=True)
            elif idle < idle_sec:
                print(f'{now} 사용 중(유휴 {idle:.0f}초) — 건너뜀', flush=True)
            elif args.dry_run:
                print(f'{now} [dry-run] 조작할 창: {window.title} (유휴 {idle:.0f}초)', flush=True)
            else:
                try:
                    poke(window)
                    print(f'{now} 활동 신호 보냄 → {window.title}', flush=True)
                except pyautogui.FailSafeException:
                    print(f'{now} 마우스가 화면 구석에 있어 비상 정지', flush=True)
                    break
                except Exception as error:  # keep the loop alive overnight
                    print(f'{now} 조작 실패: {error!r}', flush=True)
            if args.dry_run:
                break
            stop.wait(every_sec + random.uniform(-jitter, jitter))
        if stop.is_set():
            print('Ctrl+Alt+Q — 종료합니다', flush=True)
    except KeyboardInterrupt:
        print('Ctrl+C — 종료합니다', flush=True)
    finally:
        kernel32.SetThreadExecutionState(ES_CONTINUOUS)


if __name__ == '__main__':
    main()
