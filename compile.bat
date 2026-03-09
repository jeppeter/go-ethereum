rem echo off

set TOPBUILD=%~dp0
echo %TOPBUILD%
set GOPROXY=https://goproxy.cn
pushd %CD% && cd %TOPBUILD%\build\ &&  go build -o build.exe ci.go && cd %TOPBUILD% && .\build\build.exe install .\cmd\geth