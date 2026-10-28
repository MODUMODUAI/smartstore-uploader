Option Explicit

Dim fso, shell, here, root, staticDir, marker, py, launcher
Dim dataDir, bestData, bestCount, liveCount, copied, patched
Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")

here = fso.GetParentFolderName(WScript.ScriptFullName)
RepairBrokenNames here
RepairMasterShortcut
If Not ReadyArg() Then
  If OfferUpdate(here) Then WScript.Quit 0
End If
root = FindRoot(here)
If root = "" Then
  MsgBox "어제 프로그램을 찾지 못했습니다." & vbCrLf & "C:\smartstore uploader\launcher.py 가 없습니다.", 48, "모두모두AI"
  WScript.Quit 1
End If

If Not fso.FolderExists(root & "\data") Then fso.CreateFolder root & "\data"
LogLine "root " & root

staticDir = root & "\app\static"
marker = root & "\data\.yesterday-restored"
RestoreYesterday staticDir, marker

dataDir = root & "\data"
liveCount = ProductCount(dataDir)
bestData = dataDir
bestCount = liveCount
ConsiderKnownData root
If bestData <> dataDir And bestCount > liveCount Then
  LogLine "copy data " & bestData & " count " & CStr(bestCount)
  shell.Run "robocopy """ & bestData & """ """ & dataDir & """ /E /R:2 /W:1 /NFL /NDL /NJH /NJS /NP", 0, True
  copied = True
  liveCount = ProductCount(dataDir)
Else
  copied = False
End If
LogLine "products " & CStr(liveCount)

py = ChoosePython(root)
launcher = root & "\launcher.py"
If py = "" Or Not fso.FileExists(launcher) Then
  MsgBox "어제 프로그램을 열 파이썬을 찾지 못했습니다.", 48, "모두모두AI"
  WScript.Quit 1
End If
LogLine "python " & py
patched = 0
If fso.FileExists(here & "\patch-inquiry-links.py") Then
  patched = shell.Run("""" & py & """ """ & here & "\patch-inquiry-links.py"" """ & root & """", 0, True)
  LogLine "inquiry links " & CStr(patched)
End If

shell.Environment("PROCESS")("UPLOADER_SKIP_UPDATE") = "1"
shell.CurrentDirectory = root
shell.Run """" & py & """ """ & launcher & """", 1, False
If fso.FileExists(here & "\idle-update.vbs") Then
  shell.Run "wscript.exe //nologo """ & here & "\idle-update.vbs"" """ & here & """ """ & root & """", 0, False
End If

RepairMasterShortcut

If patched = 11 Then
  MsgBox "마스터 프로그램을 엽니다. 화면 버전은 v" & ScreenVersion() & " 입니다." & vbCrLf & vbCrLf & _
    "셀러용 설치 파일도 같은 버전으로 새로 만들었습니다." & vbCrLf & _
    "구매자에게 배포\모두모두AI-셀러용-설치.zip 을 주세요.", 64, "모두모두AI"
End If

Sub RepairMasterShortcut()
  Dim desktop, shellLink, folder, file, scriptPath, target, targetDir
  On Error Resume Next
  desktop = shell.SpecialFolders("Desktop")
  If desktop = "" Then Exit Sub
  scriptPath = here & "\어제오후9시.vbs"
  If Not fso.FileExists(scriptPath) Then scriptPath = WScript.ScriptFullName
  Set shellLink = shell.CreateShortcut(desktop & "\모두모두AI 마스터.lnk")
  shellLink.TargetPath = shell.ExpandEnvironmentStrings("%SystemRoot%\System32\wscript.exe")
  shellLink.Arguments = "//nologo """ & scriptPath & """"
  shellLink.WorkingDirectory = here
  If fso.FileExists(here & "\MODUMODU.exe") Then shellLink.IconLocation = here & "\MODUMODU.exe,0"
  shellLink.WindowStyle = 1
  shellLink.Description = "모두모두AI"
  shellLink.Save
  Set folder = fso.GetFolder(desktop)
  For Each file In folder.Files
    If LCase(Right(file.Name, 4)) = ".lnk" And LCase(file.Name) <> "모두모두ai 마스터.lnk" Then
      Set shellLink = shell.CreateShortcut(file.Path)
      target = shellLink.TargetPath
      If Len(target) >= 12 Then
        If LCase(Right(target, 12)) = "\modumodu.exe" Then
          targetDir = fso.GetParentFolderName(target)
          If fso.FileExists(targetDir & "\어제오후9시.vbs") Then
            shellLink.TargetPath = shell.ExpandEnvironmentStrings("%SystemRoot%\System32\wscript.exe")
            shellLink.Arguments = "//nologo """ & targetDir & "\어제오후9시.vbs"""
            shellLink.WorkingDirectory = targetDir
            If fso.FileExists(targetDir & "\MODUMODU.exe") Then shellLink.IconLocation = targetDir & "\MODUMODU.exe,0"
            shellLink.WindowStyle = 1
            shellLink.Save
          End If
        End If
      End If
    End If
  Next
  On Error GoTo 0
