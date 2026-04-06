import requests
from bs4 import BeautifulSoup
import time
import os
import sys
import threading

original_text = "[+] monitoring link from eporner"

def animation_worker():
    while True:
        for i in range(len(original_text)):
            if original_text[i] == " ":
                continue
            left = original_text[:i].lower()
            char = original_text[i].upper()
            right = original_text[i+1:].lower()
            display_text = f"{left}{char}{right}"
            sys.stdout.write(f"\033[s\r{display_text}\033[u")
            sys.stdout.flush()
            time.sleep(0.2)

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
                    sys.stdout.write(f"\r\033[K{full_url}\n")
                    sys.stdout.flush()
                    
                    log_to_file(full_url, file_log)
                    log_to_file(full_url, file_hitam)
        
    except requests.exceptions.RequestException as e:
        pass
def main():
    if len(sys.argv) < 3:
        print(f"Usage: python {sys.argv[0]} [username] [blacklist_file]")
        sys.exit(1)

    username = sys.argv[1]
    file_hitam = sys.argv[2]
    file_log = "link.txt"

    anim_thread = threading.Thread(target=animation_worker, daemon=True)
    anim_thread.start()

    try:
        while True:
            scan_profile(username, file_hitam, file_log)
    except KeyboardInterrupt:
        pass
if __name__ == "__main__":
    main()
