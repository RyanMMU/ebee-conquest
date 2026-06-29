import json
from threading import RLock
import urllib.error
import urllib.request

from .provider import AIProviderError


class OpenAICompatibleProvider:
    """Small dependency-free client for OpenAI-compatible chat endpoints."""

    def __init__(
        self,
        name,
        base_url,
        model,
        api_key=None,
        timeout=45,
        provider_label=None,
    ):
        self.name = str(name)
        self.provider_label = str(provider_label or name)
        self._lock = RLock()
        self.api_key = api_key
        self.model = str(model)
        self.base_url = str(base_url).rstrip("/")
        self.timeout = int(timeout)

    def configure(self, **config):
        allowedkeys = {"api_key", "model", "base_url", "timeout"}
        unknownkeys = sorted(set(config) - allowedkeys)
        if unknownkeys:
            raise ValueError(
                f"{self.provider_label} does not recognize config value(s): "
                f"{', '.join(unknownkeys)}."
            )
        with self._lock:
            for key, value in config.items():
                if key == "base_url":
                    value = str(value).rstrip("/")
                elif key == "timeout":
                    value = int(value)
                elif key == "model":
                    value = str(value)
                setattr(self, key, value)

    def ask(self, prompt):
        with self._lock:
            api_key = self.api_key
            model = self.model
            base_url = self.base_url
            timeout = self.timeout

        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.35,
            "max_tokens": 500,
        }
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        request = urllib.request.Request(
            f"{base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                rawbody = response.read().decode("utf-8")
        except urllib.error.HTTPError as error:
            raise AIProviderError(
                f"{self.provider_label} request failed: {self._readerrormessage(error)}"
            ) from error
        except urllib.error.URLError as error:
            raise AIProviderError(
                f"Could not connect to {self.provider_label}. Check the endpoint and connection."
            ) from error
        except TimeoutError as error:
            raise AIProviderError(
                f"{self.provider_label} took too long to respond."
            ) from error

        try:
            data = json.loads(rawbody)
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as error:
            raise AIProviderError(
                f"{self.provider_label} returned an unexpected response."
            ) from error
        return str(content).strip()

    @staticmethod
    def _readerrormessage(error):
        fallback = f"HTTP {error.code}"
        try:
            body = error.read().decode("utf-8")
            data = json.loads(body)
        except (UnicodeDecodeError, json.JSONDecodeError):
            return fallback
        detail = data.get("error") if isinstance(data, dict) else None
        if isinstance(detail, dict):
            return str(detail.get("message") or fallback)
        if isinstance(detail, str):
            return detail
        return fallback
