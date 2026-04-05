import sys
import os
import datetime
import shutil
import webbrowser
import subprocess
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QListWidgetItem, QStackedWidget, QLabel, QLineEdit,
    QPushButton, QFileDialog, QPlainTextEdit, QGroupBox, QFormLayout,
    QSpinBox, QComboBox, QDateEdit, QProgressBar, QCheckBox,
    QTableWidgetItem, QHeaderView, QTableWidget, QAbstractItemView,
    QMessageBox, QStatusBar, QSplitter, QScrollArea, QSizePolicy,
)
from PyQt6.QtCore import QSize
from PyQt6.QtCore import Qt, QDate, QSettings, pyqtSignal, QThread, QSize
from PyQt6.QtGui import QFont, QColor, QIcon
from PyQt6.QtGui import QFont, QColor, QIcon

# Add core module path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core.compiler import CompilerThread
from core.version import get_version
import webbrowser
from core.backtester import BacktesterThread
from core.config_generator import generate_configs
from core.analyzer import parse_html_report, generate_html_report, EAResult


# ---- Reusable Widgets (ui/widgets.py inlined) ----


class LogWidget(QPlainTextEdit):
    def __init__(self):
        super().__init__()
        self.setReadOnly(True)
        font = QFont("Consolas", 10)
        self.setFont(font)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.max_lines = 2000

    def append_log(self, text: str):
        color = "#888888"
        if text.startswith("(success)"):
            color = "#27ae60"
            text = text[len("(success)"):]
        elif text.startswith("(error)"):
            color = "#e74c3c"
            text = text[len("(error)"):]
        elif text.startswith("(warning)"):
            color = "#e67e22"
            text = text[len("(warning)"):]
        elif text.startswith("(info)"):
            color = "#3498db"
            text = text[len("(info)"):]

        self.appendHtml(f'<span style="color:{color}">{text}</span>')

        # Limit lines
        doc = self.document()
        if doc.blockCount() > self.max_lines:
            cursor = self.textCursor()
            cursor.movePosition(cursor.MoveOperation.Start)
            for _ in range(doc.blockCount() - self.max_lines):
                cursor.select(cursor.SelectionType.BlockUnderCursor)
                cursor.removeSelectedText()
                cursor.deleteChar()


def _make_labeled(label_text: str, widget):
    row = QHBoxLayout()
    row.addWidget(QLabel(label_text), 0)
    row.addWidget(widget, 1)
    return row


class StepPage(QWidget):
    """Base class for step pages with log area and run button."""

    def sizeHint(self):
        return QSize(300, 200)

    def minimumSizeHint(self):
        return QSize(0, 0)

    def minimumSize(self):
        return QSize(0, 0)


class DynamicStackedWidget(QStackedWidget):
    """Only considers the current widget's size hint, and doesn't push min size up."""

    def minimumSizeHint(self):
        w = self.currentWidget()
        if w:
            return w.minimumSizeHint()
        return QSize(0, 0)

    def minimumSize(self):
        return QSize(0, 0)

    def sizeHint(self):
        w = self.currentWidget()
        if w:
            return w.sizeHint()
        return QSize(300, 200)


# ---- Step Pages ----


