"""Main window for XHS Agent GUI application - Refined Sunset Theme."""

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
    """Main application window with refined sunset theme."""

    def __init__(self):
        """Initialize main window."""
        super().__init__()

        # Window configuration
        self.title("小红书流量分析助手")
        self.geometry("1200x800")

        # Set theme - Sunset Mood (Refined)
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

        # Custom color scheme - Refined Sunset Mood
        self.colors = {
            "primary": "#d98e82",      # Terracotta/Dark Peach - 主按钮色
            "primary_hover": "#c57b70", # Darker on hover
            "secondary": "#f4dcd6",    # Light Peach - 面板背景
            "accent": "#2C2C2C",       # Deep Charcoal - 深色强调
            "background": "#dbe4ef",   # Light Blue Grey - 窗口背景
            "tab_bg": "#eec9b9",       # Tab background - 标签页背景
            "input_bg": "#ffffff",     # White - 输入框背景
            "text_dark": "#1f2937",    # Dark text
            "text_light": "#6b7280",   # Light grey text
            "progress_bg": "#e5e7eb",  # Progress bar background
        }

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
        """Create all UI widgets with left-right layout."""
        # Set window background color
        self.configure(fg_color=self.colors["background"])

        # Configure grid for left-right layout
        self.grid_columnconfigure(0, weight=1, minsize=400)  # Left panel
        self.grid_columnconfigure(1, weight=2)  # Right panel (wider)
        self.grid_rowconfigure(1, weight=1)

        # ===== HEADER (spans both columns) =====
        self._create_header()

        # ===== LEFT PANEL =====
        self._create_left_panel()

        # ===== RIGHT PANEL =====
        self._create_right_panel()

    def _create_header(self):
        """Create header with title and buttons."""
        header_frame = ctk.CTkFrame(self, fg_color="transparent", height=60)
        header_frame.grid(row=0, column=0, columnspan=2, padx=20, pady=(20, 10), sticky="ew")
        header_frame.grid_propagate(False)

        title_label = ctk.CTkLabel(
            header_frame,
            text="📊 小红书流量分析助手",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=self.colors["text_dark"]
        )
        title_label.pack(side="left", padx=10)

        # Header buttons
        button_container = ctk.CTkFrame(header_frame, fg_color="transparent")
        button_container.pack(side="right")

        history_btn = ctk.CTkButton(
            button_container,
            text="📜 历史记录",
            width=110,
            height=36,
            corner_radius=25,
            command=self._open_history,
            fg_color=self.colors["primary"],
            hover_color=self.colors["primary_hover"],
            text_color="white",
            font=ctk.CTkFont(size=13, weight="bold")
        )
        history_btn.pack(side="left", padx=5)

        settings_btn = ctk.CTkButton(
            button_container,
            text="⚙️ 设置",
            width=90,
            height=36,
            corner_radius=25,
            command=self._open_settings,
            fg_color=self.colors["primary"],
            hover_color=self.colors["primary_hover"],
            text_color="white",
            font=ctk.CTkFont(size=13, weight="bold")
        )
        settings_btn.pack(side="left", padx=5)

    def _create_left_panel(self):
        """Create left control panel."""
        left_container = ctk.CTkFrame(self, fg_color="transparent")
        left_container.grid(row=1, column=0, padx=(20, 10), pady=(0, 20), sticky="nsew")
        left_container.grid_rowconfigure(0, weight=3)
        left_container.grid_rowconfigure(1, weight=2)
        left_container.grid_rowconfigure(2, weight=0)

        # Query input section
        input_frame = ctk.CTkFrame(left_container, fg_color=self.colors["secondary"], corner_radius=20)
        input_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 15))

        query_label = ctk.CTkLabel(
            input_frame,
            text="输入你的问题",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=self.colors["text_dark"]
        )
        query_label.pack(anchor="w", padx=20, pady=(20, 10))

        self.query_textbox = ctk.CTkTextbox(
            input_frame,
            fg_color=self.colors["input_bg"],
            text_color=self.colors["text_dark"],
            corner_radius=16,
            font=ctk.CTkFont(size=14),
            wrap="word"
        )
        self.query_textbox.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        self.query_textbox.insert("1.0", "最近有什么美食热点")

        # Options section
        options_frame = ctk.CTkFrame(left_container, fg_color=self.colors["secondary"], corner_radius=20)
        options_frame.grid(row=1, column=0, sticky="nsew", pady=(0, 15))

        options_label = ctk.CTkLabel(
            options_frame,
            text="分析模式",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=self.colors["text_dark"]
        )
        options_label.pack(anchor="w", padx=20, pady=(20, 15))

        # Checkboxes
        checkbox_container = ctk.CTkFrame(options_frame, fg_color="transparent")
        checkbox_container.pack(fill="x", padx=20, pady=(0, 15))

        self.rewrite_var = ctk.BooleanVar(value=True)
        rewrite_cb = ctk.CTkCheckBox(
            checkbox_container,
            text="生成仿写",
            variable=self.rewrite_var,
            fg_color=self.colors["primary"],
            hover_color=self.colors["primary_hover"],
            text_color=self.colors["text_dark"],
            font=ctk.CTkFont(size=13)
        )
        rewrite_cb.pack(anchor="w", pady=3)

        self.cover_var = ctk.BooleanVar(value=True)
        cover_cb = ctk.CTkCheckBox(
            checkbox_container,
            text="生成封面",
            variable=self.cover_var,
            fg_color=self.colors["primary"],
            hover_color=self.colors["primary_hover"],
            text_color=self.colors["text_dark"],
            font=ctk.CTkFont(size=13)
        )
        cover_cb.pack(anchor="w", pady=3)

        self.cover_image_var = ctk.BooleanVar(value=False)
        cover_image_cb = ctk.CTkCheckBox(
            checkbox_container,
            text="生成封面图片",
            variable=self.cover_image_var,
            fg_color=self.colors["primary"],
            hover_color=self.colors["primary_hover"],
            text_color=self.colors["text_dark"],
            font=ctk.CTkFont(size=13)
        )
        cover_image_cb.pack(anchor="w", pady=3)

        # Mode selection
        mode_container = ctk.CTkFrame(options_frame, fg_color="transparent")
        mode_container.pack(fill="x", padx=20, pady=(0, 15))

        mode_label = ctk.CTkLabel(
            mode_container,
            text="分析模式:",
            text_color=self.colors["text_dark"],
            font=ctk.CTkFont(size=13)
        )
        mode_label.pack(side="left", padx=(0, 10))

        self.mode_var = ctk.StringVar(value="hot")
        mode_menu = ctk.CTkOptionMenu(
            mode_container,
            variable=self.mode_var,
            values=["热点分析", "账号雷达"],
            command=self._on_mode_change,
            fg_color=self.colors["input_bg"],
            button_color=self.colors["primary"],
            button_hover_color=self.colors["primary_hover"],
            text_color=self.colors["text_dark"],
            font=ctk.CTkFont(size=13),
            dropdown_font=ctk.CTkFont(size=13),
            corner_radius=12,
            width=120
        )
        mode_menu.pack(side="left")

        # Action buttons
        button_container = ctk.CTkFrame(options_frame, fg_color="transparent")
        button_container.pack(fill="x", padx=20, pady=(0, 20))

        self.start_btn = ctk.CTkButton(
            button_container,
            text="开始分析",
            height=40,
            corner_radius=25,
            command=self._start_analysis,
            fg_color=self.colors["primary"],
            hover_color=self.colors["primary_hover"],
            text_color="white",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.start_btn.pack(fill="x", pady=3)

        self.cancel_btn = ctk.CTkButton(
            button_container,
            text="取消",
            height=40,
            corner_radius=25,
            state="disabled",
            fg_color="#c28e85",
            hover_color="#a6746b",
            command=self._cancel_analysis,
            text_color="white",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.cancel_btn.pack(fill="x", pady=3)

        batch_btn = ctk.CTkButton(
            button_container,
            text="批量处理",
            height=40,
            corner_radius=25,
            command=self._open_batch_dialog,
            fg_color=self.colors["primary"],
            hover_color=self.colors["primary_hover"],
            text_color="white",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        batch_btn.pack(fill="x", pady=3)

        # Progress section
        progress_container = ctk.CTkFrame(left_container, fg_color="transparent")
        progress_container.grid(row=2, column=0, sticky="ew")

        progress_label_frame = ctk.CTkFrame(progress_container, fg_color="transparent")
        progress_label_frame.pack(fill="x", pady=(0, 5))

        ctk.CTkLabel(
            progress_label_frame,
            text="状态",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=self.colors["text_dark"]
        ).pack(side="left")

        self.progress_label = ctk.CTkLabel(
            progress_label_frame,
            text="就绪",
            font=ctk.CTkFont(size=12),
            text_color=self.colors["text_light"]
        )
        self.progress_label.pack(side="left", padx=10)

        self.progress_bar = ctk.CTkProgressBar(
            progress_container,
            progress_color=self.colors["primary"],
            fg_color=self.colors["progress_bg"],
            corner_radius=15,
            height=12
        )
        self.progress_bar.pack(fill="x")
        self.progress_bar.set(0)

    def _create_right_panel(self):
        """Create right result panel."""
        right_container = ctk.CTkFrame(
            self,
            fg_color=self.colors["secondary"],
            corner_radius=20
        )
        right_container.grid(row=1, column=1, padx=(10, 20), pady=(0, 20), sticky="nsew")

        # Result viewer
        self.result_viewer = ResultViewer(right_container, colors=self.colors)
        self.result_viewer.pack(fill="both", expand=True, padx=5, pady=5)

    def _check_initial_config(self):
        """Check if configuration is valid on startup."""
        is_valid, error_msg = self.config_manager.validate_config()
        if not is_valid:
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
        from tkinter import messagebox
        messagebox.showinfo("提示", "批量处理功能开发中...")

    def _on_mode_change(self, mode: str):
        """Handle mode change."""
        if mode == "账号雷达":
            self.mode_var.set("radar")
            self.rewrite_var.set(False)
            self.cover_var.set(False)
            self.cover_image_var.set(False)
        else:
            self.mode_var.set("hot")

    def _start_analysis(self):
        """Start analysis task."""
        query = self.query_textbox.get("1.0", "end-1c").strip()
        if not query:
            from tkinter import messagebox
            messagebox.showerror("错误", "请输入查询内容")
            return

        is_valid, error_msg = self.config_manager.validate_config()
        if not is_valid:
            from tkinter import messagebox
            messagebox.showerror("配置错误", error_msg)
            self._open_settings()
            return

        mode = self.mode_var.get()
        options = {
            "analysis_mode": mode,
            "rewrite": self.rewrite_var.get() and mode != "radar",
            "cover": self.cover_var.get() and mode != "radar",
            "cover_image": self.cover_image_var.get() and mode != "radar",
            "gemini_model": self.config_manager.get_setting("gemini_model"),
            "gemini_base_url": self.config_manager.get_setting("gemini_base_url"),
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

        env_vars = self.config_manager.export_for_env()

        self.is_running = True
        self.start_btn.configure(state="disabled")
        self.cancel_btn.configure(state="normal")
        self.progress_bar.set(0)
        self.progress_label.configure(text="准备中...")

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
        """Handle progress update."""
        current = progress.get("current", 0)
        total = progress.get("total", 1)
        message = progress.get("message", "")

        progress_value = current / total if total > 0 else 0
        self.progress_bar.set(progress_value)
        self.progress_label.configure(text=message)

    def _on_analysis_complete(self, result: dict[str, Any]):
        """Handle analysis completion."""
        self.is_running = False
        self.start_btn.configure(state="normal")
        self.cancel_btn.configure(state="disabled")
        self.progress_bar.set(1.0)
        self.progress_label.configure(text="完成！")

        try:
            self.history_manager.save_record(
                query=result.get("query", ""),
                result=result,
                metadata={"timestamp": str(Path.cwd())},
            )
        except Exception as e:
            print(f"Failed to save history: {e}")

        self.current_result = result
        self.result_viewer.display_result(result)

    def _on_analysis_error(self, error: str):
        """Handle analysis error."""
        self.is_running = False
        self.start_btn.configure(state="normal")
        self.cancel_btn.configure(state="disabled")
        self.progress_bar.set(0)
        self.progress_label.configure(text="错误")

        from tkinter import messagebox
        messagebox.showerror("分析失败", f"分析过程中出现错误：\n\n{error}")

    def _load_history_record(self, record: dict[str, Any]):
        """Load and display history record."""
        full_record = self.history_manager.get_record(record["id"])
        if not full_record:
            return

        result = full_record["result"]
        self.current_result = result
        self.result_viewer.display_result(result)

        self.query_textbox.delete("1.0", "end")
        self.query_textbox.insert("1.0", full_record["query"])

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
