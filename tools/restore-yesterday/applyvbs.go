package main

import "strings"

func vbsQuote(value string) string {
	return `"` + strings.ReplaceAll(value, `"`, `""`) + `"`
}

// renderApplyVBS waits until this process exits, copies the new program over
// the old one, and starts it again. Product data and local settings stay.
func renderApplyVBS(pid int, src, dst, tempRoot string) string {
	robocopy := "robocopy " + cmdQuote(src) + " " + cmdQuote(dst) + " /E /XD data /XF "
	return strings.Join([]string{
		"Option Explicit",
		"Dim shell, fso, rc, i, xf, cmd, desktop, link",
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
		"xf = \"edition.txt update_url.txt license_url.txt launcher.log\"",
		"If fso.FileExists(" + vbsQuote(dst+"\\MODUMODU.exe") + ") Then",
		"  If fso.GetFile(" + vbsQuote(dst+"\\MODUMODU.exe") + ").Size > 8000000 Then xf = xf & \" MODUMODU.exe\"",
		"End If",
		"cmd = \"" + strings.ReplaceAll(robocopy, `"`, `""`) + "\" & xf & \" /R:8 /W:2 /NFL /NDL /NJH /NJS /NP\"",
		"rc = shell.Run(cmd, 0, True)",
		"If rc >= 8 Then",
		"  MsgBox \"업데이트를 적용하지 못했습니다. 모두모두AI를 다시 실행해 주세요.\", 48, \"모두모두AI\"",
		"Else",
		"  desktop = shell.SpecialFolders(\"Desktop\")",
		"  If desktop <> \"\" And fso.FileExists(" + vbsQuote(dst+"\\어제오후9시.vbs") + ") Then",
		"    Set link = shell.CreateShortcut(desktop & \"\\모두모두AI 마스터.lnk\")",
		"    link.TargetPath = shell.ExpandEnvironmentStrings(\"%SystemRoot%\\System32\\wscript.exe\")",
		"    link.Arguments = \"//nologo \"\"\" & " + vbsQuote(dst+"\\어제오후9시.vbs") + " & \"\"\"\"",
		"    link.WorkingDirectory = " + vbsQuote(dst),
		"    If fso.FileExists(" + vbsQuote(dst+"\\MODUMODU.exe") + ") Then link.IconLocation = " + vbsQuote(dst+"\\MODUMODU.exe,0"),
		"    link.WindowStyle = 1",
		"    link.Description = \"모두모두AI\"",
		"    link.Save",
		"  End If",
		"  If fso.FileExists(" + vbsQuote(dst+"\\MODUMODU.exe") + ") Then",
		"    shell.Run " + vbsQuote(cmdQuote(dst+"\\MODUMODU.exe")) + ", 1, False",
		"  End If",
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
