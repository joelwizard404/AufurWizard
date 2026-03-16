from __future__ import annotations

import os
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


_VIRTUAL_FS = {"tmpfs", "devtmpfs", "squashfs", "overlay",
               "proc", "sysfs", "cgroup", "devpts", "debugfs"}

_MACOS_SYSTEM_MOUNTS = {"/", "/System/Volumes/Data"}


def list_disks(include_virtual: bool = False) -> list[DiskInfo]:
    results: list[DiskInfo] = []
    for part in psutil.disk_partitions(all=False):
        if not include_virtual and part.fstype in _VIRTUAL_FS:
            continue
        try:
            usage = psutil.disk_usage(part.mountpoint)
        except PermissionError:
            continue
        results.append(DiskInfo(
            device=part.device,
            mountpoint=part.mountpoint,
            fstype=part.fstype,
            total=usage.total,
            used=usage.used,
            free=usage.free,
            is_removable=_is_removable(part.device, part.mountpoint),
        ))
    return results


def scan_path(root: Path) -> list[FileEntry]:
    entries: list[FileEntry] = []
    if root.is_file():
        return [_make_entry(root)]
    for dirpath, _, filenames in os.walk(root, topdown=True, onerror=lambda _: None):
        entries.append(FileEntry(path=Path(dirpath), size=_dir_size(Path(dirpath)), is_dir=True))
        for fname in filenames:
            entries.append(_make_entry(Path(dirpath) / fname))
    return sorted(entries, key=lambda e: e.path)


def _is_removable(device: str, mountpoint: str = "") -> bool:
    if sys.platform == "linux":
        name = Path(device).name.rstrip("0123456789")
        try:
            return Path(f"/sys/block/{name}/removable").read_text().strip() == "1"
        except OSError:
            return False

    if sys.platform == "darwin":
        return mountpoint not in _MACOS_SYSTEM_MOUNTS

    return False


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
