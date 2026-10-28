package main

import (
	"os"
	"path/filepath"
	"unicode/utf8"
)

// cp866High maps bytes 0x80-0xFF. Some UTF-8 names were unpacked with this
// code page, so the folder shows Cyrillic instead of Korean.
const cp866High = "АБВГДЕЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯабвгдежзийклмноп░▒▓│┤╡╢╖╕╣║╗╝╜╛┐└┴┬├─┼╞╟╚╔╩╦╠═╬╧╨╤╥╙╘╒╓╫╪┘┌█▄▌▐▀рстуфхцчшщъыьэюяЁёЄєЇїЎў°∙·√№¤■ "

func repairedName(name string) (string, bool) {
	raw := make([]byte, 0, len(name))
	for _, r := range name {
		if r < 0x80 {
			raw = append(raw, byte(r))
			continue
		}
		idx := indexRune(cp866High, r)
		if idx < 0 {
			return "", false
		}
		raw = append(raw, byte(0x80+idx))
	}
	if !utf8.Valid(raw) {
		return "", false
	}
	fixed := string(raw)
	if fixed == name || !containsHangul(fixed) {
		return "", false
	}
	return fixed, true
}

func indexRune(s string, r rune) int {
	i := 0
	for _, ch := range s {
		if ch == r {
			return i
		}
		i++
	}
	return -1
}

func containsHangul(s string) bool {
	for _, r := range s {
		if r >= 0xAC00 && r <= 0xD7A3 {
			return true
		}
	}
	return false
}

func repairBrokenNames(dir string) {
	entries, err := os.ReadDir(dir)
	if err != nil {
		return
	}
	for _, entry := range entries {
		if entry.IsDir() {
			continue
		}
		fixed, ok := repairedName(entry.Name())
		if !ok || fixed == entry.Name() || fixed == "" || fixed == "." || fixed == ".." {
			continue
		}
		src := filepath.Join(dir, entry.Name())
		dst := filepath.Join(dir, fixed)
		_ = os.Chmod(src, 0o666)
		_ = os.Chmod(dst, 0o666)
		if _, err := os.Stat(dst); err == nil {
			if sameBytes(src, dst) || !largerFile(src, dst) {
				os.Remove(src)
				continue
			}
			os.Remove(dst)
		}
		os.Rename(src, dst)
	}
}

func largerFile(src, dst string) bool {
	srcInfo, err1 := os.Stat(src)
	dstInfo, err2 := os.Stat(dst)
	if err1 != nil || err2 != nil {
		return false
	}
	return srcInfo.Size() > dstInfo.Size()
}

func sameBytes(src, dst string) bool {
	a, err1 := os.ReadFile(src)
	b, err2 := os.ReadFile(dst)
	if err1 != nil || err2 != nil || len(a) != len(b) {
		return false
	}
	for i := range a {
		if a[i] != b[i] {
			return false
		}
	}
	return true
}
