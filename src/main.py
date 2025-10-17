import sys
import pynput.keyboard
import threading
import time
import json
import psutil
import pygetwindow as gw
import numpy as np
import mss
import queue
import uuid
from multiprocessing import Pool, cpu_count, shared_memory

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QPushButton, QLabel, QLineEdit, QTextEdit,
    QMessageBox, QFileDialog, QGroupBox, QScrollArea, QFrame,
    QColorDialog
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QCoreApplication
from PyQt6.QtGui import QColor, QPalette

# Optimized input module (requires fast_input.py in the same directory)
from fast_input import fast_click, fast_move_and_click, fast_background_click

# --- Multiprocessing Worker Function (for "The Brain") ---

def _filter_points_by_distance_worker(points, min_distance):
    """Filters a list of (x, y) tuples to ensure they are min_distance apart."""
    filtered_points = []
    while points:
        px, py = points.pop(0)
        filtered_points.append((px, py))
        points = [(x, y) for x, y in points if abs(x - px) >= min_distance or abs(y - py) >= min_distance]
    return filtered_points

def process_chunk_shared_memory(task):
    """
    Multiprocessing worker that uses shared memory to analyze an image chunk.
    This "zero-copy" approach is highly efficient.
    """
    (shm_name, full_shape, dtype,
     chunk_start_y, chunk_start_x, chunk_height, chunk_width,
     colors, min_check_pixel, tolerance) = task

    existing_shm = None
    try:
        # Connect to shared memory and create a zero-copy NumPy view
        existing_shm = shared_memory.SharedMemory(name=shm_name)
        full_image = np.ndarray(full_shape, dtype=dtype, buffer=existing_shm.buf)
        
        # Get the specific chunk this worker is responsible for
        chunk_end_y = chunk_start_y + chunk_height
        chunk_end_x = chunk_start_x + chunk_width
        chunk = full_image[chunk_start_y:chunk_end_y, chunk_start_x:chunk_end_x]

        # Perform color matching
        all_match_points = []
        target_color_nps = [np.array([int(color[i:i+2], 16) for i in (1, 3, 5)]) for color in colors]

        for target_color in target_color_nps:
            matches = np.all(np.abs(chunk - target_color) <= tolerance, axis=-1)
            if np.any(matches):
                y_local, x_local = np.where(matches)
                y_global = y_local + chunk_start_y
                x_global = x_local + chunk_start_x
                all_match_points.extend(zip(x_global.tolist(), y_global.tolist()))

        # Filter points for minimum distance before returning
        if all_match_points:
            return _filter_points_by_distance_worker(all_match_points, min_check_pixel)
        
        return []

    finally:
        # CRITICAL: Always close the shared memory handle in the worker process
        if existing_shm:
            existing_shm.close()

# --- PyQt Worker Threads ---

class ClickWorker(QThread):
    """Optimized thread for Multi-Position and Dynamic clicking using direct input."""
    click_signal = pyqtSignal(int)
    
    def __init__(self, mode, click_interval_sec, positions):
        super().__init__()
        self._is_running = True
        self.mode = mode
        self.interval = click_interval_sec
        self.positions = positions

    def stop(self):
        self._is_running = False
        self.wait()

    def run(self):
        clicks_since_last_update = 0
        last_update_time = time.time()

        while self._is_running:
            if self.mode == "dynamic":
                fast_click()
                clicks_since_last_update += 1
            elif self.mode == "multi-position":
                if not self.positions:
                    time.sleep(0.1)
                    continue
                # Perform a high-speed "burst" of clicks before sleeping
                for pos in self.positions:
                    if not self._is_running: break
                    fast_move_and_click(pos[0], pos[1])
                    clicks_since_last_update += 1
            
            # Batch GUI updates to reduce CPU load
            current_time = time.time()
            if current_time - last_update_time > 0.2:
                if clicks_since_last_update > 0:
                    self.click_signal.emit(clicks_since_last_update)
                    clicks_since_last_update = 0
                last_update_time = current_time
            
            time.sleep(self.interval)

# --- New Decoupled Workers for Intelligent Mode ---

