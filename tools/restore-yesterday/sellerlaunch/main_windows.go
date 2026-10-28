//go:build windows

package main

import (
	"archive/zip"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"io"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"syscall"
	"time"
	"unsafe"
)

const defaultUpdateURL = "https://github.com/MODUMODUAI/smartstore-uploader/releases/latest/download/latest.json"

type updateManifest struct {
	Version string `json:"version"`
	URL     string `json:"url"`
	SHA256  string `json:"sha256"`
	Notes   string `json:"notes"`
}

func init() {
	stopProgram = stopModumodu
	startProgram = startModumodu
}

func main() {
	exe, err := os.Executable()
	if err != nil {
		alert("셀러용을 열지 못했습니다.")
		return
	}
	dir := filepath.Dir(exe)
	_ = tryUpdate(dir)
	refreshSellerShortcut(exe, dir)
	if err := startAccountServer(dir); err != nil {
		alert("로그인 창을 열지 못했습니다.")
		return
	}
	_ = parkData(dir)
	target := filepath.Join(dir, "MODUMODU.exe")
	if _, err := os.Stat(target); err != nil {
		alert("셀러용 프로그램을 찾지 못했습니다.")
		return
	}
	cmd := exec.Command(target)
	cmd.Dir = dir
	_ = cmd.Start()
}

func stopModumodu(dir string) error {
	target := filepath.Join(dir, "MODUMODU.exe")
	script := `Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -and ($_.ExecutablePath -ieq $env:SELLER_KILL) } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }`
	cmd := exec.Command("powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", script)
	cmd.Env = append(os.Environ(), "SELLER_KILL="+target)
	_ = cmd.Run()
	time.Sleep(300 * time.Millisecond)
	return nil
}

func startModumodu(dir string) error {
	target := filepath.Join(dir, "MODUMODU.exe")
	cmd := exec.Command(target)
	cmd.Dir = dir
	return cmd.Start()
}

func tryUpdate(dir string) error {
	local := readText(filepath.Join(dir, "version.txt"))
	if local == "" {
		local = "0"
	}
	info, err := fetchManifest(updateURL(dir))
	if err != nil || !newer(info.Version, local) {
		return err
	}
	notes := strings.TrimSpace(info.Notes)
	question := "모두모두AI 셀러용 새 버전이 있습니다.\n" + local + " → " + info.Version
	if notes != "" {
		question += "\n\n" + notes
	}
	question += "\n\n지금 업데이트할까요?"
	if !askYesNo(question) {
		return nil
	}
	temp, err := os.MkdirTemp("", "seller-update-")
	if err != nil {
		return err
	}
	defer os.RemoveAll(temp)
	zipPath := filepath.Join(temp, "update.zip")
	if err := download(info.URL, zipPath); err != nil {
		alert("업데이트를 받지 못했습니다. 지금 프로그램을 엽니다.")
		return err
	}
	if !sameSHA(zipPath, info.SHA256) {
		alert("받은 업데이트 파일이 손상되었습니다. 지금 프로그램을 엽니다.")
		return err
	}
	extracted := filepath.Join(temp, "extracted")
	if err := unzip(zipPath, extracted); err != nil {
		alert("업데이트 파일을 풀지 못했습니다. 지금 프로그램을 엽니다.")
		return err
	}
	src := findProgram(extracted)
	if src == "" {
		src = extracted
	}
	if err := copyUpdateTree(src, dir); err != nil {
		alert("업데이트를 적용하지 못했습니다. 지금 프로그램을 엽니다.")
		return err
	}
	return nil
}

func refreshSellerShortcut(exe, dir string) {
	script := "$desk=[Environment]::GetFolderPath('Desktop'); " +
		"$s=(New-Object -ComObject WScript.Shell).CreateShortcut((Join-Path $desk '모두모두AI 셀러용.lnk')); " +
		"$s.TargetPath=$env:SELLER_TARGET; $s.WorkingDirectory=$env:SELLER_WORK; " +
		"$s.IconLocation=$env:SELLER_ICON; $s.Description='모두모두AI 셀러용'; $s.Save()"
	cmd := exec.Command("powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", script)
	cmd.Env = append(os.Environ(), "SELLER_TARGET="+exe, "SELLER_WORK="+dir, "SELLER_ICON="+exe+",0")
	_ = cmd.Run()
}

func updateURL(dir string) string {
	text := readText(filepath.Join(dir, "update_url.txt"))
	if strings.HasPrefix(text, "https://") {
		return text
	}
	return defaultUpdateURL
}

