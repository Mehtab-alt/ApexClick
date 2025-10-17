# ApexClick: The Desktop Automation Assembly Line

![ApexClick UI](https-placeholder-for-your-gif-or-screenshot.png)

> **Pro Tip:** Make your repository stand out! Create a short GIF demonstrating the Intelligent Mode clicking a background window while you use your mouse for other tasks. Use a free tool like *ScreenToGif* and replace the placeholder link above.

ApexClick isn't just another autoclicker. It's a high-performance automation engine for Windows, built on a powerful "Assembly Line" architecture that enables true, non-invasive background operation.

While most autoclickers hijack your mouse, **ApexClick's Intelligent Mode sees, thinks, and acts on a target window without ever moving your cursor**, letting you work, browse, or game on the side.

---

## The Assembly Line: How It Works

ApexClick deconstructs automation into a parallel pipeline, maximizing performance by using all available CPU cores for its most advanced mode.

1.  **👁️ The Eye (Perception):** A high-speed screen capture worker (`mss`) constantly watches the target window. This process is extremely lightweight and efficient.

2.  **🧠 The Brain (Analysis):** The captured image is placed into shared memory (a "zero-copy" operation) and is instantly distributed across a pool of multiprocessing workers—one for each of your CPU cores. The Brain analyzes the image in parallel, locating target pixels thousands of times per second.

3.  **✋ The Hand (Execution):** A dedicated action worker pulls coordinates identified by the Brain from a queue. It uses low-level Windows messages (`PostMessage`) to send clicks directly to the target application. **Your mouse cursor never moves.**

This decoupled architecture means the system can find and click targets at immense speeds, limited only by your CPU and the target application's responsiveness.

---

## Features at a Glance

| Mode | Use Case | Cursor Control | Key Advantage |
| :--- | :--- | :--- | :--- |
| 🤖 **Intelligent** | Background Automation & Gaming | **None** (Doesn't move your mouse) | True background operation |
| 🎯 **Multi-Position** | Fixed Click Sequences | **Global** (Moves your mouse) | Record & playback automation |
| ⚡ **Dynamic** | Rapid Clicking | **Global** (Follows your mouse) | Maximum speed at cursor |

### 🤖 Mode 1: Intelligent Mode

The flagship mode. Perfect for automating tasks in games or applications while you use your computer for other things.

*   **True Background Operation:** Clicks a target window without stealing focus or moving your mouse.
*   **Multi-Color Targeting:** Define a list of specific colors to click.
*   **CPU-Accelerated:** Uses `multiprocessing` and `shared_memory` to scan for pixels at maximum speed.
*   **Precision Control:** Adjust the `MinCheckPixel` distance to avoid clicking clustered targets.
*   **Hotkeys:** `O` to select your target window, `Backtick` (`)` to start/stop.

### 🎯 Mode 2: Multi-Position Mode

For tasks requiring a fixed sequence of clicks. This mode uses the main system cursor.

*   **Record & Playback:** Capture a series of screen coordinates and have the autoclicker execute them in a loop.
*   **High-Speed Clicks:** Uses the low-level `SendInput` API for faster and more reliable clicks than standard libraries.
*   **Save/Load Profiles:** Save and load your captured positions for different tasks.
*   **Hotkeys:** `P` to capture a position, `Backtick` (`)` to start/stop.

### ⚡ Mode 3: Dynamic Mode

The simplest mode. Clicks rapidly at your current cursor position.

*   **Cursor-Following:** Clicks wherever your mouse is.
*   **Adjustable Interval:** Set the click speed down to the millisecond.
*   **Optimized Performance:** Also uses the `SendInput` API for maximum speed.
*   **Hotkeys:** `Backtick` (`)` to start/stop.

---

## Installation & Usage

This application is for **Windows only** due to its reliance on the Win32 API.

**1. Prerequisites:**
*   Python 3.8+
*   Git

**2. Setup:**
```bash
# 1. Clone the repository
git clone https://github.com/[YOUR_USERNAME]/ApexClick.git
cd ApexClick

# 2. (Recommended) Create and activate a virtual environment
python -m venv venv
.\venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
