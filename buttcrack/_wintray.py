"""A Windows notification-area (system tray) icon, in ``ctypes``.

The desktop app wants somewhere to live while the browser tab is the real
interface.  Every tray library on PyPI would be a runtime dependency, and this
project has none, so the two hundred lines of Win32 are spelled out here
instead: a message-only window, ``Shell_NotifyIconW`` and a popup menu.

It is strictly a bonus.  :meth:`TrayIcon.start` returns ``False`` on any
platform that is not Windows and on any Win32 call that refuses, and the caller
is expected to carry on without a tray -- so this module never raises at import
time and never raises from a public method.

The icon runs on its own thread with its own message loop, deliberately: if
anything in here wedges, it wedges alone and the Tk window above it keeps
working.  Menu callbacks are therefore invoked on *that* thread, so they must
marshal back to the UI thread themselves (the caller does this with
``root.after``).
"""

from __future__ import annotations

import contextlib
import ctypes
import sys
import threading
from collections.abc import Sequence
from typing import Callable

__all__ = ["TrayIcon"]

_IS_WINDOWS = sys.platform == "win32"

# Win32 constants, named as they are in the SDK so they can be looked up.
_WM_DESTROY = 0x0002
_WM_CLOSE = 0x0010
_WM_COMMAND = 0x0111
_WM_LBUTTONUP = 0x0202
_WM_LBUTTONDBLCLK = 0x0203
_WM_RBUTTONUP = 0x0205
_WM_APP = 0x8000
_WM_TRAY = _WM_APP + 1

_NIM_ADD = 0
_NIM_DELETE = 2
_NIF_MESSAGE = 0x01
_NIF_ICON = 0x02
_NIF_TIP = 0x04

_IMAGE_ICON = 1
_LR_LOADFROMFILE = 0x0010
_LR_DEFAULTSIZE = 0x0040
_IDI_APPLICATION = 32512

_MF_STRING = 0x0000
_TPM_RIGHTBUTTON = 0x0002
_TPM_RETURNCMD = 0x0100
_TPM_NONOTIFY = 0x0080

_HWND_MESSAGE = -3
_CW_USEDEFAULT = 0x80000000

#: Menu command ids start here; 0 means "nothing was chosen".
_FIRST_COMMAND = 0x1000


