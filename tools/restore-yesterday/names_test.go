package main

import (
	"os"
	"path/filepath"
	"testing"
	"unicode/utf8"
)

func TestRepairedName(t *testing.T) {
	if utf8.RuneCountInString(cp866High) != 128 {
		t.Fatalf("cp866 table has %d runes", utf8.RuneCountInString(cp866High))
	}
	cases := map[string]string{
		"ьВмьЪйы░йы▓Х.txt":           "사용방법.txt",
		"ьВмьЪйы░йы▓Х-ызИьКдэД░.txt": "사용방법-마스터.txt",
		"ьВмьЪйы░йы▓Х-ы░░эПмьЪй.txt": "사용방법-배포용.txt",
		"ьДдь╣Ш.bat":                 "설치.bat",
		"ьЦ┤ьаЬьШдэЫД9ьЛЬ.vbs":       "어제오후9시.vbs",
	}
	for broken, want := range cases {
		got, ok := repairedName(broken)
		if !ok || got != want {
			t.Fatalf("repairedName(%q) = %q, %v; want %q", broken, got, ok, want)
		}
	}
	if _, ok := repairedName("README.txt"); ok {
		t.Fatal("ascii name was rewritten")
	}
	if _, ok := repairedName("사용방법.txt"); ok {
		t.Fatal("korean name was rewritten")
	}
}

func TestRepairBrokenNames(t *testing.T) {
	dir := t.TempDir()
	broken := filepath.Join(dir, "ьДдь╣Ш.bat")
	if err := os.WriteFile(broken, []byte("install"), 0o644); err != nil {
		t.Fatal(err)
	}
	same := filepath.Join(dir, "ьВмьЪйы░йы▓Х.txt")
	good := filepath.Join(dir, "사용방법.txt")
	if err := os.WriteFile(same, []byte("guide"), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(good, []byte("guide"), 0o644); err != nil {
		t.Fatal(err)
	}
	repairBrokenNames(dir)
	if _, err := os.Stat(filepath.Join(dir, "설치.bat")); err != nil {
		t.Fatal(err)
	}
	if _, err := os.Stat(broken); !os.IsNotExist(err) {
		t.Fatal("broken install name still exists")
	}
	if _, err := os.Stat(same); !os.IsNotExist(err) {
		t.Fatal("duplicate broken guide still exists")
	}
	data, err := os.ReadFile(good)
	if err != nil || string(data) != "guide" {
		t.Fatalf("guide = %q, %v", data, err)
	}
}
