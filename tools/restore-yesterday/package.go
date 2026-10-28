package main

import (
	"archive/zip"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"io"
	"os"
	"path/filepath"
	"strings"
)

type updateManifest struct {
	Version string `json:"version"`
	URL     string `json:"url"`
	SHA256  string `json:"sha256"`
	Notes   string `json:"notes"`
}

func parseManifest(data []byte) (updateManifest, error) {
	var info updateManifest
	if err := json.Unmarshal(data, &info); err != nil {
		return info, err
	}
	info.Version = strings.TrimSpace(info.Version)
	info.URL = strings.TrimSpace(info.URL)
	info.SHA256 = strings.ToLower(strings.TrimSpace(info.SHA256))
	info.Notes = strings.TrimSpace(info.Notes)
	if info.Version == "" || info.URL == "" {
		return info, errors.New("manifest missing version or url")
	}
	return info, nil
}

func sameSHA256(path, expected string) (bool, error) {
	expected = strings.ToLower(strings.TrimSpace(expected))
	if expected == "" {
		return false, errors.New("missing sha256")
	}
	f, err := os.Open(path)
	if err != nil {
		return false, err
	}
	defer f.Close()
	sum := sha256.New()
	if _, err := io.Copy(sum, f); err != nil {
		return false, err
	}
	return hex.EncodeToString(sum.Sum(nil)) == expected, nil
}

func findPackageRoot(root string) (string, error) {
	var found []string
	err := filepath.WalkDir(root, func(path string, d os.DirEntry, walkErr error) error {
		if walkErr != nil || d.IsDir() {
			return nil
		}
		if strings.EqualFold(d.Name(), "MODUMODU.exe") {
			found = append(found, filepath.Dir(path))
		}
		return nil
	})
	if err != nil {
		return "", err
	}
	if len(found) == 0 {
		return "", errors.New("MODUMODU.exe missing")
	}
	best := found[0]
	for _, dir := range found[1:] {
		if len(dir) < len(best) {
			best = dir
		}
	}
	return best, nil
}

func extractZip(zipPath, dest string) error {
	reader, err := zip.OpenReader(zipPath)
	if err != nil {
		return err
	}
	defer reader.Close()
	destClean := filepath.Clean(dest)
	for _, file := range reader.File {
		name := filepath.Clean(file.Name)
		if name == "." || strings.HasPrefix(name, "..") || strings.Contains(name, ".."+string(os.PathSeparator)) {
			continue
		}
		target := filepath.Join(destClean, name)
		if target != destClean && !strings.HasPrefix(target, destClean+string(os.PathSeparator)) {
			continue
		}
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
		out, err := os.OpenFile(target, os.O_CREATE|os.O_TRUNC|os.O_WRONLY, 0o644)
		if err != nil {
			src.Close()
			return err
		}
		_, copyErr := io.Copy(out, src)
		closeErr := out.Close()
		src.Close()
		if copyErr != nil {
			return copyErr
		}
		if closeErr != nil {
			return closeErr
		}
	}
	return nil
}
