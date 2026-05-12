import asyncio
import websockets
import json
import requests
import tkinter as tk
from tkinter import messagebox, scrolledtext
from datetime import datetime
import threading

VPS_URL = "ws://174.138.22.235:8765"
EXECUTOR_URL = "http://localhost:5555"

class AgentCore:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("AetherTrade AI - MT5 Agent")
        self.root.geometry("450x400")
        self.root.configure(bg="#1a1a2e")
        self.root.resizable(False, False)
        
        tk.Label(self.root, text="AETHER TRADE AI", font=("Arial", 18, "bold"), bg="#1a1a2e", fg="#e2b04a").pack(pady=(15,0))
        tk.Label(self.root, text="Verifikasi Lisensi & Terima Sinyal", font=("Arial", 9), bg="#1a1a2e", fg="white").pack()
        tk.Frame(self.root, height=1, bg="#e2b04a").pack(fill="x", padx=30, pady=8)
        
        tk.Label(self.root, text="License Key:", font=("Arial", 11, "bold"), bg="#1a1a2e", fg="white").pack(pady=(10,0))
        self.key_entry = tk.Entry(self.root, font=("Arial", 10), width=40, justify="center", bg="#0f3460", fg="#00ff88")
        self.key_entry.pack(pady=5, ipady=2)
        
        btn_frame = tk.Frame(self.root, bg="#1a1a2e")
        btn_frame.pack(pady=8)
        self.connect_btn = tk.Button(btn_frame, text="CONNECT", command=self.connect, bg="#00cc66", fg="white", font=("Arial", 11, "bold"), width=12)
        self.connect_btn.pack(side="left", padx=5)
        self.disconnect_btn = tk.Button(btn_frame, text="DISCONNECT", command=self.disconnect, bg="#cc3333", fg="white", font=("Arial", 11, "bold"), width=12, state="disabled")
        self.disconnect_btn.pack(side="left", padx=5)
        
        self.status_label = tk.Label(self.root, text="Status: Disconnected", font=("Arial", 10), bg="#1a1a2e", fg="#ff4444")
        self.status_label.pack(pady=3)
        self.mt5_label = tk.Label(self.root, text="Executor: Not Connected", font=("Arial", 9), bg="#1a1a2e", fg="gray")
        self.mt5_label.pack(pady=2)
        self.info_label = tk.Label(self.root, text="", font=("Arial", 8), bg="#1a1a2e", fg="gray")
        self.info_label.pack(pady=2)
        
        log_frame = tk.Frame(self.root, bg="#0f3460")
        log_frame.pack(pady=8, padx=15, fill="both", expand=True)
        self.log = scrolledtext.ScrolledText(log_frame, height=8, bg="#0f3460", fg="#00ff88", font=("Consolas", 9))
        self.log.pack(fill="both", expand=True)
        self.log.insert("end", "Welcome to AetherTrade AI MT5 Agent\n")
        self.log.insert("end", "Masukkan License Key lalu klik CONNECT\n")
        self.log.configure(state="disabled")
        
        tk.Label(self.root, text="Pastikan start_executor.bat sudah dijalankan", font=("Arial", 7), bg="#1a1a2e", fg="gray").pack(side="bottom", pady=5)
        
        self.running = False
        self.ws = None
    
    def log_msg(self, msg):
        self.log.configure(state="normal")
        t = datetime.now().strftime('%H:%M:%S')
        self.log.insert("end", f"[{t}] {msg}\n")
        self.log.see("end")
        self.log.configure(state="disabled")
    
    def check_executor(self):
        try:
            r = requests.get(f"{EXECUTOR_URL}/ping", timeout=2)
            if r.status_code == 200:
                self.mt5_label.config(text="Executor: CONNECTED", fg="#00ff88")
                return True
        except:
            pass
        self.mt5_label.config(text="Executor: NOT FOUND (jalankan start_executor.bat)", fg="#ff4444")
        return False
    
    def connect(self):
        key = self.key_entry.get().strip()
        if not key:
            messagebox.showerror("Error", "Masukkan License Key!")
            return
        
        self.check_executor()
        
        self.key_entry.config(state="disabled")
        self.connect_btn.config(state="disabled")
        self.disconnect_btn.config(state="normal")
        self.status_label.config(text="Status: Connecting...", fg="#ffaa00")
        self.running = True
        
        threading.Thread(target=self.run_ws, args=(key,), daemon=True).start()
    
    def disconnect(self):
        self.running = False
        self.status_label.config(text="Status: Disconnected", fg="#ff4444")
        self.key_entry.config(state="normal")
        self.connect_btn.config(state="normal")
        self.disconnect_btn.config(state="disabled")
    
    def run_ws(self, key):
        async def main_ws():
            try:
                async with websockets.connect(VPS_URL) as ws:
                    self.ws = ws
                    await ws.send(json.dumps({"action": "auth", "key": key}))
                    resp = json.loads(await asyncio.wait_for(ws.recv(), timeout=15))
                    
                    if resp.get("status") != "OK":
                        self.root.after(0, lambda: self.log_msg(f"Error: {resp.get('message', 'Invalid')}"))
                        self.root.after(0, lambda: self.status_label.config(text="Status: License Invalid", fg="#ff4444"))
                        self.root.after(0, self.disconnect)
                        return
                    
                    pkg = resp.get("package", "?").upper()
                    exp = resp.get("expires", "Unknown")
                    self.root.after(0, lambda: self.status_label.config(text=f"Status: ACTIVE ({pkg})", fg="#00ff88"))
                    self.root.after(0, lambda: self.log_msg(f"Connected - Package: {pkg}"))
                    
                    if exp != "Unknown":
                        try:
                            exp_date = datetime.fromisoformat(exp)
                            d_left = (exp_date - datetime.now()).days
                            self.root.after(0, lambda: self.info_label.config(text=f"Expires: {exp[:10]} ({d_left} days left)"))
                            if exp_date < datetime.now():
                                self.root.after(0, lambda: self.log_msg("LICENSE EXPIRED!"))
                                self.root.after(0, lambda: messagebox.showwarning("Expired", "Lisensi sudah expired!"))
                                self.root.after(0, self.disconnect)
                                return
                        except:
                            pass
                    
                    # Check executor
                    if self.check_executor():
                        self.root.after(0, lambda: self.log_msg("Executor ready - Waiting for signals..."))
                    else:
                        self.root.after(0, lambda: self.log_msg("WARNING: Executor tidak terdeteksi!"))
                    
                    while self.running:
                        try:
                            msg = await asyncio.wait_for(ws.recv(), timeout=30)
                            data = json.loads(msg)
                            if data.get("action") == "trade_signal":
                                sig = data["signal"]
                                # Kirim ke executor
                                try:
                                    r = requests.post(f"{EXECUTOR_URL}/order", json=sig, timeout=5)
                                    ok = r.json().get("success", False) if r.status_code == 200 else False
                                    s = "OK" if ok else "FAIL"
                                    self.root.after(0, lambda: self.log_msg(f"[{s}] {sig['pair']} {sig['direction']} @ {sig['entry']}"))
                                except:
                                    self.root.after(0, lambda: self.log_msg(f"[FAIL] Executor not responding"))
                        except asyncio.TimeoutError:
                            continue
                        except:
                            break
            except Exception as e:
                self.root.after(0, lambda: self.log_msg(f"Connection error: {e}"))
            finally:
                self.root.after(0, self.disconnect)
        
        asyncio.run(main_ws())
    
    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", lambda: (setattr(self, 'running', False), self.root.destroy()))
        self.root.mainloop()

if __name__ == "__main__":
    AgentCore().run()