package main

import (
	"io"
	"os"
	"path/filepath"
	"strings"
)

const UpdateURL = "https://github.com/MODUMODUAI/smartstore-uploader/releases/latest/download/latest.json"

func InstallDir() string {
	base := strings.TrimSpace(os.Getenv("LOCALAPPDATA"))
	if base == "" {
		return `C:\모두모두AI 셀러용`
	}
	return filepath.Join(base, "모두모두AI 셀러용")
}

func IsProgramDir(path string) bool {
	for _, name := range []string{"MODUMODU.exe", "launcher.py"} {
		info, err := os.Stat(filepath.Join(path, name))
		if err == nil && !info.IsDir() {
			return true
		}
	}
	info, err := os.Stat(filepath.Join(path, "app", "static", "index.html"))
	return err == nil && !info.IsDir()
}

func skipName(name string) bool {
	switch name {
	case "data", "launcher.log", "__pycache__":
		return true
	default:
		return false
	}
}

// CopyProgram copies the seller program. Product data and the launcher log stay out.
func CopyProgram(src, dst string) error {
	return filepath.WalkDir(src, func(path string, entry os.DirEntry, walkErr error) error {
		if walkErr != nil {
			return walkErr
		}
		rel, err := filepath.Rel(src, path)
		if err != nil {
			return err
		}
		if rel == "." {
			return os.MkdirAll(dst, 0o755)
		}
		for _, part := range strings.Split(rel, string(os.PathSeparator)) {
			if skipName(part) {
				if entry.IsDir() {
					return filepath.SkipDir
				}
				return nil
			}
		}
		target := filepath.Join(dst, rel)
		if entry.IsDir() {
			return os.MkdirAll(target, 0o755)
		}
		return copyFile(path, target)
	})
}

func copyFile(src, dst string) error {
	if err := os.MkdirAll(filepath.Dir(dst), 0o755); err != nil {
		return err
	}
	in, err := os.Open(src)
	if err != nil {
		return err
	}
	defer in.Close()
	out, err := os.OpenFile(dst, os.O_RDWR|os.O_CREATE|os.O_TRUNC, 0o644)
	if err != nil {
		_ = os.Remove(dst + ".old")
		if renErr := os.Rename(dst, dst+".old"); renErr != nil {
			return err
		}
		out, err = os.Create(dst)
		if err != nil {
			return err
		}
	}
	_, copyErr := io.Copy(out, in)
	closeErr := out.Close()
	if copyErr != nil {
		return copyErr
	}
	return closeErr
}

func WriteSellerConfig(dst string) error {
	if err := os.MkdirAll(dst, 0o755); err != nil {
		return err
	}
	if err := os.WriteFile(filepath.Join(dst, "edition.txt"), []byte("test\r\n"), 0o644); err != nil {
		return err
	}
	if err := os.WriteFile(filepath.Join(dst, "update_url.txt"), []byte(UpdateURL+"\r\n"), 0o644); err != nil {
		return err
	}
	return RemoveMasterLaunchers(dst)
}

func RemoveMasterLaunchers(dir string) error {
	for _, name := range []string{"어제오후9시.vbs", "idle-update.vbs"} {
		path := filepath.Join(dir, name)
		if err := os.Remove(path); err != nil && !os.IsNotExist(err) {
			return err
		}
	}
	return nil
}
