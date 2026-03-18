param(
  [string]$AppPath = (Get-Location).Path
)
Set-Location $AppPath
py -m pip install --quiet --upgrade -r .\jobtracker\requirements.txt
py -m streamlit run .\jobtracker\Home.py
