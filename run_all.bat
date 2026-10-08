@echo off
echo ===================================================
echo  GDP Assistant - Launching Backend & Frontend
echo ===================================================
python scripts\sync_host_lan_ip.py --once
python run.py
pause
