"""Tiny image helpers in pure Python: NVDA ships no imaging library.

Pixels are 32-bit BGRX, top-down, the layout NVDA's screenBitmap returns.
"""

import struct
import zlib
from dataclasses import dataclass


@dataclass
class Image:
	width: int
	height: int
	bgra: bytes  # len == width * height * 4

	def __post_init__(self):
		if len(self.bgra) != self.width * self.height * 4:
			raise ValueError("pixel buffer does not match the image size")

	def draw_box(self, left: int, top: int, width: int, height: int, thickness: int = 3, bgr=(0, 0, 255)) -> "Image":
		"""Return a copy with a rectangle outline (red by default) so the model knows which control we mean."""
		px = bytearray(self.bgra)
		colour = bytes((*bgr, 255))
		right, bottom = left + width - 1, top + height - 1
		for t in range(thickness):
			for y in (top - t, bottom + t):
				if 0 <= y < self.height:
					x0, x1 = max(0, left - t), min(self.width - 1, right + t)
					if x0 <= x1:
						row = y * self.width * 4
						px[row + x0 * 4:row + (x1 + 1) * 4] = colour * (x1 - x0 + 1)
			for x in (left - t, right + t):
				if 0 <= x < self.width:
					for y in range(max(0, top - t), min(self.height, bottom + t + 1)):
						i = (y * self.width + x) * 4
						px[i:i + 4] = colour
		return Image(self.width, self.height, bytes(px))

	def to_png(self) -> bytes:
		rgb = bytearray(self.width * self.height * 3)
		rgb[0::3] = self.bgra[2::4]
		rgb[1::3] = self.bgra[1::4]
		rgb[2::3] = self.bgra[0::4]
		stride = self.width * 3
		raw = b"".join(b"\x00" + rgb[y * stride:(y + 1) * stride] for y in range(self.height))

		def chunk(kind: bytes, data: bytes) -> bytes:
			return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

		header = struct.pack(">IIBBBBB", self.width, self.height, 8, 2, 0, 0, 0)
		return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b"")

	def _grey_grid(self, cols: int, rows: int) -> list[float]:
		"""Box-average the image down to cols x rows greyscale values."""
		out = []
		for r in range(rows):
			y0, y1 = r * self.height // rows, max(r * self.height // rows + 1, (r + 1) * self.height // rows)
			for c in range(cols):
				x0, x1 = c * self.width // cols, max(c * self.width // cols + 1, (c + 1) * self.width // cols)
				total = n = 0
				for y in range(y0, y1):
					base = y * self.width * 4
					for x in range(x0, x1):
						i = base + x * 4
						total += self.bgra[i] * 0.114 + self.bgra[i + 1] * 0.587 + self.bgra[i + 2] * 0.299
						n += 1
				out.append(total / n)
		return out

	def dhash(self) -> str | None:
		"""64-bit difference hash as 16 hex chars, or None for flat images that would match anything."""
		grid = self._grey_grid(9, 8)
		if max(grid) - min(grid) < 8:
			return None
		bits = 0
		for r in range(8):
			for c in range(8):
				bits = (bits << 1) | (grid[r * 9 + c] > grid[r * 9 + c + 1])
		return f"{bits:016x}"


def hamming(a: str, b: str) -> int:
	return bin(int(a, 16) ^ int(b, 16)).count("1")


def context_rect(left: int, top: int, width: int, height: int, bounds: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
	"""Grow a control's rectangle so the model sees its neighbours, clamped to the screen bounds (l, t, w, h)."""
	pad = max(48, int(max(width, height) * 1.5))
	bl, bt, bw, bh = bounds
	x0, y0 = max(bl, left - pad), max(bt, top - pad)
	x1, y1 = min(bl + bw, left + width + pad), min(bt + bh, top + height + pad)
	return x0, y0, max(1, x1 - x0), max(1, y1 - y0)


def fit_size(width: int, height: int, smallest: int = 336, largest: int = 1024) -> tuple[int, int]:
	"""Output size for a capture: upscale tiny regions (models read small icons badly), downscale huge ones."""
	longest = max(width, height)
	scale = smallest / longest if longest < smallest else (largest / longest if longest > largest else 1.0)
	return max(1, round(width * scale)), max(1, round(height * scale))
