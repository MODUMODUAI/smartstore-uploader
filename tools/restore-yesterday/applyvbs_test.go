package main

import "testing"

func TestRenderApplyVBSKeepsData(t *testing.T) {
	body := renderApplyVBS(4242, `C:\smartstore uploader\배포\신규`, `C:\smartstore uploader\배포\MODUMODU-마스터`, `C:\Temp\modumodu-update-1`)
	for _, needle := range []string{
		"ProcessAlive(4242)",
		`robocopy ""C:\smartstore uploader\배포\신규"" ""C:\smartstore uploader\배포\MODUMODU-마스터""`,
		`/XD data`,
		"edition.txt",
		"update_url.txt",
		"license_url.txt",
		"launcher.log",
		"Size > 8000000",
		"모두모두AI 마스터.lnk",
		`wscript.exe`,
		`C:\smartstore uploader\배포\MODUMODU-마스터`,
		`shell.Run """C:\smartstore uploader\배포\MODUMODU-마스터\MODUMODU.exe"""`,
	} {
		if !contains(body, needle) {
			t.Fatalf("missing %s\n%s", needle, body)
		}
	}
}

func contains(body, needle string) bool {
	return len(body) >= len(needle) && (body == needle || len(needle) == 0 || indexOf(body, needle) >= 0)
}

func indexOf(body, needle string) int {
	for i := 0; i+len(needle) <= len(body); i++ {
		if body[i:i+len(needle)] == needle {
			return i
		}
	}
	return -1
}
