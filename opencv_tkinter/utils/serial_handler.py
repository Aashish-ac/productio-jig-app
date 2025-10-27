import serial
import serial.tools.list_ports
import threading
import time
import queue

class SerialHandler:
    def __init__(self, parent_app):
        self.parent_app = parent_app
        self.ser = None
        self.is_connected = False
        self.is_listening = False
        self.listen_thread = None
        self.rx_queue = queue.Queue()
        self.last_port = None
        self.last_baud = None
        self.auto_reconnect_enabled = False

    def connect(self, port, baudrate):
        try:
            # Save connection parameters for auto-reconnect
            self.last_port = port
            self.last_baud = baudrate
            
            self.ser = serial.Serial(
                port=port,
                baudrate=int(baudrate),
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=1,
                xonxoff=False,
                rtscts=False,
                dsrdtr=False,
                write_timeout=1
            )
            self.is_connected = True
            # Use thread-safe logging with connection details
            self.parent_app.log_message_safe(
                f"✓ Connected {self.ser.port} @ {self.ser.baudrate} 8N1 "
                f"(xonxoff={self.ser.xonxoff}, rtscts={self.ser.rtscts}, dsrdtr={self.ser.dsrdtr})",
                'status'
            )
            self.start_listening()
            return True
        except Exception as e:
            self.parent_app.log_message_safe(f"✗ Connection failed: {e}", 'error')
            raise Exception(f"Connection failed: {e}")
    
    def enable_auto_reconnect(self, interval=5000):
        """Enable auto-reconnect if connection is lost"""
        self.auto_reconnect_enabled = True
        self._check_and_reconnect(interval)
    
    def disable_auto_reconnect(self):
        """Disable auto-reconnect"""
        self.auto_reconnect_enabled = False
    
    def _check_and_reconnect(self, interval):
        """Check connection and reconnect if needed"""
        if self.auto_reconnect_enabled and not self.is_connected and self.last_port:
            try:
                self.parent_app.log_message_safe("Attempting auto-reconnect...", 'status')
                self.connect(self.last_port, self.last_baud)
            except Exception as e:
                self.parent_app.log_message_safe(f"Auto-reconnect failed: {e}", 'error')
        
        # Schedule next check
        if self.auto_reconnect_enabled and hasattr(self.parent_app, 'root'):
            try:
                self.parent_app.root.after(interval, lambda: self._check_and_reconnect(interval))
            except:
                pass

    def disconnect(self):
        self.stop_listening()
        if self.ser and self.ser.is_open:
            self.ser.close()
        self.is_connected = False

    # I AM READY message is added in the services that run late in the camera, so that the logic from this app is implemeted once the camera is fully booted


    def process_message(self, message):
        """Process special messages"""
        if "I AM READY" in message:
            self.parent_app.camera_status_var.set("🟢 READY")
        elif "Play streams from this server" in message:
            # Trigger boot login sequence
            self.parent_app.schedule_login()

    def send_command(self, command):
        """Send command via serial"""
        if not self.is_connected or not self.ser:
            raise Exception("Not connected")
        try:
            # Log command before sending (safe for threads)
            self.parent_app.log_message_safe(f"📤 {command}", 'sent')
            # Normalize line ending to CRLF
            cmd = (command.rstrip() + "\r\n").encode("utf-8")
            self.ser.write(cmd)
            self.ser.flush()
        except Exception as e:
            self.parent_app.log_message_safe(f"Send error: {e}", 'error')
            raise

    def start_listening(self):
        if self.is_listening:
            return
        self.is_listening = True
        self.parent_app.log_message_safe("→ Starting serial listener...", 'status')
        self.listen_thread = threading.Thread(target=self.listen_loop, daemon=True)
        self.listen_thread.start()

    def stop_listening(self):
        self.is_listening = False
        try:
            if self.ser and self.ser.is_open:
                self.ser.close()  # This will unblock read()
        except Exception:
            pass
        # No join() needed; daemon thread will exit

    def listen_loop(self):
        """Main listening loop - chunk-based reading with proper CRLF handling"""
        self.parent_app.log_message_safe("✓ Serial listener started", 'status')
        buf = b""
        while self.is_listening and self.ser and self.ser.is_open:
            try:
                # Read chunks instead of blocking on readline()
                chunk = self.ser.read(1024)
                if chunk:
                    buf += chunk
                    # Process complete lines
                    while b"\n" in buf or b"\r" in buf:
                        # Prefer LF; if only CR present, split on CR
                        sep = b"\n" if b"\n" in buf else b"\r"
                        line, buf = buf.split(sep, 1)
                        try:
                            text = line.decode('utf-8', errors='replace').strip()
                            if text:
                                # Put message in queue instead of calling after_idle
                                self.rx_queue.put(text)
                        except Exception as decode_error:
                            self.parent_app.log_message_safe(f"⚠ Decode error: {decode_error}", 'error')
                else:
                    # Idle a bit to reduce CPU when no data
                    time.sleep(0.02)
            except Exception as e:
                self.parent_app.log_message_safe(f"✗ Listening error: {e}", 'error')
                break
        self.parent_app.log_message_safe("✗ Serial listener stopped", 'status')

    @staticmethod
    def get_available_ports():
        """Get available serial ports, prioritizing USB serial ports on macOS"""
        import platform
        import glob
        
        # Get standard ports first
        ports = [port.device for port in serial.tools.list_ports.comports()]
        
        # On macOS, add USB serial ports (both tty and cu)
        if platform.system() == "Darwin":
            usb_ports = sorted(glob.glob("/dev/tty.usb*")) + sorted(glob.glob("/dev/cu.usb*"))
            # Prepend USB ports to the list
            for usb_port in usb_ports:
                if usb_port not in ports:
                    ports.insert(0, usb_port)
        
        # On Linux, add common USB serial ports
        elif platform.system() == "Linux":
            usb_ports = glob.glob("/dev/ttyUSB*") + glob.glob("/dev/ttyACM*")
            for usb_port in usb_ports:
                if usb_port not in ports:
                    ports.append(usb_port)
        
        return ports