func readText(path string) string {
	data, err := os.ReadFile(path)
	if err != nil {
		return ""
	}
	return strings.TrimSpace(strings.TrimPrefix(string(data), "\uFEFF"))
}

func fetchManifest(rawURL string) (updateManifest, error) {
	var info updateManifest
	body, err := httpGet(rawURL)
	if err != nil {
		return info, err
	}
	err = json.Unmarshal(body, &info)
	return info, err
}

func httpGet(rawURL string) ([]byte, error) {
	req, err := http.NewRequest(http.MethodGet, rawURL, nil)
	if err != nil {
		return nil, err
	}
	req.Header.Set("User-Agent", "MODUMODU-Seller/1.0")
	client := &http.Client{Timeout: 30 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	return io.ReadAll(io.LimitReader(resp.Body, 1<<20))
}

func download(rawURL, dest string) error {
	req, err := http.NewRequest(http.MethodGet, rawURL, nil)
	if err != nil {
		return err
	}
	req.Header.Set("User-Agent", "MODUMODU-Seller/1.0")
	client := &http.Client{Timeout: 5 * time.Minute}
	resp, err := client.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	out, err := os.Create(dest)
	if err != nil {
		return err
	}
	_, copyErr := io.Copy(out, resp.Body)
	closeErr := out.Close()
	if copyErr != nil {
		return copyErr
	}
	return closeErr
}

func sameSHA(path, expected string) bool {
	expected = strings.ToLower(strings.TrimSpace(expected))
	file, err := os.Open(path)
	if err != nil {
		return false
	}
	defer file.Close()
	sum := sha256.New()
	if _, err := io.Copy(sum, file); err != nil {
		return false
	}
	return hex.EncodeToString(sum.Sum(nil)) == expected
}

func unzip(zipPath, dest string) error {
	reader, err := zip.OpenReader(zipPath)
	if err != nil {
		return err
	}
	defer reader.Close()
	for _, file := range reader.File {
		name := filepath.Clean(file.Name)
		if name == "." || strings.Contains(name, "..") {
			continue
		}
		target := filepath.Join(dest, name)
		if file.FileInfo().IsDir() {
			if err := os.MkdirAll(target, 0o755); err != nil {
				return err
			}
			continue
		}
		if err := os.MkdirAll(filepath.Dir(target), 0o755); err != nil {
			return err
		}
		src, err := file.Open()
		if err != nil {
			return err
		}
		out, err := os.Create(target)
		if err != nil {
			src.Close()
			return err
		}
		_, copyErr := io.Copy(out, src)
		out.Close()
		src.Close()
		if copyErr != nil {
			return copyErr
		}
	}
	return nil
}

func findProgram(root string) string {
	var found string
	filepath.WalkDir(root, func(path string, entry os.DirEntry, err error) error {
		if err != nil || entry.IsDir() {
			return nil
		}
		if strings.EqualFold(entry.Name(), "MODUMODU.exe") && (found == "" || len(path) < len(found)) {
			found = filepath.Dir(path)
		}
		return nil
	})
	return found
}

func newer(remote, local string) bool {
	rp, lp := parts(remote), parts(local)
	n := len(rp)
	if len(lp) < n {
		n = len(lp)
	}
	for i := 0; i < n; i++ {
		if rp[i] != lp[i] {
			return rp[i] > lp[i]
		}
	}
	return len(rp) > len(lp)
}

func parts(text string) []int {
	text = strings.NewReplacer("-", ".", "_", ".").Replace(strings.TrimSpace(text))
	var out []int
	for _, chunk := range strings.Split(text, ".") {
		n := 0
		digits := false
		for _, r := range chunk {
			if r < '0' || r > '9' {
				continue
			}
			digits = true
			n = n*10 + int(r-'0')
		}
		if digits {
			out = append(out, n)
		}
	}
	return out
}

func alert(text string) {
	messageBox(text, 0x00040000|0x00010000|0x00001000|0x40)
}

func askYesNo(text string) bool {
	return messageBox(text, 0x00000004|0x00000020|0x00040000|0x00010000|0x00001000) == 6
}

func messageBox(text string, flags uintptr) uintptr {
	user32 := syscall.NewLazyDLL("user32.dll")
	proc := user32.NewProc("MessageBoxW")
	title, _ := syscall.UTF16PtrFromString("모두모두AI 셀러용")
	body, _ := syscall.UTF16PtrFromString(text)
	r, _, _ := proc.Call(0, uintptr(unsafe.Pointer(body)), uintptr(unsafe.Pointer(title)), flags)
	return r
}
