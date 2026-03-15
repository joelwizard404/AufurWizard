from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import psutil


@dataclass
class DiskInfo:
    device: str
    mountpoint: str
    fstype: str
    total: int
    used: int
    free: int
    is_removable: bool

    @property
    def usage_percent(self) -> float:
        return (self.used / self.total * 100) if self.total else 0.0

    @property
    def total_human(self) -> str:
        return _human_size(self.total)

    @property
    def free_human(self) -> str:
        return _human_size(self.free)


@dataclass
class FileEntry:
    path: Path
    size: int
    is_dir: bool

    @property
    def size_human(self) -> str:
        return _human_size(self.size)


_VIRTUAL_FS = {
    "tmpfs", "devtmpfs", "squashfs", "overlay",
    "proc", "sysfs", "cgroup", "devpts", "debugfs",
}

def list_disks(include_virtual: bool = False) -> list[DiskInfo]:
    results: list[DiskInfo] = []
    removable_set = _removable_devices()

    for part in psutil.disk_partitions(all=False):
        if not include_virtual and part.fstype in _VIRTUAL_FS:
            continue
        try:
            usage = psutil.disk_usage(part.mountpoint)
        except (PermissionError, OSError):
            continue
        results.append(DiskInfo(
            device=part.device,
            mountpoint=part.mountpoint,
            fstype=part.fstype,
            total=usage.total,
            used=usage.used,
            free=usage.free,
            is_removable=part.device in removable_set,
        ))
    return results


def scan_path(root: Path) -> list[FileEntry]:
    entries: list[FileEntry] = []
    if root.is_file():
        return [_make_entry(root)]
    for dirpath, _, filenames in os.walk(root, topdown=True, onerror=lambda _: None):
        entries.append(FileEntry(
            path=Path(dirpath),
            size=_dir_size(Path(dirpath)),
            is_dir=True,
        ))
        for fname in filenames:
            entries.append(_make_entry(Path(dirpath) / fname))
    return sorted(entries, key=lambda e: e.path)

def _removable_devices() -> set[str]:
    """Return a set of device paths that are considered removable."""
    if sys.platform == "win32":
        return _removable_windows()
    if sys.platform == "darwin":
        return _removable_macos()
    return _removable_linux()


def _removable_linux() -> set[str]:
    removable: set[str] = set()
    try:
        block = Path("/sys/block")
        for dev_dir in block.iterdir():
            removable_path = dev_dir / "removable"
            try:
                if removable_path.read_text().strip() == "1":
                    removable.add(f"/dev/{dev_dir.name}")
            except OSError:
                pass
    except OSError:
        pass
    return removable


def _removable_macos() -> set[str]:
    """Use diskutil to find external/removable disks on macOS."""
    removable: set[str] = set()
    try:
        result = subprocess.run(
            ["diskutil", "list", "-plist"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode != 0:
            return removable
        import plistlib
        data = plistlib.loads(result.stdout.encode())
        for disk in data.get("AllDisksAndPartitions", []):
            disk_id = disk.get("DeviceIdentifier", "")
            info_result = subprocess.run(
                ["diskutil", "info", "-plist", disk_id],
                capture_output=True, text=True, timeout=5,
            )
            if info_result.returncode == 0:
                info = plistlib.loads(info_result.stdout.encode())
                if info.get("RemovableMediaOrExternalDevice") or info.get("Removable"):
                    removable.add(f"/dev/{disk_id}")
    except Exception:
        pass
    return removable


def _removable_windows() -> set[str]:
    """Use wmic to detect removable drives on Windows."""
    removable: set[str] = set()
    try:
        result = subprocess.run(
            ["wmic", "logicaldisk", "get", "DeviceID,DriveType"],
            capture_output=True, text=True, timeout=10,
        )
        for line in result.stdout.splitlines():
            parts = line.split()
            if len(parts) == 2:
                device_id, drive_type = parts
                # DriveType 2 = removable, 5 = CD-ROM
                if drive_type in ("2", "5"):
                    removable.add(device_id + "\\")
    except Exception:
        pass
    return removable

def _make_entry(path: Path) -> FileEntry:
    try:
        size = path.stat().st_size
    except OSError:
        size = 0
    return FileEntry(path=path, size=size, is_dir=False)


def _dir_size(path: Path) -> int:
    total = 0
    try:
        for entry in os.scandir(path):
            try:
                total += entry.stat(follow_symlinks=False).st_size
            except OSError:
                pass
    except PermissionError:
        pass
    return total


def _human_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024  # type: ignore[assignment]
    return f"{n:.1f} PB"
