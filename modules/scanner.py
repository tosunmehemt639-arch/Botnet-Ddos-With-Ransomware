#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import socket
import threading
import ipaddress
import subprocess
import platform
import os
import re
import json
from datetime import datetime

class NetworkScanner:
    def __init__(self):
        self.open_ports = {}
        self.vulnerable_hosts = []
    
    # Port tarama
    def scan_ports(self, target_ip, ports=None, timeout=1, max_threads=100):
        if ports is None:
            ports = [21, 22, 23, 25, 53, 80, 110, 135, 139, 143, 443, 445, 993, 995, 1723, 3306, 3389, 5900, 8080]
        
        open_ports = []
        
        def check_port(port):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(timeout)
                result = sock.connect_ex((target_ip, port))
                sock.close()
                
                if result == 0:
                    open_ports.append(port)
                    service = self.get_service_name(port)
                    return port, service
            except:
                pass
            return None
        
        # Thread pool ile tarama
        with ThreadPoolExecutor(max_workers=max_threads) as executor:
            results = list(executor.map(check_port, ports))
        
        self.open_ports[target_ip] = [r for r in results if r]
        return self.open_ports[target_ip]
    
    def get_service_name(self, port):
        services = {
            21: 'FTP',
            22: 'SSH',
            23: 'Telnet',
            25: 'SMTP',
            53: 'DNS',
            80: 'HTTP',
            110: 'POP3',
            135: 'MSRPC',
            139: 'NetBIOS',
            143: 'IMAP',
            443: 'HTTPS',
            445: 'SMB',
            993: 'IMAPS',
            995: 'POP3S',
            1723: 'PPTP',
            3306: 'MySQL',
            3389: 'RDP',
            5900: 'VNC',
            8080: 'HTTP-Proxy'
        }
        return services.get(port, 'Unknown')
    
    # Ağ tarama (CIDR)
    def scan_network(self, network_cidr="192.168.1.0/24", ports=[22, 80, 443]):
        active_hosts = []
        
        def scan_host(ip_str):
            try:
                # Ping gönder (platform bağımsız)
                param = '-n' if platform.system().lower() == 'windows' else '-c'
                command = ['ping', param, '1', '-W', '1', ip_str]
                
                if subprocess.call(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0:
                    open_ports = self.scan_ports(ip_str, ports)
                    if open_ports:
                        active_hosts.append({
                            'ip': ip_str,
                            'ports': open_ports,
                            'timestamp': datetime.now().isoformat()
                        })
            except:
                pass
        
        # Tüm IP'leri tarı
        threads = []
        for ip in ipaddress.IPv4Network(network_cidr):
            t = threading.Thread(target=scan_host, args=(str(ip),))
            t.start()
            threads.append(t)
        
        # Bekle
        for t in threads:
            t.join(timeout=2)
        
        return active_hosts
    
    # SSH Brute Force (sadece test)
    def ssh_bruteforce(self, target_ip, port=22, username_list=None, password_list=None):
        if username_list is None:
            username_list = ['root', 'admin', 'user', 'ubuntu', 'pi']
        
        if password_list is None:
            password_list = ['admin', 'password', '123456', 'root', 'toor', 'raspberry']
        
        import paramiko
        
        for username in username_list:
            for password in password_list:
                try:
                    ssh = paramiko.SSHClient()
                    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    ssh.connect(target_ip, port=port, username=username, password=password, timeout=5)
                    ssh.close()
                    
                    return {
                        'ip': target_ip,
                        'username': username,
                        'password': password,
                        'port': port,
                        'status': 'SUCCESS'
                    }
                except:
                    continue
        
        return {'status': 'FAILED'}
    
    # Web tarama
    def web_scanner(self, target_url):
        import requests
        
        results = {
            'url': target_url,
            'headers': {},
            'technologies': [],
            'vulnerabilities': []
        }
        
        try:
            # HEAD isteği
            resp = requests.head(target_url, timeout=5, allow_redirects=True)
            results['headers'] = dict(resp.headers)
            
            # GET isteği
            resp = requests.get(target_url, timeout=5)
            results['status_code'] = resp.status_code
            
            # Technology detection
            if 'X-Powered-By' in resp.headers:
                results['technologies'].append(resp.headers['X-Powered-By'])
            
            if 'Server' in resp.headers:
                results['technologies'].append(resp.headers['Server'])
            
            # Basic vulnerability checks
            if resp.status_code == 200:
                if 'php' in resp.text.lower():
                    results['technologies'].append('PHP')
                
                # SQL injection test
                test_url = f"{target_url}'"
                test_resp = requests.get(test_url, timeout=3)
                if 'sql' in test_resp.text.lower() or 'syntax' in test_resp.text.lower():
                    results['vulnerabilities'].append('SQL_INJECTION_POSSIBLE')
                
                # Directory traversal test
                traversal_test = f"{target_url}/../../../../etc/passwd"
                traversal_resp = requests.get(traversal_test, timeout=3)
                if 'root:' in traversal_resp.text:
                    results['vulnerabilities'].append('DIRECTORY_TRAVERSAL_POSSIBLE')
            
        except Exception as e:
            results['error'] = str(e)
        
        return results
    
    # Sistem bilgisi toplama
    def gather_system_info(self):
        info = {
            'platform': platform.platform(),
            'system': platform.system(),
            'release': platform.release(),
            'version': platform.version(),
            'architecture': platform.architecture(),
            'processor': platform.processor(),
            'hostname': socket.gethostname(),
            'ip_address': socket.gethostbyname(socket.gethostname()),
            'users': [],
            'processes': []
        }
        
        # Kullanıcılar (Linux)
        if os.path.exists('/etc/passwd'):
            with open('/etc/passwd', 'r') as f:
                for line in f:
                    if ':/' in line:
                        username = line.split(':')[0]
                        info['users'].append(username)
        
        # Çalışan prosesler
        try:
            if platform.system() == 'Windows':
                output = subprocess.check_output('tasklist', shell=True).decode()
                info['processes'] = output.split('\n')[:20]
            else:
                output = subprocess.check_output('ps aux', shell=True).decode()
                info['processes'] = output.split('\n')[:20]
        except:
            pass
        
        return info
    
    # Otomatik exploit tarama
    def vulnerability_scan(self, target_ip, target_port):
        vuln_results = []
        
        # Port bazlı exploit kontrolü
        common_vulns = {
            21: ['FTP_ANONYMOUS', 'FTP_BRUTEFORCE'],
            22: ['SSH_BRUTEFORCE', 'SSH_WEAK_KEYS'],
            23: ['TELNET_CLEARTEXT'],
            80: ['HTTP_DIR_TRAVERSAL', 'SQL_INJECTION', 'XSS'],
            443: ['SSL_WEAK_CIPHERS', 'HEARTBLEED'],
            445: ['ETERNALBLUE', 'SMB_V1'],
            3389: ['BLUEKEEP', 'RDP_BRUTEFORCE']
        }
        
        if target_port in common_vulns:
            vuln_results.extend(common_vulns[target_port])
        
        return {
            'ip': target_ip,
            'port': target_port,
            'vulnerabilities': vuln_results,
            'timestamp': datetime.now().isoformat()
        }
          
