Option Explicit

Dim fso, shell, here, root, staticDir, marker, py, launcher, desktop, link, restored
Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")

here = fso.GetParentFolderName(WScript.ScriptFullName)
root = FindRoot(here)
If root = "" Then
  MsgBox "어제 프로그램을 찾지 못했습니다." & vbCrLf & "C:\smartstore uploader\launcher.py 가 없습니다.", 48, "모두모두AI"
  WScript.Quit 1
End If

staticDir = root & "\app\static"
marker = root & "\data\.yesterday-restored"
If Not fso.FolderExists(root & "\data") Then fso.CreateFolder root & "\data"
restored = RestoreYesterday(staticDir, marker)

py = "C:\Users\user\smartstore-shorts\.venv\Scripts\pythonw.exe"
If Not fso.FileExists(py) Then py = "C:\Users\user\smartstore-shorts\.venv\Scripts\python.exe"
launcher = root & "\launcher.py"
If Not fso.FileExists(py) Or Not fso.FileExists(launcher) Then
  MsgBox "어제 프로그램을 열 파이썬을 찾지 못했습니다.", 48, "모두모두AI"
  WScript.Quit 1
End If

shell.Environment("PROCESS")("UPLOADER_SKIP_UPDATE") = "1"
shell.CurrentDirectory = root
shell.Run """" & py & """ """ & launcher & """", 0, False

On Error Resume Next
desktop = shell.SpecialFolders("Desktop")
Set link = shell.CreateShortcut(desktop & "\모두모두AI 마스터.lnk")
link.TargetPath = "wscript.exe"
link.Arguments = "//nologo """ & WScript.ScriptFullName & """"
link.WorkingDirectory = here
link.WindowStyle = 7
link.Description = "모두모두AI"
link.Save
On Error GoTo 0

MsgBox "어제 오후 9시 프로그램을 엽니다." & vbCrLf & _
  "화면 번호는 v2026.10.22.8 입니다." & vbCrLf & _
  "문의 버튼이 답변 보내기 이면 그 프로그램입니다." & vbCrLf & vbCrLf & _
  "브라우저가 열리면 Ctrl+Shift+R 을 한 번 누르세요.", 64, "모두모두AI"

Function FindRoot(startDir)
  Dim dir, i, parent
  dir = startDir
  For i = 1 To 6
    If fso.FileExists(dir & "\launcher.py") Then
      FindRoot = dir
      Exit Function
    End If
    parent = fso.GetParentFolderName(dir)
    If parent = "" Or parent = dir Then Exit For
    dir = parent
  Next
  If fso.FileExists("C:\smartstore uploader\launcher.py") Then
    FindRoot = "C:\smartstore uploader"
  Else
    FindRoot = ""
  End If
End Function

Function RestoreYesterday(staticDir, markerPath)
  Dim names, i, bak, count
  RestoreYesterday = 0
  If fso.FileExists(markerPath) Then Exit Function
  If Not fso.FolderExists(staticDir) Then Exit Function
  names = Array("app.js", "index.html", "styles.css")
  count = 0
  For i = 0 To UBound(names)
    bak = OldestBackup(staticDir, names(i))
    If bak <> "" Then
      fso.CopyFile bak, staticDir & "\" & names(i), True
      count = count + 1
    End If
  Next
  If count > 0 Then
    Dim ts
    Set ts = fso.CreateTextFile(markerPath, True)
    ts.WriteLine "2026-10-26"
    ts.Close
  End If
  RestoreYesterday = count
End Function

Function OldestBackup(folder, name)
  Dim folderObj, file, prefix, best
  OldestBackup = ""
  best = ""
  prefix = name & ".bak-20261027"
  Set folderObj = fso.GetFolder(folder)
  For Each file In folderObj.Files
    If Left(file.Name, Len(prefix)) = prefix Then
      If best = "" Or file.Name < best Then best = file.Name
    End If
  Next
  If best <> "" Then OldestBackup = folder & "\" & best
End Function
