"""Main window for XHS Agent GUI application."""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

import customtkinter as ctk

from ..core.config_manager import ConfigManager
from ..core.history_manager import HistoryManager
from ..core.task_manager import TaskManager
from .settings_dialog import SettingsDialog
from .history_panel import HistoryPanel
from .result_viewer import ResultViewer


class MainWindow(ctk.CTk):
    """Main application window."""

    def __init__(self):
        """Initialize main window."""
        super().__init__()

        # Window configuration
        self.title("小红书流量分析助手")
        self.geometry("1000x800")

        # Set theme
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

        # Initialize managers
        self.config_manager = ConfigManager()
        self.history_manager = HistoryManager()
        self.task_manager = TaskManager(progress_callback=self._on_progress_update)

        # State
        self.current_result: dict[str, Any] | None = None
        self.is_running = False

        # Create UI
        self._create_widgets()

        # Check configuration
        self.after(100, self._check_initial_config)

    def _create_widgets(self):
        """Create all UI widgets."""
        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        # Header frame
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")

        title_label = ctk.CTkLabel(
            header_frame, text="小红书流量分析助手", font=ctk.CTkFont(size=24, weight="bold")
        )
        title_label.pack(side="left")

        settings_btn = ctk.CTkButton(
            header_frame, text="设置", width=80, command=self._open_settings
        )
        settings_btn.pack(side="right", padx=5)

        history_btn = ctk.CTkButton(
            header_frame, text="历史记录", width=100, command=self._open_history
        )
        history_btn.pack(side="right")

        # Query input frame
        input_frame = ctk.CTkFrame(self)
        input_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")

        query_label = ctk.CTkLabel(input_frame, text="输入你的问题：")
        query_label.pack(anchor="w", padx=10, pady=(10, 5))

        self.query_textbox = ctk.CTkTextbox(input_frame, height=80)
        self.query_textbox.pack(fill="x", padx=10, pady=(0, 10))
        self.query_textbox.insert("1.0", "最近有什么美食热点")

        # Options frame
        options_frame = ctk.CTkFrame(self)
        options_frame.grid(row=2, column=0, padx=20, pady=10, sticky="ew")

        # Checkboxes
        checkbox_frame = ctk.CTkFrame(options_frame, fg_color="transparent")
        checkbox_frame.pack(fill="x", padx=10, pady=10)

        self.rewrite_var = ctk.BooleanVar(value=True)
        rewrite_cb = ctk.CTkCheckBox(checkbox_frame, text="生成仿写", variable=self.rewrite_var)
        rewrite_cb.pack(side="left", padx=10)

        self.cover_var = ctk.BooleanVar(value=True)
        cover_cb = ctk.CTkCheckBox(checkbox_frame, text="生成封面", variable=self.cover_var)
        cover_cb.pack(side="left", padx=10)

        self.cover_image_var = ctk.BooleanVar(value=False)
        cover_image_cb = ctk.CTkCheckBox(
            checkbox_frame, text="生成封面图片", variable=self.cover_image_var
        )
        cover_image_cb.pack(side="left", padx=10)

        # Mode selection
        mode_frame = ctk.CTkFrame(options_frame, fg_color="transparent")
        mode_frame.pack(fill="x", padx=10, pady=(0, 10))

        mode_label = ctk.CTkLabel(mode_frame, text="分析模式：")
        mode_label.pack(side="left", padx=10)

        self.mode_var = ctk.StringVar(value="hot")
        mode_menu = ctk.CTkOptionMenu(
            mode_frame,
            variable=self.mode_var,
            values=["热点分析", "账号雷达"],
            command=self._on_mode_change,
        )
        mode_menu.pack(side="left")

        # Action buttons
        button_frame = ctk.CTkFrame(options_frame, fg_color="transparent")
        button_frame.pack(fill="x", padx=10, pady=(0, 10))

        self.start_btn = ctk.CTkButton(
            button_frame, text="开始分析", width=120, command=self._start_analysis
        )
        self.start_btn.pack(side="left", padx=10)

        self.cancel_btn = ctk.CTkButton(
            button_frame,
            text="取消",
            width=80,
            state="disabled",
            fg_color="gray",
            command=self._cancel_analysis,
        )
        self.cancel_btn.pack(side="left")

        batch_btn = ctk.CTkButton(
            button_frame, text="批量处理", width=100, command=self._open_batch_dialog
        )
        batch_btn.pack(side="left", padx=10)

        # Progress frame
        progress_frame = ctk.CTkFrame(self)
        progress_frame.grid(row=3, column=0, padx=20, pady=10, sticky="ew")

        self.progress_bar = ctk.CTkProgressBar(progress_frame)
        self.progress_bar.pack(fill="x", padx=10, pady=(10, 5))
        self.progress_bar.set(0)

        self.progress_label = ctk.CTkLabel(progress_frame, text="就绪")
        self.progress_label.pack(anchor="w", padx=10, pady=(0, 10))

        # Result viewer
        self.result_viewer = ResultViewer(self)
        self.result_viewer.grid(row=4, column=0, padx=20, pady=(10, 20), sticky="nsew")

    def _check_initial_config(self):
        """Check if configuration is valid on startup."""
        is_valid, error_msg = self.config_manager.validate_config()
        if not is_valid:
            response = ctk.CTkInputDialog(
                text=f"配置不完整：{error_msg}\n\n是否现在配置？",
                title="配置检查",
            )
            if response.get_input():
                self._open_settings()

    def _open_settings(self):
        """Open settings dialog."""
        dialog = SettingsDialog(self, self.config_manager)
        dialog.grab_set()
        self.wait_window(dialog)

    def _open_history(self):
        """Open history panel."""
        dialog = HistoryPanel(self, self.history_manager, self._load_history_record)
        dialog.grab_set()

    def _open_batch_dialog(self):
        """Open batch processing dialog."""
        # TODO: Implement batch dialog
        ctk.CTkMessagebox(title="提示", message="批量处理功能开发中...")

    def _on_mode_change(self, mode: str):
        """Handle mode change.

        Args:
            mode: Selected mode
        """
        if mode == "账号雷达":
            self.mode_var.set("radar")
            # Disable rewrite/cover for radar mode
            self.rewrite_var.set(False)
            self.cover_var.set(False)
            self.cover_image_var.set(False)
        else:
            self.mode_var.set("hot")

    def _start_analysis(self):
        """Start analysis task."""
        # Get query
        query = self.query_textbox.get("1.0", "end-1c").strip()
        if not query:
            ctk.CTkMessagebox(title="错误", message="请输入查询内容")
            return

        # Validate configuration
        is_valid, error_msg = self.config_manager.validate_config()
        if not is_valid:
            ctk.CTkMessagebox(title="配置错误", message=error_msg)
            self._open_settings()
            return

        # Prepare options
        mode = self.mode_var.get()
        options = {
            "analysis_mode": mode,
            "rewrite": self.rewrite_var.get() and mode != "radar",
            "cover": self.cover_var.get() and mode != "radar",
            "cover_image": self.cover_image_var.get() and mode != "radar",
            "gemini_model": self.config_manager.get_setting("gemini_model"),
            "minimax_model": self.config_manager.get_setting("minimax_model"),
            "minimax_base_url": self.config_manager.get_setting("minimax_base_url"),
            "analysis_temperature": self.config_manager.get_setting("analysis_temperature"),
            "rewrite_temperature": self.config_manager.get_setting("rewrite_temperature"),
            "cover_temperature": self.config_manager.get_setting("cover_temperature"),
            "max_results": self.config_manager.get_setting("max_results"),
            "max_queries": self.config_manager.get_setting("max_queries"),
            "max_sources": self.config_manager.get_setting("max_sources"),
            "days": self.config_manager.get_setting("days"),
            "lang": self.config_manager.get_setting("lang"),
            "region": self.config_manager.get_setting("region"),
            "verbose": False,
        }

        # Get environment variables
        env_vars = self.config_manager.export_for_env()

        # Update UI state
        self.is_running = True
        self.start_btn.configure(state="disabled")
        self.cancel_btn.configure(state="normal", fg_color=["#3B8ED0", "#1F6AA5"])
        self.progress_bar.set(0)
        self.progress_label.configure(text="准备中...")

        # Run in background thread
        def worker():
            try:
                result = self.task_manager.run_analysis(query, options, env_vars)
                self.after(0, lambda: self._on_analysis_complete(result))
            except Exception as e:
                self.after(0, lambda: self._on_analysis_error(str(e)))

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    def _cancel_analysis(self):
        """Cancel running analysis."""
        self.task_manager.cancel_task()
        self.progress_label.configure(text="正在取消...")

    def _on_progress_update(self, progress: dict[str, Any]):
        """Handle progress update.

        Args:
            progress: Progress dictionary
        """
        current = progress.get("current", 0)
        total = progress.get("total", 1)
        message = progress.get("message", "")

        progress_value = current / total if total > 0 else 0
        self.progress_bar.set(progress_value)
        self.progress_label.configure(text=message)

    def _on_analysis_complete(self, result: dict[str, Any]):
        """Handle analysis completion.

        Args:
            result: Analysis result
        """
        self.is_running = False
        self.start_btn.configure(state="normal")
        self.cancel_btn.configure(state="disabled", fg_color="gray")
        self.progress_bar.set(1.0)
        self.progress_label.configure(text="完成！")

        # Save to history
        try:
            self.history_manager.save_record(
                query=result.get("query", ""),
                result=result,
                metadata={"timestamp": str(Path.cwd())},
            )
        except Exception as e:
            print(f"Failed to save history: {e}")

        # Display result
        self.current_result = result
        self.result_viewer.display_result(result)

    def _on_analysis_error(self, error: str):
        """Handle analysis error.

        Args:
            error: Error message
        """
        self.is_running = False
        self.start_btn.configure(state="normal")
        self.cancel_btn.configure(state="disabled", fg_color="gray")
        self.progress_bar.set(0)
        self.progress_label.configure(text="错误")

        ctk.CTkMessagebox(title="分析失败", message=f"分析过程中出现错误：\n\n{error}")

    def _load_history_record(self, record: dict[str, Any]):
        """Load and display history record.

        Args:
            record: History record
        """
        # Load full record
        full_record = self.history_manager.get_record(record["id"])
        if not full_record:
            return

        # Display result
        result = full_record["result"]
        self.current_result = result
        self.result_viewer.display_result(result)

        # Update query textbox
        self.query_textbox.delete("1.0", "end")
        self.query_textbox.insert("1.0", full_record["query"])

        # Update mode
        mode = result.get("mode", "hot")
        if mode == "radar":
            self.mode_var.set("radar")
        else:
            self.mode_var.set("hot")

    def on_closing(self):
        """Handle window closing."""
        self.history_manager.close()
        self.destroy()


def main():
    """Main entry point."""
    app = MainWindow()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()


if __name__ == "__main__":
    main()
