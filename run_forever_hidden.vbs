' Launches run_forever.bat with NO visible console window.
' Put a shortcut to THIS file in shell:startup to run the dashboard
' silently every time you log in.
Set fso = CreateObject("Scripting.FileSystemObject")
Set sh  = CreateObject("WScript.Shell")
sh.CurrentDirectory = fso.GetParentFolderName(WScript.ScriptFullName)
sh.Run """" & sh.CurrentDirectory & "\run_forever.bat""", 0, False