class ClickActionWorker(QThread):
    """The 'Hand': Pulls coordinates from a queue and executes background clicks."""
    click_executed_signal = pyqtSignal()

    def __init__(self, target_queue, window_handle):
        super().__init__()
        self._is_running = True
        self.target_queue = target_queue
        self.hwnd = window_handle

    def stop(self):
        self._is_running = False
        self.target_queue.put(None) # Sentinel to unblock .get()
        self.wait()

    def run(self):
        while self._is_running:
            coords = self.target_queue.get()
            if coords is None or not self._is_running: break
            fast_background_click(self.hwnd, coords[0], coords[1])
            self.click_executed_signal.emit()

class CaptureWorker(QThread):
    """The 'Eye': Captures screenshots with MSS and submits them to the 'Brain' for analysis."""
    error_signal = pyqtSignal(str)

    def __init__(self, main_app_instance):
        super().__init__()
        self._is_running = True
        self.app = main_app_instance

    def stop(self):
        self._is_running = False
        self.wait()
    
    def run(self):
        with mss.mss() as sct:
            while self._is_running:
                try:
                    if not self.app.window or not self.app.window.isActive:
                        self.error_signal.emit("Target window is closed or invalid. Stopping.")
                        break

                    monitor = {"top": self.app.window.top, "left": self.app.window.left, "width": self.app.window.width, "height": self.app.window.height}
                    sct_img = sct.grab(monitor)
                    
                    # Copy screenshot data into the shared memory buffer
                    screenshot_np = np.array(sct_img, dtype=np.uint8)[:, :, :3]
                    shm_array = np.ndarray(self.app.shm_shape, dtype=self.app.shm_dtype, buffer=self.app.shm.buf)
                    np.copyto(shm_array, screenshot_np)

                    # Create and submit tasks to the processing pool without blocking
                    chunks = self.app.split_screenshot_into_chunks(self.app.shm_shape)
                    tasks = [
                        (self.app.shm_name, self.app.shm_shape, self.app.shm_dtype,
                         start_y, start_x, height, width,
                         self.app.colors, self.app.min_check_pixel, 10) # 10 = tolerance
                        for start_y, start_x, height, width in chunks
                    ]
                    self.app.pool.map_async(process_chunk_shared_memory, tasks, callback=self.app.handle_results)

                except Exception as e:
                    self.error_signal.emit(f"Capture error: {e}. Stopping.")
                    break

class PerformanceWorker(QThread):
    performance_signal = pyqtSignal(int, float, float)
    
    def __init__(self, app_instance):
        super().__init__()
        self._is_running = True
        self.app = app_instance
        self.last_click_count = 0
        self.last_time = time.time()

    def stop(self): self._is_running = False; self.wait()

    def run(self):
        while self._is_running:
            time.sleep(1)
            current_time = time.time()
            if current_time - self.last_time >= 1:
                current_click_count = self.app.click_count
                cps = current_click_count - self.last_click_count
                position_count = self.app.get_position_count()
                cps_per_position = cps / position_count if position_count > 0 else 0
                cpu_usage = psutil.cpu_percent()
                self.performance_signal.emit(cps, cps_per_position, cpu_usage)
                self.last_click_count = current_click_count
                self.last_time = current_time

# --- Main Application Window ---

