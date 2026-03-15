' KYRA Silent Launcher
' Runs start.ps1 with no console window visible at any point.
' Double-click this file to start KYRA.

Dim shell
Set shell = CreateObject("WScript.Shell")

' Get the directory this script lives in (strip trailing backslash)
Dim scriptDir
scriptDir = Left(WScript.ScriptFullName, InStrRev(WScript.ScriptFullName, "\") - 1)

Dim psScript
psScript = scriptDir & "\start.ps1"

' -WindowStyle Hidden keeps the PowerShell window invisible
' -ExecutionPolicy Bypass avoids policy prompts
Dim cmd
cmd = "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File """ & psScript & """"

' 0 = hide window, False = don't wait for exit
shell.Run cmd, 0, False

Set shell = Nothing
