from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


logger = logging.getLogger(__name__)


def _messages_to_openai(messages: list[Any]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for m in messages:
        role = getattr(m, "type", None) or getattr(m, "role", None)
        # langchain_core messages
        if role == "system":
            r = "system"
        elif role == "human":
            r = "user"
        elif role == "ai":
            r = "assistant"
        elif role == "tool":
            r = "tool"
        else:
            # Best-effort fallback
            r = "user"

        content = getattr(m, "content", m)
        if not isinstance(content, str):
            content = str(content)

        out.append({"role": r, "content": content})

    return out


def _extract_chat_content(response_json: dict[str, Any]) -> str:
    """Best-effort extract assistant text across MiniMax response variants."""

    choices = response_json.get("choices")
    if isinstance(choices, list) and choices:
        c0 = choices[0]
        if isinstance(c0, dict):
            msg = c0.get("message")
            if isinstance(msg, dict) and isinstance(msg.get("content"), str):
                return msg["content"]

            msgs = c0.get("messages")
            if isinstance(msgs, list) and msgs:
                # Some APIs return a list of messages; pick the last assistant-like content.
                for m in reversed(msgs):
                    if not isinstance(m, dict):
                        continue
                    role = str(m.get("role") or "").lower()
                    content = m.get("content")
                    if isinstance(content, str) and content.strip() and (role in {"assistant", "bot", ""}):
                        return content
                # Fallback to last content if present.
                last = msgs[-1]
                if isinstance(last, dict) and isinstance(last.get("content"), str):
                    return last["content"]

    for k in ("reply", "output_text", "text", "result"):
        v = response_json.get(k)
        if isinstance(v, str) and v.strip():
            return v

    raise KeyError("Unable to extract assistant content from MiniMax response")


class MiniMaxChatClient:
    """Minimal MiniMax Chat Completions client (OpenAI-compatible endpoint)."""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        temperature: float = 0.0,
        timeout_s: float = 60.0,
        max_retries: int = 0,
    ) -> None:
        key = (api_key or "").strip()
        if key.lower().startswith("bearer "):
            key = key[7:].strip()

        self.api_key = key
        self.base_url = (base_url or "").strip()
        self.model = model
        self.temperature = temperature
        self.timeout_s = timeout_s
        self.max_retries = max(0, int(max_retries))

    def invoke(self, messages: list[Any]) -> str:
        # MiniMax has multiple gateway styles; keep payload OpenAI-like by default.
        # Official docs endpoint often looks like: /v1/text/chatcompletion_v2
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": _messages_to_openai(messages),
            "stream": False,
            "temperature": self.temperature,
        }

        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            self.base_url,
            data=data,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )

        last_err: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                    body = resp.read().decode("utf-8")
                j = json.loads(body)
                return _extract_chat_content(j)
            except urllib.error.HTTPError as e:
                detail = e.read().decode("utf-8", errors="replace")
                raise RuntimeError(f"MiniMax HTTP {e.code}: {detail}") from e
            except Exception as e:
                last_err = e
                if attempt < self.max_retries:
                    time.sleep(min(2**attempt, 8))
                    continue
                raise

        raise RuntimeError(f"MiniMax request failed: {last_err}") from last_err


def _messages_to_plaintext(messages: list[Any]) -> tuple[str, str]:
    """Return (system_text, user_text) from a LangChain-style messages list."""

    system_parts: list[str] = []
    user_parts: list[str] = []
    for m in messages:
        role = getattr(m, "type", None) or getattr(m, "role", None)
        content = getattr(m, "content", m)
        if not isinstance(content, str):
            content = str(content)
        content = content.strip()
        if not content:
            continue
        if role == "system":
            system_parts.append(content)
        elif role in {"human", "user"}:
            user_parts.append(content)
        else:
            # For tool/assistant messages, keep them as context inside user text.
            user_parts.append(f"[{role}] {content}" if role else content)

    return ("\n\n".join(system_parts).strip(), "\n\n".join(user_parts).strip())


