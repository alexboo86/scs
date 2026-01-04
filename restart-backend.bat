@echo off
REM Быстрый перезапуск backend на VPS

echo Restarting backend on VPS...
ssh root@89.110.111.184 "cd ~/projects/secure-content-service && docker-compose restart backend"
echo Done!
