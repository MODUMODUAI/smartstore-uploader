package main

import (
	"os"
	"path/filepath"
	"testing"
)

func TestOldestBackup(t *testing.T) {
	dir := t.TempDir()
	for _, name := range []string{
		"app.js.bak-20261027-164205",
		"app.js.bak-20261027-080318",
		"app.js.bak-20261026-999999",
		"index.html",
	} {
		if err := os.WriteFile(filepath.Join(dir, name), []byte("x"), 0o644); err != nil {
			t.Fatal(err)
		}
	}
	got, ok := oldestBackup(dir, "app.js")
	if !ok {
		t.Fatal("expected a backup")
	}
	if filepath.Base(got) != "app.js.bak-20261027-080318" {
		t.Fatalf("got %s", got)
	}
	if _, ok := oldestBackup(dir, "styles.css"); ok {
		t.Fatal("styles.css has no backup")
	}
}
