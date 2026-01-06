import psutil
import time
import sys
import platform
import subprocess
import csv
from datetime import datetime
from pathlib import Path

# ================= CONFIG =================
TOTAL_DURATION = 3600        # seconds (1 hour)
SAMPLE_INTERVAL = 5          # seconds
DATA_FOLDER_NAME = "Telemetry_Data"
# =========================================

# ---------- Directory Handling ----------
def get_storage_directory():
    """Creates or returns the folder to store telemetry logs on Desktop"""
    home = Path.home()
    desktop = home / "Desktop"
    target = desktop if desktop.exists() else home
    folder = target / DATA_FOLDER_NAME
    folder.mkdir(parents=True, exist_ok=True)
    return folder

# ---------- Hardware Label ----------
def get_hardware_label():
    """Generates a label based on CPU and RAM"""
    cpu = "UnknownCPU"
    try:
        if sys.platform == "win32":
            result = subprocess.run(
                ["wmic", "cpu", "get", "name"],
                capture_output=True,
                text=True
            )
            cpu = result.stdout.split("\n")[1].strip()
        else:
            cpu = platform.processor() or "UnknownCPU"
    except:
        pass

    ram = round(psutil.virtual_memory().total / (1024 ** 3))
    label = f"{cpu}-RAM{ram}GB"
    return label.replace(" ", "_").replace("(R)", "").replace("(TM)", "")

# ---------- CSV Writer ----------
def write_csv(base, label, logs, folder):
    """Writes all collected telemetry logs to a CSV file"""
    file = folder / f"{base}_metrics.csv"

    fields = [
        "timestamp_unix", "timestamp_human", "hw_label",
        "cpu_percent", "ram_percent", "ram_used_gb",
        "disk_read_kb_s", "disk_write_kb_s",
        "net_sent_kb_s", "net_recv_kb_s",
        "charging"
    ]

    for i in range(1, 11):
        fields += [
            f"top_cpu_{i}_pid", f"top_cpu_{i}_name", f"top_cpu_{i}_value",
            f"top_mem_{i}_pid", f"top_mem_{i}_name", f"top_mem_{i}_value"
        ]

    try:
        with open(file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()

            for log in logs:
                row = {
                    "timestamp_unix": log["ts"],
                    "timestamp_human": log["time"],
                    "hw_label": label,
                    "cpu_percent": log["cpu"],
                    "ram_percent": log["ram"],
                    "ram_used_gb": log["ram_gb"],
                    "disk_read_kb_s": log["disk_r"],
                    "disk_write_kb_s": log["disk_w"],
                    "net_sent_kb_s": log["net_s"],
                    "net_recv_kb_s": log["net_r"],
                    "charging": log["charging"]
                }

                for i, p in enumerate(log["top_cpu"], 1):
                    row[f"top_cpu_{i}_pid"] = p["pid"]
                    row[f"top_cpu_{i}_name"] = p["name"]
                    row[f"top_cpu_{i}_value"] = p["cpu"]

                for i, p in enumerate(log["top_mem"], 1):
                    row[f"top_mem_{i}_pid"] = p["pid"]
                    row[f"top_mem_{i}_name"] = p["name"]
                    row[f"top_mem_{i}_value"] = p["mem"]

                writer.writerow(row)
        print(f"[✓] CSV saved: {file}")
    except Exception as e:
        print(f"[!] Failed to write CSV: {e}")

# ---------- Telemetry Core ----------
def collect_telemetry(label, duration, interval):
    """Collects CPU, RAM, disk, network, and top process data"""
    storage_dir = get_storage_directory()
    start_ts = time.strftime("%Y%m%d_%H%M%S")
    filename_base = f"telemetry_{label}_{start_ts}"
    file_path = storage_dir / f"{filename_base}_metrics.csv"

    print(f"[✓] Telemetry will be saved to:\n{file_path}\n")
    print(f"--- Starting telemetry collection ({TOTAL_DURATION}s total, {SAMPLE_INTERVAL}s interval) ---\n")

    logs = []

    # PRIME CPU counters (needed for accurate first reading)
    psutil.cpu_percent(None)
    for p in psutil.process_iter():
        try:
            p.cpu_percent(None)
        except:
            pass

    net_prev = psutil.net_io_counters()
    disk_prev = psutil.disk_io_counters()

    samples = duration // interval

    try:
        for i in range(samples):
            print(f"Collecting sample {i+1}/{samples}...", end="\r")

            ts = time.time()
            time_h = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")

            battery = psutil.sensors_battery()
            charging = battery.power_plugged if battery else False

            cpu = psutil.cpu_percent(interval=interval)
            mem = psutil.virtual_memory()

            net_now = psutil.net_io_counters()
            disk_now = psutil.disk_io_counters()

            net_sent = (net_now.bytes_sent - net_prev.bytes_sent) / 1024 / interval
            net_recv = (net_now.bytes_recv - net_prev.bytes_recv) / 1024 / interval
            disk_r = (disk_now.read_bytes - disk_prev.read_bytes) / 1024 / interval
            disk_w = (disk_now.write_bytes - disk_prev.write_bytes) / 1024 / interval

            net_prev, disk_prev = net_now, disk_now

            processes = []
            for p in psutil.process_iter(["pid", "name", "memory_percent"]):
                try:
                    processes.append({
                        "pid": p.pid,
                        "name": p.info["name"],
                        "cpu": p.cpu_percent(None),
                        "mem": p.info["memory_percent"]
                    })
                except:
                    continue

            top_cpu = sorted(processes, key=lambda x: x["cpu"], reverse=True)[:10]
            top_mem = sorted(processes, key=lambda x: x["mem"], reverse=True)[:10]

            logs.append({
                "ts": ts,
                "time": time_h,
                "cpu": cpu,
                "ram": mem.percent,
                "ram_gb": round(mem.used / (1024 ** 3), 2),
                "disk_r": round(disk_r, 2),
                "disk_w": round(disk_w, 2),
                "net_s": round(net_sent, 2),
                "net_r": round(net_recv, 2),
                "charging": charging,
                "top_cpu": top_cpu,
                "top_mem": top_mem
            })

    except KeyboardInterrupt:
        print("\n[!] Telemetry interrupted by user.")

    # Write CSV (even if interrupted)
    write_csv(filename_base, label, logs, storage_dir)
    print("\n[✓] Telemetry collection finished.")
    

# ---------- Entry ----------
if __name__ == "__main__":
    hw_label = get_hardware_label()
    collect_telemetry(hw_label, TOTAL_DURATION, SAMPLE_INTERVAL)
