#!/bin/sh
# startup.sh -- App Service Python-start. MASTE ha LF-radslut (D.23):
# skapad pa Windows med CRLF -> Linux laste /bin/sh\r -> 'not found'.
# Skrivs darfor med python (newline='') sa inga CR smyger in. PowerShells
# Set-Content ateranfor BOM/CRLF -- anvand ALDRIG for denna fil.
cd /home/site/wwwroot
exec gunicorn --bind=0.0.0.0:8000 --timeout 600 --workers 2 app:app
