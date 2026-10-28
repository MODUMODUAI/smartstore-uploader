package main

import (
	"os"
	"path/filepath"
	"testing"
)

func TestCopyProgramSkipsData(t *testing.T) {
	src := t.TempDir()
	if err := os.MkdirAll(filepath.Join(src, "data", "products"), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(src, "data", "products", "secret.txt"), []byte("nope"), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(src, "launcher.py"), []byte("print(1)\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(src, "launcher.log"), []byte("log"), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(filepath.Join(src, "app", "static"), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(src, "app", "static", "app.js"), []byte("function applyEdition(){}\n"), 0o644); err != nil {
		t.Fatal(err)
	}

	dst := filepath.Join(t.TempDir(), "installed")
	if err := CopyProgram(src, dst); err != nil {
		t.Fatal(err)
	}
	if _, err := os.Stat(filepath.Join(dst, "data")); !os.IsNotExist(err) {
		t.Fatalf("data copied: %v", err)
	}
	if _, err := os.Stat(filepath.Join(dst, "launcher.log")); !os.IsNotExist(err) {
		t.Fatalf("log copied: %v", err)
	}
	body, err := os.ReadFile(filepath.Join(dst, "app", "static", "app.js"))
	if err != nil || string(body) == "" {
		t.Fatalf("app missing: %v", err)
	}
	kept := filepath.Join(dst, "data", "products", "keep.txt")
	if err := os.MkdirAll(filepath.Dir(kept), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(kept, []byte("stay"), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := CopyProgram(src, dst); err != nil {
		t.Fatal(err)
	}
	got, err := os.ReadFile(kept)
	if err != nil || string(got) != "stay" {
		t.Fatalf("existing data lost: %v %q", err, got)
	}
}

func TestWriteSellerConfig(t *testing.T) {
	dst := t.TempDir()
	if err := WriteSellerConfig(dst); err != nil {
		t.Fatal(err)
	}
	edition, err := os.ReadFile(filepath.Join(dst, "edition.txt"))
	if err != nil || string(edition) != "test\r\n" {
		t.Fatalf("edition %q %v", edition, err)
	}
	url, err := os.ReadFile(filepath.Join(dst, "update_url.txt"))
	if err != nil || string(url) != UpdateURL+"\r\n" {
		t.Fatalf("url %q %v", url, err)
	}
	if err := os.WriteFile(filepath.Join(dst, "어제오후9시.vbs"), []byte("master"), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := WriteSellerConfig(dst); err != nil {
		t.Fatal(err)
	}
	if _, err := os.Stat(filepath.Join(dst, "어제오후9시.vbs")); !os.IsNotExist(err) {
		t.Fatal("master launcher kept")
	}
	if err := os.WriteFile(filepath.Join(dst, "launcher.py"), []byte("x"), 0o644); err != nil {
		t.Fatal(err)
	}
	if !IsProgramDir(dst) {
		t.Fatal("program dir not recognized")
	}
}

func TestInstallDir(t *testing.T) {
	t.Setenv("LOCALAPPDATA", `C:\Users\buyer\AppData\Local`)
	if got := InstallDir(); got != filepath.Join(`C:\Users\buyer\AppData\Local`, "모두모두AI 셀러용") {
		t.Fatal(got)
	}
}
