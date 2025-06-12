import pathlib
import sys

import win32api
import win32con
import win32gui

from sendto3dsmax.errors import (
    ListenerWindowNotFoundError,
    MaxNotFoundError,
    UnsupportedFileTypeError,
)

MAX_TITLE = "Autodesk 3ds Max"
LISTENER_CLASS = "MXS_Scintilla"


def find_3dsmax_windows() -> list[tuple[int, str]]:
    hwnds = []

    def enum_windows_proc(hwnd: int, lParam):
        title = win32gui.GetWindowText(hwnd)
        if MAX_TITLE in title:
            hwnds.append((hwnd, title))
        return True

    win32gui.EnumWindows(enum_windows_proc, None)
    return hwnds


def find_listener_hwnd(parent_hwnd: int) -> int | None:
    listener_hwnd = None

    def enum_child_proc(hwnd: int, lParam):
        nonlocal listener_hwnd
        class_name = win32gui.GetClassName(hwnd)
        if class_name is not None and LISTENER_CLASS in class_name:
            listener_hwnd = hwnd
            return False
        return True

    win32gui.EnumChildWindows(parent_hwnd, enum_child_proc, None)
    return listener_hwnd


def send_command_to_listener(hwnd: int, command: str) -> None:
    win32gui.SendMessage(hwnd, win32con.WM_SETTEXT, 0, command.encode("utf-16-le"))
    win32api.PostMessage(hwnd, win32con.WM_CHAR, win32con.VK_RETURN)


def build_command(file_path: pathlib.Path) -> str | None:
    ext = file_path.suffix
    if ext in [".ms", ".mcr"]:
        return f'fileIn @"{file_path}"\r\n'
    elif ext == ".py":
        return f'python.executeFile @"{file_path}"\r\n'
    return None


def send(file_path: pathlib.Path | str):
    file_path = pathlib.Path(file_path).resolve().absolute()
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    cmd = build_command(file_path)
    if not cmd:
        raise UnsupportedFileTypeError(f"Unsupported file type: {file_path}")
    windows = find_3dsmax_windows()
    if not windows:
        raise MaxNotFoundError("No 3ds Max instance found.")
    if len(windows) > 1:
        sys.stderr.write(
            f"Multiple instances found. Using the first one: {windows[0][1]}\n"
        )
    listener = find_listener_hwnd(windows[0][0])
    if listener is None:
        raise ListenerWindowNotFoundError("Listener window not found.")

    send_command_to_listener(listener, cmd)
    sys.stderr.write("Command sent to 3ds Max.\n")
