//go:build !windows

package main

import (
	"os"
	"path/filepath"
)

func relink(link, target string) error {
	if err := os.MkdirAll(target, 0o755); err != nil {
		return err
	}
	if err := os.MkdirAll(filepath.Dir(link), 0o755); err != nil {
		return err
	}
	if _, err := os.Lstat(link); err == nil {
		if err := os.Remove(link); err != nil {
			return err
		}
	}
	return os.Symlink(target, link)
}
