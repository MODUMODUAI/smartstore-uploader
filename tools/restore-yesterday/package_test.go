package main

import (
	"archive/zip"
	"os"
	"path/filepath"
	"testing"
)

func TestParseManifest(t *testing.T) {
	info, err := parseManifest([]byte(`{"version":"2026.10.27.25","url":"https://example.com/a.zip","sha256":"ABC","notes":" hi "}`))
	if err != nil {
		t.Fatal(err)
	}
	if info.Version != "2026.10.27.25" || info.SHA256 != "abc" || info.Notes != "hi" {
		t.Fatalf("%+v", info)
	}
	if _, err := parseManifest([]byte(`{"version":"1"}`)); err == nil {
		t.Fatal("expected missing url to fail")
	}
}

func TestFindPackageRootAndZipSlip(t *testing.T) {
	dir := t.TempDir()
	zipPath := filepath.Join(dir, "update.zip")
	zw, err := os.Create(zipPath)
	if err != nil {
		t.Fatal(err)
	}
	w := zip.NewWriter(zw)
	exe, err := w.Create("MODUMODU-update/MODUMODU.exe")
	if err != nil {
		t.Fatal(err)
	}
	if _, err := exe.Write([]byte("MZ")); err != nil {
		t.Fatal(err)
	}
	slip, err := w.Create("../escaped.txt")
	if err != nil {
		t.Fatal(err)
	}
	if _, err := slip.Write([]byte("nope")); err != nil {
		t.Fatal(err)
	}
	if err := w.Close(); err != nil {
		t.Fatal(err)
	}
	if err := zw.Close(); err != nil {
		t.Fatal(err)
	}

	dest := filepath.Join(dir, "extracted")
	if err := extractZip(zipPath, dest); err != nil {
		t.Fatal(err)
	}
	root, err := findPackageRoot(dest)
	if err != nil {
		t.Fatal(err)
	}
	if filepath.Base(root) != "MODUMODU-update" {
		t.Fatalf("root %s", root)
	}
	if _, err := os.Stat(filepath.Join(dir, "escaped.txt")); !os.IsNotExist(err) {
		t.Fatal("zip slip file was written")
	}
}
