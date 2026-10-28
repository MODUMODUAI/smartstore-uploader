//go:build windows

package main

import (
	"encoding/binary"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"syscall"
	"time"
	"unicode/utf16"
	"unsafe"
)

const defaultManifestURL = "https://github.com/MODUMODUAI/smartstore-uploader/releases/latest/download/latest.json"

func main() {
	exe, err := os.Executable()
	if err != nil {
		alert("어제 오후 9시 프로그램을 열지 못했습니다.")
		return
	}
	dir := filepath.Dir(exe)
	if !skipRequested() {
		started, updateErr := applyIfNewer(dir)
		if updateErr != nil {
			appendLog(dir, updateErr.Error())
		}
		if started {
			return
		}
	}
	launchYesterday(dir)
}

func skipRequested() bool {
	for _, arg := range os.Args[1:] {
		if arg == "--noupdate" || arg == "/noupdate" {
			return true
		}
	}
	switch strings.ToLower(strings.TrimSpace(os.Getenv("UPLOADER_SKIP_UPDATE"))) {
	case "1", "true", "yes":
		return true
	default:
		return false
	}
}

func applyIfNewer(dir string) (bool, error) {
	local := readVersion(dir)
	info, err := fetchManifest(manifestURL(dir))
	if err != nil {
		return false, err
	}
	if !isNewer(info.Version, local) {
		return false, nil
	}
	notes := info.Notes
	if notes != "" {
		notes += "\n\n"
	}
	question := "모두모두AI 새 버전이 있습니다.\n" + local + " → " + info.Version + "\n\n" + notes + "지금 업데이트할까요?"
	if !askYesNo(question) {
		return false, nil
	}
	tempRoot, err := os.MkdirTemp("", "modumodu-update-")
	if err != nil {
		return false, err
	}
	zipPath := filepath.Join(tempRoot, "update.zip")
	if err := downloadFile(info.URL, zipPath); err != nil {
		os.RemoveAll(tempRoot)
		alert("업데이트를 받지 못했습니다. 지금 프로그램을 그대로 엽니다.")
		return false, err
	}
	ok, err := sameSHA256(zipPath, info.SHA256)
	if err != nil || !ok {
		os.RemoveAll(tempRoot)
		alert("받은 업데이트 파일이 손상되었습니다. 지금 프로그램을 그대로 엽니다.")
		if err == nil {
			err = fmt.Errorf("sha256 mismatch")
		}
		return false, err
	}
	extracted := filepath.Join(tempRoot, "extracted")
	if err := extractZip(zipPath, extracted); err != nil {
		os.RemoveAll(tempRoot)
		alert("업데이트 파일을 풀지 못했습니다. 지금 프로그램을 그대로 엽니다.")
		return false, err
	}
	src, err := findPackageRoot(extracted)
	if err != nil {
		os.RemoveAll(tempRoot)
		alert("업데이트 파일에 프로그램이 없습니다. 지금 프로그램을 그대로 엽니다.")
		return false, err
	}
	script := filepath.Join(os.TempDir(), fmt.Sprintf("modumodu-apply-%d.vbs", os.Getpid()))
	body := renderApplyVBS(os.Getpid(), src, dir, tempRoot)
	if err := os.WriteFile(script, encodeUTF16LE(body), 0o644); err != nil {
		os.RemoveAll(tempRoot)
		return false, err
	}
	cmd := exec.Command("wscript.exe", "//nologo", script)
	cmd.SysProcAttr = &syscall.SysProcAttr{CreationFlags: 0x08000000, HideWindow: true}
	if err := cmd.Start(); err != nil {
		os.RemoveAll(tempRoot)
		alert("업데이트를 적용하지 못했습니다. 지금 프로그램을 그대로 엽니다.")
		return false, err
	}
	appendLog(dir, "update "+local+" -> "+info.Version)
	return true, nil
}

func readVersion(dir string) string {
	data, err := os.ReadFile(filepath.Join(dir, "version.txt"))
	if err != nil {
		return "0"
	}
	text := strings.TrimPrefix(string(data), "\uFEFF")
	text = strings.TrimSpace(text)
	if text == "" {
		return "0"
	}
	return text
}

func manifestURL(dir string) string {
	if text := strings.TrimSpace(os.Getenv("UPLOADER_UPDATE_URL")); text != "" && httpsURL(text) {
		return text
	}
	data, err := os.ReadFile(filepath.Join(dir, "update_url.txt"))
	if err == nil {
		if text := strings.TrimSpace(strings.TrimPrefix(string(data), "\uFEFF")); text != "" && httpsURL(text) {
			return text
		}
	}
	return defaultManifestURL
}

