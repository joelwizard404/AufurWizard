from __future__ import annotations

import os
import secrets
import stat
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import Callable

from .standards import Standard, Pass


class EventType(Enum):
    PASS_START    = auto()
    PASS_PROGRESS = auto()
    PASS_DONE     = auto()
    FILE_DONE     = auto()
    VERIFY_START  = auto()
    VERIFY_DONE   = auto()
    ERROR         = auto()


@dataclass
class ShredEvent:
    type: EventType
    path: Path | None = None
    pass_index: int = 0
    pass_total: int = 0
    pass_label: str = ""
    bytes_written: int = 0
    bytes_total: int = 0
    message: str = ""


Callback = Callable[[ShredEvent], None]

CHUNK = 1024 * 1024  # 1 MiB


def shred_file(path: Path, standard: Standard,
               callback: Callback | None = None) -> bool:
    cb = callback or _noop
    try:
        size = path.stat().st_size
    except OSError as exc:
        cb(ShredEvent(EventType.ERROR, path=path, message=str(exc)))
        return False

    try:
        with open(path, "r+b") as fh:
            for i, p in enumerate(standard.passes):
                cb(ShredEvent(EventType.PASS_START, path=path,
                              pass_index=i, pass_total=len(standard.passes),
                              pass_label=p.label, bytes_total=size))
                _overwrite_fd(fh, size, p, i, len(standard.passes), path, cb)
                cb(ShredEvent(EventType.PASS_DONE, path=path,
                              pass_index=i, pass_total=len(standard.passes),
                              pass_label=p.label))
            if standard.verify:
                cb(ShredEvent(EventType.VERIFY_START, path=path))
                _verify_zeros(fh, size)
                cb(ShredEvent(EventType.VERIFY_DONE, path=path))
        path.unlink()
        cb(ShredEvent(EventType.FILE_DONE, path=path))
        return True
    except OSError as exc:
        cb(ShredEvent(EventType.ERROR, path=path, message=str(exc)))
        return False


def shred_directory(root: Path, standard: Standard,
                    callback: Callback | None = None) -> tuple[int, int]:
    ok = err = 0
    all_files = sorted(p for p in root.rglob("*") if p.is_file())
    for fpath in all_files:
        if shred_file(fpath, standard, callback):
            ok += 1
        else:
            err += 1
    for dirpath in sorted(root.rglob("*"), reverse=True):
        if dirpath.is_dir():
            try:
                dirpath.rmdir()
            except OSError:
                pass
    try:
        root.rmdir()
    except OSError:
        pass
    return ok, err


def shred_block_device(device: Path, standard: Standard,
                       callback: Callback | None = None) -> bool:
    cb = callback or _noop
    if not device.exists():
        cb(ShredEvent(EventType.ERROR, path=device, message=f"Device not found: {device}"))
        return False
    if not stat.S_ISBLK(device.stat().st_mode):
        cb(ShredEvent(EventType.ERROR, path=device, message=f"{device} is not a block device"))
        return False
    size = _block_device_size(device)
    if size == 0:
        cb(ShredEvent(EventType.ERROR, path=device, message="Could not determine device size"))
        return False
    try:
        with open(device, "r+b", buffering=0) as fh:
            for i, p in enumerate(standard.passes):
                cb(ShredEvent(EventType.PASS_START, path=device,
                              pass_index=i, pass_total=len(standard.passes),
                              pass_label=p.label, bytes_total=size))
                _overwrite_fd(fh, size, p, i, len(standard.passes), device, cb)
                cb(ShredEvent(EventType.PASS_DONE, path=device,
                              pass_index=i, pass_total=len(standard.passes),
                              pass_label=p.label))
        return True
    except PermissionError:
        cb(ShredEvent(EventType.ERROR, path=device, message="Permission denied – root required."))
        return False
    except OSError as exc:
        cb(ShredEvent(EventType.ERROR, path=device, message=str(exc)))
        return False


def _overwrite_fd(fh, size: int, p: Pass, pass_idx: int,
                  pass_total: int, path: Path, cb: Callback) -> None:
    fh.seek(0)
    written = 0
    while written < size:
        chunk_size = min(CHUNK, size - written)
        if p.pattern is None:
            data = secrets.token_bytes(chunk_size)
        else:
            repeats = -(-chunk_size // len(p.pattern))
            data = (p.pattern * repeats)[:chunk_size]
        fh.write(data)
        written += chunk_size
        cb(ShredEvent(EventType.PASS_PROGRESS, path=path,
                      pass_index=pass_idx, pass_total=pass_total,
                      pass_label=p.label, bytes_written=written, bytes_total=size))
    fh.flush()
    os.fsync(fh.fileno())


def _verify_zeros(fh, size: int) -> None:
    fh.seek(0)
    read = 0
    while read < size:
        chunk = fh.read(min(CHUNK, size - read))
        if not chunk:
            break
        if any(chunk):
            raise OSError("Verify failed: non-zero byte detected after shred")
        read += len(chunk)


def _block_device_size(device: Path) -> int:
    name = device.name.rstrip("0123456789")
    for path in (Path(f"/sys/block/{name}/{device.name}/size"),
                 Path(f"/sys/block/{name}/size")):
        try:
            return int(path.read_text().strip()) * 512
        except (OSError, ValueError):
            pass
    try:
        with open(device, "rb") as fh:
            fh.seek(0, 2)
            return fh.tell()
    except OSError:
        return 0


def _noop(_: ShredEvent) -> None:
    pass
