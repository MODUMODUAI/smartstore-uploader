//go:build windows

package main

import (
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"syscall"
	"time"
	"unsafe"
)

func main() {
	exe, err := os.Executable()
	if err != nil {
		alert("설치 파일을 찾지 못했습니다.")
		return
	}
	payload := filepath.Join(filepath.Dir(exe), "프로그램")
	if !IsProgramDir(payload) {
		alert("설치할 프로그램 폴더가 없습니다.\n모두모두AI-셀러용-설치.exe 와 프로그램 폴더를 같은 곳에 두고 다시 실행하세요.")
		return
	}
	dest := InstallDir()
	if err := os.MkdirAll(dest, 0o755); err != nil {
		alert("설치 폴더를 만들지 못했습니다.")
		return
	}
	stopInstalledApp(dest)
	if err := CopyProgram(payload, dest); err != nil {
		alert("파일을 복사하지 못했습니다.\n" + err.Error())
		return
	}
	if err := WriteSellerConfig(dest); err != nil {
		alert("셀러용 설정을 쓰지 못했습니다.")
		return
	}
	target := filepath.Join(dest, "셀러실행.exe")
	if _, err := os.Stat(target); err != nil {
		target = filepath.Join(dest, "MODUMODU.exe")
	}
	if _, err := os.Stat(target); err != nil {
		target = filepath.Join(dest, "launcher.py")
	}
	_ = createDesktopShortcut(target, dest)
	alert("모두모두AI 셀러용을 설치했습니다.\n바탕화면의 모두모두AI 셀러용을 누르면 로그인 창이 열립니다.\n주소는 http://127.0.0.1:8788 입니다.")
	if strings.HasSuffix(strings.ToLower(target), ".exe") {
		cmd := exec.Command(target)
		cmd.Dir = dest
		_ = cmd.Start()
	}
}

func stopInstalledApp(dest string) {
	script := `Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -and $_.ExecutablePath.StartsWith($env:SELLER_DEST, [StringComparison]::OrdinalIgnoreCase) } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }`
	cmd := exec.Command("powershell", "-NoProfile", "-Command", script)
	cmd.Env = append(os.Environ(), "SELLER_DEST="+dest)
	_ = cmd.Run()
	time.Sleep(400 * time.Millisecond)
}

func createDesktopShortcut(target, work string) error {
	out, err := exec.Command("powershell", "-NoProfile", "-Command", "[Environment]::GetFolderPath('Desktop')").Output()
	if err != nil {
		return err
	}
	desktop := strings.TrimSpace(string(out))
	if desktop == "" {
		return err
	}
	link := filepath.Join(desktop, "모두모두AI 셀러용.lnk")
	script := "$s=(New-Object -ComObject WScript.Shell).CreateShortcut($env:SELLER_LINK); " +
		"$s.TargetPath=$env:SELLER_TARGET; $s.WorkingDirectory=$env:SELLER_WORK; " +
		"$s.IconLocation=$env:SELLER_ICON; $s.Description='모두모두AI 셀러용'; $s.Save()"
	cmd := exec.Command("powershell", "-NoProfile", "-Command", script)
	cmd.Env = append(os.Environ(), "SELLER_LINK="+link, "SELLER_TARGET="+target, "SELLER_WORK="+work, "SELLER_ICON="+target+",0")
	return cmd.Run()
}

func alert(text string) {
	user32 := syscall.NewLazyDLL("user32.dll")
	proc := user32.NewProc("MessageBoxW")
	title, _ := syscall.UTF16PtrFromString("모두모두AI 셀러용")
	body, _ := syscall.UTF16PtrFromString(text)
	proc.Call(0, uintptr(unsafe.Pointer(body)), uintptr(unsafe.Pointer(title)), 0x00040000|0x00010000|0x00001000|0x40)
}
