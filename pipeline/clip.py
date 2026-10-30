"""Describe an input video. Videos are used as given; any splitting happens beforehand."""

from __future__ import annotations

import json
import subprocess
from fractions import Fraction
from pathlib import Path


def probe(video: Path) -> dict:
    """Return the frame count, frame rate, size and duration of `video`."""

    result = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_packets",
         "-show_entries", "stream=nb_read_packets,r_frame_rate,width,height",
         "-of", "json", str(video)],
        capture_output=True, text=True, check=True,
    )
    stream = json.loads(result.stdout)["streams"][0]
    fps = Fraction(stream["r_frame_rate"])
    frames = int(stream["nb_read_packets"])
    return {
        "frames": frames,
        "fps": float(fps),
        "width": int(stream["width"]),
        "height": int(stream["height"]),
        "duration": round(frames / float(fps), 3),
    }
