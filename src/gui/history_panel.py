"""History panel for XHS Agent GUI application."""

from __future__ import annotations

from typing import Any, Callable

import customtkinter as ctk

from ..core.history_manager import HistoryManager


class HistoryPanel(ctk.CTkToplevel):
    """History records panel."""

    def __init__(
        self,
        parent,
        history_manager: HistoryManager,
        load_callback: Callable[[dict[str, Any]], None],
    ):
        """Initialize history panel.

        Args:
            parent: Parent window
            history_manager: History manager instance
            load_callback: Callback to load selected record
        """
        super().__init__(parent)

        self.history_manager = history_manager
        self.load_callback = load_callback

        self.title("历史记录")
        self.geometry("800x600")

        # Center window
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (800 // 2)
        y = (self.winfo_screenheight() // 2) - (600 // 2)
        self.geometry(f"+{x}+{y}")

        self._create_widgets()
        self._load_records()

    def _create_widgets(self):
        """Create all UI widgets."""
        # Search frame
        search_frame = ctk.CTkFrame(self)
        search_frame.pack(fill="x", padx=20, pady=20)

        self.search_entry = ctk.CTkEntry(search_frame, placeholder_text="搜索...", width=600)
        self.search_entry.pack(side="left", padx=10)
        self.search_entry.bind("<Return>", lambda e: self._search_records())

        search_btn = ctk.CTkButton(search_frame, text="🔍", width=60, command=self._search_records)
        search_btn.pack(side="left")

        clear_btn = ctk.CTkButton(
            search_frame, text="清除", width=80, command=self._clear_search
        )
        clear_btn.pack(side="left", padx=5)

        # Records list frame
        list_frame = ctk.CTkFrame(self)
        list_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        # Scrollable frame for records
        self.records_frame = ctk.CTkScrollableFrame(list_frame, label_text="历史记录")
        self.records_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Bottom buttons
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.pack(fill="x", padx=20, pady=(0, 20))

        delete_all_btn = ctk.CTkButton(
            button_frame,
            text="删除全部",
            width=100,
            fg_color="red",
            hover_color="darkred",
            command=self._delete_all_records,
        )
        delete_all_btn.pack(side="left")

        close_btn = ctk.CTkButton(button_frame, text="关闭", width=100, command=self.destroy)
        close_btn.pack(side="right")

    def _load_records(self, records: list[dict[str, Any]] | None = None):
        """Load and display records.

        Args:
            records: Optional list of records to display.
                    If None, loads all records from database.
        """
        # Clear existing records
        for widget in self.records_frame.winfo_children():
            widget.destroy()

        # Get records
        if records is None:
            records = self.history_manager.get_records(limit=100)

        if not records:
            no_records_label = ctk.CTkLabel(
                self.records_frame, text="暂无历史记录", text_color="gray"
            )
            no_records_label.pack(pady=50)
            return

        # Display records
        for record in records:
            self._create_record_widget(record)

    def _create_record_widget(self, record: dict[str, Any]):
        """Create widget for single record.

        Args:
            record: Record dictionary
        """
        record_frame = ctk.CTkFrame(self.records_frame)
        record_frame.pack(fill="x", padx=5, pady=5)

        # Info frame
        info_frame = ctk.CTkFrame(record_frame, fg_color="transparent")
        info_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)

        # Date and mode
        date_mode_text = f"{record['created_at']} | {record['mode']}"
        date_label = ctk.CTkLabel(
            info_frame, text=date_mode_text, font=ctk.CTkFont(size=11), text_color="gray"
        )
        date_label.pack(anchor="w")

        # Query text
        query_text = record["query"][:80] + ("..." if len(record["query"]) > 80 else "")
        query_label = ctk.CTkLabel(
            info_frame, text=query_text, font=ctk.CTkFont(size=13), anchor="w"
        )
        query_label.pack(anchor="w", pady=(5, 0))

        # Buttons frame
        buttons_frame = ctk.CTkFrame(record_frame, fg_color="transparent")
        buttons_frame.pack(side="right", padx=10)

        load_btn = ctk.CTkButton(
            buttons_frame,
            text="查看",
            width=80,
            command=lambda r=record: self._load_record(r),
        )
        load_btn.pack(side="left", padx=5)

        delete_btn = ctk.CTkButton(
            buttons_frame,
            text="删除",
            width=80,
            fg_color="red",
            hover_color="darkred",
            command=lambda r=record: self._delete_record(r),
        )
        delete_btn.pack(side="left")

    def _search_records(self):
        """Search records by keyword."""
        keyword = self.search_entry.get().strip()
        if not keyword:
            self._load_records()
            return

        records = self.history_manager.search_records(keyword)
        self._load_records(records)

    def _clear_search(self):
        """Clear search and reload all records."""
        self.search_entry.delete(0, "end")
        self._load_records()

    def _load_record(self, record: dict[str, Any]):
        """Load selected record.

        Args:
            record: Record dictionary
        """
        self.load_callback(record)
        self.destroy()

    def _delete_record(self, record: dict[str, Any]):
        """Delete single record.

        Args:
            record: Record dictionary
        """
        # Confirm deletion
        dialog = ctk.CTkInputDialog(
            text=f"确定要删除这条记录吗？\n\n{record['query'][:50]}...",
            title="确认删除",
        )
        if dialog.get_input():
            self.history_manager.delete_record(record["id"])
            self._load_records()

    def _delete_all_records(self):
        """Delete all records."""
        # Confirm deletion
        dialog = ctk.CTkInputDialog(
            text="确定要删除所有历史记录吗？此操作不可恢复！",
            title="确认删除全部",
        )
        if dialog.get_input():
            self.history_manager.delete_all_records()
            self._load_records()