def _extract_gemini_text(response_json: dict[str, Any]) -> str:
    """Best-effort extract assistant text from a Gemini generateContent response."""

    candidates = response_json.get("candidates")
    if isinstance(candidates, list) and candidates:
        c0 = candidates[0]
        if isinstance(c0, dict):
            content = c0.get("content")
            if isinstance(content, dict):
                parts = content.get("parts")
                if isinstance(parts, list) and parts:
                    p0 = parts[0]
                    if isinstance(p0, dict) and isinstance(p0.get("text"), str):
                        return p0["text"]
            # Some proxies may return "output" fields
            for k in ("output", "text"):
                v = c0.get(k)
                if isinstance(v, str) and v.strip():
                    return v

    for k in ("text", "output_text", "result"):
        v = response_json.get(k)
        if isinstance(v, str) and v.strip():
            return v

    raise KeyError("Unable to extract text from Gemini response")


class GeminiGenerateContentClient:
    """Minimal Gemini generateContent client (v1beta REST)."""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        auth_mode: str = "auto",
        temperature: float = 0.0,
        timeout_s: float = 60.0,
        max_retries: int = 0,
    ) -> None:
        self.api_key = (api_key or "").strip()
        self.base_url = (base_url or "").strip().rstrip("/")
        self.model = (model or "").strip()
        self.auth_mode = (auth_mode or "").strip().lower() or "auto"
        self.temperature = float(temperature)
        self.timeout_s = timeout_s
        self.max_retries = max(0, int(max_retries))

    def _endpoint(self) -> str:
        # base_url is expected like: https://.../v1beta/models
        # generateContent endpoint: POST {base_url}/{model}:generateContent
        return f"{self.base_url}/{self.model}:generateContent"

    def _request(self, *, url: str, payload: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            method="POST",
            headers=headers,
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                body = resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Gemini HTTP {e.code}: {detail}") from e

        return json.loads(body)

    def invoke(self, messages: list[Any]) -> str:
        system_text, user_text = _messages_to_plaintext(messages)
        if not user_text:
            user_text = ""

        payload: dict[str, Any] = {
            "contents": [{"role": "user", "parts": [{"text": user_text}]}],
            "generationConfig": {"temperature": self.temperature},
        }
        if system_text:
            # Some endpoints accept systemInstruction; keep it best-effort.
            payload["systemInstruction"] = {"parts": [{"text": system_text}]}

        base = self._endpoint()

        def _headers(*, bearer: bool) -> dict[str, str]:
            h = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "xhs_an_agent/1.0",
            }
            if bearer and self.api_key:
                h["Authorization"] = f"Bearer {self.api_key}"
            if self.api_key:
                h["x-goog-api-key"] = self.api_key
            return h

        def _with_key(url: str) -> str:
            if not self.api_key:
                return url
            sep = "&" if "?" in url else "?"
            return f"{url}{sep}key={urllib.parse.quote(self.api_key)}"

        attempts: list[tuple[str, dict[str, str]]] = []
        if self.auth_mode == "bearer":
            attempts = [(base, _headers(bearer=True))]
        elif self.auth_mode == "query":
            attempts = [(_with_key(base), _headers(bearer=False))]
        elif self.auth_mode == "header":
            attempts = [(base, _headers(bearer=False))]
        else:
            # auto: try query+header first, then bearer (common for proxies)
            attempts = [(_with_key(base), _headers(bearer=False)), (base, _headers(bearer=True))]

        last_err: Exception | None = None
        for attempt in range(self.max_retries + 1):
            for url, headers in attempts:
                try:
                    j = self._request(url=url, payload=payload, headers=headers)
                    return _extract_gemini_text(j)
                except Exception as e:
                    last_err = e
                    continue
            if attempt < self.max_retries:
                time.sleep(min(2**attempt, 8))
                continue
            break

        # Payload fallback: some proxies don't support systemInstruction.
        if system_text:
            payload2 = dict(payload)
            payload2.pop("systemInstruction", None)
            payload2["contents"] = [
                {
                    "role": "user",
                    "parts": [{"text": f"{system_text}\n\n{user_text}".strip()}],
                }
            ]
            for attempt in range(self.max_retries + 1):
                for url, headers in attempts:
                    try:
                        j = self._request(url=url, payload=payload2, headers=headers)
                        return _extract_gemini_text(j)
                    except Exception as e:
                        last_err = e
                        continue
                if attempt < self.max_retries:
                    time.sleep(min(2**attempt, 8))
                    continue
                break

        raise RuntimeError(f"Gemini request failed: {last_err}") from last_err
