import os
import subprocess
import argparse
import time
import random
import sys
import re
from pathlib import Path
from datetime import datetime

# --- CONFIGURATION ---
MAX_FOLDERS = 12
FILES_PER_FOLDER = 5
TOTAL_LIMIT = MAX_FOLDERS * FILES_PER_FOLDER

# --- UI CONSTANTS ---
CLEAR   = "\033[H\033[2J"
CUR_OFF = "\033[?25l"
CUR_ON  = "\033[?25h"

# --- GLOBAL STATE ---
start_time = datetime.now()
total_processed = 0
current_target = "SCANNING..."
current_status = "IDLE"
defrag_count = 0
ffmpeg_log = "WAITING FOR PROCESS..."
current_progress = "0%"
current_percent = 0 # Nilai integer untuk bar
current_tf = "" 

def get_progress_bar(percent, width=47):
    """Menghasilkan visual bar [###-----]"""
    filled_len = int(width * percent // 100)
    bar = "█" * filled_len + "░" * (width - filled_len)
    return f"[{bar}] {percent}%"

def get_folder_stats():
    counts = []
    for i in range(1, MAX_FOLDERS + 1):
        d_name = f"edit_{i}"
        count = len(list(Path(d_name).glob("*.mp4"))) if os.path.exists(d_name) else 0
        counts.append(f"{count:02d}")
    return counts


def draw_ui():
    elapsed = str(datetime.now() - start_time).split('.')[0]
    sys.stdout.write(CLEAR)
    #print(f"\t\t\t\tHikari 5.4.6")
    display_target = (current_target[:30] + '..') if len(current_target) > 30 else current_target
    ts = datetime.now().strftime("%H:%M:%S")
    counts = get_folder_stats()
    a=["00", "AB", "AF", "08", "CB", "F3", "AE", "0E", "F0", "BA", "80", "01"]
    print(f"""
                           HIKARI 6.0.0

    [{ts}] {total_processed} out of defragment file {defrag_count:<27}

    Status: {current_status:<20}, {display_target}\tFFMPEG

                {ffmpeg_log}

    FOLDER     : 01 02 03 04 05 06 07 08 09 10 11 12
               : {' '.join(counts)}

    BINARY     : {random.choice(a)} {random.choice(a)} {random.choice(a)} {random.choice(a)} {random.choice(a)} {random.choice(a)} {random.choice(a)} {random.choice(a)} {random.choice(a)} {random.choice(a)} {random.choice(a)} {random.choice(a)} {random.choice(a)} {random.choice(a)} {random.choice(a)}
                 {random.choice(a)} {random.choice(a)} {random.choice(a)} {random.choice(a)} {random.choice(a)} {random.choice(a)} {random.choice(a)} {random.choice(a)} {random.choice(a)} {random.choice(a)} {random.choice(a)} {random.choice(a)} {random.choice(a)} {random.choice(a)} {random.choice(a)}
                 {random.choice(a)} {random.choice(a)} {random.choice(a)} {random.choice(a)} {random.choice(a)} {random.choice(a)} {random.choice(a)} {random.choice(a)} {random.choice(a)} {random.choice(a)} {random.choice(a)} {random.choice(a)} {random.choice(a)} {random.choice(a)} {random.choice(a)}

    PROGRESS   : {get_progress_bar(current_percent)}
    """)

def get_duration(file):
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", file]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try: return float(res.stdout)
    except: return 1

def run_ffmpeg_with_progress(cmd, duration):
    global current_progress, ffmpeg_log, current_percent
    cmd += ["-progress", "pipe:1", "-nostats"]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)

    while True:
        line = process.stdout.readline()
        if not line and process.poll() is not None:
            break

        if line:
            if "out_time_ms" in line:
                try:
                    time_ms = int(line.split('=')[1])
                    current_percent = min(int((time_ms / 1000000) / duration * 100), 100)
                    current_progress = f"{current_percent}%"
                except:
                    pass

            if "frame=" in line:
                ffmpeg_log = line.strip()
                draw_ui()

    return process.wait()

