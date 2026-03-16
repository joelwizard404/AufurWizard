# AufurWizard

A terminal-based secure file shredding tool for **Linux** and **macOS**.

```
┌──────────────────────────────────────────────┐
│  AufurWizard                                 │
│                                              │
│  ❯ Shred files / folders                     │
│    Shred disk / partition                    │
│    View history                              │
│    Quit                                      │
└──────────────────────────────────────────────┘
```

## Features

- Multiple wipe standards: Zero Fill, Random, DoD 3-Pass, DoD 7-Pass, Gutmann 35-Pass
- Shred individual files, entire folders, or raw block devices / partitions
- Cryptographically random data via Python's `secrets` module
- Verification pass after DoD standards
- Operation history log at `~/.aufur_wizard/history.log`
- Fully keyboard-navigable TUI

## Installation

```bash
pip install aufur-wizard
```

Or from source:

```bash
git clone https://github.com/joelwizard404/AuferWizard.git
cd AuferWizard
pip install .
```

## Usage

```bash
aufur
```

Wiping block devices requires root:

```bash
sudo aufur
```

## Wipe Standards

| ID        | Name                     | Passes | Verify |
|-----------|--------------------------|--------|--------|
| `zero`    | Zero Fill                | 1      | No     |
| `random`  | Random (1-Pass)          | 1      | No     |
| `dod3`    | DoD 5220.22-M (3-Pass)   | 3      | Yes    |
| `dod7`    | DoD 5220.22-M ECE (7-Pass)| 7     | Yes    |
| `gutmann` | Gutmann (35-Pass)        | 35     | No     |

## Requirements

- Python 3.11+
- Linux or macOS (Windows not supported)

## License

Public domain — see [LICENSE](LICENSE).
