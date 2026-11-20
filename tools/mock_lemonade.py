"""A stand-in for Lemonade Server, for tests and for trying the add-on without a model.

Run:  python tools/mock_lemonade.py            (listens on 13305, like Lemonade)
      python tools/mock_lemonade.py --port 13399

It answers the endpoints Labelade uses with fixed, obviously fake replies.
"""

import argparse
import base64
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MODELS = [
	{"id": "Qwen3-0.6B-GGUF", "labels": ["chat"], "recipe": "llamacpp", "downloaded": True},
	{"id": "Gemma-3-4b-it-GGUF", "labels": ["chat", "vision"], "recipe": "llamacpp", "downloaded": True},
	{"id": "Qwen3-VL-4B-Instruct-GGUF", "labels": ["chat", "vision"], "recipe": "llamacpp", "downloaded": True},
]


def default_reply(messages: list[dict]) -> str:
	prompt = " ".join(part.get("text", "") for m in messages if isinstance(m.get("content"), list) for part in m["content"])
	if "red box" in prompt:
		return '{"label": "Send message", "confidence": "high"}'
	if messages[-1]["role"] == "user" and isinstance(messages[-1]["content"], str):
		return f"(mock) You asked: {messages[-1]['content']}"
	return "(mock) A chat window with a message box and a send button."


class MockLemonade:
	def __init__(self, port: int = 0, api_key: str = "", models=None, loaded=(), reply=default_reply):
		self.requests: list[dict] = []
		self.models, self.loaded, self.reply, self.api_key = list(models if models is not None else MODELS), list(loaded), reply, api_key
		mock = self

		class Handler(BaseHTTPRequestHandler):
			def log_message(self, *args):
				pass

			def _send(self, code: int, body: dict):
				data = json.dumps(body).encode()
				self.send_response(code)
				self.send_header("Content-Type", "application/json")
				self.send_header("Content-Length", str(len(data)))
				self.end_headers()
				self.wfile.write(data)

			def _authorised(self) -> bool:
				if mock.api_key and self.headers.get("Authorization") != f"Bearer {mock.api_key}":
					self._send(401, {"error": {"message": "Invalid API key"}})
					return False
				return True

			def do_GET(self):
				if not self._authorised():
					return
				path = self.path.split("?")[0].replace("/api/v1", "/v1")
				if path == "/v1/models":
					self._send(200, {"object": "list", "data": mock.models})
				elif path == "/v1/health":
					self._send(200, {"status": "ok", "version": "mock", "all_models_loaded": [{"model_name": m} for m in mock.loaded]})
				else:
					self._send(404, {"error": {"message": "not found"}})

			def do_POST(self):
				if not self._authorised():
					return
				body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
				mock.requests.append(body)
				if self.path.replace("/api/v1", "/v1") == "/v1/pull":
					mock.models.append({"id": body["model_name"], "labels": ["chat", "vision"], "recipe": "llamacpp", "downloaded": True})
					self._send(200, {"model_name": body["model_name"], "status": "success"})
					return
				if self.path.replace("/api/v1", "/v1") != "/v1/chat/completions":
					self._send(404, {"error": {"message": "not found"}})
					return
				if body.get("model") not in {m["id"] for m in mock.models}:
					self._send(404, {"error": {"message": f"model {body.get('model')} not found"}})
					return
				for m in body.get("messages", []):
					for part in m["content"] if isinstance(m.get("content"), list) else []:
						if part.get("type") == "image_url":
							png = base64.b64decode(part["image_url"]["url"].split(",", 1)[1])
							if not png.startswith(b"\x89PNG"):
								self._send(400, {"error": {"message": "image is not a PNG"}})
								return
				content = mock.reply(body["messages"])
				self._send(200, {"choices": [{"index": 0, "message": {"role": "assistant", "content": content}, "finish_reason": "stop"}]})

		self.server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
		self.url = f"http://127.0.0.1:{self.server.server_address[1]}/api/v1"
		threading.Thread(target=self.server.serve_forever, daemon=True).start()

	def close(self):
		self.server.shutdown()
		self.server.server_close()


if __name__ == "__main__":
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--port", type=int, default=13305)
	args = parser.parse_args()
	mock = MockLemonade(args.port, loaded=["Qwen3-VL-4B-Instruct-GGUF"])
	print(f"Mock Lemonade at {mock.url} (Ctrl+C to stop)")
	try:
		threading.Event().wait()
	except KeyboardInterrupt:
		mock.close()
