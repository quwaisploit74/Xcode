import requests
from bs4 import BeautifulSoup
import time
import os
import sys
import threading

# Konfigurasi Warna Terminal
GREEN   = "\033[32m"
CYAN    = "\033[36m"
RED     = "\033[31m"  # Warna untuk huruf kapital
WHITE   = "\033[37m"  # Warna untuk huruf non-kapital (Putih)
RESET   = "\033[0m"

# Teks target
original_text = "[+] monitoring link from eporner..."

def animation_worker():
    """Animasi huruf kapital merah satu per satu, sisanya putih."""
    while True:
        for i in range(len(original_text)):
            # Lewati spasi agar animasi tidak terlihat berhenti mendadak
            if original_text[i] == " ":
                continue
            
            # 1. Bagian kiri (Putih & kecil)
            left = original_text[:i].lower()
            # 2. Huruf tengah (Merah & KAPITAL)
            char = original_text[i].upper()
            # 3. Bagian kanan (Putih & kecil)
            right = original_text[i+1:].lower()
            
            # Gabungkan dengan kode warna ANSI
            # \r = kembali ke awal baris
            # \033[s = simpan posisi kursor
            # \033[u = kembalikan kursor
            display_text = f"{WHITE}{left}{RED}{char}{WHITE}{right}{RESET}"
            
            sys.stdout.write(f"\033[s\r{display_text}\033[u")
            sys.stdout.flush()
            
            # Kecepatan langkah (0.1 detik agar halus, ganti 0.5 jika ingin lambat)
            time.sleep(0.1)

def is_blacklisted(url, filename):
    if not os.path.exists(filename):
        return False
    with open(filename, 'r') as f:
        blacklist = {line.strip() for line in f}
        return url in blacklist

def log_to_file(url, filename):
    with open(filename, 'a') as f:
        f.write(f"{url}\n")

def scan_profile(username, file_hitam, file_log):
    target_url = f"https://www.eporner.com/profile/{username}/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    try:
        response = requests.get(target_url, headers=headers, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        links = soup.find_all('a', href=True)
        
        for link in links:
            href = link['href']
            if "/video-" in href:
                full_url = f"https://www.eporner.com{href}" if href.startswith('/') else href
                
                if not is_blacklisted(full_url, file_hitam):
                    # Bersihkan baris animasi sejenak untuk print link
                    sys.stdout.write(f"\r\033[K{CYAN}{full_url}{RESET}\n")
                    sys.stdout.flush()
                    
                    log_to_file(full_url, file_log)
                    log_to_file(full_url, file_hitam)
        
    except requests.exceptions.RequestException as e:
        pass
def main():
    if len(sys.argv) < 3:
        print(f"Penggunaan: python {sys.argv[0]} [username] [blacklist_file]")
        sys.exit(1)

    username = sys.argv[1]
    file_hitam = sys.argv[2]
    file_log = "link.txt"

    # Threading untuk animasi pelangi/wave
    anim_thread = threading.Thread(target=animation_worker, daemon=True)
    anim_thread.start()

    try:
        while True:
            scan_profile(username, file_hitam, file_log)
    except KeyboardInterrupt:
        pass
if __name__ == "__main__":
    main()
