@echo off
REM Script to run the API server with JWT authentication enabled on Windows

echo Starting API server with JWT authentication enabled...

REM Set environment variables
set ENABLE_JWT_AUTH=true
set DISABLE_DB=true

REM Run the API server
python -m api.server

echo API server stopped.
