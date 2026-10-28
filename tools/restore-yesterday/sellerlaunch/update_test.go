package main

import (
	"os"
	"path/filepath"
	"testing"
)

func TestCopyUpdateKeepsProgramAndData(t *testing.T) {
	src := t.TempDir()
	dst := t.TempDir()
	if err := os.WriteFile(filepath.Join(src, "version.txt"), []byte("2026.10.28.12\r\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(src, "MODUMODU.exe"), []byte("small-updater"), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(src, "어제오후9시.vbs"), []byte("master"), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(filepath.Join(src, "data"), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(src, "data", "new.txt"), []byte("nope"), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(filepath.Join(dst, "data"), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(dst, "data", "keep.txt"), []byte("stay"), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(dst, "edition.txt"), []byte("test\r\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(dst, "MODUMODU.exe"), []byte("PyInstaller-app"), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := copyUpdateTree(src, dst); err != nil {
		t.Fatal(err)
	}
	got, err := os.ReadFile(filepath.Join(dst, "MODUMODU.exe"))
	if err != nil || string(got) != "PyInstaller-app" {
		t.Fatalf("exe replaced: %q %v", got, err)
	}
	if _, err := os.Stat(filepath.Join(dst, "data", "new.txt")); !os.IsNotExist(err) {
		t.Fatal("update data copied")
	}
	kept, err := os.ReadFile(filepath.Join(dst, "data", "keep.txt"))
	if err != nil || string(kept) != "stay" {
		t.Fatal(err)
	}
	edition, err := os.ReadFile(filepath.Join(dst, "edition.txt"))
	if err != nil || string(edition) != "test\r\n" {
		t.Fatalf("edition %q", edition)
	}
	ver, err := os.ReadFile(filepath.Join(dst, "version.txt"))
	if err != nil || string(ver) == "" {
		t.Fatal(err)
	}
	if _, err := os.Stat(filepath.Join(dst, "어제오후9시.vbs")); !os.IsNotExist(err) {
		t.Fatal("master script copied")
	}
}
