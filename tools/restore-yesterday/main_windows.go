//go:build windows

package main

import (
	"os"
	"os/exec"
	"path/filepath"
	"syscall"
	"unsafe"
)

func main() {
	exe, err := os.Executable()
	if err != nil {
		alert("어제 오후 9시 프로그램을 열지 못했습니다.")
		return
	}
	script := filepath.Join(filepath.Dir(exe), "어제오후9시.vbs")
	if _, err := os.Stat(script); err != nil {
		alert("어제오후9시.vbs 파일이 없습니다.\n모두모두AI 폴더에서 그 파일을 더블클릭하세요.")
		return
	}
	cmd := exec.Command("wscript.exe", "//nologo", script)
	cmd.SysProcAttr = &syscall.SysProcAttr{
		CreationFlags: 0x08000000,
		HideWindow:    true,
	}
	if err := cmd.Start(); err != nil {
		alert("어제 오후 9시 프로그램을 열지 못했습니다.")
	}
}

func alert(text string) {
	user32 := syscall.NewLazyDLL("user32.dll")
	proc := user32.NewProc("MessageBoxW")
	title, _ := syscall.UTF16PtrFromString("모두모두AI")
	body, _ := syscall.UTF16PtrFromString(text)
	const flags = 0x00040000 | 0x00010000 | 0x40
	proc.Call(0, uintptr(unsafe.Pointer(body)), uintptr(unsafe.Pointer(title)), flags)
}
