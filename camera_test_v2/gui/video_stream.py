"""
Video streaming manager with proper 16:9 aspect ratio handling
"""
import cv2
import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import QLabel
import logging
import time

logger = logging.getLogger(__name__)


class VideoStreamThread(QThread):
    """Background thread for video streaming"""
    frame_ready = pyqtSignal(np.ndarray)
    error_occurred = pyqtSignal(str)
    stream_stopped = pyqtSignal()
    
    def __init__(self, rtsp_url: str):
        super().__init__()
        self.rtsp_url = rtsp_url
        self.is_running = False
        self.cap = None
    
    def run(self):
        """Main streaming loop - simplified"""
        self.is_running = True
        consecutive_failures = 0
        
        try:
            logger.info(f"Starting RTSP stream: {self.rtsp_url}")
            
            # Simplified VideoCapture - no forced backend
            self.cap = cv2.VideoCapture(self.rtsp_url)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            # Give camera time to initialize
            time.sleep(0.5)
            
            # Verify connection
            ret, frame = self.cap.read()
            if not ret:
                raise Exception("Could not open RTSP stream")
            
            logger.info("RTSP stream opened successfully")
            self.frame_ready.emit(frame)
            
            while self.is_running:
                ret, frame = self.cap.read()
                
                if not ret:
                    consecutive_failures += 1
                    if consecutive_failures >= 10:
                        logger.error("Too many consecutive frame failures")
                        break
                    time.sleep(0.1)
                    continue
                
                consecutive_failures = 0
                self.frame_ready.emit(frame)
                self.msleep(33)  # ~30 FPS
        
        except Exception as e:
            logger.error(f"Stream error: {e}")
            self.error_occurred.emit(str(e))
        finally:
            self.cleanup()
    
    def stop(self):
        logger.info("Stopping RTSP stream")
        self.is_running = False
    
    def cleanup(self):
        if self.cap:
            try:
                self.cap.release()
            except:
                pass
        self.stream_stopped.emit()
        logger.info("Stream cleanup complete")


class VideoStreamManager:
    """Manages video streaming with proper 16:9 aspect ratio"""
    
    def __init__(self, video_label: QLabel):
        self.video_label = video_label
        self.stream_thread = None
        self.current_url = None
    
    def start_stream(self, rtsp_url: str):
        if not rtsp_url or not rtsp_url.strip():
            logger.error("Invalid RTSP URL")
            return False
        
        self.stop_stream()
        
        self.stream_thread = VideoStreamThread(rtsp_url.strip())
        self.stream_thread.frame_ready.connect(self.update_frame)
        self.stream_thread.error_occurred.connect(self.handle_error)
        self.stream_thread.stream_stopped.connect(self.on_stream_stopped)
        
        self.current_url = rtsp_url
        self.stream_thread.start()
        logger.info(f"Stream started: {rtsp_url}")
        return True
    
    def stop_stream(self):
        if self.stream_thread and self.stream_thread.isRunning():
            self.stream_thread.stop()
            self.stream_thread.wait(3000)
            logger.info("Stream stopped")
    
    def update_frame(self, frame: np.ndarray):
        """Update frame maintaining 16:9 ratio with letterboxing"""
        try:
            # Fixed 16:9 container dimensions (720x405)
            container_width = 720
            container_height = 405
            
            # Get frame dimensions
            frame_height, frame_width = frame.shape[:2]
            
            # Calculate 16:9 dimensions that fit inside container
            target_ratio = 16 / 9
            frame_ratio = frame_width / frame_height
            
            if frame_ratio > target_ratio:
                # Frame is wider than 16:9
                new_width = container_width
                new_height = int(container_width / target_ratio)
            else:
                # Frame is taller than 16:9
                new_height = container_height
                new_width = int(container_height * target_ratio)
            
            # Ensure it fits in container
            if new_width > container_width:
                new_width = container_width
                new_height = int(container_width / target_ratio)
            if new_height > container_height:
                new_height = container_height
                new_width = int(container_height * target_ratio)
            
            # Resize frame
            frame_resized = cv2.resize(frame, (new_width, new_height), 
                                      interpolation=cv2.INTER_LINEAR)
            
            # Create black letterbox canvas
            canvas = np.zeros((container_height, container_width, 3), dtype=np.uint8)
            
            # Center frame on canvas
            y_offset = (container_height - new_height) // 2
            x_offset = (container_width - new_width) // 2
            canvas[y_offset:y_offset+new_height, x_offset:x_offset+new_width] = frame_resized
            
            # Convert to Qt format
            frame_rgb = cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB)
            h, w, ch = frame_rgb.shape
            bytes_per_line = ch * w
            qt_image = QImage(frame_rgb.data, w, h, bytes_per_line, 
                            QImage.Format.Format_RGB888)
            
            # Display without additional scaling
            pixmap = QPixmap.fromImage(qt_image)
            self.video_label.setPixmap(pixmap)
        
        except Exception as e:
            logger.error(f"Frame update error: {e}")
    
    def handle_error(self, error_msg: str):
        logger.error(f"Stream error: {error_msg}")
        self.video_label.setText(f"❌ Stream Error:\n{error_msg}")
        self.video_label.setStyleSheet(
            "background-color: #000000; border: 2px solid #d32f2f; "
            "border-radius: 5px; color: #fff; font-size: 12px;"
        )
    
    def on_stream_stopped(self):
        self.video_label.setText("📺 Stream stopped")
        self.video_label.setStyleSheet(
            "background-color: #000000; border: 2px solid #3d3d3d; "
            "border-radius: 5px; color: #888; font-size: 14px;"
        )
    
    def is_streaming(self) -> bool:
        return self.stream_thread is not None and self.stream_thread.isRunning()
