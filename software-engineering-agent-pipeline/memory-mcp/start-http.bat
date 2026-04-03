@echo off
:: Start memory-mcp HTTP server
:: Usage: start-http.bat [port]
:: Default port: 8000

if "%1"=="" (
    set PORT=8000
) else (
    set PORT=%1
)

node %~dp0http-server.js %PORT%
