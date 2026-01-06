import PyInstaller.__main__
import os
import sys

SCRIPT = "telemetry_collector.py"
APP_NAME = "SystemTelemetryMonitor"

if not os.path.exists(SCRIPT):
    print("Telemetry script not found!")
    sys.exit(1)

PyInstaller.__main__.run([
    SCRIPT,
    "--onefile",
    "--name=" + APP_NAME,
    "--collect-all=psutil",
    "--clean",
    "--noconfirm"
])

print(f"\n[✓] EXE built → dist/{APP_NAME}.exe")
