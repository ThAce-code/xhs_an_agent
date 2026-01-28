"""Result viewer for XHS Agent GUI application."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import customtkinter as ctk


class ResultViewer(ctk.CTkFrame):
    """Result display and export widget."""

    def __init__(self, parent, colors=None):
        """Initialize result viewer.

        Args:
            parent: Parent widget
            colors: Optional color scheme dictionary
        """
        super().__init__(parent)

        self.current_result: dict[str, Any] | None = None

        # Use provided colors or defaults
        self.colors = colors or {
            "primary": "#FFB7A1",
            "secondary": "#F0D6D1",
            "accent": "#2C2C2C",
            "background": "#D3DEE8",
            "text_dark": "#2C2C2C",
            "text_light": "#FFFFFF",
        }

        # Set frame background
        self.configure(fg_color=self.colors["secondary"])

        self._create_widgets()

    def _create_widgets(self):
        """Create all UI widgets."""
        # Tabview for different result sections
        self.tabview = ctk.CTkTabview(
            self,
            fg_color="transparent",
            segmented_button_fg_color=self.colors["tab_bg"],
            segmented_button_selected_color=self.colors["input_bg"],
            segmented_button_selected_hover_color=self.colors["input_bg"],
            segmented_button_unselected_color=self.colors["tab_bg"],
            segmented_button_unselected_hover_color=self.colors["tab_bg"],
            text_color=self.colors["text_dark"],
            text_color_disabled=self.colors["text_light"],
            corner_radius=15
        )
        self.tabview.pack(fill="both", expand=True, padx=15, pady=15)

        # Add tabs
        self.tabview.add("分析")
        self.tabview.add("仿写")
        self.tabview.add("封面")
        self.tabview.add("来源")

        # Create textboxes for each tab
        self.analysis_textbox = ctk.CTkTextbox(
            self.tabview.tab("分析"),
            fg_color=self.colors["input_bg"],
            text_color=self.colors["text_dark"],
            corner_radius=16,
            font=ctk.CTkFont(size=13),
            wrap="word"
        )
        self.analysis_textbox.pack(fill="both", expand=True, padx=10, pady=10)

        self.rewrite_textbox = ctk.CTkTextbox(
            self.tabview.tab("仿写"),
            fg_color=self.colors["input_bg"],
            text_color=self.colors["text_dark"],
            corner_radius=16,
            font=ctk.CTkFont(size=13),
            wrap="word"
        )
        self.rewrite_textbox.pack(fill="both", expand=True, padx=10, pady=10)

        self.cover_textbox = ctk.CTkTextbox(
            self.tabview.tab("封面"),
            fg_color=self.colors["input_bg"],
            text_color=self.colors["text_dark"],
            corner_radius=16,
            font=ctk.CTkFont(size=13),
            wrap="word"
        )
        self.cover_textbox.pack(fill="both", expand=True, padx=10, pady=10)

        self.sources_textbox = ctk.CTkTextbox(
            self.tabview.tab("来源"),
            fg_color=self.colors["input_bg"],
            text_color=self.colors["text_dark"],
            corner_radius=16,
            font=ctk.CTkFont(size=13),
            wrap="word"
        )
        self.sources_textbox.pack(fill="both", expand=True, padx=10, pady=10)

        # Export buttons
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.pack(fill="x", padx=15, pady=(0, 15))

        export_json_btn = ctk.CTkButton(
            button_frame,
            text="📄 导出JSON",
            width=120,
            height=36,
            corner_radius=25,
            command=self._export_json,
            fg_color=self.colors["primary"],
            hover_color=self.colors.get("primary_hover", self.colors["primary"]),
            text_color="white",
            font=ctk.CTkFont(size=13, weight="bold")
        )
        export_json_btn.pack(side="left", padx=5)

        copy_btn = ctk.CTkButton(
            button_frame,
            text="📋 复制当前",
            width=120,
            height=36,
            corner_radius=25,
            command=self._copy_current,
            fg_color=self.colors["primary"],
            hover_color=self.colors.get("primary_hover", self.colors["primary"]),
            text_color="white",
            font=ctk.CTkFont(size=13, weight="bold")
        )
        copy_btn.pack(side="left")

    def display_result(self, result: dict[str, Any]):
        """Display analysis result.

        Args:
            result: Result dictionary
        """
        self.current_result = result

        mode = result.get("mode", "hot")

        # Clear all textboxes
        self.analysis_textbox.delete("1.0", "end")
        self.rewrite_textbox.delete("1.0", "end")
        self.cover_textbox.delete("1.0", "end")
        self.sources_textbox.delete("1.0", "end")

        # Display analysis
        if mode == "radar":
            self._display_radar_result(result)
        else:
            self._display_hot_result(result)

        # Display sources
        self._display_sources(result.get("parsed", {}).get("sources", []))

        # Switch to analysis tab
        self.tabview.set("分析")

    def _display_hot_result(self, result: dict[str, Any]):
        """Display hot analysis result.

        Args:
            result: Result dictionary
        """
        parsed = result.get("parsed", {})

        # Format analysis
        analysis_text = self._format_hot_analysis(parsed)
        self.analysis_textbox.insert("1.0", analysis_text)

        # Display rewrite if available
        if "rewrite" in result:
            rewrite_text = self._format_rewrite(result["rewrite"].get("parsed", {}))
            self.rewrite_textbox.insert("1.0", rewrite_text)

        # Display cover if available
        if "cover" in result:
            cover_text = self._format_cover(result["cover"].get("parsed", {}))
            self.cover_textbox.insert("1.0", cover_text)

    def _display_radar_result(self, result: dict[str, Any]):
        """Display radar analysis result.

        Args:
            result: Result dictionary
        """
        parsed = result.get("parsed", {})

        # Format radar analysis
        radar_text = self._format_radar_analysis(parsed)
        self.analysis_textbox.insert("1.0", radar_text)

        # Disable rewrite and cover tabs for radar mode
        self.rewrite_textbox.insert("1.0", "雷达模式不支持仿写功能")
        self.cover_textbox.insert("1.0", "雷达模式不支持封面功能")

    def _format_hot_analysis(self, parsed: dict[str, Any]) -> str:
        """Format hot analysis for display.

        Args:
            parsed: Parsed analysis data

        Returns:
            Formatted text
        """
        lines = []
        lines.append("=" * 60)
        lines.append("📊 热点分析报告")
        lines.append("=" * 60)
        lines.append("")

        # Why hot
        why_hot = parsed.get("why_hot", {})
        if why_hot:
            lines.append("🔥 为什么这些话题会火？")
            lines.append("")

            if "core_pain_points" in why_hot:
                lines.append("核心痛点：")
                for item in why_hot["core_pain_points"]:
                    text = item.get("text", "")
                    cites = item.get("cites", [])
                    lines.append(f"  • {text} [{','.join(map(str, cites))}]")
                lines.append("")

            if "emotional_hooks" in why_hot:
                lines.append("情绪钩子：")
                for item in why_hot["emotional_hooks"]:
                    text = item.get("text", "")
                    cites = item.get("cites", [])
                    lines.append(f"  • {text} [{','.join(map(str, cites))}]")
                lines.append("")

        # Ideas
        ideas = parsed.get("ideas", {})
        if ideas:
            lines.append("💡 爆款选题方向")
            lines.append("")

            for category, items in ideas.items():
                if category == "follow":
                    lines.append("【跟风型】低成本快速复制")
                elif category == "reverse":
                    lines.append("【反向型】唱反调/差异化观点")
                elif category == "upgrade":
                    lines.append("【升级型】更深、更全、更美")

                for item in items:
                    text = item.get("text", "")
                    cites = item.get("cites", [])
                    lines.append(f"  • {text} [{','.join(map(str, cites))}]")
                lines.append("")

        return "\n".join(lines)

    def _format_radar_analysis(self, parsed: dict[str, Any]) -> str:
        """Format radar analysis for display.

        Args:
            parsed: Parsed radar data

        Returns:
            Formatted text
        """
        lines = []
        lines.append("=" * 60)
        lines.append("🎯 账号方向雷达")
        lines.append("=" * 60)
        lines.append("")

        niches = parsed.get("niches", [])
        for i, niche in enumerate(niches, 1):
            lines.append(f"【赛道 {i}】{niche.get('name', '')}")
            lines.append("")

            target = niche.get("target_persona", {})
            if target:
                lines.append(f"目标人群：{target.get('text', '')}")
                lines.append("")

            pain_points = niche.get("core_pain_points", [])
            if pain_points:
                lines.append("核心痛点：")
                for item in pain_points:
                    lines.append(f"  • {item.get('text', '')}")
                lines.append("")

            lines.append("-" * 60)
            lines.append("")

        return "\n".join(lines)

    def _format_rewrite(self, parsed: dict[str, Any]) -> str:
        """Format rewrite for display.

        Args:
            parsed: Parsed rewrite data

        Returns:
            Formatted text
        """
        lines = []
        lines.append("=" * 60)
        lines.append("✍️ 爆款仿写素材")
        lines.append("=" * 60)
        lines.append("")

        drafts = parsed.get("drafts", [])
        for i, draft in enumerate(drafts, 1):
            lines.append(f"【草稿 {i}】")
            lines.append("")
            lines.append(f"标题：{draft.get('title', '')}")
            lines.append("")
            lines.append(draft.get("body", ""))
            lines.append("")
            lines.append("-" * 60)
            lines.append("")

        # Title bank
        title_bank = parsed.get("title_bank", [])
        if title_bank:
            lines.append("📝 标题库")
            lines.append("")
            for item in title_bank:
                lines.append(f"  • {item.get('text', '')}")
            lines.append("")

        return "\n".join(lines)

    def _format_cover(self, parsed: dict[str, Any]) -> str:
        """Format cover for display.

        Args:
            parsed: Parsed cover data

        Returns:
            Formatted text
        """
        lines = []
        lines.append("=" * 60)
        lines.append("🎨 封面设计方案")
        lines.append("=" * 60)
        lines.append("")

        concepts = parsed.get("cover_concepts", [])
        for i, concept in enumerate(concepts, 1):
            lines.append(f"【方案 {i}】{concept.get('name', '')}")
            lines.append("")
            lines.append(f"主标题：{concept.get('headline', '')}")
            lines.append(f"副标题：{concept.get('subheadline', '')}")
            lines.append("")
            lines.append(f"构图：{concept.get('composition', '')}")
            lines.append(f"光线：{concept.get('lighting', '')}")
            lines.append("")
            lines.append("-" * 60)
            lines.append("")

        return "\n".join(lines)

    def _display_sources(self, sources: list[dict[str, Any]]):
        """Display sources.

        Args:
            sources: List of source dictionaries
        """
        lines = []
        lines.append("=" * 60)
        lines.append("📚 信息来源")
        lines.append("=" * 60)
        lines.append("")

        for source in sources:
            source_id = source.get("id", "")
            title = source.get("title", "")
            url = source.get("url", "")

            lines.append(f"[{source_id}] {title}")
            lines.append(f"    {url}")
            lines.append("")

        self.sources_textbox.insert("1.0", "\n".join(lines))

    def _export_json(self):
        """Export current result as JSON."""
        if not self.current_result:
            return

        # Ask for save location
        from tkinter import filedialog

        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )

        if filename:
            try:
                with open(filename, "w", encoding="utf-8") as f:
                    json.dump(self.current_result, f, ensure_ascii=False, indent=2)

                ctk.CTkMessagebox(title="成功", message=f"已导出到：\n{filename}")
            except Exception as e:
                ctk.CTkMessagebox(title="导出失败", message=f"导出时出错：{e}")

    def _copy_current(self):
        """Copy current tab content to clipboard."""
        current_tab = self.tabview.get()

        textbox_map = {
            "分析": self.analysis_textbox,
            "仿写": self.rewrite_textbox,
            "封面": self.cover_textbox,
            "来源": self.sources_textbox,
        }

        textbox = textbox_map.get(current_tab)
        if textbox:
            content = textbox.get("1.0", "end-1c")
            self.clipboard_clear()
            self.clipboard_append(content)

            ctk.CTkMessagebox(title="成功", message="已复制到剪贴板")
