package main

import (
	"errors"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestSellerCommandStaysOnSellerPort(t *testing.T) {
	t.Setenv("UPLOADER_PORT", "8787")
	t.Setenv("UPLOADER_SKIP_UPDATE", "0")
	dir := t.TempDir()
	if err := os.WriteFile(filepath.Join(dir, "edition.txt"), []byte("master\r\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(dir, "어제오후9시.vbs"), []byte("master"), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(dir, "idle-update.vbs"), []byte("idle"), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(dir, "MODUMODU.exe"), []byte("PyInstaller-seller"), 0o644); err != nil {
		t.Fatal(err)
	}
	cmd, err := prepareSellerCommand(dir)
	if err != nil {
		t.Fatal(err)
	}
	if cmd.Dir != dir {
		t.Fatal(cmd.Dir)
	}
	joined := strings.Join(cmd.Env, "\n")
	if !strings.Contains(joined, "UPLOADER_PORT=8788") || strings.Contains(joined, "UPLOADER_PORT=8787") {
		t.Fatalf("port env\n%s", joined)
	}
	if !strings.Contains(joined, "UPLOADER_SKIP_UPDATE=1") || strings.Contains(joined, "UPLOADER_SKIP_UPDATE=0") {
		t.Fatalf("skip env\n%s", joined)
	}
	edition, err := os.ReadFile(filepath.Join(dir, "edition.txt"))
	if err != nil || string(edition) != "test\r\n" {
		t.Fatalf("edition %q %v", edition, err)
	}
	if _, err := os.Stat(filepath.Join(dir, "어제오후9시.vbs")); !os.IsNotExist(err) {
		t.Fatal("master launcher left behind")
	}
}

func TestPrepareRejectsMasterUpdater(t *testing.T) {
	dir := t.TempDir()
	if err := os.WriteFile(filepath.Join(dir, "MODUMODU.exe"), []byte("go-updater"), 0o644); err != nil {
		t.Fatal(err)
	}
	_, err := prepareSellerCommand(dir)
	if !errors.Is(err, errMasterLauncher) {
		t.Fatal(err)
	}
	_, err = prepareSellerCommand(t.TempDir())
	if !errors.Is(err, errMissingProgram) {
		t.Fatal(err)
	}
}
