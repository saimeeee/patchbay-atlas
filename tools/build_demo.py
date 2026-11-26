"""Rebuild the static Pages demo with a small fictional radio project."""
from datetime import datetime, timedelta, timezone
from hashlib import sha1
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from atlas import render


# Subjects and paths tell a small story; all authors, hashes and counts are synthetic.
HISTORY = """
Build the first receiver graph|engine/graph.py signals/receiver.py
Document the six-band receiver|docs/receiver.md
Add a dial for tuning by ear|interface/dial.js
Feed a sine wave into the receiver|signals/wave.py engine/graph.py
Record reference tones for the test bench|fixtures/tones.json
Give each station a stable identity|engine/station.py
Add a station readout to the dial|interface/readout.js interface/dial.js
Describe how the mixer sums channels|docs/mixer.md engine/mixer.py
Seed the test band with local stations|tools/seed.py fixtures/stations.json
Move frequency validation into the receiver|signals/receiver.py engine/station.py
Display clipping on the output meter|interface/meter.js engine/mixer.py
Recover the last known station on startup|engine/state.py
Ship a reference recording for calibration|fixtures/reference.wav
Explain the calibration sequence|docs/calibration.md
Cache the last three tuning positions|engine/state.py interface/dial.js
Add a noise floor to weak stations|signals/noise.py engine/mixer.py
Mark the active band on small screens|interface/dial.css
Smooth volume changes between buffers|engine/envelope.py
Export a compact station catalogue|tools/export.py engine/station.py
Tune the meter falloff by ear|interface/meter.js
Generate pink noise for the shortwave band|signals/noise.py
Avoid a click when the channel closes|engine/envelope.py signals/receiver.py
Label the scan interval on the tuning dial|interface/dial.js
Sketch the station discovery sequence|docs/discovery.md
Save scan results as a deterministic fixture|tools/scan.py fixtures/scan.json
Index stations by their carrier frequency|engine/station.py engine/index.py
Add keyboard controls for fine tuning|interface/keyboard.js interface/dial.js
Clamp oscillator drift near the band edge|signals/wave.py engine/graph.py
Support an empty station catalogue|engine/index.py
Draw tick marks at even frequency intervals|interface/dial.css
Update the band map for night listening|docs/bands.md
Add a soft knee to the output limiter|engine/mixer.py signals/limiter.py
Give mono recordings a centered readout|interface/meter.js engine/mixer.py
Capture a silent frame for the noise tests|fixtures/silence.wav signals/noise.py
Keep the station name while retuning|engine/state.py interface/readout.js
Report median scan time in the benchmark|tools/bench.py
Debounce repeated changes from the dial|interface/dial.js engine/graph.py
Show the last carrier when reception fades|interface/readout.js signals/receiver.py
Publish a field guide to weak signals|docs/field-guide.md
Restart the graph after an interrupted scan|engine/graph.py
Compare limiter output against reference audio|signals/limiter.py fixtures/reference.wav
Draw a wider scale for the longwave band|interface/dial.css
Split station lookup from signal routing|engine/index.py engine/graph.py
Include the band name in exported presets|tools/export.py engine/state.py
Carry the tuning offset across band changes|engine/state.py interface/dial.js
Make the dial announce the selected station|interface/readout.js docs/controls.md
Reduce envelope noise between stations|engine/envelope.py signals/noise.py
Preserve named stations after a rescan|engine/index.py engine/station.py
""".strip()


def build_demo():
    authors = ["Mira Vale", "Finn Aalto", "Iris North", "Arden Lu", "Jules Wren"]
    start = datetime(2025, 3, 4, 9, 20, tzinfo=timezone.utc)
    commits = []
    for i, line in enumerate(HISTORY.splitlines()):
        subject, paths = line.split("|")
        oid = sha1(("fictional relay station: " + line).encode()).hexdigest()
        day = start + timedelta(days=i * 1.62 + (i % 3) * .48, hours=i % 7)
        changes = []
        for j, path in enumerate(paths.split()):
            binary = path.endswith(".wav")
            changes.append([path, None if binary else 2 + (i * 17 + j * 3) % 62,
                            None if binary else (i * 3 + j * 13) % 24])
        commits.append({"id": oid, "time": int(day.timestamp()), "subject": subject,
                        "author": authors[(i * i + i // 4) % len(authors)], "files": changes})
    return {"repo": "relay-station", "ref": "main", "demo": True, "commits": commits[::-1]}


if __name__ == "__main__":
    base_url = "https://saimeeee.github.io/patchbay-atlas/"
    description = "Explore a topographic map of Git history. Replay commits, inspect files and export your own map."
    social = f"""
<meta name="description" content="{description}">
<meta property="og:type" content="website">
<meta property="og:title" content="Patchbay Atlas — Git history, mapped">
<meta property="og:description" content="{description}">
<meta property="og:url" content="{base_url}">
<meta property="og:image" content="{base_url}docs/preview.png">
<meta property="og:image:alt" content="A topographic map of the fictional relay-station Git repository">
<meta name="twitter:card" content="summary_large_image">"""
    meta_lines = "\n".join("    " + line for line in social.strip().splitlines())
    html = render(build_demo()).replace("  </head>", meta_lines + "\n  </head>", 1)
    (ROOT / "index.html").write_bytes(html.encode("utf-8"))
