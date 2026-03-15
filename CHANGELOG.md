# Changelog – AufurWizard

## o2 (current) – Windows Compatibility

### Added

**`ui/path_browser.py`** *(new)*
- New `PathBrowser` as a Textual `ModalScreen` with a built-in `DirectoryTree`
- Keyboard navigation: `↑ ↓` to browse, `Enter` to confirm, `Escape` to cancel
- Returns the selected `Path` via `dismiss()` – or `None` on cancel
- Defaults to the user's home directory on all platforms

### Changed

**`ui/file_picker.py`**
- Added "Browse…" button next to the path input
- Opens `PathBrowser` as a modal and writes the selected path into the input field automatically
- Browse and Shred buttons are disabled during an active shred operation

**`ui/disk_picker.py`**
- On Windows, additionally lists physical drives (`\\.\PhysicalDrive0`, `\\.\PhysicalDrive1`, …) via `wmic diskdrive`
- Helper `_list_physical_drives_windows()` returns a label with model name and size

**`core/shredder.py`**
- Block device size detection is now cross-platform:
  - Linux: `/sys/block/<dev>/size`
  - macOS: `ioctl DKIOCGETBLOCKCOUNT + DKIOCGETBLOCKSIZE`
  - Windows: `DeviceIoControl IOCTL_DISK_GET_DRIVE_GEOMETRY_EX` via `ctypes`
  - Universal fallback: seek-to-end
- `os.fsync()` errors are now caught silently (fails on some block devices)
- `stat.S_ISBLK` check is skipped on Windows (no block device nodes)

**`core/scanner.py`**
- Removable device detection is now cross-platform:
  - Linux: `/sys/block/<dev>/removable`
  - macOS: `diskutil info -plist` via subprocess
  - Windows: `wmic logicaldisk get DeviceID,DriveType` (DriveType 2 = removable)
- `PermissionError` when reading disk usage is now caught as `OSError`

**`utils/permissions.py`**
- Elevation error message is now OS-specific:
  - Windows: *"Run as administrator"*
  - Linux/macOS: *"Re-run with sudo"*

### Fixed

**`utils/logger.py`**
- Corrected log directory: `~/.aufur_wizard` (was incorrectly `~/.aufer_wizard`)

---

## o1

- Initial release
- TUI built with Textual: Dashboard, FilePicker, DiskPicker, HistoryScreen
- Wipe standards: Zero Fill, Random, DoD 3-Pass, DoD 7-Pass, Gutmann 35-Pass
- Logging to `~/.aufur_wizard/history.log`
- Support for files, folders, and block devices
- Linux and macOS
