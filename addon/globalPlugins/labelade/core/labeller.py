"""Talks to the model on a background thread so NVDA never freezes while a label is generated."""

import queue
import threading
from collections.abc import Callable

from . import heuristics, prompts
from .client import LemonadeClient, LemonadeError


class Labeller:
	"""Turns screenshots into labels and descriptions. Remembers which model to use."""

	def __init__(self, client_factory: Callable[[], LemonadeClient], model_setting: Callable[[], str]):
		self._client_factory = client_factory
		self._model_setting = model_setting
		self._model = ""
		self._conversation: list[dict] = []

	def _client_and_model(self) -> tuple[LemonadeClient, str]:
		client = self._client_factory()
		if not self._model or self._model_setting():
			self._model = client.pick_vision_model(self._model_setting())
		return client, self._model

	def label(self, png: bytes, role: str, app: str, window: str) -> tuple[str | None, str, str]:
		"""Returns (label or None, confidence, model)."""
		client, model = self._client_and_model()
		try:
			text = client.chat(model, prompts.label_messages(png, role, app, window), max_tokens=64)
		except LemonadeError:
			self._model = ""  # the model may have been deleted; pick again next time
			raise
		label, confidence = heuristics.parse_label(text, role)
		return label, confidence, model

	def describe(self, png: bytes, what: str, app: str, window: str) -> str:
		client, model = self._client_and_model()
		messages = prompts.describe_messages(png, what, app, window)
		answer = heuristics.strip_thinking(client.chat(model, messages, max_tokens=700))
		self._conversation = [*messages, {"role": "assistant", "content": answer}]
		return answer

	@property
	def can_follow_up(self) -> bool:
		return bool(self._conversation)

	def ask(self, question: str) -> str:
		"""Follow-up question about the last described image."""
		if not self._conversation:
			raise LemonadeError("Describe something first, then ask about it.")
		client, model = self._client_and_model()
		messages = [*self._conversation, {"role": "user", "content": question}]
		answer = heuristics.strip_thinking(client.chat(model, messages, max_tokens=700))
		self._conversation = [*messages, {"role": "assistant", "content": answer}]
		return answer


class Worker:
	"""One background thread; results are handed back through `post` (NVDA's main-thread queue)."""

	def __init__(self, post: Callable[..., None]):
		self._post = post
		# Newest first: after fast tabbing, the control the user is on now is labelled next.
		self._jobs: queue.LifoQueue = queue.LifoQueue()
		self._pending: set = set()
		self._lock = threading.Lock()
		self._generation = 0
		self._thread = threading.Thread(target=self._run, name="labelade", daemon=True)
		self._thread.start()

	def submit(self, key, work: Callable[[], object], done: Callable[[object, Exception | None], None]) -> bool:
		"""Queue work unless the same key is already waiting. Returns False for duplicates."""
		with self._lock:
			if key in self._pending:
				return False
			self._pending.add(key)
			self._jobs.put((self._generation, key, work, done))
		return True

	def cancel_all(self) -> None:
		with self._lock:
			self._generation += 1
			self._pending.clear()

	def stop(self) -> None:
		self.cancel_all()
		self._jobs.put(None)

	def _run(self) -> None:
		while (job := self._jobs.get()) is not None:
			generation, key, work, done = job
			with self._lock:
				if generation != self._generation:
					continue
			try:
				result, error = work(), None
			except Exception as e:  # reported to the user via done(); the thread must survive
				result, error = None, e
			with self._lock:
				current = generation == self._generation
				self._pending.discard(key)
			if current:
				self._post(done, result, error)
