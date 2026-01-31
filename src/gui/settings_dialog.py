"""Settings dialog for XHS Agent GUI application."""

from __future__ import annotations

import os
import threading

import customtkinter as ctk

from ..core.config_manager import ConfigManager


class SettingsDialog(ctk.CTkToplevel):
    """Settings configuration dialog."""

    def __init__(self, parent, config_manager: ConfigManager):
        """Initialize settings dialog.

        Args:
            parent: Parent window
            config_manager: Configuration manager instance
        """
        super().__init__(parent)

        self.config_manager = config_manager
        self.title("设置")
        self.geometry("600x700")
        self.resizable(False, False)

        # Center window
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (600 // 2)
        y = (self.winfo_screenheight() // 2) - (700 // 2)
        self.geometry(f"+{x}+{y}")

        self._create_widgets()
        self._load_settings()

    def _create_widgets(self):
        """Create all UI widgets."""
        # Tabview for different settings categories
        self.tabview = ctk.CTkTabview(self, width=560, height=600)
        self.tabview.pack(padx=20, pady=20)

        # Add tabs
        self.tabview.add("API密钥")
        self.tabview.add("模型配置")
        self.tabview.add("搜索参数")
        self.tabview.add("输出设置")

        # API Keys tab
        self._create_api_keys_tab()

        # Model Configuration tab
        self._create_model_config_tab()

        # Search Parameters tab
        self._create_search_params_tab()

        # Output Settings tab
        self._create_output_settings_tab()

        # Bottom buttons
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.pack(fill="x", padx=20, pady=(0, 20))

        save_btn = ctk.CTkButton(button_frame, text="保存", width=100, command=self._save_settings)
        save_btn.pack(side="right", padx=5)

        cancel_btn = ctk.CTkButton(
            button_frame, text="取消", width=100, fg_color="gray", command=self.destroy
        )
        cancel_btn.pack(side="right")

        reset_btn = ctk.CTkButton(
            button_frame, text="恢复默认", width=100, command=self._reset_to_defaults
        )
        reset_btn.pack(side="left")

    def _create_api_keys_tab(self):
        """Create API keys configuration tab."""
        tab = self.tabview.tab("API密钥")

        # Google API Key
        google_frame = ctk.CTkFrame(tab)
        google_frame.pack(fill="x", padx=10, pady=10)

        google_label = ctk.CTkLabel(google_frame, text="Google API Key (必需):")
        google_label.pack(anchor="w", padx=10, pady=(10, 5))

        self.google_key_entry = ctk.CTkEntry(google_frame, show="*", width=500)
        self.google_key_entry.pack(padx=10, pady=(0, 10))

        # Tavily API Key
        tavily_frame = ctk.CTkFrame(tab)
        tavily_frame.pack(fill="x", padx=10, pady=10)

        tavily_label = ctk.CTkLabel(tavily_frame, text="Tavily API Key (必需):")
        tavily_label.pack(anchor="w", padx=10, pady=(10, 5))

        self.tavily_key_entry = ctk.CTkEntry(tavily_frame, show="*", width=500)
        self.tavily_key_entry.pack(padx=10, pady=(0, 10))

        # MiniMax API Key
        minimax_frame = ctk.CTkFrame(tab)
        minimax_frame.pack(fill="x", padx=10, pady=10)

        minimax_label = ctk.CTkLabel(minimax_frame, text="MiniMax API Key (可选，备用模型):")
        minimax_label.pack(anchor="w", padx=10, pady=(10, 5))

        self.minimax_key_entry = ctk.CTkEntry(minimax_frame, show="*", width=500)
        self.minimax_key_entry.pack(padx=10, pady=(0, 10))

        # Gemini Proxy API Key (optional)
        gemini_key_frame = ctk.CTkFrame(tab)
        gemini_key_frame.pack(fill="x", padx=10, pady=10)

        gemini_key_label = ctk.CTkLabel(
            gemini_key_frame,
            text="Gemini 中转站 API Key (可选，sk- 开头时填这里):"
        )
        gemini_key_label.pack(anchor="w", padx=10, pady=(10, 5))

        self.gemini_api_key_entry = ctk.CTkEntry(gemini_key_frame, show="*", width=500)
        self.gemini_api_key_entry.pack(padx=10, pady=(0, 10))

        # Gemini Base URL (for proxy/relay)
        gemini_url_frame = ctk.CTkFrame(tab)
        gemini_url_frame.pack(fill="x", padx=10, pady=10)

        gemini_url_label = ctk.CTkLabel(
            gemini_url_frame,
            text="Gemini 中转站URL (可选，留空使用官方API):"
        )
        gemini_url_label.pack(anchor="w", padx=10, pady=(10, 5))

        self.gemini_base_url_entry = ctk.CTkEntry(gemini_url_frame, width=500)
        self.gemini_base_url_entry.pack(padx=10, pady=(0, 5))

        gemini_url_hint = ctk.CTkLabel(
            gemini_url_frame,
            text="示例: https://api.api2d.com/v1beta 或其他中转站地址",
            text_color="gray",
            font=ctk.CTkFont(size=11),
        )
        gemini_url_hint.pack(anchor="w", padx=10, pady=(0, 10))

        # Gemini auth mode (proxy compatibility)
        auth_frame = ctk.CTkFrame(tab)
        auth_frame.pack(fill="x", padx=10, pady=10)

        auth_label = ctk.CTkLabel(auth_frame, text="Gemini Auth Mode (optional):")
        auth_label.pack(anchor="w", padx=10, pady=(10, 5))

        self.gemini_auth_mode_var = ctk.StringVar(value="auto")
        auth_menu = ctk.CTkOptionMenu(
            auth_frame,
            variable=self.gemini_auth_mode_var,
            values=["auto", "query", "header", "bearer"],
            width=200,
        )
        auth_menu.pack(anchor="w", padx=10, pady=(0, 10))

        # Debug / Connectivity
        debug_frame = ctk.CTkFrame(tab)
        debug_frame.pack(fill="x", padx=10, pady=10)

        debug_label = ctk.CTkLabel(debug_frame, text="Debug:")
        debug_label.pack(anchor="w", padx=10, pady=(10, 5))

        btn_row = ctk.CTkFrame(debug_frame, fg_color="transparent")
        btn_row.pack(fill="x", padx=10, pady=(0, 10))

        show_btn = ctk.CTkButton(btn_row, text="Show effective Gemini config", command=self._show_effective_gemini)
        show_btn.pack(side="left", padx=(0, 10))

        test_btn = ctk.CTkButton(btn_row, text="Test Gemini connection", command=self._test_gemini_connection)
        test_btn.pack(side="left")

        # Help text
        help_label = ctk.CTkLabel(
            tab,
            text="提示：API密钥将加密存储在本地配置文件中",
            text_color="gray",
            font=ctk.CTkFont(size=12),
        )
        help_label.pack(pady=10)

    def _create_model_config_tab(self):
        """Create model configuration tab."""
        tab = self.tabview.tab("模型配置")

        # Gemini Model
        gemini_frame = ctk.CTkFrame(tab)
        gemini_frame.pack(fill="x", padx=10, pady=10)

        gemini_label = ctk.CTkLabel(gemini_frame, text="Gemini 模型:")
        gemini_label.pack(anchor="w", padx=10, pady=(10, 5))

        self.gemini_model_entry = ctk.CTkEntry(gemini_frame, width=500)
        self.gemini_model_entry.pack(padx=10, pady=(0, 10))

        # MiniMax Model
        minimax_model_frame = ctk.CTkFrame(tab)
        minimax_model_frame.pack(fill="x", padx=10, pady=10)

        minimax_model_label = ctk.CTkLabel(minimax_model_frame, text="MiniMax 模型:")
        minimax_model_label.pack(anchor="w", padx=10, pady=(10, 5))

        self.minimax_model_entry = ctk.CTkEntry(minimax_model_frame, width=500)
        self.minimax_model_entry.pack(padx=10, pady=(0, 10))

        # Temperature settings
        temp_frame = ctk.CTkFrame(tab)
        temp_frame.pack(fill="x", padx=10, pady=10)

        temp_label = ctk.CTkLabel(temp_frame, text="温度参数 (0.0-1.0):")
        temp_label.pack(anchor="w", padx=10, pady=(10, 5))

        # Analysis temperature
        analysis_temp_frame = ctk.CTkFrame(temp_frame, fg_color="transparent")
        analysis_temp_frame.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(analysis_temp_frame, text="分析温度:", width=100).pack(side="left")
        self.analysis_temp_entry = ctk.CTkEntry(analysis_temp_frame, width=100)
        self.analysis_temp_entry.pack(side="left", padx=10)

        # Rewrite temperature
        rewrite_temp_frame = ctk.CTkFrame(temp_frame, fg_color="transparent")
        rewrite_temp_frame.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(rewrite_temp_frame, text="仿写温度:", width=100).pack(side="left")
        self.rewrite_temp_entry = ctk.CTkEntry(rewrite_temp_frame, width=100)
        self.rewrite_temp_entry.pack(side="left", padx=10)

        # Cover temperature
        cover_temp_frame = ctk.CTkFrame(temp_frame, fg_color="transparent")
        cover_temp_frame.pack(fill="x", padx=10, pady=(5, 10))

        ctk.CTkLabel(cover_temp_frame, text="封面温度:", width=100).pack(side="left")
        self.cover_temp_entry = ctk.CTkEntry(cover_temp_frame, width=100)
        self.cover_temp_entry.pack(side="left", padx=10)

        # Prompt style preset
        style_frame = ctk.CTkFrame(tab, fg_color="transparent")
        style_frame.pack(fill="x", padx=10, pady=(0, 10))

        ctk.CTkLabel(style_frame, text="Style Preset:", width=120).pack(side="left", padx=10)
        self.style_preset_var = ctk.StringVar(value="balanced")
        style_menu = ctk.CTkOptionMenu(
            style_frame,
            variable=self.style_preset_var,
            values=["balanced", "xhs"],
            width=200,
        )
        style_menu.pack(side="left")

        # Validation retries
        validate_frame = ctk.CTkFrame(tab, fg_color="transparent")
        validate_frame.pack(fill="x", padx=10, pady=(0, 10))

        ctk.CTkLabel(validate_frame, text="Validate Retries:", width=120).pack(side="left", padx=10)
        self.validate_retries_entry = ctk.CTkEntry(validate_frame, width=100)
        self.validate_retries_entry.pack(side="left")

    def _create_search_params_tab(self):
        """Create search parameters tab."""
        tab = self.tabview.tab("搜索参数")

        # Max results
        results_frame = ctk.CTkFrame(tab, fg_color="transparent")
        results_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(results_frame, text="每次搜索结果数:", width=150).pack(side="left", padx=10)
        self.max_results_entry = ctk.CTkEntry(results_frame, width=100)
        self.max_results_entry.pack(side="left")

        # Max queries
        queries_frame = ctk.CTkFrame(tab, fg_color="transparent")
        queries_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(queries_frame, text="多查询数量:", width=150).pack(side="left", padx=10)
        self.max_queries_entry = ctk.CTkEntry(queries_frame, width=100)
        self.max_queries_entry.pack(side="left")

        # Max sources
        sources_frame = ctk.CTkFrame(tab, fg_color="transparent")
        sources_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(sources_frame, text="最大来源数:", width=150).pack(side="left", padx=10)
        self.max_sources_entry = ctk.CTkEntry(sources_frame, width=100)
        self.max_sources_entry.pack(side="left")

        # Days
        days_frame = ctk.CTkFrame(tab, fg_color="transparent")
        days_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(days_frame, text="搜索天数范围:", width=150).pack(side="left", padx=10)
        self.days_entry = ctk.CTkEntry(days_frame, width=100)
        self.days_entry.pack(side="left")

        # Language
        lang_frame = ctk.CTkFrame(tab, fg_color="transparent")
        lang_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(lang_frame, text="语言:", width=150).pack(side="left", padx=10)
        self.lang_entry = ctk.CTkEntry(lang_frame, width=100)
        self.lang_entry.pack(side="left")

        # Region
        region_frame = ctk.CTkFrame(tab, fg_color="transparent")
        region_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(region_frame, text="地区:", width=150).pack(side="left", padx=10)
        self.region_entry = ctk.CTkEntry(region_frame, width=100)
        self.region_entry.pack(side="left")

    def _create_output_settings_tab(self):
        """Create output settings tab."""
        tab = self.tabview.tab("输出设置")

        # Output directory
        out_dir_frame = ctk.CTkFrame(tab)
        out_dir_frame.pack(fill="x", padx=10, pady=10)

        out_dir_label = ctk.CTkLabel(out_dir_frame, text="输出目录:")
        out_dir_label.pack(anchor="w", padx=10, pady=(10, 5))

        self.out_dir_entry = ctk.CTkEntry(out_dir_frame, width=500)
        self.out_dir_entry.pack(padx=10, pady=(0, 10))

        # Cover image provider
        provider_frame = ctk.CTkFrame(tab)
        provider_frame.pack(fill="x", padx=10, pady=10)

        provider_label = ctk.CTkLabel(provider_frame, text="封面图片生成提供商:")
        provider_label.pack(anchor="w", padx=10, pady=(10, 5))

        self.provider_var = ctk.StringVar(value="minimax")
        provider_menu = ctk.CTkOptionMenu(
            provider_frame, variable=self.provider_var, values=["minimax", "google"]
        )
        provider_menu.pack(anchor="w", padx=10, pady=(0, 10))

    def _load_settings(self):
        """Load current settings into form."""
        # API Keys
        self.google_key_entry.insert(0, self.config_manager.get_api_key("google"))
        self.tavily_key_entry.insert(0, self.config_manager.get_api_key("tavily"))
        self.minimax_key_entry.insert(0, self.config_manager.get_api_key("minimax"))

        # Gemini Base URL
        self.gemini_base_url_entry.insert(0, self.config_manager.get_setting("gemini_base_url", ""))
        if hasattr(self, "gemini_api_key_entry"):
            self.gemini_api_key_entry.insert(0, self.config_manager.get_setting("gemini_api_key", ""))
        if hasattr(self, "gemini_auth_mode_var"):
            self.gemini_auth_mode_var.set(self.config_manager.get_setting("gemini_auth_mode", "auto"))

        # Model Configuration
        self.gemini_model_entry.insert(0, self.config_manager.get_setting("gemini_model", "gemini-2.5-flash"))
        self.minimax_model_entry.insert(0, self.config_manager.get_setting("minimax_model", "MiniMax-M2.1"))
        self.analysis_temp_entry.insert(0, str(self.config_manager.get_setting("analysis_temperature", 0.0)))
        self.rewrite_temp_entry.insert(0, str(self.config_manager.get_setting("rewrite_temperature", 0.7)))
        self.cover_temp_entry.insert(0, str(self.config_manager.get_setting("cover_temperature", 0.6)))
        if hasattr(self, "style_preset_var"):
            self.style_preset_var.set(self.config_manager.get_setting("style_preset", "balanced"))
        if hasattr(self, "validate_retries_entry"):
            self.validate_retries_entry.insert(0, str(self.config_manager.get_setting("validate_retries", 1)))

        # Search Parameters
        self.max_results_entry.insert(0, str(self.config_manager.get_setting("max_results", 5)))
        self.max_queries_entry.insert(0, str(self.config_manager.get_setting("max_queries", 6)))
        self.max_sources_entry.insert(0, str(self.config_manager.get_setting("max_sources", 10)))
        self.days_entry.insert(0, str(self.config_manager.get_setting("days", 30)))
        self.lang_entry.insert(0, self.config_manager.get_setting("lang", "zh"))
        self.region_entry.insert(0, self.config_manager.get_setting("region", "cn"))

        # Output Settings
        self.out_dir_entry.insert(0, self.config_manager.get_setting("out_dir", "outputs"))
        self.provider_var.set(self.config_manager.get_setting("cover_image_provider", "minimax"))

    def _save_settings(self):
        """Save settings to configuration."""
        try:
            # Save API keys
            self.config_manager.set_api_key("google", self.google_key_entry.get().strip())
            self.config_manager.set_api_key("tavily", self.tavily_key_entry.get().strip())
            self.config_manager.set_api_key("minimax", self.minimax_key_entry.get().strip())

            # Save Gemini base URL
            self.config_manager.set_setting("gemini_base_url", self.gemini_base_url_entry.get().strip())
            if hasattr(self, "gemini_api_key_entry"):
                self.config_manager.set_setting("gemini_api_key", self.gemini_api_key_entry.get().strip())
            if hasattr(self, "gemini_auth_mode_var"):
                self.config_manager.set_setting("gemini_auth_mode", self.gemini_auth_mode_var.get().strip())

            # Save model configuration
            self.config_manager.set_setting("gemini_model", self.gemini_model_entry.get().strip())
            self.config_manager.set_setting("minimax_model", self.minimax_model_entry.get().strip())
            self.config_manager.set_setting("analysis_temperature", float(self.analysis_temp_entry.get()))
            self.config_manager.set_setting("rewrite_temperature", float(self.rewrite_temp_entry.get()))
            self.config_manager.set_setting("cover_temperature", float(self.cover_temp_entry.get()))
            if hasattr(self, "style_preset_var"):
                self.config_manager.set_setting("style_preset", self.style_preset_var.get().strip())
            if hasattr(self, "validate_retries_entry"):
                self.config_manager.set_setting("validate_retries", int(self.validate_retries_entry.get()))

            # Save search parameters
            self.config_manager.set_setting("max_results", int(self.max_results_entry.get()))
            self.config_manager.set_setting("max_queries", int(self.max_queries_entry.get()))
            self.config_manager.set_setting("max_sources", int(self.max_sources_entry.get()))
            self.config_manager.set_setting("days", int(self.days_entry.get()))
            self.config_manager.set_setting("lang", self.lang_entry.get().strip())
            self.config_manager.set_setting("region", self.region_entry.get().strip())

            # Save output settings
            self.config_manager.set_setting("out_dir", self.out_dir_entry.get().strip())
            self.config_manager.set_setting("cover_image_provider", self.provider_var.get())

            # Persist to file
            self.config_manager.save_config()

            # Validate
            is_valid, error_msg = self.config_manager.validate_config()
            if not is_valid:
                from tkinter import messagebox

                messagebox.showwarning("配置警告", error_msg)
            else:
                from tkinter import messagebox

                messagebox.showinfo("成功", "设置已保存")
                self.destroy()

        except ValueError as e:
            from tkinter import messagebox

            messagebox.showerror("输入错误", f"请检查输入值：{e}")
        except Exception as e:
            from tkinter import messagebox

            messagebox.showerror("保存失败", f"保存设置时出错：{e}")

    def _mask_secret(self, value: str) -> str:
        v = (value or "").strip()
        if not v:
            return ""
        if len(v) <= 10:
            return v[:2] + "***" + v[-2:]
        return v[:6] + "***" + v[-4:]

    def _get_effective_gemini_config(self) -> dict[str, str]:
        base_url = (self.gemini_base_url_entry.get() or "").strip()
        model = (self.gemini_model_entry.get() or "").strip()

        auth_mode = "auto"
        if hasattr(self, "gemini_auth_mode_var"):
            auth_mode = (self.gemini_auth_mode_var.get() or "auto").strip().lower()

        proxy_key = ""
        if hasattr(self, "gemini_api_key_entry"):
            proxy_key = (self.gemini_api_key_entry.get() or "").strip()
        google_key = (self.google_key_entry.get() or "").strip()

        route = "proxy" if base_url else "official"
        key_used = proxy_key or google_key
        endpoint = f"{base_url.rstrip('/')}/{model}:generateContent" if base_url and model else ""

        return {
            "route": route,
            "model": model,
            "base_url": base_url,
            "endpoint": endpoint,
            "auth_mode": auth_mode,
            "key_source": "gemini_proxy_key" if proxy_key else ("google_key" if google_key else ""),
            "key_used": self._mask_secret(key_used),
        }

    def _show_effective_gemini(self) -> None:
        from tkinter import messagebox

        cfg = self._get_effective_gemini_config()
        lines = [
            f"route: {cfg['route']}",
            f"model: {cfg['model'] or '(empty)'}",
            f"base_url: {cfg['base_url'] or '(empty)'}",
            f"auth_mode: {cfg['auth_mode']}",
            f"key_source: {cfg['key_source'] or '(none)'}",
            f"key_used: {cfg['key_used'] or '(empty)'}",
        ]
        if cfg["endpoint"]:
            lines.append(f"endpoint: {cfg['endpoint']}")
        messagebox.showinfo("Gemini config", "\n".join(lines))

    def _test_gemini_connection(self) -> None:
        from tkinter import messagebox

        cfg = self._get_effective_gemini_config()
        base_url = cfg["base_url"]
        model = cfg["model"]
        auth_mode = cfg["auth_mode"]

        proxy_key = ""
        if hasattr(self, "gemini_api_key_entry"):
            proxy_key = (self.gemini_api_key_entry.get() or "").strip()
        google_key = (self.google_key_entry.get() or "").strip()
        api_key = proxy_key or google_key

        if not model:
            messagebox.showerror("Test failed", "Gemini model is empty.")
            return

        def worker() -> None:
            try:
                if base_url:
                    from langchain_core.messages import HumanMessage, SystemMessage

                    from ..llms import GeminiGenerateContentClient

                    client = GeminiGenerateContentClient(
                        api_key=api_key,
                        base_url=base_url,
                        model=model,
                        auth_mode=auth_mode,
                        temperature=0.0,
                        timeout_s=20.0,
                        max_retries=0,
                    )
                    text = client.invoke(
                        [
                            SystemMessage(content="Health check. Reply with OK."),
                            HumanMessage(content="OK"),
                        ]
                    )
                else:
                    # Official API test (requires GOOGLE_API_KEY).
                    from langchain_core.messages import HumanMessage
                    from langchain_google_genai import ChatGoogleGenerativeAI

                    old = os.environ.get("GOOGLE_API_KEY")
                    try:
                        if google_key:
                            os.environ["GOOGLE_API_KEY"] = google_key
                        llm = ChatGoogleGenerativeAI(model=model, temperature=0.0)
                        resp = llm.invoke([HumanMessage(content="Reply with OK.")])
                        text = str(getattr(resp, "content", resp))
                    finally:
                        if old is None:
                            os.environ.pop("GOOGLE_API_KEY", None)
                        else:
                            os.environ["GOOGLE_API_KEY"] = old

                self.after(0, lambda: messagebox.showinfo("Test OK", f"Response:\n{text[:500]}"))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Test failed", str(e)))

        threading.Thread(target=worker, daemon=True).start()

    def _reset_to_defaults(self):
        """Reset settings to defaults."""
        self.config_manager.reset_to_defaults()
        self.config_manager.save_config()

        # Clear and reload form
        for widget in [
            self.gemini_model_entry,
            self.minimax_model_entry,
            self.analysis_temp_entry,
            self.rewrite_temp_entry,
            self.cover_temp_entry,
            self.max_results_entry,
            self.max_queries_entry,
            self.max_sources_entry,
            self.days_entry,
            self.lang_entry,
            self.region_entry,
            self.out_dir_entry,
        ]:
            widget.delete(0, "end")

        self._load_settings()

        from tkinter import messagebox

        messagebox.showinfo("成功", "已恢复默认设置（API密钥已保留）")
