import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List

from PIL import Image


ASSETS_DIR = Path(__file__).resolve().parents[1] / "assets"
PATTERN = re.compile(r"^(?P<idx>\d+)_((?P<type>до|после))\.(?P<ext>jpg|jpeg|png)$", re.IGNORECASE)


@dataclass
class BeforeAfterPair:
    index: int
    before_path: Path
    after_path: Path


def _collect_pairs() -> List[BeforeAfterPair]:
    pairs = {}
    if not ASSETS_DIR.exists():
        return []
    for entry in os.listdir(ASSETS_DIR):
        match = PATTERN.match(entry)
        if not match:
            continue
        idx = int(match.group("idx"))
        kind = match.group("type").lower()
        path = ASSETS_DIR / entry
        item = pairs.get(idx, {"before": None, "after": None})
        if kind == "до":
            item["before"] = path
        else:
            item["after"] = path
        pairs[idx] = item

    result: List[BeforeAfterPair] = []
    for idx in sorted(pairs.keys()):
        item = pairs[idx]
        if item["before"] and item["after"]:
            result.append(
                BeforeAfterPair(index=idx, before_path=item["before"], after_path=item["after"])
            )
    return result


def list_before_after_pairs() -> List[BeforeAfterPair]:
    return _collect_pairs()


def build_collage(before_path: Path, after_path: Path) -> Path:
    with Image.open(before_path) as before_img, Image.open(after_path) as after_img:
        before = before_img.convert("RGB")
        after = after_img.convert("RGB")

    max_height = 800
    target_height = min(max_height, max(before.height, after.height))

    def _resize(image: Image.Image) -> Image.Image:
        if image.height == target_height:
            return image
        ratio = target_height / image.height
        width = int(image.width * ratio)
        return image.resize((width, target_height), Image.LANCZOS)

    before_resized = _resize(before)
    after_resized = _resize(after)

    total_width = before_resized.width + after_resized.width
    collage = Image.new("RGB", (total_width, target_height), (255, 255, 255))
    collage.paste(before_resized, (0, 0))
    collage.paste(after_resized, (before_resized.width, 0))

    output_path = Path(f"/tmp/before_after_{before_path.stem}_{after_path.stem}.jpg")
    collage.save(output_path, format="JPEG", quality=85, optimize=True)
    return output_path
