package main

import "testing"

func TestIsNewer(t *testing.T) {
	cases := []struct {
		remote, local string
		want          bool
	}{
		{"2026.10.27.25", "2026.10.27.24", true},
		{"2026.10.27.25", "2026.10.27.23", true},
		{"2026.10.27.25", "2026.10.22.8", true},
		{"2026.10.27.25", "2026.10.27.25", false},
		{"2026.10.27.24", "2026.10.27.25", false},
		{"2026.10.27.25", "0", true},
		{"2026.10.27.25", "", true},
		{"1.2.0", "1.2", true},
		{"1.2", "1.2.0", false},
		{"v2026.10.27.25", "2026.10.27.24\r\n", true},
	}
	for _, tc := range cases {
		if got := isNewer(tc.remote, tc.local); got != tc.want {
			t.Fatalf("isNewer(%q, %q) = %v, want %v", tc.remote, tc.local, got, tc.want)
		}
	}
}