def main():
    global total_processed, current_target, current_status, defrag_count, ffmpeg_log, current_progress, current_tf, current_percent

    parser = argparse.ArgumentParser()
    parser.add_argument("-f", default="a.gif")
    parser.add_argument("-i", default="b.png")
    parser.add_argument("-d", type=int, default=120)
    parser.add_argument("-v", default=".")
    args = parser.parse_args()

    abs_gif, abs_png, target_dir = os.path.abspath(args.f), os.path.abspath(args.i), os.path.abspath(args.v)
    if not os.path.exists(target_dir): return
    os.chdir(target_dir)

    videos = [f for f in os.listdir(".") if f.lower().endswith(".mp4") and not f.startswith("temp") and not f.startswith("edit_")]
    if not videos: return

    print(CUR_OFF, end="")
    try:
        for v_name in videos:
            if total_processed >= TOTAL_LIMIT: break
            current_target, current_status = v_name, "DEFRAGMENTING"
            ffmpeg_log = "Splitting video source..."
            current_tf = ""
            current_percent = 0
            draw_ui()

            cmd_seg = ["ffmpeg", "-v", "error", "-i", v_name, "-f", "segment", "-segment_time", str(args.d), "-c", "copy", "-reset_timestamps", "1", "temp_h_%03d.mp4", "-y"]
            if subprocess.run(cmd_seg).returncode == 0: os.remove(v_name)
            else: continue

            temp_files = sorted([f for f in os.listdir(".") if f.startswith("temp_h_")])
            defrag_count = len(temp_files)

            for tf in temp_files:
                if total_processed >= TOTAL_LIMIT: break
                current_status = "INJECTING"
                current_tf = tf

                target_folder = ""
                for i in range(1, MAX_FOLDERS + 1):
                    d_name = f"edit_{i}"
                    os.makedirs(d_name, exist_ok=True)
                    if len(list(Path(d_name).glob("*.mp4"))) < FILES_PER_FOLDER:
                        target_folder = d_name
                        break
                if not target_folder: break

                file_index = len(list(Path(target_folder).glob("*.mp4"))) + 1
                output_path = os.path.join(target_folder, f"edit_{file_index}.mp4")

                duration = get_duration(tf)
                current_percent = 0
                ffmpeg_log = "Initializing Engine..."

                filter_c = (
                    "[0:v]scale=720:480:force_original_aspect_ratio=decrease,pad=720:480:(720-iw)/2:(480-ih)/2,setsar=1[main];"
                    "[1:v]scale=720:40[top];[2:v]scale=720:40[bottom];"
                    "[3:v]scale=100:-1,format=rgba,colorchannelmixer=aa=0.8[logo_f];"
                    "[main][top]overlay=0:0:enable='gte(t,4)':shortest=1[v1];"
                    "[v1][bottom]overlay=0:H-h:enable='gte(t,4)':shortest=1[v2];"
                    "[v2][logo_f]overlay=20:50:enable='gte(t,4)'"
                )

                cmd_enc = [
                    "ffmpeg", "-v", "error", "-i", tf, "-ignore_loop", "0", "-i", abs_gif,
                    "-ignore_loop", "0", "-i", abs_gif, "-i", abs_png,
                    "-filter_complex", filter_c, "-map", "0:a?", "-c:v", "libx264",
                    "-preset", "veryfast", "-crf", "28", "-b:v", "500k", "-c:a", "aac",
                    "-b:a", "64k", "-ac", "1", "-shortest", output_path, "-y"
                ]

                if run_ffmpeg_with_progress(cmd_enc, duration) == 0:
                    total_processed += 1

                os.remove(tf)
                defrag_count -= 1
                current_tf = ""
                draw_ui()

        current_status, current_percent, ffmpeg_log = "FINISHED", 100, "All tasks secured."
        draw_ui()

    except KeyboardInterrupt:
        print("\n[!] MISSION ABORTED")
    finally:
        print(CUR_ON, end="")

if __name__ == "__main__":
    main()