class SettingsPage(StepPage):
    def __init__(self, settings_obj: QSettings, parent=None):
        super().__init__(parent)
        self.settings = settings_obj
        self.init_ui()
        self._load_settings()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # MT5 Paths group
        paths_group = QGroupBox("MT5 Paths")
        paths_layout = QFormLayout()

        self.mt5_path = QLineEdit()
        self.mt5_path.setPlaceholderText("C:\\Program Files\\MetaTrader 5-1\\")
        mt5_browse = QPushButton("Browse")
        mt5_browse.clicked.connect(self._browse_mt5)
        mt5_row = QHBoxLayout()
        mt5_row.addWidget(self.mt5_path)
        mt5_row.addWidget(mt5_browse)
        paths_layout.addRow("MT5 Path:", mt5_row)

        self.ea_dir = QLineEdit()
        self.ea_dir.setPlaceholderText("./ea")
        ea_browse = QPushButton("Browse")
        ea_browse.clicked.connect(lambda: self._browse_dir(self.ea_dir))
        ea_row = QHBoxLayout()
        ea_row.addWidget(self.ea_dir)
        ea_row.addWidget(ea_browse)
        paths_layout.addRow("EA Directory:", ea_row)

        self.report_dir = QLineEdit()
        self.report_dir.setPlaceholderText("./reports")
        report_browse = QPushButton("Browse")
        report_browse.clicked.connect(lambda: self._browse_dir(self.report_dir))
        report_row = QHBoxLayout()
        report_row.addWidget(self.report_dir)
        report_row.addWidget(report_browse)
        paths_layout.addRow("Report Directory:", report_row)

        paths_group.setLayout(paths_layout)
        layout.addWidget(paths_group)

        # Backtest Parameters group
        params_group = QGroupBox("Backtest Parameters")
        params_layout = QFormLayout()

        self.symbol = QLineEdit("XAUUSDm")
        params_layout.addRow("Symbol:", self.symbol)

        self.period_combo = QComboBox()
        self.period_combo.addItems(["M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1"])
        self.period_combo.setCurrentText("H1")
        params_layout.addRow("Timeframe:", self.period_combo)

        from_date_layout = QHBoxLayout()
        self.from_date = QDateEdit()
        self.from_date.setCalendarPopup(True)
        self.from_date.setDate(QDate(2025, 1, 1))
        from_date_layout.addWidget(self.from_date)
        to_date_layout = QHBoxLayout()
        self.to_date = QDateEdit()
        self.to_date.setCalendarPopup(True)
        self.to_date.setDate(QDate(2026, 3, 1))
        to_date_layout.addWidget(self.to_date)

        params_layout.addRow("From Date:", from_date_layout)
        params_layout.addRow("To Date:", to_date_layout)

        self.deposit = QSpinBox()
        self.deposit.setRange(100, 1000000)
        self.deposit.setSingleStep(1000)
        self.deposit.setValue(10000)
        self.deposit.setSuffix(" USD")
        params_layout.addRow("Initial Deposit:", self.deposit)

        self.leverage = QSpinBox()
        self.leverage.setRange(1, 10000)
        self.leverage.setValue(500)
        params_layout.addRow("Leverage:", self.leverage)

        params_group.setLayout(params_layout)
        layout.addWidget(params_group)

        # Test paths button
        self.test_btn = QPushButton("Test Path Validity")
        self.test_btn.clicked.connect(self._test_paths)
        layout.addWidget(self.test_btn)

        # Version info
        from core.version import get_version
        version_label = QLabel(f"Version: {get_version()}")
        version_label.setStyleSheet("color: #888; font-size: 12px;")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version_label)

        changelog_btn = QPushButton("View Changelog")
        changelog_btn.clicked.connect(self._open_changelog)
        layout.addWidget(changelog_btn)

        layout.addStretch()

    def _load_settings(self):
        s = self.settings
        if s.value("mt5_path"):
            self.mt5_path.setText(str(s.value("mt5_path")))
        if s.value("ea_dir"):
            self.ea_dir.setText(str(s.value("ea_dir")))
        if s.value("report_dir"):
            self.report_dir.setText(str(s.value("report_dir")))
        if s.value("symbol"):
            self.symbol.setText(str(s.value("symbol")))
        if s.value("period"):
            self.period_combo.setCurrentText(str(s.value("period")))
        if s.value("deposit"):
            self.deposit.setValue(int(s.value("deposit")))
        if s.value("leverage"):
            self.leverage.setValue(int(s.value("leverage")))

    def save_settings(self):
        self.settings.setValue("mt5_path", self.mt5_path.text())
        self.settings.setValue("ea_dir", self.ea_dir.text())
        self.settings.setValue("report_dir", self.report_dir.text())
        self.settings.setValue("symbol", self.symbol.text())
        self.settings.setValue("period", self.period_combo.currentText())
        self.settings.setValue("deposit", self.deposit.value())
        self.settings.setValue("leverage", self.leverage.value())

    def _browse_mt5(self):
        d = QFileDialog.getExistingDirectory(self, "Select MT5 Installation Path")
        if d:
            self.mt5_path.setText(d)

    def _browse_dir(self, line_edit):
        d = QFileDialog.getExistingDirectory(self, "Select Directory")
        if d:
            line_edit.setText(d)

    def _test_paths(self):
        mt5 = self.mt5_path.text().strip()
        editor = os.path.join(mt5, "metaeditor64.exe")
        terminal = os.path.join(mt5, "terminal64.exe")
        ea = self.ea_dir.text().strip()
        msgs = []
        msgs.append(f"MT5 Path: {mt5}")
        msgs.append(f"Checking: {editor}")
        msgs.append("")
        if os.path.exists(editor):
            msgs.append("(OK) metaeditor64.exe found.")
        else:
            msgs.append("ERROR: metaeditor64.exe not found.")
            # List actual files for debugging
            try:
                if os.path.isdir(mt5):
                    files = [f for f in os.listdir(mt5) if f.lower().startswith("meta") or f.lower().startswith("terminal")]
                    msgs.append(f"Files in MT5 dir: {files}")
                else:
                    msgs.append(f"MT5 dir does not exist!")
            except Exception as e:
                msgs.append(f"Error listing dir: {e}")
        msgs.append(f"Checking: {terminal}")
        if os.path.exists(terminal):
            msgs.append("(OK) terminal64.exe found.")
        else:
            msgs.append("ERROR: terminal64.exe not found.")
        msgs.append("")
        if os.path.isdir(ea):
            msgs.append(f"(OK) EA directory exists.")
        else:
            msgs.append(f"WARNING: EA directory does not exist.")
            msgs.append(f"Checked: {ea}")
        QMessageBox.information(self, "Path Check", "\n".join(msgs))

    def _open_changelog(self):
        changelog_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "CHANGELOG.md")
        if os.path.exists(changelog_path):
            os.startfile(changelog_path)
        else:
            QMessageBox.information(self, "Changelog", "CHANGELOG.md not found.")


