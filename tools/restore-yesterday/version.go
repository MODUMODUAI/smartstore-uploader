package main

import (
	"strings"
	"unicode"
)

// versionParts matches the installed updater: separators are . - _, and only
// digits inside each piece count. Comparison is Python tuple order.
func versionParts(text string) []int {
	text = strings.TrimPrefix(strings.TrimSpace(text), "\uFEFF")
	text = strings.ReplaceAll(text, "-", ".")
	text = strings.ReplaceAll(text, "_", ".")
	var parts []int
	for _, chunk := range strings.Split(text, ".") {
		digits := make([]rune, 0, len(chunk))
		for _, r := range chunk {
			if unicode.IsDigit(r) {
				digits = append(digits, r)
			}
		}
		if len(digits) == 0 {
			continue
		}
		n := 0
		for _, r := range digits {
			n = n*10 + int(r-'0')
		}
		parts = append(parts, n)
	}
	return parts
}

func isNewer(remote, local string) bool {
	rp := versionParts(remote)
	lp := versionParts(local)
	n := len(rp)
	if len(lp) < n {
		n = len(lp)
	}
	for i := 0; i < n; i++ {
		if rp[i] != lp[i] {
			return rp[i] > lp[i]
		}
	}
	return len(rp) > len(lp)
}
