import ctypes
import ctypes.wintypes
import win32api
import win32con
import win32gui

# --- Part 1: CTypes for High-Speed Global Cursor Control ---
# Used for Dynamic and Multi-Position modes where the main cursor must move.

# Define necessary C structures for the SendInput API
PUL = ctypes.POINTER(ctypes.c_ulong)
class KeyBdInput(ctypes.Structure):
    _fields_ = [("wVk", ctypes.c_ushort), ("wScan", ctypes.c_ushort), ("dwFlags", ctypes.c_ulong), ("time", ctypes.c_ulong), ("dwExtraInfo", PUL)]
class HardwareInput(ctypes.Structure):
    _fields_ = [("uMsg", ctypes.c_ulong), ("wParamL", ctypes.c_short), ("wParamH", ctypes.c_ushort)]
class MouseInput(ctypes.Structure):
    _fields_ = [("dx", ctypes.c_long), ("dy", ctypes.c_long), ("mouseData", ctypes.c_ulong), ("dwFlags", ctypes.c_ulong), ("time", ctypes.c_ulong), ("dwExtraInfo", PUL)]
class Input_I(ctypes.Union):
    _fields_ = [("ki", KeyBdInput), ("mi", MouseInput), ("hi", HardwareInput)]
class Input(ctypes.Structure):
    _fields_ = [("type", ctypes.c_ulong), ("ii", Input_I)]

# Constants for mouse events
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_ABSOLUTE = 0x8000
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
INPUT_MOUSE = 0

user32 = ctypes.windll.user32
SCREEN_WIDTH = user32.GetSystemMetrics(0)
SCREEN_HEIGHT = user32.GetSystemMetrics(1)

def fast_click():
    """Performs a left click at the current cursor position using SendInput."""
    extra = ctypes.c_ulong(0)
    ii_ = Input_I()
    ii_.mi = MouseInput(0, 0, 0, MOUSEEVENTF_LEFTDOWN, 0, ctypes.pointer(extra))
    x = Input(ctypes.c_ulong(INPUT_MOUSE), ii_)
    user32.SendInput(1, ctypes.byref(x), ctypes.sizeof(x))
    
    ii_.mi = MouseInput(0, 0, 0, MOUSEEVENTF_LEFTUP, 0, ctypes.pointer(extra))
    x = Input(ctypes.c_ulong(INPUT_MOUSE), ii_)
    user32.SendInput(1, ctypes.byref(x), ctypes.sizeof(x))

def fast_move_and_click(x: int, y: int):
    """Atomically moves the global cursor to absolute coordinates and clicks."""
    norm_x = int(x * 65535 / SCREEN_WIDTH)
    norm_y = int(y * 65535 / SCREEN_HEIGHT)
    extra = ctypes.c_ulong(0)
    ii_ = Input_I()
    flags = MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_LEFTDOWN | MOUSEEVENTF_LEFTUP
    ii_.mi = MouseInput(norm_x, norm_y, 0, flags, 0, ctypes.pointer(extra))
    inp = Input(ctypes.c_ulong(INPUT_MOUSE), ii_)
    user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp))

# --- Part 2: Win32 API for Background Window Clicking ---
# Used for Intelligent Mode to click without moving the user's cursor.

def fast_background_click(hwnd, x, y):
    """
    Sends a click event directly to a window handle at coordinates
    relative to that window, without moving the global mouse cursor.

    Args:
        hwnd: The handle (HWND) of the target window.
        x (int): The x-coordinate relative to the window's top-left corner.
        y (int): The y-coordinate relative to the window's top-left corner.
    """
    # Pack coordinates into a single integer for the API call
    l_param = win32api.MAKELONG(x, y)
    
    # Post the messages. PostMessage is non-blocking and extremely fast.
    win32gui.PostMessage(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, l_param)
    win32gui.PostMessage(hwnd, win32con.WM_LBUTTONUP, 0, l_param)
