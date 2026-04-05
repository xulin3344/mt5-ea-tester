# MT5 EA Batch Tester

> One-click batch compile, backtest, and rank all your MetaTrader 5 strategies.

[![Version](https://img.shields.io/github/v/tag/xulin3344/mt5-ea-tester?label=version&sort=semver&color=blue)](https://github.com/xulin3344/mt5-ea-tester/releases)
[![Python](https://img.shields.io/badge/python-3.8+-green)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-orange)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-windows-lightgrey)]()

---

## What is this?

You've got multiple EA strategies sitting in your MT5 `Experts` folder. Testing them one by one through the Strategy Tester is **slow and painful**.

**MT5 EA Batch Tester** fixes that. Put all your `.mq5` files in one folder, click a few buttons, and watch it:

1. **Compile** every strategy into `.ex5`
2. **Generate** backtest configs automatically
3. **Run** all backtests sequentially (wait-free, no babysitting)
4. **Analyze & rank** results by profit, drawdown, and win rate

All from one clean desktop GUI. No command line needed.

---

## Demo

```
Settings → Compile → Config → Backtest → Analyze → Done!
```

The entire pipeline is automated — from raw MQ5 source to a ranked HTML report.

---

## Features

| Feature | Description |
|---|---|
| **GUI Dashboard** | Clean PyQt6 interface with 6-step workflow navigation |
| **Batch Compile** | Compile all `.mq5` files at once via MetaEditor |
| **Auto Config** | Generate `.ini` backtest configs with one click |
| **Batch Backtest** | Sequential MT5 Strategy Tester runs, auto-wait for each result |
| **Result Ranking** | Parse all reports, sort by profit, export to HTML |
| **Real-time Logs** | Color-coded live log output during every operation |
| **Config Persistence** | Settings saved between sessions (paths, params, etc.) |
| **Version Management** | Built-in versioning, changelog, exe metadata |
| **Standalone EXE** | Single-file executable — no Python install required |
| **One-Click Pipeline** | Compile → Config → Backtest → Analysis in one click (▶ Auto Mode) |
| **Cleanup** | One-click remove all temp files between runs |

---

## Quick Start

### Method 1: Download EXE (No Python Required)

1. Go to [Releases](https://github.com/xulin3344/mt5-ea-tester/releases)
2. Download the latest `MT5_EA_Tester.exe`
3. Double-click to run

### Method 2: Run from Source

```bash
# Prerequisites: Python 3.8+
git clone https://github.com/xulin3344/mt5-ea-tester.git
cd mt5-ea-tester
pip install PyQt6
python main.py
```

### Build Your Own EXE

```bash
pip install pyinstaller
build.bat
# or manually:
pyinstaller --clean build.spec
# Output: dist/MT5_EA_Tester.exe
```

---

## How It Works

### The Pipeline

You can either go through each step manually, or use **▶ Auto Mode** (one-click full pipeline):

```
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│ Setting │ -> │ Compile │ -> │ Config  │ -> │Backtest │ -> │ Analyze │ -> 📊
│   ⚙️    │    │   🔨    │    │   📋    │    │   🚀    │    │   📊    │
└─────────┘    └─────────┘    └─────────┘    └─────────┘    └─────────┘
                                                                    │
                                                           ┌─────────┐
                                                           │ Cleanup │
                                                           │   🧹    │
                                                           └─────────┘
```

### ▶ Auto Mode (One-Click Pipeline)

Select **▶ Auto Mode** from the sidebar to run the entire pipeline with a single click:

1. Compiles all `.mq5` files
2. Generates backtest configs
3. Runs all backtests sequentially
4. Parses and ranks results in HTML report

The progress bar and live log show each step's status. If any step fails, the pipeline stops and highlights the error.

### Step Details

#### ⚙️ Settings (One-Time Setup)

Configure your MT5 environment and backtest parameters:

- **MT5 Path** → Where `metaeditor64.exe` and `terminal64.exe` live
- **EA Directory** → Folder containing your `.mq5` strategy files
- **Report Directory** → Where backtest `.htm` reports will be saved
- **Symbol / Timeframe** → e.g. `XAUUSDm` / `H1`
- **Date Range** → Backtest period (e.g. 2025.01.01 → 2026.03.01)
- **Deposit & Leverage** → Starting capital and leverage multiplier

All settings persist between sessions. Close and reopen — your config is still there.

#### 🔨 Compile

Scans your EA directory for all `.mq5` files and compiles them via MetaEditor.

- Progress bar shows how far through the list you are
- Color-coded log: blue (info), green (success), red (error)
- Generates `.ex5` compiled files + `.log` for each

#### 📋 Config

Generates `.ini` configuration files for each compiled EA — these tell MT5's Strategy Tester what parameters to use during backtesting.

- Each `.ini` contains: symbol, timeframe, date range, deposit, leverage
- Configs are UTF-16-LE encoded (MT5 requirement)
- Click "Generate Configs" → all done in one second

#### 🚀 Backtest

The meat of the system. Runs all your EAs through the MT5 Strategy Tester one by one.

Behind the scenes:

1. Deletes any old report files
2. Launches `terminal64.exe /config:xxx.ini`
3. Polls every 5 seconds for the new report
4. 10-minute timeout per EA (prevents hanging)
5. Automatically moves to the next EA when done

You just click one button and watch it go.

#### 📊 Analyze

Reads all `.htm` backtest reports from your reports directory and:

- Extracts profit, drawdown, profit factor, trades, win rate
- Displays ranked table in-app
- Generates an HTML ranking report (`ea_ranking_report.html`)
- Opens it in your browser with one click

Top performer gets highlighted in green. You instantly see which strategy to focus on.

#### 🧹 Cleanup

Between testing rounds, delete temp files:

- `.ex5` — compiled files
- `.log` — compilation logs
- `.ini` — backtest configs
- `.htm` — old reports
- Or check "All" to wipe everything

---

## Project Structure

```
mt5-ea-tester/
├── main.py              # Application entry point + GUI
├── core/
│   ├── compiler.py       # Batch compilation thread
│   ├── config_generator.py  # .ini config file generator
│   ├── backtester.py     # Sequential backtest runner
│   ├── analyzer.py       # Report parser + HTML generator
│   └── version.py        # Version string reader
├── ui/
│   └── __init__.py       # UI module (widgets inlined in main.py)
├── VERSION               # Current version number
├── CHANGELOG.md          # Version history
├── version_info.txt      # Windows exe metadata
├── build.spec            # PyInstaller config
├── build.bat             # One-click build script
├── requirements.txt      # Python dependencies
├── .gitignore            # Git ignore rules
├── 使用指南.md            # Usage guide (Chinese)
└── README.md             # You are here!
```

---

## Requirements

| Requirement | Version | Notes |
|---|---|---|
| **Python** | 3.8+ | Only needed to run from source |
| **PyQt6** | 6.x | GUI framework |
| **PyInstaller** | 6.x | For building the EXE (optional) |
| **MetaTrader 5** | Any recent | Must be installed on your machine |

---

## Development

### Adding New EA Strategies

1. Drop your `.mq5` file into the EA directory
2. Open the app → Compile step
3. Click **Refresh** → your new file should appear
4. Click **Compile All** → `.ex5` generated
5. Continue through the pipeline

That's it. No code changes needed to the tester.

### Versioning a New Release

```bash
# 1. Bump version
echo "0.2.0" > VERSION

# 2. Update version_info.txt
#    Change all "0.1.0.0" to "0.2.0.0"

# 3. Update CHANGELOG.md
#    Add new section at top

# 4. Commit and push
git add -A
git commit -m "feat: v0.2.0 - your changelog summary"
git push origin master
git tag v0.2.0 && git push origin v0.2.0

# 5. Build new exe
build.bat
```

### Project Roadmap

- [ ] Drag-and-drop EA files into the app
- [ ] Chart preview (render `.png` reports in-app)
- [ ] Multi-symbol backtesting (test on EURUSD, GBPUSD, etc.)
- [ ] Export results to CSV
- [ ] Cloud/remote backtesting via MT5 terminal service
- [ ] Email/Telegram notifications on completion

---

## Troubleshooting

| Problem | Solution |
|---|---|
| **"metaeditor64.exe not found"** | Check Settings → MT5 Path. Must point to the folder containing `metaeditor64.exe` |
| **No .mq5 files found** | Verify EA Directory contains your `.mq5` source files |
| **Backtest hangs** | Check that MT5 hasn't crashed. The app has a 10-minute timeout per EA. You can also check `Journal` tab in MT5 |
| **No reports generated** | Make sure MT5 Strategy Tester works manually on one of your EAs. Some EAs may have bugs that prevent backtesting |
| **Proxy/connect issues on push** | If you cloned/pushed from behind a proxy, try `git config --global --unset http.proxy` |

---

## License

[MIT](LICENSE) — do whatever you want with this.

---

## Star History

If this tool saved you time, a ⭐ would be much appreciated!
