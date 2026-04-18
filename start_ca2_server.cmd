@echo off
REM Development launcher for CA2 Django server
set DJANGO_DEBUG=true
set DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost
set DJANGO_EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
set DJANGO_SECRET_KEY=dev-secret-key
cd /d %~dp0
echo [%date% %time%] launching server >> runserver.log
%~dp0\.venv\Scripts\python.exe manage.py runserver 0.0.0.0:8000 >> runserver.log 2>&1
