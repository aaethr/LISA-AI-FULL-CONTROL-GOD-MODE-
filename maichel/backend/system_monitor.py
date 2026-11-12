import json
import os
import platform
import sqlite3
import subprocess
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import psutil


DATABASE_PATH = Path.home() / ".michael" / "system_monitor.sqlite3"


def analyze_metrics(
    cpu_percent: float, ram_percent: float, disk_free_percent: float
) -> Dict:
    findings = []
    score = 100

    if cpu_percent > 90:
        critical = cpu_percent >= 98
        findings.append(
            {
                "severity": "critical" if critical else "warning",
                "message": f"การใช้งาน CPU สูง ({cpu_percent:.0f}%)",
                "recommendation": "ตรวจสอบโปรแกรมที่กำลังใช้ CPU และปิดเฉพาะโปรแกรมที่ไม่จำเป็น",
            }
        )
        score -= 20

    if ram_percent >= 85:
        critical = ram_percent >= 95
        findings.append(
            {
                "severity": "critical" if critical else "warning",
                "message": f"การใช้งาน RAM สูง ({ram_percent:.0f}%)",
                "recommendation": "ตรวจสอบแอปที่ใช้หน่วยความจำมาก และบันทึกงานก่อนปิดแอป",
            }
        )
        score -= 20

    if disk_free_percent < 15:
        critical = disk_free_percent < 8
        findings.append(
            {
                "severity": "critical" if critical else "warning",
                "message": f"พื้นที่ว่างในไดรฟ์ระบบเหลือน้อย ({disk_free_percent:.0f}%)",
                "recommendation": "ตรวจสอบพื้นที่และสำรองไฟล์ก่อนลบสิ่งใด",
            }
        )
        score -= 20

    status = (
        "attention"
        if any(finding["severity"] == "critical" for finding in findings)
        else "warning"
        if findings
        else "healthy"
    )
    return {"health_score": max(0, score), "status": status, "findings": findings}


def _read_gpu_name() -> Tuple[Optional[str], Optional[str]]:
    if os.name != "nt":
        return None, "การอ่านชื่อ GPU ผ่าน WMI ใช้ได้เฉพาะ Windows"

    command = (
        "$ErrorActionPreference='Stop'; "
        "Get-CimInstance Win32_VideoController | "
        "Select-Object -ExpandProperty Name | ConvertTo-Json -Compress"
    )
    try:
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
            capture_output=True,
            text=True,
            timeout=8,
            check=True,
        )
        output = result.stdout.strip()
        names = json.loads(output) if output else []
        if isinstance(names, str):
            names = [names]
        if not isinstance(names, list):
            raise ValueError("Unexpected GPU query response")
        cleaned_names = [
            name.strip() for name in names if isinstance(name, str) and name.strip()
        ]
        if not cleaned_names:
            return None, "Windows ไม่รายงานชื่อ GPU"
        return ", ".join(cleaned_names), None
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError, ValueError):
        return None, "อ่านชื่อ GPU ไม่สำเร็จ"


def collect_system_report() -> Dict:
    memory = psutil.virtual_memory()
    system_drive = os.environ.get("SystemDrive") or Path.home().anchor or "C:\\"
    disk = psutil.disk_usage(system_drive)
    cpu_percent = psutil.cpu_percent(interval=0.2)
    gpu_name, gpu_warning = _read_gpu_name()
    warnings = [gpu_warning] if gpu_warning else []
    free_percent = 100 - disk.percent
    analysis = analyze_metrics(cpu_percent, memory.percent, free_percent)

    return {
        "measured_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "computer_name": platform.node() or "ไม่ทราบ",
        "operating_system": platform.platform(),
        "cpu": {
            "name": platform.processor().strip() or "ไม่สามารถอ่านชื่อ CPU ได้",
            "logical_cores": psutil.cpu_count(logical=True),
            "usage_percent": round(cpu_percent, 1),
        },
        "gpu": {"name": gpu_name or "ไม่สามารถอ่านชื่อ GPU ได้"},
        "ram": {
            "total_gb": round(memory.total / 1024**3, 1),
            "used_gb": round(memory.used / 1024**3, 1),
            "available_gb": round(memory.available / 1024**3, 1),
            "usage_percent": round(memory.percent, 1),
        },
        "system_drive": {
            "path": system_drive,
            "total_gb": round(disk.total / 1024**3, 1),
            "free_gb": round(disk.free / 1024**3, 1),
            "free_percent": round(free_percent, 1),
        },
        "health_score": analysis["health_score"],
        "status": analysis["status"],
        "findings": analysis["findings"],
        "collection_warnings": warnings,
    }


def save_daily_snapshot(
    report: Dict, database_path: Optional[Path] = None
) -> None:
    database_path = database_path or DATABASE_PATH
    database_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS daily_snapshots (
                snapshot_date TEXT PRIMARY KEY,
                measured_at TEXT NOT NULL,
                report_json TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            INSERT INTO daily_snapshots (snapshot_date, measured_at, report_json)
            VALUES (?, ?, ?)
            ON CONFLICT(snapshot_date) DO UPDATE SET
                measured_at = excluded.measured_at,
                report_json = excluded.report_json
            """,
            (
                report["measured_at"][:10],
                report["measured_at"],
                json.dumps(report, ensure_ascii=False),
            ),
        )
        oldest_date = (date.today() - timedelta(days=364)).isoformat()
        connection.execute(
            "DELETE FROM daily_snapshots WHERE snapshot_date < ?", (oldest_date,)
        )


def collect_daily_snapshot_if_missing() -> bool:
    if get_daily_history(days=1):
        return False
    save_daily_snapshot(collect_system_report())
    return True


def get_daily_history(
    days: int = 30, database_path: Optional[Path] = None
) -> List[Dict]:
    database_path = database_path or DATABASE_PATH
    if not database_path.exists():
        return []

    cutoff = (date.today() - timedelta(days=days - 1)).isoformat()
    with sqlite3.connect(database_path) as connection:
        rows = connection.execute(
            """
            SELECT report_json FROM daily_snapshots
            WHERE snapshot_date >= ?
            ORDER BY snapshot_date ASC
            """,
            (cutoff,),
        ).fetchall()
    return [json.loads(row[0]) for row in rows]