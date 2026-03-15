@echo off
:: KYRA Silent Bootstrap
:: This .bat triggers the VBScript launcher which runs PowerShell hidden.
:: No console window will appear after this momentary flash.
wscript.exe "%~dp0launch.vbs"
