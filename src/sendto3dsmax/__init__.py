import ctypes
import dataclasses
import json
import pathlib
import sys
import time

import pywintypes
import win32con
import win32gui
import win32process
import winerror
from comtypes.client import CreateObject, GetModule

from sendto3dsmax.errors import (
    EditBoxNotFoundError,
    MaxNotFoundError,
    MaxNotRespondingError,
    StatusPanelFoundError,
    UnsupportedFileTypeError,
)

GetModule("UIAutomationCore.dll")
import comtypes.gen.UIAutomationClient as uia  # noqa: E402


def quote(s: pathlib.Path | str):
    if isinstance(s, pathlib.Path):
        s = str(s.absolute())
    return json.dumps(s)


def build_command(file_path: pathlib.Path) -> str:
    ext = file_path.suffix
    if ext in [".ms", ".mcr"]:
        return f"fileIn {quote(file_path)}"
    elif ext == ".py":
        return f"python.executeFile {quote(file_path)}"
    raise UnsupportedFileTypeError(f"Unsupported file type: {ext}")


@dataclasses.dataclass
class MaxProcess:
    pid: int
    hwnd: int
    name: str


def get_3dsmax_process(pid: int | None):
    automation = CreateObject(uia.CUIAutomation, interface=uia.IUIAutomation)
    values: list[MaxProcess] = []

    def callback(hwnd: int, _):
        _, found_pid = win32process.GetWindowThreadProcessId(hwnd)
        classname = automation.ElementFromHandle(hwnd).CurrentClassName
        if classname == "QmaxApplicationWindow":
            values.append(
                MaxProcess(
                    pid=found_pid,
                    hwnd=hwnd,
                    name=win32gui.GetWindowText(hwnd),
                )
            )
            return False
        return True

    win32gui.EnumWindows(callback, None)
    if pid is None:
        return values
    return [p for p in values if p.pid == pid]


def wait_max_responsive(hwnd: int, timeout: float):
    start_time = time.time()
    response = None
    while True:
        if time.time() - start_time > timeout:
            break

        try:
            response, result = win32gui.SendMessageTimeout(
                hwnd,
                win32con.WM_NULL,
                0,
                0,
                win32con.SMTO_ABORTIFHUNG,
                1000,
            )
            break
        except pywintypes.error as e:
            if e.winerror == winerror.ERROR_TIMEOUT:
                continue
            raise

    if not response:
        raise MaxNotRespondingError("3ds Max not responding.")


def send(pid: int | None, files: list[str], timeout: float):
    files_path = [pathlib.Path(f).resolve().absolute() for f in files]
    for file_path in files_path:
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
    commands = [build_command(p) for p in files_path]

    process_list = get_3dsmax_process(pid=pid)
    if not process_list:
        raise MaxNotFoundError("No 3ds Max instance found.")
    if len(process_list) > 1:
        sys.stderr.write(
            "Multiple instances found. Please select one of the following:\n"
        )
        for p in process_list:
            sys.stderr.write(f"{p.name} ({p.pid})\n")
        sys.exit(1)
    process = process_list[0]

    automation = CreateObject(uia.CUIAutomation, interface=uia.IUIAutomation)
    root = automation.GetRootElement()
    app = root.FindFirst(
        uia.TreeScope_Children,
        automation.CreateAndCondition(
            automation.CreatePropertyCondition(
                uia.UIA_ProcessIdPropertyId,
                process.pid,
            ),
            automation.CreatePropertyCondition(
                uia.UIA_ClassNamePropertyId,
                "QmaxApplicationWindow",
            ),
        ),
    )
    if not app:
        raise MaxNotFoundError("QmaxApplicationWindow not found.")

    status_panel = app.FindFirst(
        uia.TreeScope_Children,
        automation.CreatePropertyCondition(
            uia.UIA_NamePropertyId,
            "StatusPanel",
        ),
    )
    if not status_panel:
        raise StatusPanelFoundError("StatusPanel not found.")

    edit = status_panel.FindFirst(
        uia.TreeScope_Children,
        automation.CreateAndCondition(
            automation.CreatePropertyCondition(
                uia.UIA_NamePropertyId,
                "Mini_Edit_Box",
            ),
            automation.CreatePropertyCondition(
                uia.UIA_ClassNamePropertyId,
                "MXS_Scintilla",
            ),
        ),
    )
    if not edit:
        raise EditBoxNotFoundError("Mini_Edit_Box not found.")

    hwnd = edit.CurrentNativeWindowHandle
    for command in commands:
        try:
            print(f">>> {command}")
            command += "\r\n\0\0"
            win32gui.SendMessageTimeout(
                hwnd,
                win32con.WM_SETTEXT,
                0,
                command.encode("utf-16-le"),
                win32con.SMTO_ABORTIFHUNG,
                2000,
            )
            win32gui.SendMessageTimeout(
                hwnd,
                win32con.WM_CHAR,
                win32con.VK_RETURN,
                0,
                win32con.SMTO_ABORTIFHUNG,
                2000,
            )
        except pywintypes.error as e:
            if e.winerror == winerror.ERROR_TIMEOUT:
                raise TimeoutError(e.strerror) from e
            raise

        wait_max_responsive(hwnd, timeout=timeout)
        max_len = 1024
        buffer = ctypes.create_unicode_buffer(max_len)
        try:
            win32gui.SendMessageTimeout(
                hwnd,
                win32con.WM_GETTEXT,
                max_len,
                buffer,
                win32con.SMTO_ABORTIFHUNG,
                2000,
            )
        except pywintypes.error as e:
            if e.winerror == winerror.ERROR_TIMEOUT:
                raise TimeoutError(e.strerror) from e
            raise
        print(buffer.value)
