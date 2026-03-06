```shell
# windows
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

$env:Path = "C:\Users\liyf\.local\bin;$env:Path"

uv --version
```