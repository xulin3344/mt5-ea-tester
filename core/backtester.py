import os
import time
import subprocess
from PyQt6.QtCore import QThread, pyqtSignal

# CREATE_BREAKAWAY_FROM_JOB + CREATE_NEW_PROCESS_GROUP
CREATION_FLAGS = 0x01000000 | 0x00000200


class BacktesterThread(QThread):
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int, int)  # current, total
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, terminal_path, ea_source_dir, report_dir):
        super().__init__()
        self.terminal_path = terminal_path
        self.ea_source_dir = ea_source_dir
        self.report_dir = report_dir
        self.running = True
        os.makedirs(report_dir, exist_ok=True)

    def run(self):
        ex5_files = sorted(
            f for f in os.listdir(self.ea_source_dir) if f.endswith(".ex5")
        )
        if not ex5_files:
            self.log_signal.emit("(error) No .ex5 files found. Compile first.")
            self.finished_signal.emit(False, "No .ex5 files found.")
            return

        total = len(ex5_files)
        self.log_signal.emit(f"(info) Found {total} EA(s) to backtest.")

        for i, ex5 in enumerate(ex5_files, 1):
            if not self.running:
                self.finished_signal.emit(False, "Cancelled by user.")
                return

            name = os.path.splitext(ex5)[0]
            # Fix 2: Force absolute path — MT5 /config: requires it
            ini_file = os.path.abspath(os.path.join(self.ea_source_dir, f"{name}.ini"))
            report_file = os.path.abspath(os.path.join(self.report_dir, f"{name}.htm"))

            self.log_signal.emit(f"{'─' * 50}")
            self.log_signal.emit(f"(info) [{i}/{total}] Testing {name}...")
            self.progress_signal.emit(i, total)

            # Delete old report
            if os.path.exists(report_file):
                os.remove(report_file)
                self.log_signal.emit(f"(info) Deleted old report for {name}.")

            if not os.path.exists(ini_file):
                self.log_signal.emit(
                    f"(error) Config not found: {name}.ini. Generate configs first."
                )
                continue

            # Launch MT5 Terminal — direct call with absolute path
            self.log_signal.emit(f"(info) Launching MT5 Terminal...")
            self.log_signal.emit(f"(info) Config: {ini_file}")
            try:
                subprocess.Popen(
                    [self.terminal_path, f"/config:{ini_file}"],
                    creationflags=CREATION_FLAGS,
                )
            except Exception as e:
                self.log_signal.emit(f"(error) Failed to launch terminal: {e}")
                continue

            # Wait for report
            self.log_signal.emit(f"(info) Waiting for report: {name}.htm")
            counter = 0
            report_found = False
            while counter < 120:
                if not self.running:
                    self.finished_signal.emit(False, "Cancelled by user.")
                    return
                time.sleep(5)
                if os.path.exists(report_file):
                    self.log_signal.emit(f"(success) Report found for {name}.")
                    report_found = True
                    break
                counter += 1
                if counter % 12 == 0:
                    self.log_signal.emit(
                        f"(info) Still waiting... ({counter * 5}s elapsed)"
                    )

            if not report_found:
                self.log_signal.emit(
                    f"(warning) Timeout: Report not found for {name} after 10 min."
                )

            self.log_signal.emit(f"(info) Done with {name}.")
            # Brief pause between tests
            time.sleep(2)

        self.finished_signal.emit(True, f"Backtested {total} EA(s).")

    def stop(self):
        self.running = False
        self.terminate()