End Sub

Sub RepairBrokenNames(folder)
  Dim pairs, i, parts, src, dst
  pairs = Array( _
    "ьВмьЪйы░йы▓Х.txt|사용방법.txt", _
    "ьВмьЪйы░йы▓Х-ызИьКдэД░.txt|사용방법-마스터.txt", _
    "ьВмьЪйы░йы▓Х-ы░░эПмьЪй.txt|사용방법-배포용.txt", _
    "ьДдь╣Ш.bat|설치.bat", _
    "ьЦ┤ьаЬьШдэЫД9ьЛЬ.vbs|어제오후9시.vbs")
  For i = 0 To UBound(pairs)
    parts = Split(pairs(i), "|")
    src = folder & "\" & parts(0)
    dst = folder & "\" & parts(1)
    If fso.FileExists(src) Then
      On Error Resume Next
      If Not fso.FileExists(dst) Then
        fso.MoveFile src, dst
      ElseIf NewerFile(fso.GetFile(src), fso.GetFile(dst)) Then
        fso.DeleteFile dst, True
        fso.MoveFile src, dst
      Else
        fso.DeleteFile src, True
      End If
      On Error GoTo 0
    End If
  Next
End Sub

Function NewerFile(a, b)
  Dim gap
  gap = DateDiff("s", b.DateLastModified, a.DateLastModified)
  If gap > 2 Then
    NewerFile = True
  ElseIf gap < -2 Then
    NewerFile = False
  Else
    NewerFile = a.Size > b.Size
  End If
End Function

Function ScreenVersion()
  Dim ts, text
  ScreenVersion = ""
  On Error Resume Next
  If fso.FileExists(here & "\version.txt") Then
    Set ts = fso.OpenTextFile(here & "\version.txt", 1, False)
    text = Trim(Replace(Replace(ts.ReadAll, vbCr, ""), vbLf, ""))
    ts.Close
    ScreenVersion = text
  End If
  On Error GoTo 0
End Function

Function ReadyArg()
  Dim i
  ReadyArg = False
  For i = 0 To WScript.Arguments.Count - 1
    If WScript.Arguments(i) = "/ready" Then
      ReadyArg = True
      Exit Function
    End If
  Next
End Function

