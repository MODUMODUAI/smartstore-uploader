Option Explicit

Dim fso, shell, here, root, lock, rc, py, ts
Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")
If WScript.Arguments.Count < 2 Then WScript.Quit 0
here = WScript.Arguments(0)
root = WScript.Arguments(1)

If Not fso.FolderExists(root & "\data") Then
  On Error Resume Next
  fso.CreateFolder root & "\data"
  On Error GoTo 0
End If

lock = root & "\data\idle-update.lock"
If fso.FileExists(lock) Then
  If DateDiff("n", fso.GetFile(lock).DateLastModified, Now) < 90 Then WScript.Quit 0
End If
Set ts = fso.CreateTextFile(lock, True)
ts.WriteLine "idle"
ts.Close

WScript.Sleep 3600000
Do
  On Error Resume Next
  Set ts = fso.CreateTextFile(lock, True)
  ts.WriteLine "idle"
  ts.Close
  On Error GoTo 0
  If Not fso.FileExists(here & "\check-update.ps1") Then WScript.Quit 0
  rc = shell.Run("powershell.exe -NoProfile -ExecutionPolicy Bypass -File """ & here & "\check-update.ps1"" -Check """ & here & """", 0, True)
  If rc = 2 Then
    rc = shell.Run("powershell.exe -NoProfile -ExecutionPolicy Bypass -File """ & here & "\check-update.ps1"" -Apply """ & here & """", 0, True)
    If rc = 0 Then
      py = root & "\.venv\Scripts\python.exe"
      If Not fso.FileExists(py) Then py = "C:\Users\user\smartstore-shorts\.venv\Scripts\python.exe"
      If fso.FileExists(py) And fso.FileExists(here & "\patch-inquiry-links.py") Then
        shell.Run """" & py & """ """ & here & "\patch-inquiry-links.py"" """ & root & """", 0, True
      End If
    End If
  End If
  WScript.Sleep 900000
Loop
