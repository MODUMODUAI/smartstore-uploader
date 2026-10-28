//go:build windows

package main

import (
	"fmt"
	"os"
	"os/exec"
	"syscall"
)

func relink(link, target string) error {
	if err := os.MkdirAll(target, 0o755); err != nil {
		return err
	}
	if _, err := os.Lstat(link); err == nil {
		if err := os.Remove(link); err != nil {
			return err
		}
	}
	cmd := exec.Command("cmd", "/c", "mklink", "/J", link, target)
	cmd.SysProcAttr = &syscall.SysProcAttr{HideWindow: true, CreationFlags: 0x08000000}
	out, err := cmd.CombinedOutput()
	if err != nil {
		return fmt.Errorf("%s: %w", out, err)
	}
	return nil
}
