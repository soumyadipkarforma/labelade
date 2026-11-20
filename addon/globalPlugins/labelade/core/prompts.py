"""What we ask the vision model. Kept short: small models follow short instructions best."""

from .client import image_part

LABEL_SYSTEM = (
	"You name controls in software for blind people who use a screen reader. "
	"You answer with JSON only."
)

DESCRIBE_SYSTEM = (
	"You describe what is on a computer screen for a blind person using a screen reader. "
	"Be accurate and concrete. Read out important text exactly. Never guess at things you can't see; say when "
	"something is unclear. Use short paragraphs and no markdown tables."
)


def label_messages(png: bytes, role: str, app: str, window: str) -> list[dict]:
	text = (
		f"The {role} inside the red box has no accessible name. App: {app}. Window: {window or 'unknown'}.\n"
		f"What does it do? Reply as JSON: {{\"label\": \"...\", \"confidence\": \"high\" or \"low\"}}\n"
		"The label is 1 to 4 words naming its action or purpose, like \"Send message\", \"Mute microphone\", "
		"\"Close\", \"Settings\" or \"Add attachment\". If it shows text, use that text. "
		f"Don't include the word {role}. If you can't tell, use \"unknown\"."
	)
	return [
		{"role": "system", "content": LABEL_SYSTEM},
		{"role": "user", "content": [image_part(png), {"type": "text", "text": text}]},
	]


def describe_messages(png: bytes, what: str, app: str, window: str) -> list[dict]:
	text = (
		f"Describe this {what} from the app {app} (window: {window or 'unknown'}). "
		"Start with one sentence on what it is. Then the main content and any text, then controls a person could use."
	)
	return [
		{"role": "system", "content": DESCRIBE_SYSTEM},
		{"role": "user", "content": [image_part(png), {"type": "text", "text": text}]},
	]
