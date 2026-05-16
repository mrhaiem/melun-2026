@echo off
title Scraper Melun 2026 - NatVision
color 1F

:loop
echo.
echo ============================================
echo   SCRAPER MELUN 2026 — NatVision
echo   Ctrl+C pour arreter
echo ============================================
echo.
py -3.11 scrape_melun.py --loop 300 --push
echo.
echo *** Scraper arrete — relance dans 15s ***
timeout /t 15
goto loop
