"""P15b: print the cached raw OCR / Grounding DINO boxes (debug helper)."""
import sys
from p15b_common import *  # noqa
for ms in sys.argv[1].split(","):
    for c in sys.argv[2].split(","):
        k = load_cache(ms, c)
        print(ms, c)
        for key in ("ocr", "gdino"):
            for r in k[key]:
                print("  ", key, [round(v) for v in r["box"]], r["type"], round(r["confidence"], 2))