class CompilePage(StepPage):
    def __init__(self, settings_obj: QSettings, parent=None):
        super().__init__(parent)
        self.settings = settings_obj
        self.worker: CompilerThread | None = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # File list
        list_group = QGroupBox("EA Source Files")
        list_layout = QVBoxLayout()
        self.file_list = QListWidget()
        self.file_list.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh_files)
        list_layout.addWidget(self.file_list)
        list_layout.addWidget(refresh_btn)
        list_group.setLayout(list_layout)
        layout.addWidget(list_group)

        # Progress
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        # Run button
        self.run_btn = QPushButton("Compile All")
        self.run_btn.clicked.connect(self._start_compile)
        layout.addWidget(self.run_btn)

        # Log
        self.log = LogWidget()
        layout.addWidget(QLabel("Log:"))
        layout.addWidget(self.log)

    def refresh_files(self):
        ea_dir = self.settings.value("ea_dir", "./ea")
        self.file_list.clear()
        if not os.path.isdir(ea_dir):
            return
        for f in sorted(os.listdir(ea_dir)):
            if f.endswith(".mq5"):
                has_ex5 = os.path.exists(os.path.join(ea_dir, f.replace(".mq5", ".ex5")))
                status = "Compiled" if has_ex5 else "Not compiled"
                item = QListWidgetItem(f"{f}  ({status})")
                self.file_list.addItem(item)

    def _start_compile(self):
        if self.worker and self.worker.isRunning():
            self.log.append_log("(warning) Compilation already in progress...")
            return

        mt5_path = self.settings.value("mt5_path", "")
        ea_dir = self.settings.value("ea_dir", "./ea")

        metaeditor = os.path.join(mt5_path, "metaeditor64.exe")
        if not os.path.exists(metaeditor):
            self.log.append_log(f"(error) metaeditor64.exe not found at: {metaeditor}")
            QMessageBox.warning(self, "Error", "MT5 path is incorrect or missing. Please check Settings.")
            return
        if not os.path.isdir(ea_dir):
            self.log.append_log(f"(error) EA directory not found: {ea_dir}")
            return

        mq5_count = len([f for f in os.listdir(ea_dir) if f.endswith(".mq5")])
        if mq5_count == 0:
            self.log.append_log("(warning) No .mq5 files found.")
            return

        self.run_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setValue(0)
        self.log.append_log(f"(info) Starting compilation of {mq5_count} EA(s)...")

        self.worker = CompilerThread(metaeditor, ea_dir)
        self.worker.log_signal.connect(self.log.append_log)
        self.worker.progress_signal.connect(self._on_progress)
        self.worker.finished_signal.connect(self._on_finished)
        self.worker.start()

    def _on_progress(self, current, total):
        self.progress.setMaximum(total)
        self.progress.setValue(current)

    def _on_finished(self, success: bool, msg: str):
        self.run_btn.setEnabled(True)
        self.progress.setVisible(False)
        self.refresh_files()
        self.log.append_log(f"{'(success)' if success else '(warning)'} {msg}")


class ConfigPage(StepPage):
    def __init__(self, settings_obj: QSettings, parent=None):
        super().__init__(parent)
        self.settings = settings_obj
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        info_label = QLabel("Generate .ini configuration files for each compiled EA.")
        layout.addWidget(info_label)

        # File list
        self.file_list = QListWidget()
        self.file_list.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        layout.addWidget(QLabel("Available EAs (.ex5):"))
        layout.addWidget(self.file_list)

        # Run button
        self.run_btn = QPushButton("Generate Configs")
        self.run_btn.clicked.connect(self._generate)
        layout.addWidget(self.run_btn)

        self.status_label = QLabel("")
        layout.addWidget(self.status_label)

        layout.addStretch()

    def refresh_files(self):
        ea_dir = self.settings.value("ea_dir", "./ea")
        self.file_list.clear()
        if not os.path.isdir(ea_dir):
            return
        for f in sorted(os.listdir(ea_dir)):
            if f.endswith(".ex5"):
                self.file_list.addItem(f)

    def _generate(self):
        ea_dir = self.settings.value("ea_dir", "./ea")
        if not os.path.isdir(ea_dir):
            self.status_label.setText("(error) EA directory not found.")
            return

        report_dir = self.settings.value("report_dir", "./reports")
        names = generate_configs(
            ea_dir,
            report_dir,
            symbol=self.settings.value("symbol", "XAUUSDm"),
            period=self.settings.value("period", "H1"),
            from_date=self.settings.value("from_date", "2025.01.01"),
            to_date=self.settings.value("to_date", "2026.03.01"),
            deposit=int(self.settings.value("deposit", 10000)),
            leverage=int(self.settings.value("leverage", 500)),
        )

        if names:
            self.status_label.setText(f"(success) Generated {len(names)} config(s).")
            self.refresh_files()
        else:
            self.status_label.setText("(warning) No .ex5 files found. Compile first.")


