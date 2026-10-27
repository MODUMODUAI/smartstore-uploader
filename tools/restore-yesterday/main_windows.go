//go:build windows

package main

import (
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"syscall"
	"unsafe"
)

func main() {
	root, err := findRoot()
	if err != nil {
		alert("어제 프로그램을 찾지 못했습니다.\nC:\\smartstore uploader\\launcher.py 가 없습니다.")
		return
	}
	staticDir := filepath.Join(root, "app", "static")
	logPath := filepath.Join(root, "data", "restore-yesterday.log")
	_ = os.MkdirAll(filepath.Join(root, "data"), 0o755)
	logf := openLog(logPath)
	defer logf.Close()

	fmt.Fprintf(logf, "root %s\n", root)
	restored := restoreYesterday(staticDir, filepath.Join(root, "data", ".yesterday-restored"), logf)
	fmt.Fprintf(logf, "restored %d\n", restored)

	py, err := findPython()
	if err != nil {
		fmt.Fprintf(logf, "python %v\n", err)
		alert("어제 프로그램을 열 파이썬을 찾지 못했습니다.")
		return
	}
	launcher := filepath.Join(root, "launcher.py")
	cmd := exec.Command(py, launcher)
	cmd.Dir = root
	cmd.Env = append(os.Environ(), "UPLOADER_SKIP_UPDATE=1")
	cmd.SysProcAttr = &syscall.SysProcAttr{
		CreationFlags: 0x08000000, // CREATE_NO_WINDOW
		HideWindow:    true,
	}
	if err := cmd.Start(); err != nil {
		fmt.Fprintf(logf, "start %v\n", err)
		alert("어제 프로그램을 켜지 못했습니다.")
		return
	}
	fmt.Fprintf(logf, "started %s pid %d\n", py, cmd.Process.Pid)
	alert("어제 오후 9시 프로그램을 엽니다.\n화면 번호는 v2026.10.22.8 입니다.\n문의 버튼이 답변 보내기 이면 그 프로그램입니다.\n\n브라우저가 열리면 Ctrl+Shift+R 을 한 번 누르세요.")
}

func findRoot() (string, error) {
	if exe, err := os.Executable(); err == nil {
		dir := filepath.Dir(exe)
		for i := 0; i < 6; i++ {
			if isLauncher(dir) {
				return dir, nil
			}
			parent := filepath.Dir(dir)
			if parent == dir {
				break
			}
			dir = parent
		}
	}
	fixed := `C:\smartstore uploader`
	if isLauncher(fixed) {
		return fixed, nil
	}
	return "", fmt.Errorf("launcher.py not found")
}

func isLauncher(dir string) bool {
	info, err := os.Stat(filepath.Join(dir, "launcher.py"))
	return err == nil && !info.IsDir()
}

func findPython() (string, error) {
	candidates := []string{
		`C:\Users\user\smartstore-shorts\.venv\Scripts\pythonw.exe`,
		`C:\Users\user\smartstore-shorts\.venv\Scripts\python.exe`,
	}
	for _, path := range candidates {
		info, err := os.Stat(path)
		if err == nil && !info.IsDir() {
			return path, nil
		}
	}
	return "", fmt.Errorf("venv python missing")
}

func restoreYesterday(staticDir, marker string, logf io.Writer) int {
	if _, err := os.Stat(marker); err == nil {
		fmt.Fprintf(logf, "already restored\n")
		return 0
	}
	count := 0
	for _, name := range []string{"app.js", "index.html", "styles.css"} {
		bak, ok := oldestBackup(staticDir, name)
		if !ok {
			fmt.Fprintf(logf, "no backup %s\n", name)
			continue
		}
		data, err := os.ReadFile(bak)
		if err != nil || len(data) == 0 {
			fmt.Fprintf(logf, "backup empty %s %v\n", bak, err)
			continue
		}
		dest := filepath.Join(staticDir, name)
		if err := os.WriteFile(dest, data, 0o644); err != nil {
			fmt.Fprintf(logf, "write %s %v\n", dest, err)
			continue
		}
		fmt.Fprintf(logf, "restored %s from %s (%d)\n", name, filepath.Base(bak), len(data))
		count++
	}
	if count > 0 {
		_ = os.WriteFile(marker, []byte("2026-10-26\n"), 0o644)
	}
	return count
}

func openLog(path string) io.WriteCloser {
	f, err := os.OpenFile(path, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0o644)
	if err != nil {
		return nopCloser{io.Discard}
	}
	return f
}

type nopCloser struct{ io.Writer }

func (nopCloser) Close() error { return nil }

func alert(text string) {
	user32 := syscall.NewLazyDLL("user32.dll")
	proc := user32.NewProc("MessageBoxW")
	title, _ := syscall.UTF16PtrFromString("모두모두AI")
	body, _ := syscall.UTF16PtrFromString(text)
	const mbTopmost = 0x00040000
	const mbSetForeground = 0x00010000
	const mbIcon = 0x40
	proc.Call(0, uintptr(unsafe.Pointer(body)), uintptr(unsafe.Pointer(title)), mbTopmost|mbSetForeground|mbIcon)
}
