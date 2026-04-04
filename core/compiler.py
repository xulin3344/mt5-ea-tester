import os
import time
import subprocess
from PyQt6.QtCore import QThread, pyqtSignal


class CompilerThread(QThread):
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int, int)  # current, total
    finished_signal = pyqtSignal(bool, str)  # success, message

    def __init__(self, metaeditor_path, ea_source_dir):
        super().__init__()
        self.metaeditor_path = metaeditor_path
        self.ea_source_dir = ea_source_dir
        self.running = True

    def run(self):
        mq5_files = sorted(
            f for f in os.listdir(self.ea_source_dir) if f.endswith(".mq5")
        )
        if not mq5_files:
            self.log_signal.emit("(error) No .mq5 files found.")
            self.finished_signal.emit(False, "No .mq5 files found.")
            return

        total = len(mq5_files)
        success_count = 0

        self.log_signal.emit(f"(info) Found {total} EA(s) to compile.")

        for i, mq5 in enumerate(mq5_files, 1):
            if not self.running:
                self.finished_signal.emit(False, "Cancelled by user.")
                return

            mq5_path = os.path.abspath(os.path.join(self.ea_source_dir, mq5))
            log_path = mq5_path.replace(".mq5", ".log")

            self.log_signal.emit(f"(info) Compiling {mq5}...")
            self.progress_signal.emit(i, total)

            try:
                proc = subprocess.Popen(
                    [self.metaeditor_path, f"/compile:{mq5_path}", f"/log:{log_path}"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                proc.wait()

                # Check log file for errors
                if os.path.exists(log_path):
                    with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                        log_content = f.read()
                    if "error" in log_content.lower():
                        self.log_signal.emit(f"(error) {mq5}: compilation errors found. See {log_path}")
                    else:
                        self.log_signal.emit(f"(success) {mq5}: compiled OK.")
                        success_count += 1
                else:
                    self.log_signal.emit(f"(info) {mq5}: compiled (no log generated).")
                    success_count += 1

            except Exception as e:
                self.log_signal.emit(f"(error) {mq5}: {e}")

            # Small delay to avoid overwhelming the compiler
            time.sleep(0.5)

        self.finished_signal.emit(
            success_count == total,
            f"Compiled {success_count}/{total} EA(s).",
        )

    def stop(self):
        self.running = False
        self.terminate()