class BacktestPage(StepPage):
    def __init__(self, settings_obj: QSettings, parent=None):
        super().__init__(parent)
        self.settings = settings_obj
        self.worker: BacktesterThread | None = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        self.file_list = QListWidget()
        self.file_list.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        layout.addWidget(QLabel("EAs to Backtest (.ex5):"))
        layout.addWidget(self.file_list)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        self.run_btn = QPushButton("Start Batch Backtest")
        self.run_btn.clicked.connect(self._start_backtest)
        layout.addWidget(self.run_btn)

        layout.addWidget(QLabel("Log:"))
        self.log = LogWidget()
        layout.addWidget(self.log)

    def refresh_files(self):
        ea_dir = self.settings.value("ea_dir", "./ea")
        self.file_list.clear()
        if not os.path.isdir(ea_dir):
            return
        for f in sorted(os.listdir(ea_dir)):
            if f.endswith(".ex5"):
                ini_exists = os.path.exists(os.path.join(ea_dir, f.replace(".ex5", ".ini")))
                status = "Config OK" if ini_exists else "Missing .ini"
                self.file_list.addItem(f"  {f}  ({status})")

    def _start_backtest(self):
        if self.worker and self.worker.isRunning():
            self.log.append_log("(warning) Backtest already in progress...")
            return

        mt5_path = self.settings.value("mt5_path", "")
        ea_dir = self.settings.value("ea_dir", "./ea")
        report_dir = self.settings.value("report_dir", "./reports")

        terminal = os.path.join(mt5_path, "terminal64.exe")
        if not os.path.exists(terminal):
            self.log.append_log(f"(error) terminal64.exe not found at: {terminal}")
            QMessageBox.warning(self, "Error", "MT5 path is incorrect or missing.")
            return
        if not os.path.isdir(ea_dir):
            self.log.append_log(f"(error) EA directory not found: {ea_dir}")
            return

        ex5_count = len([f for f in os.listdir(ea_dir) if f.endswith(".ex5")])
        if ex5_count == 0:
            self.log.append_log("(warning) No .ex5 files found.")
            return

        self.run_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setValue(0)
        self.log.append_log(f"(info) Starting batch backtest of {ex5_count} EA(s)...")

        self.worker = BacktesterThread(terminal, ea_dir, report_dir)
        self.worker.log_signal.connect(self.log.append_log)
        self.worker.progress_signal.connect(self._on_progress)
        self.worker.finished_signal.connect(self._on_finished)
        self.worker.start()

    def _on_progress(self, current, total):
        self.progress.setMaximum(total)
        self.progress.setValue(current)

    def _on_finished(self, success: bool, msg: str):
        self.run_btn.setEnabled(True)
        self.progress.setVisible(False)
        self.log.append_log(f"{'(success)' if success else '(warning)'} {msg}")


