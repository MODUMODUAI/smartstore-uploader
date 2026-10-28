package main

import (
	"bytes"
	"io"
	"os"
	"path/filepath"
	"strings"
)

func skipUpdateRel(rel string) bool {
	rel = strings.TrimPrefix(rel, string(os.PathSeparator))
	if rel == "." || rel == "" {
		return false
	}
	base := rel
	if i := strings.IndexAny(rel, `\/`); i >= 0 {
		base = rel[:i]
	}
	switch base {
	case "data", "edition.txt", "update_url.txt", "license_url.txt", "launcher.log":
		return true
	default:
		return false
	}
}

func keepProgramExe(existingPath string) bool {
	info, err := os.Stat(existingPath)
	if err != nil || info.IsDir() {
		return false
	}
	file, err := os.Open(existingPath)
	if err != nil {
		return false
	}
	defer file.Close()
	buf := make([]byte, 1<<20)
	var tail []byte
	for {
		n, readErr := file.Read(buf)
		if n > 0 {
			chunk := buf[:n]
			if bytes.Contains(chunk, []byte("PyInstaller")) || bytes.Contains(chunk, []byte("python313.dll")) {
				return true
			}
			if bytes.Contains(append(tail, chunk...), []byte("PyInstaller")) || bytes.Contains(append(tail, chunk...), []byte("python313.dll")) {
				return true
			}
			if n > 32 {
				tail = append([]byte{}, chunk[n-32:]...)
			} else {
				tail = append([]byte{}, chunk...)
			}
		}
		if readErr == io.EOF {
			break
		}
		if readErr != nil {
			return false
		}
	}
	return false
}

func copyUpdateTree(src, dst string) error {
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
		if skipUpdateRel(rel) {
			if entry.IsDir() {
				return filepath.SkipDir
			}
			return nil
		}
		target := filepath.Join(dst, rel)
		if entry.IsDir() {
			return os.MkdirAll(target, 0o755)
		}
		if strings.EqualFold(filepath.Base(target), "MODUMODU.exe") && keepProgramExe(target) {
			return nil
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
	out, err := os.Create(dst)
	if err != nil {
		return err
	}
	_, copyErr := io.Copy(out, in)
	closeErr := out.Close()
	if copyErr != nil {
		return copyErr
	}
	return closeErr
}