func httpsURL(raw string) bool {
	parsed, err := url.Parse(raw)
	return err == nil && parsed.Scheme == "https" && parsed.Host != ""
}

func fetchManifest(rawURL string) (updateManifest, error) {
	var info updateManifest
	body, err := httpGet(rawURL, 15*time.Second)
	if err != nil {
		return info, err
	}
	return parseManifest(body)
}

func downloadFile(rawURL, dest string) error {
	if !httpsURL(rawURL) {
		return fmt.Errorf("refusing non-https update url")
	}
	req, err := http.NewRequest(http.MethodGet, rawURL, nil)
	if err != nil {
		return err
	}
	req.Header.Set("User-Agent", "MODUMODU-Updater/1.0")
	client := &http.Client{Timeout: 3 * time.Minute}
	resp, err := client.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return fmt.Errorf("download status %d", resp.StatusCode)
	}
	out, err := os.Create(dest)
	if err != nil {
		return err
	}
	defer out.Close()
	_, err = io.Copy(out, resp.Body)
	return err
}

func httpGet(rawURL string, timeout time.Duration) ([]byte, error) {
	if !httpsURL(rawURL) {
		return nil, fmt.Errorf("refusing non-https url")
	}
	req, err := http.NewRequest(http.MethodGet, rawURL, nil)
	if err != nil {
		return nil, err
	}
	req.Header.Set("User-Agent", "MODUMODU-Updater/1.0")
	client := &http.Client{Timeout: timeout}
	resp, err := client.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return nil, fmt.Errorf("status %d", resp.StatusCode)
	}
	return io.ReadAll(io.LimitReader(resp.Body, 1<<20))
}

func launchYesterday(dir string) {
	repairBrokenNames(dir)
	deploy := filepath.Join(dir, "배포")
	if entries, err := os.ReadDir(deploy); err == nil {
		for _, entry := range entries {
			if entry.IsDir() {
				repairBrokenNames(filepath.Join(deploy, entry.Name()))
			}
		}
	}
	script := filepath.Join(dir, "어제오후9시.vbs")
	if _, err := os.Stat(script); err != nil {
		alert("어제 프로그램을 열 파일이 없습니다.")
		return
	}
	cmd := exec.Command("wscript.exe", "//nologo", script, "/ready")
	cmd.SysProcAttr = &syscall.SysProcAttr{
		CreationFlags: 0x08000000,
		HideWindow:    true,
	}
	if err := cmd.Start(); err != nil {
		alert("어제 오후 9시 프로그램을 열지 못했습니다.")
	}
}

func appendLog(dir, text string) {
	path := filepath.Join(dir, "data", "launcher.log")
	_ = os.MkdirAll(filepath.Dir(path), 0o755)
	f, err := os.OpenFile(path, os.O_CREATE|os.O_APPEND|os.O_WRONLY, 0o644)
	if err != nil {
		return
	}
	defer f.Close()
	fmt.Fprintf(f, "%s %s\n", time.Now().Format(time.RFC3339), text)
}

func encodeUTF16LE(text string) []byte {
	units := utf16.Encode([]rune(text))
	buf := make([]byte, 2+len(units)*2)
	buf[0] = 0xFF
	buf[1] = 0xFE
	for i, unit := range units {
		binary.LittleEndian.PutUint16(buf[2+i*2:], unit)
	}
	return buf
}

func alert(text string) {
	messageBox(text, 0x00040000|0x00010000|0x00001000|0x40)
}

func askYesNo(text string) bool {
	// YESNO | ICONQUESTION | TOPMOST | SETFOREGROUND | SYSTEMMODAL
	return messageBox(text, 0x00000004|0x00000020|0x00040000|0x00010000|0x00001000) == 6
}

func messageBox(text string, flags uintptr) uintptr {
	user32 := syscall.NewLazyDLL("user32.dll")
	proc := user32.NewProc("MessageBoxW")
	title, _ := syscall.UTF16PtrFromString("모두모두AI")
	body, _ := syscall.UTF16PtrFromString(text)
	r, _, _ := proc.Call(0, uintptr(unsafe.Pointer(body)), uintptr(unsafe.Pointer(title)), flags)
	return r
}