class AutoPipelineWidget(StepPage):
    """One-click pipeline: Compile → Config → Backtest → Analysis."""

    pipeline_done = pyqtSignal(bool, str)  # success, message

    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.mw = main_window
        self.settings = main_window.settings
        self._running = False
        self._compile_done = False
        self._config_done = False
        self._backtest_done = False
        self._analysis_done = False
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        info = QLabel("一键执行全流程：编译 → 配置 → 回测 → 分析\n\n每步完成后自动进入下一步，失败即停止。")
        info.setStyleSheet("font-size: 14px; padding: 12px;")
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        # Step indicator
        self.step_label = QLabel("就绪")
        self.step_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.step_label.setStyleSheet("font-size: 13px; color: #555; padding: 8px;")
        layout.addWidget(self.step_label)

        # Log
        layout.addWidget(QLabel("运行日志："))
        self.log = LogWidget()
        layout.addWidget(self.log)

        self.layout().addStretch()

        # Buttons row
        btn_row = QHBoxLayout()
        self.run_btn = QPushButton("Start Pipeline")
        self.run_btn.clicked.connect(self._start_pipeline)
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._stop_pipeline)
        btn_row.addWidget(self.run_btn)
        btn_row.addWidget(self.stop_btn)
        layout.addLayout(btn_row)

    def _start_pipeline(self):
        self.save_settings()
        self._running = True
        self._compile_done = False
        self._config_done = False
        self._backtest_done = False
        self._analysis_done = False

        self.run_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress.setVisible(True)
        self.progress.setRange(0, 4)
        self.progress.setValue(0)

        self.log.append_log("(info) ===== Pipeline started =====")
        self._run_compile()

    def _stop_pipeline(self):
        self._running = False
        if self.mw.compile_page.worker and self.mw.compile_page.worker.isRunning():
            self.mw.compile_page.worker.stop()
            self.mw.compile_page.worker.terminate()
        if self.mw.backtest_page.worker and self.mw.backtest_page.worker.isRunning():
            self.mw.backtest_page.worker.terminate()
        self.run_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress.setVisible(False)
        self.log.append_log("(warning) Pipeline stopped by user.")
        self.step_label.setText("已停止")

    def save_settings(self):
        self.mw.settings_page.save_settings()
        self.mw.settings.setValue("from_date", self.mw.settings_page.from_date.date().toString("yyyy.MM.dd"))
        self.mw.settings.setValue("to_date", self.mw.settings_page.to_date.date().toString("yyyy.MM.dd"))

    # ---- Step 1: Compile ----
    def _run_compile(self):
        self.step_label.setText("Step 1/4: 编译 EA")
        self.log.append_log("(info) [1/4] Starting compilation...")
        self.progress.setValue(0)

        mt5_path = self.settings.value("mt5_path", "")
        ea_dir = self.settings.value("ea_dir", "./ea")
        metaeditor = os.path.join(mt5_path, "metaeditor64.exe")
        if not os.path.exists(metaeditor):
            self.log.append_log(f"(error) metaeditor64.exe not found")
            self._pipeline_fail("metaeditor64.exe not found. Check Settings.")
            return
        if not os.path.isdir(ea_dir):
            self.log.append_log(f"(error) EA directory not found")
            self._pipeline_fail("EA directory not found. Check Settings.")
            return
        mq5_count = len([f for f in os.listdir(ea_dir) if f.endswith(".mq5")])
        if mq5_count == 0:
            self.log.append_log(f"(error) No .mq5 files found")
            self._pipeline_fail("No .mq5 files found.")
            return

        self.mw.stack.setCurrentIndex(1)  # switch to compile page
        self.mw.compile_page.progress.setVisible(True)
        self.mw.compile_page.run_btn.setEnabled(False)
        worker = CompilerThread(metaeditor, ea_dir)
        worker.log_signal.connect(self.log.append_log)
        worker.finished_signal.connect(self._on_compile_done)
        self.mw.compile_page.worker = worker
        worker.start()

    def _on_compile_done(self, success, msg):
        if not self._running:
            return
        self.mw.compile_page.progress.setVisible(False)
        self.mw.compile_page.progress.setValue(0)
        self.mw.compile_page.run_btn.setEnabled(True)
        self.log.append_log(f"{'(success)' if success else '(error)'} Compile: {msg}")
        if not success:
            self._pipeline_fail(f"Compile failed: {msg}")
            return
        self._compile_done = True
        self.progress.setValue(1)
        self._run_config()

    # ---- Step 2: Config ----
    def _run_config(self):
        self.step_label.setText("Step 2/4: 生成配置")
        self.log.append_log("(info) [2/4] Generating configs...")
        self.mw.stack.setCurrentIndex(2)

        ea_dir = self.settings.value("ea_dir", "./ea")
        report_dir = self.settings.value("report_dir", "./reports")
        names = generate_configs(
            ea_dir,
            report_dir,
            symbol=self.settings.value("symbol", "XAUUSDm"),
            period=self.settings.value("period", "H1"),
            from_date=self.settings.value("from_date", "2025.01.01"),
            to_date=self.settings.value("to_date", "2026.03.01"),
            deposit=int(self.settings.value("deposit", 10000)),
            leverage=int(self.settings.value("leverage", 500)),
        )
        if not names:
            self.log.append_log("(error) Config: no .ex5 files found")
            self._pipeline_fail("Config failed: no .ex5 files. Compile first.")
            return
        self.log.append_log(f"(success) Config: generated {len(names)} config(s)")
        self._config_done = True
        self.progress.setValue(2)
        self.progress.setRange(0, 0)  # indeterminate during backtest
        self._run_backtest()

    # ---- Step 3: Backtest ----
    def _run_backtest(self):
        self.step_label.setText("Step 3/4: 批量回测")
        self.log.append_log("(info) [3/4] Starting backtest...")
        self.mw.stack.setCurrentIndex(3)

        mt5_path = self.settings.value("mt5_path", "")
        ea_dir = self.settings.value("ea_dir", "./ea")
        report_dir = self.settings.value("report_dir", "./reports")
        terminal = os.path.join(mt5_path, "terminal64.exe")
        if not os.path.exists(terminal):
            self.log.append_log(f"(error) terminal64.exe not found")
            self._pipeline_fail("terminal64.exe not found.")
            return

        ex5_count = len([f for f in os.listdir(ea_dir) if f.endswith(".ex5")])
        if ex5_count == 0:
            self.log.append_log("(error) Backtest: no .ex5 files")
            self._pipeline_fail("Backtest failed: no .ex5 files.")
            return

        self.mw.backtest_page.run_btn.setEnabled(False)
        self.mw.backtest_page.progress.setVisible(True)
        self.mw.backtest_page.progress.setRange(0, 0)
        worker = BacktesterThread(terminal, ea_dir, report_dir)
        worker.log_signal.connect(self.log.append_log)
        worker.progress_signal.connect(self._on_backtest_progress)
        worker.finished_signal.connect(self._on_backtest_done)
        self.mw.backtest_page.worker = worker
        worker.start()

    def _on_backtest_progress(self, current, total):
        self.mw.backtest_page.progress.setMaximum(total)
        self.mw.backtest_page.progress.setValue(current)
        self.progress.setMaximum(total)
        self.progress.setValue(current)

    def _on_backtest_done(self, success, msg):
        if not self._running:
            return
        self.mw.backtest_page.run_btn.setEnabled(True)
        self.mw.backtest_page.progress.setVisible(False)
        self.mw.backtest_page.progress.setRange(0, 100)
        self.mw.backtest_page.progress.setValue(0)
        self.log.append_log(f"{'(success)' if success else '(error)'} Backtest: {msg}")
        if not success:
            self._pipeline_fail(f"Backtest failed: {msg}")
            return
        self._backtest_done = True
        self.progress.setRange(0, 4)
        self.progress.setValue(3)
        # Switch backtab page to analysis
        self._run_analysis()

    # ---- Step 4: Analysis ----
    def _run_analysis(self):
        self.step_label.setText("Step 4/4: 分析报告")
        self.log.append_log("(info) [4/4] Analyzing results...")
        self.mw.stack.setCurrentIndex(4)

        report_dir = self.settings.value("report_dir", "./reports")
        import glob as glob_mod
        htm_files = glob_mod.glob(os.path.join(report_dir, "*.htm"))
        if not htm_files:
            self.log.append_log("(warning) Analysis: no .htm reports found")
            self._pipeline_fail("No .htm reports found for analysis.")
            return
        results = [parse_html_report(f) for f in htm_files]
        results.sort(key=lambda x: x.total_profit, reverse=True)
        self.mw.analysis_page.table.setRowCount(len(results))
        for i, r in enumerate(results):
            self.mw.analysis_page.table.setItem(i, 0, QTableWidgetItem(r.name))
            self.mw.analysis_page.table.setItem(i, 1, QTableWidgetItem(f"{r.total_profit:,.2f}"))
            self.mw.analysis_page.table.setItem(i, 2, QTableWidgetItem(f"{r.max_drawdown:.2f}"))
            self.mw.analysis_page.table.setItem(i, 3, QTableWidgetItem(f"{r.profit_factor:.2f}"))
            self.mw.analysis_page.table.setItem(i, 4, QTableWidgetItem(str(r.total_trades)))
            self.mw.analysis_page.table.setItem(i, 5, QTableWidgetItem(f"{r.win_rate:.2f}"))

            profit_item = self.mw.analysis_page.table.item(i, 1)
            if r.total_profit >= 0:
                profit_item.setForeground(QColor("#27ae60"))
            else:
                profit_item.setForeground(QColor("#e74c3c"))

        if results and results[0].total_profit > 0:
            for col in range(6):
                item = self.mw.analysis_page.table.item(0, col)
                if item:
                    item.setBackground(QColor("#e8f5e9"))

        output = os.path.join(report_dir, "ea_ranking_report.html")
        if results:
            generate_html_report(results, output)
        self.log.append_log(f"(success) Analysis: {len(results)} report(s)")
        self._analysis_done = True
        self.progress.setValue(4)
        self._pipeline_success(f"Pipeline complete: {len(results)} strategies analyzed.")

    def _pipeline_fail(self, msg):
        self._running = False
        self.run_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress.setVisible(False)
        self.step_label.setText(f"失败: {msg}")
        self.log.append_log(f"(error) Pipeline failed: {msg}")

    def _pipeline_success(self, msg):
        self._running = False
        self.run_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress.setVisible(False)
        self.step_label.setText(f"完成: {msg}")
        self.log.append_log(f"(success) {msg}")
        QMessageBox.information(self, "Pipeline Complete", msg)