class PointerAutoClicker(QMainWindow):
    text_signal = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ApexClick")
        self.setGeometry(100, 100, 960, 580)

        # Core application state
        self.pointer_positions = []; self.clicking = False; self.click_count = 0
        self.mode = "multi-position"; self.window = None; self.colors = []
        self.selected_color_index = None; self.min_check_pixel = 10; self.click_interval = 0.003
        
        # High-performance pipeline components
        self.target_queue = queue.Queue(maxsize=2000)
        self.num_cores = psutil.cpu_count(logical=False) or cpu_count()
        self.pool = Pool(processes=self.num_cores)
        self.shm = None; self.shm_name = None; self.shm_shape = None; self.shm_dtype = np.uint8
        
        # Worker thread references
        self.click_worker = None; self.capture_worker = None; self.click_action_worker = None; self.performance_worker = None

        self.setup_ui()
        self.start_global_hotkey_listener()
        self.start_performance_monitoring()
        self.text_signal.connect(self.update_text_box)
        self.set_multi_position_mode()

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        mode_frame = QFrame()
        mode_layout = QHBoxLayout(mode_frame)
        self.multi_position_button = QPushButton("Multi-Position")
        self.multi_position_button.clicked.connect(self.set_multi_position_mode)
        self.dynamic_button = QPushButton("Dynamic")
        self.dynamic_button.clicked.connect(self.set_dynamic_mode)
        self.intelligent_button = QPushButton("Intelligent")
        self.intelligent_button.clicked.connect(self.set_intelligent_mode)
        mode_layout.addWidget(self.multi_position_button)
        mode_layout.addWidget(self.dynamic_button)
        mode_layout.addWidget(self.intelligent_button)
        main_layout.addWidget(mode_frame)

        self.text_box = QTextEdit()
        self.text_box.setReadOnly(True)
        self.text_box.setFixedHeight(80)
        main_layout.addWidget(self.text_box)

        self.mode_container = QWidget()
        self.mode_container_layout = QGridLayout(self.mode_container)
        self.mode_container.setLayout(self.mode_container_layout)
        
        self.multi_position_frame = self._create_multi_position_frame()
        self.dynamic_frame = self._create_dynamic_frame()
        self.intelligent_frame = self._create_intelligent_frame()
        
        self.mode_container_layout.addWidget(self.multi_position_frame, 0, 0)
        self.mode_container_layout.addWidget(self.dynamic_frame, 0, 0)
        self.mode_container_layout.addWidget(self.intelligent_frame, 0, 0)
        main_layout.addWidget(self.mode_container)
        
        self.performance_label = QLabel("Performance: CPS: 0 | CPU: 0%")
        self.performance_label.setFixedHeight(20)
        main_layout.addWidget(self.performance_label)
        
        self.footer_label = QLabel("ApexClick: High-Performance Desktop Automation")
        self.footer_label.setStyleSheet("color: grey;")
        self.footer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.footer_label)
        
        self.dynamic_frame.hide()
        self.intelligent_frame.hide()

    def _create_multi_position_frame(self):
        frame = QGroupBox("Multi-Position Mode")
        layout = QVBoxLayout(frame)
        layout.addWidget(QLabel("Press 'P' to capture pointer positions."))
        interval_frame = QHBoxLayout()
        interval_frame.addWidget(QLabel("Autoclicker Interval (ms):"))
        self.interval_entry = QLineEdit("3")
        interval_frame.addWidget(self.interval_entry)
        set_interval_button = QPushButton("Set Interval")
        set_interval_button.clicked.connect(lambda: self.set_interval("multi-position"))
        interval_frame.addWidget(set_interval_button)
        layout.addLayout(interval_frame)
        button_frame = QGridLayout()
        self.save_button = QPushButton("Save Positions"); self.save_button.clicked.connect(self.save_positions)
        self.load_button = QPushButton("Load Positions"); self.load_button.clicked.connect(self.load_positions)
        self.clear_button = QPushButton("Clear Positions"); self.clear_button.clicked.connect(self.clear_positions)
        button_frame.addWidget(self.save_button, 0, 0); button_frame.addWidget(self.load_button, 0, 1); button_frame.addWidget(self.clear_button, 1, 0, 1, 2)
        layout.addLayout(button_frame)
        self.autoclick_button_multi = QPushButton("Start/Stop Autoclicker (`)"); self.autoclick_button_multi.clicked.connect(self.toggle_autoclicker)
        layout.addWidget(self.autoclick_button_multi)
        layout.addStretch(1)
        return frame

    def _create_dynamic_frame(self):
        frame = QGroupBox("Dynamic Mode")
        layout = QVBoxLayout(frame)
        interval_frame = QHBoxLayout()
        interval_frame.addWidget(QLabel("Autoclicker Interval (ms):"))
        self.dynamic_interval_entry = QLineEdit("3")
        interval_frame.addWidget(self.dynamic_interval_entry)
        dynamic_set_interval_button = QPushButton("Set Interval")
        dynamic_set_interval_button.clicked.connect(lambda: self.set_interval("dynamic"))
        interval_frame.addWidget(dynamic_set_interval_button)
        layout.addLayout(interval_frame)
        warning_label = QLabel("Please increase ms in case of system instability and skipping clicks."); warning_label.setStyleSheet("color: yellow;")
        layout.addWidget(warning_label)
        self.autoclick_button_dynamic = QPushButton("Start/Stop Autoclicker (`)"); self.autoclick_button_dynamic.clicked.connect(self.toggle_autoclicker)
        layout.addWidget(self.autoclick_button_dynamic)
        layout.addStretch(1)
        return frame

    def _create_intelligent_frame(self):
        frame = QGroupBox("Intelligent Mode")
        main_layout = QHBoxLayout(frame)
        left_group = QGroupBox("Target Colors")
        left_layout = QVBoxLayout(left_group)
        color_buttons_frame = QHBoxLayout()
        self.add_color_button = QPushButton("Add Color"); self.add_color_button.clicked.connect(self.add_color)
        self.delete_color_button = QPushButton("Delete Color"); self.delete_color_button.clicked.connect(self.delete_color)
        color_buttons_frame.addWidget(self.add_color_button); color_buttons_frame.addWidget(self.delete_color_button)
        left_layout.addLayout(color_buttons_frame)
        self.color_boxes_widget = QWidget()
        self.color_boxes_layout = QVBoxLayout(self.color_boxes_widget)
        self.color_boxes_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        color_scroll = QScrollArea(); color_scroll.setWidgetResizable(True); color_scroll.setWidget(self.color_boxes_widget)
        left_layout.addWidget(color_scroll)
        right_layout = QVBoxLayout()
        right_layout.addWidget(QLabel("MinCheckPixel defines click accuracy."))
        min_check_frame = QHBoxLayout()
        min_check_frame.addWidget(QLabel("Min Check Pixel:"))
        self.min_check_pixel_entry = QLineEdit("10"); self.min_check_pixel_entry.setFixedWidth(50)
        min_check_frame.addWidget(self.min_check_pixel_entry)
        set_min_check_pixel_button = QPushButton("Set"); set_min_check_pixel_button.clicked.connect(self.set_min_pixel)
        min_check_frame.addWidget(set_min_check_pixel_button); min_check_frame.addStretch(1)
        right_layout.addLayout(min_check_frame)
        window_frame = QHBoxLayout()
        select_window_button = QPushButton("Select Window (O)"); select_window_button.clicked.connect(self.select_window)
        clear_window_button = QPushButton("Clear Window"); clear_window_button.clicked.connect(self.clear_window)
        window_frame.addWidget(select_window_button); window_frame.addWidget(clear_window_button)
        right_layout.addLayout(window_frame)
        save_load_frame = QHBoxLayout()
        save_colors_button = QPushButton("Save Color Data"); save_colors_button.clicked.connect(self.save_colors)
        load_colors_button = QPushButton("Load Color Data"); load_colors_button.clicked.connect(self.load_colors)
        save_load_frame.addWidget(save_colors_button); save_load_frame.addWidget(load_colors_button)
        right_layout.addLayout(save_load_frame)
        self.autoclick_button_intelligent = QPushButton("Start/Stop Autoclicker (`)"); self.autoclick_button_intelligent.clicked.connect(self.toggle_autoclicker)
        right_layout.addWidget(self.autoclick_button_intelligent)
        right_layout.addStretch(1)
        main_layout.addWidget(left_group); main_layout.addLayout(right_layout)
        return frame

    def start_performance_monitoring(self):
        self.performance_worker = PerformanceWorker(self)
        self.performance_worker.performance_signal.connect(self._update_performance_ui)
        self.performance_worker.start()

    def _update_performance_ui(self, cps, cps_per_position, cpu_usage):
        self.performance_label.setText(f"Performance: CPS: {cps} | CPS/Position: {cps_per_position:.2f} | CPU: {cpu_usage:.2f}%")
        
    def closeEvent(self, event):
        self.stop_autoclicker_worker()
        if self.performance_worker: self.performance_worker.stop()
        if hasattr(self, 'keyboard_listener'): self.keyboard_listener.stop()
        self._cleanup_shared_memory()
        if self.pool: self.pool.close(); self.pool.join()
        event.accept()

    def _create_shared_memory(self, shape, dtype=np.uint8):
        if hasattr(self, 'shm') and self.shm: self._cleanup_shared_memory()
        self.shm_shape = shape; self.shm_dtype = dtype
        required_bytes = int(np.prod(shape) * np.dtype(dtype).itemsize)
        self.shm_name = f"autoclicker_screenshot_{uuid.uuid4()}"
        try:
            self.shm = shared_memory.SharedMemory(name=self.shm_name, create=True, size=required_bytes)
        except FileExistsError:
            temp_shm = shared_memory.SharedMemory(name=self.shm_name, create=False)
            temp_shm.close(); temp_shm.unlink()
            self.shm = shared_memory.SharedMemory(name=self.shm_name, create=True, size=required_bytes)

    def _cleanup_shared_memory(self):
        if hasattr(self, 'shm') and self.shm:
            try:
                self.shm.close()
                self.shm.unlink()
            except FileNotFoundError: pass
            finally: self.shm = None; self.shm_name = None

    def handle_results(self, results):
        if not self.clicking: return
        for result_chunk in results:
            for coords in result_chunk:
                x_local = coords[0] - self.window.left
                y_local = coords[1] - self.window.top
                if not self.target_queue.full():
                    self.target_queue.put((x_local, y_local))

    def split_screenshot_into_chunks(self, shape):
        height, width, _ = shape
        chunks = []
        rows = int(np.ceil(np.sqrt(self.num_cores)))
        cols = int(np.ceil(self.num_cores / rows))
        chunk_height, chunk_width = height // rows, width // cols
        for row in range(rows):
            for col in range(cols):
                start_y = row * chunk_height
                h = (height - start_y) if row == rows - 1 else chunk_height
                start_x = col * chunk_width
                w = (width - start_x) if col == cols - 1 else chunk_width
                chunks.append((start_y, start_x, h, w))
        return chunks

    def start_autoclicker_worker(self):
        self.stop_autoclicker_worker()
        if self.mode in ["dynamic", "multi-position"]:
            self.click_worker = ClickWorker(self.mode, self.click_interval, self.pointer_positions)
            self.click_worker.click_signal.connect(self._update_click_count)
            self.click_worker.start()
        elif self.mode == "intelligent":
            if not self.window or not hasattr(self.window, '_hWnd'):
                QMessageBox.warning(self, "No Window", "Please select a valid target window."); self.clicking = False; return
            while not self.target_queue.empty(): self.target_queue.get()
            self._create_shared_memory(shape=(self.window.height, self.window.width, 3))
            self.click_action_worker = ClickActionWorker(self.target_queue, self.window._hWnd)
            self.click_action_worker.click_executed_signal.connect(lambda: self._update_click_count(1))
            self.click_action_worker.start()
            self.capture_worker = CaptureWorker(self)
            self.capture_worker.error_signal.connect(self.on_worker_error)
            self.capture_worker.start()

    def stop_autoclicker_worker(self):
        if self.click_worker and self.click_worker.isRunning(): self.click_worker.stop()
        if self.capture_worker and self.capture_worker.isRunning(): self.capture_worker.stop()
        if self.click_action_worker and self.click_action_worker.isRunning(): self.click_action_worker.stop()
        self._cleanup_shared_memory()

    def on_worker_error(self, message):
        self.text_signal.emit(message)
        if self.clicking: self.toggle_autoclicker()

    def toggle_autoclicker(self):
        if self.clicking:
            self.stop_autoclicker_worker()
            self.clicking = False
            self.text_signal.emit("Autoclicker disabled.")
        else:
            if self.mode == "multi-position" and not self.pointer_positions:
                QMessageBox.warning(self, "No Positions", "No positions captured yet!"); return
            if self.mode == "intelligent" and not self.colors:
                QMessageBox.warning(self, "No Colors", "No target colors defined!"); return
            self.clicking = True
            self.text_signal.emit("Autoclicker enabled.")
            self.start_autoclicker_worker()

    def _update_click_count(self, clicks=1): self.click_count += clicks
    def get_position_count(self): return len(self.pointer_positions) if self.mode == "multi-position" else (len(self.colors) if self.mode == "intelligent" else 1)
    def update_text_box(self, message): self.text_box.insertPlainText(message + "\n"); self.text_box.ensureCursorVisible()
    def set_multi_position_mode(self): self.mode = "multi-position"; self.multi_position_frame.show(); self.dynamic_frame.hide(); self.intelligent_frame.hide(); self.resize(500, 500)
    def set_dynamic_mode(self): self.mode = "dynamic"; self.multi_position_frame.hide(); self.dynamic_frame.show(); self.intelligent_frame.hide(); self.resize(500, 400)
    def set_intelligent_mode(self): self.mode = "intelligent"; self.multi_position_frame.hide(); self.dynamic_frame.hide(); self.intelligent_frame.show(); self.resize(960, 580)
    def add_color(self): color = QColorDialog.getColor(); self.colors.append(color.name().upper()) if color.isValid() else None; self.update_color_boxes()
    def delete_color(self): self.colors.pop(self.selected_color_index) if self.selected_color_index is not None else None; self.selected_color_index = None; self.update_color_boxes()
    def start_global_hotkey_listener(self):
        def on_press(key):
            try:
                if key == pynput.keyboard.KeyCode.from_char('`'): QTimer.singleShot(0, self.toggle_autoclicker)
                elif key == pynput.keyboard.KeyCode.from_char('p') and not self.clicking and self.mode == "multi-position": QTimer.singleShot(0, self.capture_position)
                elif key == pynput.keyboard.KeyCode.from_char('o') and self.mode == "intelligent": QTimer.singleShot(0, self.select_window)
            except Exception: pass
        self.keyboard_listener = pynput.keyboard.Listener(on_press=on_press); self.keyboard_listener.daemon = True; self.keyboard_listener.start()
    def capture_position(self): x, y = pynput.mouse.Controller().position; self.pointer_positions.append((x, y)); self.text_signal.emit(f"Captured: ({x}, {y})")
    def clear_positions(self): self.pointer_positions.clear(); self.text_signal.emit("Positions cleared.")
    def select_window(self):
        self.setWindowState(self.windowState() | Qt.WindowState.WindowMinimized); QCoreApplication.processEvents(); time.sleep(0.5)
        self.window = gw.getActiveWindow()
        self.setWindowState(self.windowState() & ~Qt.WindowState.WindowMinimized); self.activateWindow(); self.raise_()
        if self.window: self.text_signal.emit(f"Window selected: {self.window.title}")
        else: self.text_signal.emit("No active window detected.")
    def clear_window(self): self.window = None; self.text_signal.emit("Window cleared.")
    def update_color_boxes(self):
        for i in reversed(range(self.color_boxes_layout.count())): self.color_boxes_layout.itemAt(i).widget().deleteLater()
        for i, color in enumerate(self.colors):
            color_box = QLabel(color); color_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
            fg_color = "black" if (int(color[1:3], 16)*0.299 + int(color[3:5], 16)*0.587 + int(color[5:7], 16)*0.114) > 140 else "white"
            style = f"QLabel {{ background-color: {color}; color: {fg_color}; border: 1px solid #555; padding: 5px; }}"
            if i == self.selected_color_index: style += "QLabel { border: 2px solid yellow; }"
            color_box.setStyleSheet(style); color_box.mousePressEvent = lambda e, idx=i: self.select_color(idx); self.color_boxes_layout.addWidget(color_box)
    def select_color(self, index): self.selected_color_index = index; self.update_color_boxes()
    def set_min_pixel(self): self.min_check_pixel = int(self.min_check_pixel_entry.text())
    def save_positions(self): file_name, _ = QFileDialog.getSaveFileName(self, "Save Positions", "", "JSON Files (*.json)"); json.dump(self.pointer_positions, open(file_name, "w")) if file_name else None
    def load_positions(self): file_name, _ = QFileDialog.getOpenFileName(self, "Load Positions", "", "JSON Files (*.json)"); self.pointer_positions = json.load(open(file_name, "r")) if file_name else None
    def save_colors(self): file_name, _ = QFileDialog.getSaveFileName(self, "Save Colors", "", "JSON Files (*.json)"); json.dump({"colors_to_click": self.colors}, open(file_name, "w")) if file_name else None
    def load_colors(self): file_name, _ = QFileDialog.getOpenFileName(self, "Load Colors", "", "JSON Files (*.json)"); self.colors = json.load(open(file_name, "r")).get("colors_to_click", []) if file_name else None; self.update_color_boxes()
    def set_interval(self, mode): self.click_interval = float(self.interval_entry.text()) / 1000 if mode == "multi-position" else float(self.dynamic_interval_entry.text()) / 1000
    
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53)); palette.setColor(QPalette.ColorRole.WindowText, QColor(255, 255, 255)); palette.setColor(QPalette.ColorRole.Base, QColor(25, 25, 25)); palette.setColor(QPalette.ColorRole.AlternateBase, QColor(53, 53, 53)); palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(255, 255, 255)); palette.setColor(QPalette.ColorRole.ToolTipText, QColor(255, 255, 255)); palette.setColor(QPalette.ColorRole.Text, QColor(255, 255, 255)); palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53)); palette.setColor(QPalette.ColorRole.ButtonText, QColor(255, 255, 255)); palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 0, 0)); palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218)); palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218)); palette.setColor(QPalette.ColorRole.HighlightedText, QColor(0, 0, 0))
    app.setPalette(palette)
    window = PointerAutoClicker()
    window.show()
    sys.exit(app.exec())
