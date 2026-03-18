Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "cmd /c cd /d C:\Users\omran\OneDrive\Desktop\CV && py -m streamlit run .\jobtracker\Home.py", 0
Set WshShell = Nothing