class TrayIcon:
    """A tray icon with a right-click menu, or a no-op when that is impossible.

    ``items`` is a sequence of ``(label, callback)``; a label of ``"-"`` draws a
    separator.  ``on_activate`` fires on left click and double click.
    """

    def __init__(
        self,
        title: str,
        icon_path: str | None = None,
        items: Sequence[tuple[str, Callable[[], None]]] = (),
        on_activate: Callable[[], None] | None = None,
    ) -> None:
        self.title = title[:127]
        self.icon_path = icon_path
        self.items = list(items)
        self.on_activate = on_activate
        self.active = False
        self._thread: threading.Thread | None = None
        self._hwnd: int | None = None
        self._ready = threading.Event()
        # ctypes callbacks must outlive the window that uses them, or Windows
        # calls into freed memory the next time the shell pokes the icon.
        self._wndproc_ref: object = None
        self._hicon: int | None = None
        # Built in _create(); the window procedure needs it to remove the icon
        # on WM_DESTROY, and may be reached before _create() has finished.
        self._nid: object = None

    # ----------------------------------------------------------------- #
    # public surface
    # ----------------------------------------------------------------- #

    def start(self) -> bool:
        """Create the icon.  False means there is no tray; carry on without one."""
        if not _IS_WINDOWS or self._thread is not None:
            return False
        self._thread = threading.Thread(target=self._run, name="buttcrack-tray", daemon=True)
        self._thread.start()
        # Bounded: a tray that has not appeared in two seconds is not going to.
        self._ready.wait(timeout=2.0)
        return self.active

    def stop(self) -> None:
        """Remove the icon and end its message loop.  Safe to call twice."""
        if not self.active or self._hwnd is None:
            return
        self.active = False
        with contextlib.suppress(Exception):
            ctypes.windll.user32.PostMessageW(self._hwnd, _WM_CLOSE, 0, 0)
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None

    # ----------------------------------------------------------------- #
    # the thread
    # ----------------------------------------------------------------- #

    def _run(self) -> None:
        try:
            self._create()
        except Exception:
            self.active = False
        finally:
            self._ready.set()
        if not self.active:
            return
        with contextlib.suppress(Exception):
            self._pump()

    def _create(self) -> None:
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        shell32 = ctypes.windll.shell32
        kernel32 = ctypes.windll.kernel32

        lresult = ctypes.c_ssize_t
        wndproc_type = ctypes.WINFUNCTYPE(lresult, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)

        class WNDCLASSEXW(ctypes.Structure):
            _fields_ = [
                ("cbSize", wintypes.UINT),
                ("style", wintypes.UINT),
                ("lpfnWndProc", wndproc_type),
                ("cbClsExtra", ctypes.c_int),
                ("cbWndExtra", ctypes.c_int),
                ("hInstance", wintypes.HINSTANCE),
                ("hIcon", wintypes.HICON),
                ("hCursor", wintypes.HANDLE),
                ("hbrBackground", wintypes.HBRUSH),
                ("lpszMenuName", wintypes.LPCWSTR),
                ("lpszClassName", wintypes.LPCWSTR),
                ("hIconSm", wintypes.HICON),
            ]

        class GUID(ctypes.Structure):
            _fields_ = [
                ("Data1", wintypes.DWORD),
                ("Data2", wintypes.WORD),
                ("Data3", wintypes.WORD),
                ("Data4", ctypes.c_byte * 8),
            ]

        class NOTIFYICONDATAW(ctypes.Structure):
            _fields_ = [
                ("cbSize", wintypes.DWORD),
                ("hWnd", wintypes.HWND),
                ("uID", wintypes.UINT),
                ("uFlags", wintypes.UINT),
                ("uCallbackMessage", wintypes.UINT),
                ("hIcon", wintypes.HICON),
                ("szTip", wintypes.WCHAR * 128),
                ("dwState", wintypes.DWORD),
                ("dwStateMask", wintypes.DWORD),
                ("szInfo", wintypes.WCHAR * 256),
                ("uVersion", wintypes.UINT),
                ("szInfoTitle", wintypes.WCHAR * 64),
                ("dwInfoFlags", wintypes.DWORD),
                ("guidItem", GUID),
                ("hBalloonIcon", wintypes.HICON),
            ]

        # Default argtypes assume 32-bit ints, which truncates every handle in a
        # 64-bit process.  Declare the ones that carry pointers.
        user32.DefWindowProcW.restype = lresult
        user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
        user32.CreateWindowExW.restype = wintypes.HWND
        user32.CreateWindowExW.argtypes = [
            wintypes.DWORD,
            wintypes.LPCWSTR,
            wintypes.LPCWSTR,
            wintypes.DWORD,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            wintypes.HWND,
            wintypes.HMENU,
            wintypes.HINSTANCE,
            wintypes.LPVOID,
        ]
        user32.LoadImageW.restype = wintypes.HANDLE
        user32.LoadImageW.argtypes = [
            wintypes.HINSTANCE,
            wintypes.LPCWSTR,
            wintypes.UINT,
            ctypes.c_int,
            ctypes.c_int,
            wintypes.UINT,
        ]
        user32.LoadIconW.restype = wintypes.HICON
        user32.LoadIconW.argtypes = [wintypes.HINSTANCE, wintypes.LPCWSTR]
        user32.CreatePopupMenu.restype = wintypes.HMENU
        user32.TrackPopupMenu.restype = ctypes.c_int
        user32.TrackPopupMenu.argtypes = [
            wintypes.HMENU,
            wintypes.UINT,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            wintypes.HWND,
            wintypes.LPVOID,
        ]
        shell32.Shell_NotifyIconW.restype = wintypes.BOOL
        shell32.Shell_NotifyIconW.argtypes = [wintypes.DWORD, ctypes.POINTER(NOTIFYICONDATAW)]
        kernel32.GetModuleHandleW.restype = wintypes.HMODULE
        kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]

        instance = kernel32.GetModuleHandleW(None)

        def wndproc(hwnd, message, wparam, lparam):  # noqa: ANN001 - Win32 signature
            try:
                if message == _WM_TRAY:
                    event = lparam & 0xFFFF
                    if event in (_WM_LBUTTONUP, _WM_LBUTTONDBLCLK):
                        self._invoke(self.on_activate)
                    elif event == _WM_RBUTTONUP:
                        self._show_menu(hwnd)
                    return 0
                if message == _WM_COMMAND:
                    index = (wparam & 0xFFFF) - _FIRST_COMMAND
                    if 0 <= index < len(self.items):
                        self._invoke(self.items[index][1])
                    return 0
                if message == _WM_CLOSE:
                    user32.DestroyWindow(hwnd)
                    return 0
                if message == _WM_DESTROY:
                    with contextlib.suppress(Exception):
                        shell32.Shell_NotifyIconW(_NIM_DELETE, ctypes.byref(self._nid))
                    user32.PostQuitMessage(0)
                    return 0
            except Exception:
                pass
            return user32.DefWindowProcW(hwnd, message, wparam, lparam)

        self._wndproc_ref = wndproc_type(wndproc)

        class_name = f"ButtcrackTray_{id(self):x}"
        wndclass = WNDCLASSEXW()
        wndclass.cbSize = ctypes.sizeof(WNDCLASSEXW)
        wndclass.lpfnWndProc = self._wndproc_ref
        wndclass.hInstance = instance
        wndclass.lpszClassName = class_name
        if not user32.RegisterClassExW(ctypes.byref(wndclass)):
            raise OSError("RegisterClassExW failed")

        # A message-only window: never painted, never in the task bar, but it
        # has a queue, which is all the shell needs to deliver icon events to.
        hwnd = user32.CreateWindowExW(
            0,
            class_name,
            self.title,
            0,
            _CW_USEDEFAULT,
            _CW_USEDEFAULT,
            _CW_USEDEFAULT,
            _CW_USEDEFAULT,
            _HWND_MESSAGE,
            None,
            instance,
            None,
        )
        if not hwnd:
            raise OSError("CreateWindowExW failed")
        self._hwnd = hwnd

        hicon = 0
        if self.icon_path:
            hicon = user32.LoadImageW(None, self.icon_path, _IMAGE_ICON, 0, 0, _LR_LOADFROMFILE | _LR_DEFAULTSIZE)
        if not hicon:
            hicon = user32.LoadIconW(None, ctypes.cast(_IDI_APPLICATION, wintypes.LPCWSTR))
        self._hicon = hicon

        nid = NOTIFYICONDATAW()
        nid.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
        nid.hWnd = hwnd
        nid.uID = 1
        nid.uFlags = _NIF_MESSAGE | _NIF_ICON | _NIF_TIP
        nid.uCallbackMessage = _WM_TRAY
        nid.hIcon = hicon
        nid.szTip = self.title
        self._nid = nid

        if not shell32.Shell_NotifyIconW(_NIM_ADD, ctypes.byref(nid)):
            user32.DestroyWindow(hwnd)
            raise OSError("Shell_NotifyIconW(NIM_ADD) failed")

        self.active = True

    def _pump(self) -> None:
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        user32.GetMessageW.restype = ctypes.c_int
        user32.GetMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT]
        message = wintypes.MSG()
        while True:
            result = user32.GetMessageW(ctypes.byref(message), None, 0, 0)
            if result in (0, -1):  # WM_QUIT, or an error we cannot recover from
                break
            user32.TranslateMessage(ctypes.byref(message))
            user32.DispatchMessageW(ctypes.byref(message))
        self.active = False

    def _show_menu(self, hwnd: int) -> None:
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        point = wintypes.POINT()
        user32.GetCursorPos(ctypes.byref(point))
        menu = user32.CreatePopupMenu()
        if not menu:
            return
        try:
            for index, (label, _callback) in enumerate(self.items):
                if label == "-":
                    user32.AppendMenuW(menu, 0x800, 0, None)  # MF_SEPARATOR
                else:
                    user32.AppendMenuW(menu, _MF_STRING, _FIRST_COMMAND + index, label)
            # Without this the menu refuses to close when you click elsewhere --
            # the documented quirk of showing a menu from a hidden window.
            user32.SetForegroundWindow(hwnd)
            chosen = user32.TrackPopupMenu(
                menu,
                _TPM_RIGHTBUTTON | _TPM_RETURNCMD | _TPM_NONOTIFY,
                point.x,
                point.y,
                0,
                hwnd,
                None,
            )
            user32.PostMessageW(hwnd, 0, 0, 0)  # WM_NULL, the other half of the quirk
            if chosen:
                index = chosen - _FIRST_COMMAND
                if 0 <= index < len(self.items):
                    self._invoke(self.items[index][1])
        finally:
            with contextlib.suppress(Exception):
                user32.DestroyMenu(menu)

    @staticmethod
    def _invoke(callback: Callable[[], None] | None) -> None:
        """Run a menu callback without letting it kill the message loop."""
        if callback is None:
            return
        with contextlib.suppress(Exception):
            callback()
