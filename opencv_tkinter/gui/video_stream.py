import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import cv2
from PIL import Image, ImageTk
import threading
import time
from datetime import datetime

class VideoStreamWindow:
    def __init__(self, parent_app, video_frame):
        self.parent_app = parent_app
        self.video_frame = video_frame
        self.cap = None
        self.is_streaming = False
        self.stream_thread = None
        self.default_rtsp_url = "rtsp://192.168.2.2/main"
        self.current_frame = None
        self.create_video_widgets()
        
    def create_video_widgets(self):
        """Create video stream widgets in the provided frame"""
        # Make controls frame more compact
        controls_frame = tk.Frame(self.video_frame, bg=self.parent_app.colors['card_bg'], height=30)
        controls_frame.pack(fill='x', padx=2, pady=2)
        controls_frame.pack_propagate(False)
        
        # URL input
        tk.Label(controls_frame, text="RTSP:", 
                bg=self.parent_app.colors['card_bg'], 
                fg=self.parent_app.colors['text']).pack(side='left', padx=5)
        
        self.url_var = tk.StringVar(value=self.default_rtsp_url)
        self.url_entry = ttk.Entry(controls_frame, textvariable=self.url_var, 
                                 width=25,
                                 style='Form.TEntry')
        self.url_entry.pack(side='left', padx=5)
        
        # Control buttons
        self.start_btn = ttk.Button(controls_frame, text="▶️", 
                                   command=self.start_stream, 
                                   style='Success.TButton', width=3)
        self.start_btn.pack(side='left', padx=2)
        
        self.stop_btn = ttk.Button(controls_frame, text="⏹️", 
                                  command=self.stop_stream, 
                                  style='Danger.TButton', width=3,
                                  state='disabled')
        self.stop_btn.pack(side='left', padx=2)
        
        # Screenshot button
        self.screenshot_btn = ttk.Button(controls_frame, text="📸", 
                                       command=self.take_screenshot, 
                                       style='Modern.TButton', width=3,
                                       state='disabled')
        self.screenshot_btn.pack(side='left', padx=2)
        
        # Status label
        self.stream_status_var = tk.StringVar(value="Ready")
        self.status_label = tk.Label(controls_frame, textvariable=self.stream_status_var,
                                    bg=self.parent_app.colors['card_bg'], 
                                    fg=self.parent_app.colors['text_secondary'])
        self.status_label.pack(side='right', padx=5)
        
        # Video display label - make it larger
        self.video_label = tk.Label(self.video_frame, 
                                   text="📺 Click ▶️ to start stream",
                                   bg=self.parent_app.colors['card_bg'], 
                                   fg=self.parent_app.colors['text_secondary'])
        self.video_label.pack(fill='both', expand=True, padx=2, pady=2)

    def start_stream(self):
        """Start the video stream - thread-safe version"""
        if self.is_streaming:
            return
            
        rtsp_url = self.url_var.get().strip()
        if not rtsp_url:
            messagebox.showerror("Error", "Please enter RTSP URL")
            return
        
        # Thread-safe function to update GUI after connection
        def _start_stream_internal():
            try:
                self.stream_status_var.set("Connecting...")
                self.cap = cv2.VideoCapture(rtsp_url)
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                
                ret, frame = self.cap.read()
                if not ret:
                    raise Exception("Could not read from stream")
                
                self.is_streaming = True
                self.stream_status_var.set("🟢 Streaming")
                
                # Update GUI elements
                if hasattr(self, 'start_btn'):
                    self.start_btn.configure(state='disabled')
                if hasattr(self, 'stop_btn'):
                    self.stop_btn.configure(state='normal')
                if hasattr(self, 'screenshot_btn'):
                    self.screenshot_btn.configure(state='normal')
                if hasattr(self, 'url_entry'):
                    self.url_entry.configure(state='disabled')
                
                # Start streaming thread
                self.stream_thread = threading.Thread(target=self.stream_loop, daemon=True)
                self.stream_thread.start()
                
            except Exception as e:
                self.stream_status_var.set("❌ Connection failed")
                
                # Thread-safe error dialog
                def _show_error():
                    messagebox.showerror("Stream Error", f"Failed to start video stream:\n{e}")
                
                try:
                    self.parent_app.root.after_idle(_show_error)
                except:
                    messagebox.showerror("Stream Error", f"Failed to start video stream:\n{e}")
                
                if self.cap:
                    self.cap.release()
                    self.cap = None
        
        # Schedule on main thread to ensure mainloop is running
        try:
            if hasattr(self.parent_app, 'root'):
                self.parent_app.root.after_idle(_start_stream_internal)
            else:
                _start_stream_internal()
        except RuntimeError:
            # If mainloop not started yet, run directly
            _start_stream_internal()

    def stream_loop(self):
        """Main video streaming loop"""
        fps_counter = 0
        fps_start_time = time.time()
        last_photo = None  # Keep reference to prevent GC
        
        while self.is_streaming and self.cap and self.cap.isOpened():
            try:
                ret, frame = self.cap.read()
                if not ret:
                    break
                
                self.current_frame = frame.copy()
                frame = self.resize_frame(frame, max_width=760, max_height=480)
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                photo = ImageTk.PhotoImage(Image.fromarray(frame_rgb))
                last_photo = photo  # Keep reference
                
                # Thread-safe GUI update with photo captured in closure
                def _update_image(img=photo):  # Capture photo in closure
                    if self.video_label and self.video_frame.winfo_exists():
                        self.video_label.configure(image=img, text='')
                        self.video_label.image = img  # Keep reference
                
                try:
                    self.parent_app.root.after_idle(_update_image)
                except:
                    pass
                
                fps_counter += 1
                if fps_counter >= 30:
                    current_time = time.time()
                    fps = fps_counter / (current_time - fps_start_time)
                    # Thread-safe status update
                    def _update_fps():
                        self.stream_status_var.set(f"🟢 Streaming ({fps:.1f} FPS)")
                    try:
                        self.parent_app.root.after_idle(_update_fps)
                    except:
                        pass
                    fps_counter = 0
                    fps_start_time = current_time
                
                time.sleep(0.01)
                
            except Exception as e:
                def _log_error():
                    if hasattr(self.parent_app, 'log_message'):
                        self.parent_app.log_message(f"Stream error: {e}", 'error')
                try:
                    self.parent_app.root.after_idle(_log_error)
                except:
                    print(f"Stream error: {e}")
                break
        
        self.stop_stream()

    def stop_stream(self):
        """Stop the video stream - thread-safe version"""
        self.is_streaming = False
        if self.cap:
            self.cap.release()
            self.cap = None
        
        # Thread-safe GUI updates
        def _update_gui():
            try:
                if hasattr(self, 'start_btn'):
                    self.start_btn.configure(state='normal')
                if hasattr(self, 'stop_btn'):
                    self.stop_btn.configure(state='disabled')
                if hasattr(self, 'screenshot_btn'):
                    self.screenshot_btn.configure(state='disabled')
                if hasattr(self, 'url_entry'):
                    self.url_entry.configure(state='normal')
                
                if hasattr(self, 'stream_status_var'):
                    self.stream_status_var.set("⏹️ Stopped")
                if hasattr(self, 'video_label'):
                    self.video_label.configure(image='', text="📺 Click ▶️ to start stream")
            except Exception as e:
                print(f"Error updating GUI: {e}")
        
        # ALWAYS schedule on main thread to avoid "main thread is not in main loop" error
        try:
            if self.parent_app and self.parent_app.root:
                self.parent_app.root.after_idle(_update_gui)
            else:
                # Fallback if not yet initialized
                pass
        except RuntimeError:
            # Main loop not ready - skip GUI update
            pass
        except Exception as e:
            print(f"Error scheduling GUI update: {e}")

    def resize_frame(self, frame, max_width=1280, max_height=720):  # Increased size
        """Resize frame while maintaining aspect ratio"""
        height, width = frame.shape[:2]
        scale_ratio = min(max_width/width, max_height/height)
        if scale_ratio < 1.0:
            new_width = int(width * scale_ratio)
            new_height = int(height * scale_ratio)
            frame = cv2.resize(frame, (new_width, new_height), 
                             interpolation=cv2.INTER_AREA)
        return frame

    def take_screenshot(self):
        """Take screenshot of current frame"""
        if self.current_frame is not None:
            try:
                timestamp = datetime.now().strftime("screenshot_%Y%m%d_%H%M%S")
                file_path = filedialog.asksaveasfilename(
                    defaultextension=".jpg",
                    initialfile=f"{timestamp}.jpg",
                    filetypes=[("JPEG files", "*.jpg"), 
                              ("PNG files", "*.png"),
                              ("All files", "*.*")]
                )
                if file_path:
                    cv2.imwrite(file_path, self.current_frame)
                    messagebox.showinfo("Success", f"Screenshot saved to:\n{file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save screenshot:\n{e}")
