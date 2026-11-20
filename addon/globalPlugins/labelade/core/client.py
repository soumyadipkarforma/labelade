"""Minimal Lemonade Server client on the standard library (NVDA add-ons can't pip install)."""

import base64
import json
import urllib.error
import urllib.parse
import urllib.request

DEFAULT_URL = "http://localhost:13305/api/v1"
# Small vision models in Lemonade's catalogue, best first for reading UI icons and text.
PREFERRED_MODELS = (
	"Qwen3-VL-4B-Instruct-GGUF",
	"Qwen3.5-4B-GGUF",
	"Gemma-4-E4B-it-GGUF",
	"Gemma-3-4b-it-GGUF",
	"Qwen3.5-2B-GGUF",
	"Ministral-3-3B-Instruct-2512-GGUF",
)


class LemonadeError(Exception):
	"""Raised with a message that is safe and useful to speak to the user."""


class NoVisionModel(LemonadeError):
	"""Lemonade is running but has no vision model downloaded."""


def is_local(url: str) -> bool:
	host = (urllib.parse.urlparse(url).hostname or "").lower()
	return host in ("localhost", "127.0.0.1", "::1") or host.endswith(".localhost")


def image_part(png: bytes) -> dict:
	return {"type": "image_url", "image_url": {"url": "data:image/png;base64," + base64.b64encode(png).decode("ascii")}}


class LemonadeClient:
	def __init__(self, base_url: str = DEFAULT_URL, api_key: str = "", timeout: float = 120):
		self.base_url = (base_url or DEFAULT_URL).rstrip("/")
		self.api_key = api_key
		self.timeout = timeout

	def _request(self, method: str, path: str, body: dict | None = None) -> dict:
		headers = {"Content-Type": "application/json"}
		if self.api_key:
			headers["Authorization"] = f"Bearer {self.api_key}"
		data = json.dumps(body).encode() if body is not None else None
		req = urllib.request.Request(self.base_url + path, data=data, headers=headers, method=method)
		try:
			with urllib.request.urlopen(req, timeout=self.timeout) as res:
				return json.loads(res.read().decode("utf-8"))
		except urllib.error.HTTPError as e:
			detail = e.read().decode("utf-8", "replace")[:300]
			e.close()
			if e.code == 401:
				raise LemonadeError("Lemonade rejected the API key. Check it in Labelade settings.") from e
			raise LemonadeError(f"Lemonade returned error {e.code}: {detail}") from e
		except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
			raise LemonadeError(f"Can't reach Lemonade at {self.base_url}. Is Lemonade Server running?") from e
		except ValueError as e:
			raise LemonadeError("Lemonade sent a reply Labelade couldn't read.") from e

	def models(self) -> list[dict]:
		return self._request("GET", "/models").get("data", [])

	def health(self) -> dict:
		return self._request("GET", "/health")

	def pick_vision_model(self, preferred: str = "") -> str:
		"""The configured model, else a loaded vision model, else the best downloaded one."""
		if preferred:
			return preferred
		vision = [m["id"] for m in self.models() if "vision" in (m.get("labels") or [])]
		if not vision:
			raise NoVisionModel(
				"No vision model is downloaded in Lemonade. Download one, for example "
				"Qwen3-VL-4B-Instruct-GGUF, in the Lemonade app's model manager."
			)
		try:
			loaded = [m.get("model_name") for m in self.health().get("all_models_loaded") or []]
		except LemonadeError:
			loaded = []
		for model in loaded:
			if model in vision:
				return model
		for model in PREFERRED_MODELS:
			if model in vision:
				return model
		return vision[0]

	def pull(self, model: str) -> None:
		"""Download a model from Lemonade's catalogue. Blocks until done, so give this client a long timeout."""
		self._request("POST", "/pull", {"model_name": model, "stream": False})

	def chat(self, model: str, messages: list[dict], max_tokens: int = 256) -> str:
		reply = self._request("POST", "/chat/completions", {
			"model": model,
			"messages": messages,
			"max_tokens": max_tokens,
			"temperature": 0,
			"stream": False,
			"enable_thinking": False,  # Lemonade extension; thinking only adds delay for a 2-word label
		})
		try:
			return reply["choices"][0]["message"].get("content") or ""
		except (KeyError, IndexError, TypeError) as e:
			raise LemonadeError("Lemonade's reply had no message in it.") from e