class AnalysisPage(StepPage):
    def __init__(self, settings_obj: QSettings, parent=None):
        super().__init__(parent)
        self.settings = settings_obj
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(9, 9, 9, 9)
        layout.setSpacing(6)

        self.setMinimumSize(0, 0)
        self.setSizePolicy(
            QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum
        )

        top_row = QHBoxLayout()
        self.analyze_btn = QPushButton("Analyze Results")
        self.analyze_btn.clicked.connect(self._analyze)
        top_row.addWidget(self.analyze_btn)

        self.open_report_btn = QPushButton("Open HTML Report")
        self.open_report_btn.clicked.connect(self._open_report)
        top_row.addWidget(self.open_report_btn)

        self.open_dir_btn = QPushButton("Open Report Directory")
        self.open_dir_btn.clicked.connect(self._open_dir)
        top_row.addWidget(self.open_dir_btn)

        layout.addLayout(top_row)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Expanding)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["Strategy", "Net Profit ($)", "Max DD (%)", "Profit Factor", "Trades", "Win Rate (%)"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Expanding)
        self.table.setMinimumSize(0, 0)
        self.table.setSortingEnabled(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(
            """
            QTableWidget {
                gridline-color: #ccc;
                font-size: 12px;
            }
            QTableWidget::item {
                padding: 6px;
                color: #1a1a1a;
            }
            QHeaderView::section {
                background: #2c3e50;
                color: white;
                font-weight: bold;
                font-size: 12px;
                padding: 6px;
                border: 1px solid #34495e;
            }
            QTableWidget::item:selected {
                background: #3498db;
                color: white;
                font-weight: bold;
            }
            QTableWidget::item:nth-child(even) {
                background: #f7f7f7;
            }
            """
        )

        scroll.setWidget(self.table)
        layout.addWidget(scroll)

        self.status_label = QLabel("")
        layout.addWidget(self.status_label)

    def _analyze(self):
        report_dir = self.settings.value("report_dir", "./reports")
        import glob as glob_mod

        htm_files = glob_mod.glob(os.path.join(report_dir, "*.htm"))
        if not htm_files:
            self.status_label.setText("(warning) No .htm reports found in reports/")
            self.table.setRowCount(0)
            return

        results = [parse_html_report(f) for f in htm_files]
        results.sort(key=lambda x: x.total_profit, reverse=True)

        self.table.setRowCount(len(results))
        for i, r in enumerate(results):
            self.table.setItem(i, 0, QTableWidgetItem(r.name))
            self.table.setItem(i, 1, QTableWidgetItem(f"{r.total_profit:,.2f}"))
            self.table.setItem(i, 2, QTableWidgetItem(f"{r.max_drawdown:.2f}"))
            self.table.setItem(i, 3, QTableWidgetItem(f"{r.profit_factor:.2f}"))
            self.table.setItem(i, 4, QTableWidgetItem(str(r.total_trades)))
            self.table.setItem(i, 5, QTableWidgetItem(f"{r.win_rate:.2f}"))

            # Color profit
            profit_item = self.table.item(i, 1)
            if r.total_profit >= 0:
                profit_item.setForeground(QColor("#27ae60"))
            else:
                profit_item.setForeground(QColor("#e74c3c"))

        # Highlight top row
        if results and results[0].total_profit > 0:
            for col in range(6):
                self.table.item(0, col).setBackground(QColor("#e8f5e9"))

        # Also regenerate HTML report in report_dir
        report_dir = self.settings.value("report_dir", "./reports")
        output = os.path.join(report_dir, "ea_ranking_report.html")
        if results:
            generate_html_report(results, output)
            self.status_label.setText(f"(success) Analyzed {len(results)} report(s). Report saved to {report_dir}/")
        else:
            self.status_label.setText("(warning) Parsed reports but found no data.")

    def _open_report(self):
        report_dir = self.settings.value("report_dir", "./reports")
        report_path = os.path.join(report_dir, "ea_ranking_report.html")
        if os.path.exists(report_path):
            webbrowser.open(report_path)
        else:
            QMessageBox.warning(self, "Not Found", "No ranking report found. Run analysis first.")

    def _open_dir(self):
        report_dir = self.settings.value("report_dir", "./reports")
        if os.path.isdir(report_dir):
            os.startfile(report_dir)
        else:
            QMessageBox.warning(self, "Not Found", "Report directory does not exist.")


class CleanupPage(StepPage):
    def __init__(self, settings_obj: QSettings, parent=None):
        super().__init__(parent)
        self.settings = settings_obj
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        group = QGroupBox("Cleanup Options")
        group_layout = QVBoxLayout()

        self.ex5_check = QCheckBox("Compiled files (.ex5)")
        self.log_check = QCheckBox("Compilation logs (.log)")
        self.ini_check = QCheckBox("Config files (.ini)")
        self.htm_check = QCheckBox("Backtest reports (.htm)")
        self.all_check = QCheckBox("All of the above")
        self.all_check.stateChanged.connect(self._toggle_all)

        group_layout.addWidget(self.ex5_check)
        group_layout.addWidget(self.log_check)
        group_layout.addWidget(self.ini_check)
        group_layout.addWidget(self.htm_check)
        group_layout.addWidget(self.all_check)
        group.setLayout(group_layout)
        layout.addWidget(group)

        self.run_btn = QPushButton("Run Cleanup")
        self.run_btn.clicked.connect(self._cleanup)
        layout.addWidget(self.run_btn)

        self.status_label = QLabel("")
        layout.addWidget(self.status_label)
        layout.addStretch()

    def _toggle_all(self, state):
        checked = state == Qt.CheckState.Checked.value
        self.ex5_check.setChecked(checked)
        self.log_check.setChecked(checked)
        self.ini_check.setChecked(checked)
        self.htm_check.setChecked(checked)

    def _cleanup(self):
        ea_dir = self.settings.value("ea_dir", "./ea")
        report_dir = self.settings.value("report_dir", "./reports")
        patterns = []
        if self.ex5_check.isChecked():
            patterns.append((ea_dir, "*.ex5"))
        if self.log_check.isChecked():
            patterns.append((ea_dir, "*.log"))
        if self.ini_check.isChecked():
            patterns.append((ea_dir, "*.ini"))
        if self.htm_check.isChecked():
            patterns.append((report_dir, "*.htm"))

        if not patterns:
            self.status_label.setText("(warning) Nothing selected.")
            return

        import glob as glob_mod
        total_deleted = 0
        for directory, pattern in patterns:
            for f in glob_mod.glob(os.path.join(directory, pattern)):
                try:
                    os.remove(f)
                    total_deleted += 1
                except Exception:
                    pass

        self.status_label.setText(f"(success) Deleted {total_deleted} file(s).")


# ---- Main Window ----


class MainWindow(QMainWindow):
    STEP_NAMES = [
        "Settings",
        "Compile",
        "Config",
        "Backtest",
        "Analysis",
        "Cleanup",
        "Auto Mode",
    ]

    def __init__(self):
        super().__init__()
        self.settings = QSettings("MT5EATester", "MainWindow")
        self._version = get_version()
        self.setWindowTitle(f"MT5 EA Batch Tester v{self._version}")
        self.resize(900, 650)

        self._build_ui()
        self._restore_geometry()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Splitter for resizable sidebar/content
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left sidebar
        self.sidebar = QListWidget()
        self.sidebar.setMinimumWidth(80)
        self.sidebar.setSizePolicy(
            QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding
        )
        self.sidebar.setSpacing(4)
        icon_list = ["⚙", "🔨", "📋", "🚀", "📊", "🧹", "▶"]
        for icon, name in zip(icon_list, self.STEP_NAMES):
            item = QListWidgetItem(f"{icon}  {name}")
            item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            font = QFont("Microsoft YaHei", 11)
            item.setFont(font)
            self.sidebar.addItem(item)
        self.sidebar.currentRowChanged.connect(self._on_step_changed)
        splitter.addWidget(self.sidebar)

        # Right stacked widget
        self.stack = DynamicStackedWidget()
        self.settings_page = SettingsPage(self.settings)
        self.compile_page = CompilePage(self.settings)
        self.config_page = ConfigPage(self.settings)
        self.backtest_page = BacktestPage(self.settings)
        self.analysis_page = AnalysisPage(self.settings)
        self.cleanup_page = CleanupPage(self.settings)
        self.auto_page = AutoPipelineWidget(self)

        self.stack.addWidget(self.settings_page)
        self.stack.addWidget(self.compile_page)
        self.stack.addWidget(self.config_page)
        self.stack.addWidget(self.backtest_page)
        self.stack.addWidget(self.analysis_page)
        self.stack.addWidget(self.cleanup_page)
        self.stack.addWidget(self.auto_page)
        splitter.addWidget(self.stack)

        # Initial split ratio ~160:740 for 900px width
        splitter.setSizes([160, 740])
        main_layout.addWidget(splitter)

        # Set initial selection after stack is created
        self.stack.setCurrentIndex(0)

        # Status bar
        self.statusBar().showMessage("Ready")

    def _on_step_changed(self, index):
        if not hasattr(self, "stack"):
            return
        self.stack.setCurrentIndex(index)
        self.statusBar().showMessage(f"Step: {self.STEP_NAMES[index]}")

        # Refresh file lists on page switch
        if index == 1:
            self.compile_page.refresh_files()
        elif index == 2:
            self.config_page.refresh_files()
        elif index == 3:
            self.backtest_page.refresh_files()

    def _restore_geometry(self):
        if self.settings.contains("geometry"):
            self.restoreGeometry(self.settings.value("geometry"))

    def closeEvent(self, event):
        self.settings.setValue("geometry", self.saveGeometry())
        # Save settings
        self.settings_page.save_settings()
        self.settings.setValue("from_date", self.settings_page.from_date.date().toString("yyyy.MM.dd"))
        self.settings.setValue("to_date", self.settings_page.to_date.date().toString("yyyy.MM.dd"))
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setFont(QFont("Microsoft YaHei", 10))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
