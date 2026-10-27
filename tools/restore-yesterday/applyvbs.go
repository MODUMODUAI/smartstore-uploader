package main

import "strings"

func vbsQuote(value string) string {
	return `"` + strings.ReplaceAll(value, `"`, `""`) + `"`
}

// renderApplyVBS waits until this process exits, copies the new program over
// the old one, and starts it again. Product data and local settings stay.
func renderApplyVBS(pid int, src, dst, tempRoot string) string {
	robocopy := "robocopy " + cmdQuote(src) + " " + cmdQuote(dst) + " /E /XD data /XF edition.txt update_url.txt license_url.txt launcher.log /R:8 /W:2 /NFL /NDL /NJH /NJS /NP"
	return strings.Join([]string{
		"Option Explicit",
		"Dim shell, fso, rc, i",
		"Set shell = CreateObject(\"WScript.Shell\")",
		"Set fso = CreateObject(\"Scripting.FileSystemObject\")",
		"For i = 1 To 40",
		"  If Not ProcessAlive(" + itoa(pid) + ") Then Exit For",
		"  WScript.Sleep 500",
		"Next",
		"WScript.Sleep 1500",
		"On Error Resume Next",
		"If Not fso.FolderExists(" + vbsQuote(dst+"\\data") + ") Then fso.CreateFolder " + vbsQuote(dst+"\\data"),
		"On Error GoTo 0",
		"rc = shell.Run(" + vbsQuote(robocopy) + ", 0, True)",
		"If rc >= 8 Then",
		"  MsgBox \"업데이트를 적용하지 못했습니다. 모두모두AI를 다시 실행해 주세요.\", 48, \"모두모두AI\"",
		"ElseIf fso.FileExists(" + vbsQuote(dst+"\\MODUMODU.exe") + ") Then",
		"  shell.Run " + vbsQuote(cmdQuote(dst+"\\MODUMODU.exe")) + ", 1, False",
		"End If",
		"On Error Resume Next",
		"fso.DeleteFolder " + vbsQuote(tempRoot) + ", True",
		"fso.DeleteFile WScript.ScriptFullName, True",
		"On Error GoTo 0",
		"",
		"Function ProcessAlive(pid)",
		"  Dim wmi, procs",
		"  On Error Resume Next",
		"  Set wmi = GetObject(\"winmgmts:\\\\.\\root\\cimv2\")",
		"  Set procs = wmi.ExecQuery(\"Select ProcessId from Win32_Process Where ProcessId = \" & CStr(pid))",
		"  ProcessAlive = (Err.Number = 0 And Not procs Is Nothing And procs.Count > 0)",
		"  Err.Clear",
		"  On Error GoTo 0",
		"End Function",
		"",
	}, "\r\n")
}

func cmdQuote(path string) string {
	return `"` + strings.ReplaceAll(path, `"`, "") + `"`
}

func itoa(n int) string {
	if n == 0 {
		return "0"
	}
	neg := n < 0
	if neg {
		n = -n
	}
	var buf [16]byte
	i := len(buf)
	for n > 0 {
		i--
		buf[i] = byte('0' + n%10)
		n /= 10
	}
	if neg {
		i--
		buf[i] = '-'
	}
	return string(buf[i:])
}