Function OfferUpdate(folder)
  Dim ps1, exec, rc, offer, ts, remote, local, notes, answer, updatedExe
  OfferUpdate = False
  ps1 = folder & "\check-update.ps1"
  If Not fso.FileExists(ps1) Then Exit Function
  On Error Resume Next
  Set exec = shell.Exec("powershell.exe -NoProfile -ExecutionPolicy Bypass -File """ & ps1 & """ -Check """ & folder & """")
  If Err.Number <> 0 Then
    Err.Clear
    On Error GoTo 0
    Exit Function
  End If
  Do While exec.Status = 0
    WScript.Sleep 200
  Loop
  rc = exec.ExitCode
  On Error GoTo 0
  If rc <> 2 Then Exit Function
  offer = folder & "\data\update-offer.txt"
  If Not fso.FileExists(offer) Then Exit Function
  Set ts = fso.OpenTextFile(offer, 1, False, -1)
  remote = ts.ReadLine
  local = ts.ReadLine
  notes = ""
  If Not ts.AtEndOfStream Then notes = ts.ReadAll
  ts.Close
  On Error Resume Next
  fso.DeleteFile offer, True
  On Error GoTo 0
  answer = MsgBox("모두모두AI 새 버전이 있습니다." & vbCrLf & local & " → " & remote & vbCrLf & vbCrLf & notes & vbCrLf & vbCrLf & "지금 업데이트할까요?", 4132, "모두모두AI")
  If answer <> 6 Then Exit Function
  rc = shell.Run("powershell.exe -NoProfile -ExecutionPolicy Bypass -File """ & ps1 & """ -Apply """ & folder & """", 0, True)
  If rc <> 0 Then
    MsgBox "업데이트를 받지 못했습니다. 지금 프로그램을 그대로 엽니다.", 48, "모두모두AI"
    Exit Function
  End If
  updatedExe = folder & "\MODUMODU.exe"
  If fso.FileExists(updatedExe) Then
    shell.Run """" & updatedExe & """", 1, False
    OfferUpdate = True
  End If
End Function

Sub LogLine(text)
  Dim ts
  On Error Resume Next
  Set ts = fso.OpenTextFile(root & "\data\restore-yesterday.log", 8, True)
  ts.WriteLine text
  ts.Close
  On Error GoTo 0
End Sub

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

Sub RestoreYesterday(staticDir, markerPath)
  Dim names, i, bak, count, ts
  If fso.FileExists(markerPath) Then Exit Sub
  If Not fso.FolderExists(staticDir) Then Exit Sub
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
    Set ts = fso.CreateTextFile(markerPath, True)
    ts.WriteLine "2026-10-26"
    ts.Close
  End If
End Sub

Function OldestBackup(folder, name)
  Dim folderObj, file, prefix, best
  OldestBackup = ""
  best = ""
  prefix = name & ".bak-20261027"
  If Not fso.FolderExists(folder) Then Exit Function
  Set folderObj = fso.GetFolder(folder)
  For Each file In folderObj.Files
    If Left(file.Name, Len(prefix)) = prefix Then
      If best = "" Or file.Name < best Then best = file.Name
    End If
  Next
  If best <> "" Then OldestBackup = folder & "\" & best
End Function

Function ProductCount(folderPath)
  Dim products, folderObj, file, n
  ProductCount = 0
  products = folderPath & "\products"
  If Not fso.FolderExists(products) Then Exit Function
  On Error Resume Next
  Set folderObj = fso.GetFolder(products)
  n = 0
  For Each file In folderObj.Files
    n = n + 1
  Next
  On Error GoTo 0
  ProductCount = n
End Function

Sub ConsiderData(folderPath)
  Dim n
  If folderPath = "" Then Exit Sub
  If Not fso.FolderExists(folderPath) Then Exit Sub
  n = ProductCount(folderPath)
  If n > bestCount Then
    bestCount = n
    bestData = folderPath
  End If
End Sub

Sub ConsiderKnownData(appRoot)
  Dim paths, i, downloads, folderObj, subFolder, nested
  paths = Array( _
    appRoot & "\data", _
    appRoot & "\배포\MODUMODU-마스터\data", _
    appRoot & "\dist\MODUMODU\data", _
    "C:\Users\user\Downloads\MODUMODU-master-oneshot-2026.10.27.9\모두모두AI-마스터\data", _
    "C:\Users\user\Downloads\MODUMODU-master-oneshot-2026.10.27.8\모두모두AI-마스터\data", _
    "C:\Users\user\Downloads\MODUMODU-master-oneshot-2026.10.27.7\모두모두AI-마스터\data" _
  )
  For i = 0 To UBound(paths)
    ConsiderData paths(i)
  Next
  downloads = "C:\Users\user\Downloads"
  If Not fso.FolderExists(downloads) Then Exit Sub
  On Error Resume Next
  Set folderObj = fso.GetFolder(downloads)
  For Each subFolder In folderObj.SubFolders
    If Left(subFolder.Name, 8) = "MODUMODU" Then
      ConsiderData subFolder.Path & "\data"
      ConsiderData subFolder.Path & "\모두모두AI-마스터\data"
      nested = subFolder.Path & "\모두모두AI-마스터\data"
      ConsiderData nested
    End If
  Next
  On Error GoTo 0
End Sub

Function ChoosePython(appRoot)
  Dim localPy, knownPy, sysPy
  localPy = appRoot & "\.venv\Scripts\python.exe"
  knownPy = "C:\Users\user\smartstore-shorts\.venv\Scripts\python.exe"
  If fso.FileExists(localPy) Then
    If Not CanImport(localPy) Then InstallRequirements localPy, appRoot
    If CanImport(localPy) Then
      ChoosePython = localPy
      Exit Function
    End If
  End If
  If fso.FileExists(knownPy) And CanImport(knownPy) Then
    ChoosePython = knownPy
    Exit Function
  End If
  sysPy = "python"
  InstallRequirements sysPy, appRoot
  ChoosePython = sysPy
End Function

Function CanImport(py)
  Dim rc
  On Error Resume Next
  rc = shell.Run("""" & py & """ -c ""import pybase64""", 0, True)
  CanImport = (Err.Number = 0 And rc = 0)
  Err.Clear
  On Error GoTo 0
End Function

Sub InstallRequirements(py, appRoot)
  Dim req
  req = appRoot & "\requirements.txt"
  On Error Resume Next
  If fso.FileExists(req) Then
    shell.Run """" & py & """ -m pip install -r """ & req & """", 1, True
  Else
    shell.Run """" & py & """ -m pip install pybase64", 1, True
  End If
  On Error GoTo 0
End Sub
