package main

import (
	"bytes"
	"flag"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"
)

const (
	MaxFolders     = 12
	FilesPerFolder = 5
	TotalLimit     = MaxFolders * FilesPerFolder

	ColorGreen  = "\033[38;5;82m"
	ColorCyan   = "\033[38;5;51m"
	ColorRed    = "\033[38;5;196m"
	ColorYellow = "\033[38;5;226m"
	ColorWhite  = "\033[38;5;255m"
	ColorReset  = "\033[0m"
	ColorBlue   = "\033[38;5;27m"
	ColorPurple = "\033[38;5;129m"
)

var (
	gifFile         string
	pngFile         string
	videoDir        string
	segmentDuration int
	minSizeMB       float64
	totalProcessed  int
)

func hikariLog(label, message, color string) {
	timestamp := time.Now().Format("15:04:05.000")
	fmt.Printf("%s[%s] %s%-12s %s| %s%s\n", ColorWhite, timestamp, ColorPurple, label, ColorWhite, color, message)
}

func countTotalFinished() int {
	total := 0
	for i := 1; i <= MaxFolders; i++ {
		path := fmt.Sprintf("edit_%d", i)
		files, _ := os.ReadDir(path)
		for _, file := range files {
			if strings.HasSuffix(file.Name(), ".mp4") {
				total++
			}
		}
	}
	return total
}

func getFileSizeMB(filename string) float64 {
	info, err := os.Stat(filename)
	if err != nil {
		return 0.0
	}
	return float64(info.Size()) / (1024 * 1024)
}

func main() {
	flag.StringVar(&gifFile, "f", "a.gif", "GIF asset")
	flag.StringVar(&pngFile, "i", "b.png", "PNG asset")
	flag.IntVar(&segmentDuration, "d", 120, "Duration per segment (seconds)")
	flag.Float64Var(&minSizeMB, "m", 0.0, "Minimum file size in MB")
	flag.StringVar(&videoDir, "v", ".", "Target video directory")
	flag.Parse()

	// LOCK ABSOLUTE PATHS
	absGif, errG := filepath.Abs(gifFile)
	absPng, errP := filepath.Abs(pngFile)
	if errG == nil { gifFile = absGif }
	if errP == nil { pngFile = absPng }

	fmt.Printf("%s[SYSTEM] HIKARI v5.0 ENGINE :: DELAY 4s ENABLED%s\n", ColorBlue, ColorReset)

	if err := os.Chdir(videoDir); err != nil {
		hikariLog("CRITICAL", "FAILED TO ENTER DIRECTORY: "+err.Error(), ColorRed)
		return
	}

	files, _ := os.ReadDir(".")
	var videos []string
	for _, f := range files {
		if strings.HasSuffix(f.Name(), ".mp4") && !strings.HasPrefix(f.Name(), "temp") {
			videos = append(videos, f.Name())
		}
	}

	for _, vName := range videos {
		if countTotalFinished() >= TotalLimit { break }

		hikariLog("TARGET", "Processing: "+vName, ColorWhite)

		// --- PHASE 1: SEGMENTING ---
		cmdSegment := exec.Command("ffmpeg", "-v", "error", "-i", vName, "-f", "segment", "-segment_time",
			fmt.Sprintf("%d", segmentDuration), "-c", "copy", "-reset_timestamps", "1", "temp_h_%03d.mp4", "-y")
		
		var segErr bytes.Buffer
		cmdSegment.Stderr = &segErr
		if err := cmdSegment.Run(); err != nil {
			hikariLog("SEG_ERR", "Info: "+segErr.String(), ColorRed)
			continue
		}
		os.Remove(vName)

		tempFiles, _ := os.ReadDir(".")
		for _, tf := range tempFiles {
			if strings.HasPrefix(tf.Name(), "temp_h_") {

				folderTujuan := ""
				nextFileNumber := 1

				for i := 1; i <= MaxFolders; i++ {
					dName := fmt.Sprintf("edit_%d", i)
					os.Mkdir(dName, 0777)
					existingFiles, _ := os.ReadDir(dName)
					usedNumbers := make(map[int]bool)
					count := 0
					for _, ef := range existingFiles {
						if strings.HasSuffix(ef.Name(), ".mp4") {
							count++
							var n int
							fmt.Sscanf(ef.Name(), "edit_%d.mp4", &n)
							usedNumbers[n] = true
						}
					}
					if count < FilesPerFolder {
						folderTujuan = dName
						for n := 1; n <= FilesPerFolder; n++ {
							if !usedNumbers[n] {
								nextFileNumber = n
								break
							}
						}
						break
					}
				}

				if folderTujuan == "" { break }

				finalName := filepath.Join(folderTujuan, fmt.Sprintf("edit_%d.mp4", nextFileNumber))

				// --- PHASE 2: RENDERING (DELAY 4s & OPTIMIZED QUALITY) ---
				hikariLog("INJECT", "Encoding: "+finalName, ColorCyan)

				// enable='gte(t,4)' memindahkan kemunculan aset ke detik ke-4
				filter := "[0:v]scale=720:480:force_original_aspect_ratio=decrease,pad=720:480:(720-iw)/2:(480-ih)/2,setsar=1[main];" +
					"[1:v]scale=720:40[top];[2:v]scale=720:40[bottom];" +
					"[3:v]scale=100:-1,format=rgba,colorchannelmixer=aa=0.8[logo_f];" +
					"[main][top]overlay=0:0:enable='gte(t,4)':shortest=1[v1];" +
					"[v1][bottom]overlay=0:H-h:enable='gte(t,4)':shortest=1[v2];" +
					"[v2][logo_f]overlay=20:50:enable='gte(t,4)'"

				cmdRender := exec.Command("ffmpeg", "-v", "error", "-i", tf.Name(),
					"-ignore_loop", "0", "-i", gifFile,
					"-ignore_loop", "0", "-i", gifFile,
					"-i", pngFile,
					"-filter_complex", filter,
					"-map", "0:a?",
					"-c:v", "libx264",
					"-preset", "faster",
					"-crf", "22",        // Kualitas lebih tajam (semakin kecil angka, semakin bagus)
					"-maxrate", "1.2M",  // Menjaga ukuran tetap di bawah 15MB untuk durasi 2 menit
					"-bufsize", "2.4M",
					"-c:a", "aac",
					"-b:a", "128k",
					"-shortest", finalName, "-y")

				var renderErr bytes.Buffer
				cmdRender.Stderr = &renderErr
				if err := cmdRender.Run(); err != nil {
					hikariLog("FAIL", "Error: "+renderErr.String(), ColorRed)
				} else {
					size := getFileSizeMB(finalName)
					hikariLog("SUCCESS", fmt.Sprint("Captured: ", size, "MB"), ColorGreen)
					totalProcessed++
				}
				os.Remove(tf.Name())
			}
		}
	}
	hikariLog("EXIT", "Neutralizing traces...", ColorPurple)
}
