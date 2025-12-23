"""
create_sprites.py

Utility to generate individual grenade animation frames via the OpenAI Images API
and save them as PNGs into assets/sprites/.

Usage (after setting OPENAI_API_KEY in your environment and installing openai>=1.0):

    python3 utils/create_sprites.py

This will create:

    assets/sprites/grenade_00.png
    ...
    assets/sprites/grenade_23.png
"""

import os
import base64
from pathlib import Path

from PIL import Image, ImageDraw
from openai import OpenAI

# ---------------------------------------------------------------------------
# 1. Frame descriptions (single source of truth)
# ---------------------------------------------------------------------------

FRAME_DESCRIPTIONS = {
    1: "Grenade entering from the right on a shallow arc, barely above the ground.",
    2: "Grenade moving leftward, slightly higher than before along the arc.",
    3: "Grenade reaching its small peak, only about half a grenade height above the ground.",
    4: "Grenade descending along the arc toward the ground.",
    5: "Grenade just about to touch down on the floor.",
    6: "First contact with the floor: tiny squash, tiny dust puff, small 'thnk!' comic text.",

    7: "Grenade rising from the first bounce, a small rebound.",
    8: "Grenade at the modest peak of the first bounce, about one-third to one-half grenade height.",
    9: "Grenade descending from the first bounce rebound toward the floor.",
    10: "Grenade hitting the floor again, second ground contact with minimal squash.",
    11: "Grenade making a small sideways hop as the second bounce begins.",
    12: "Micro peak of the second bounce, about one-quarter grenade height, tiny 'tik!' comic text.",

    13: "Grenade landing again with almost no squash, close to rest.",
    14: "Tiny micro-hop or wobble of the grenade for the third bounce.",
    15: "Grenade settling on the floor, rotated slightly or rolled a few pixels.",
    16: "Grenade fully settled on the floor, fuse clearly visible.",
    17: "Fuse begins sparking, faint glowing outline around the grenade.",
    18: "Stronger glow and spark from the fuse, grenade slightly scaled up (about 4%).",

    19: "Very bright frame: white or yellow flash with the grenade silhouette.",
    20: "Full comic explosion: jagged yellow core, orange mid-layer, red outer burst, bold 'KA-BOOM!' text.",
    21: "Explosion expanded, slight vibration feeling, smoke beginning to form.",
    22: "Explosion fading into smoke clouds above the floor.",
    23: "Mostly smoke plumes rising, residual glow where the grenade was.",
    24: "Final settling smoke, no grenade visible, just lingering smoke on a transparent background."
}

BASE_STYLE_PROMPT = """
You are drawing a single frame of a 24-frame grenade animation for a 2D mobile game.

Art style:
- Comic-book style
- Thick black outlines
- Clean flat colors
- Slight halftone shading
- Crisp and readable at small size

Subject:
- A small, iconic hand grenade in a simple 'ball room' or arena, with a clear, flat floor line.
- The grenade should keep consistent proportions, lighting, and camera angle across all frames.
- The floor line should stay in the same position in all frames; if the grenade is in the air, it is above this floor.

Technical requirements:
- Transparent background
- Center the grenade and its effects within the frame
- No borders, no extra labels other than very subtle sound text like 'thnk!' or 'tik!' where specified
- Draw only ONE frame per image (no grids, no multiple panels)
"""


# ---------------------------------------------------------------------------
# 2. Prompt builder
# ---------------------------------------------------------------------------

def build_frame_prompt(frame_index: int) -> str:
    """
    Build the full DALL-E / gpt-image-1 prompt string for a single frame.
    """
    desc = FRAME_DESCRIPTIONS[frame_index]
    return (
        f"{BASE_STYLE_PROMPT}\n\n"
        f"You are drawing frame {frame_index:02d} of 24 in the animation sequence.\n"
        f"Frame description:\n"
        f"{desc}\n\n"
        "Make sure this frame looks like one moment in a smooth animation, with the same "
        "grenade design and floor position as the other frames in the sequence."
    )


# ---------------------------------------------------------------------------
# 3. Output directory helper
# ---------------------------------------------------------------------------

def get_sprites_output_dir() -> Path:
    """
    Returns the absolute path to assets/sprites and ensures it exists.
    """
    base_dir = Path(__file__).resolve().parent
    out_dir = (base_dir.parent / "assets" / "sprites").resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


# ---------------------------------------------------------------------------
# 4. OpenAI image generation helpers
# ---------------------------------------------------------------------------

def generate_frame_png(client: OpenAI, frame_index: int, size: str = "512x512") -> Path:
    """
    Generate a single PNG frame using the OpenAI Images API and save it as
    assets/sprites/grenade_XX.png, where XX runs 00..23 for frames 1..24.

    Note: Assumes OPENAI_API_KEY is set in the environment, or the OpenAI
    client is otherwise configured.
    """
    out_dir = get_sprites_output_dir()
    prompt = build_frame_prompt(frame_index)

    print(f"[OPENAI] Generating frame {frame_index:02d} -> grenade_{frame_index-1:02d}.png")

    response = client.images.generate(
        model="gpt-image-1",
        prompt=prompt,
        size=size,
        n=1,
    )

    image_b64 = response.data[0].b64_json
    image_bytes = base64.b64decode(image_b64)

    # Our game expects 0-based indices in filenames: 00..23
    filename = f"grenade_{frame_index-1:02d}.png"
    out_path = out_dir / filename

    with open(out_path, "wb") as f:
        f.write(image_bytes)

    print(f"[WRITE] {out_path}")
    return out_path


def generate_all_frames(size: str = "512x512"):
    """
    Generate all 24 frames using the OpenAI Images API.
    """
    # The client will pick up OPENAI_API_KEY from the environment.
    client = OpenAI()

    for frame_index in range(1, 25):
        try:
            generate_frame_png(client, frame_index, size=size)
        except Exception as exc:
            print(f"[ERROR] Failed to generate frame {frame_index:02d}: {exc}")
            # Optional: break or continue depending on how robust you want it
            continue


# ---------------------------------------------------------------------------
# 5. Sanity test helper
# ---------------------------------------------------------------------------

def sanity_test():
    """
    More elaborate sanity check that steps through the workflow without
    calling the OpenAI API, and writes a dummy PNG file to assets/sprites/.

    It verifies:
    - We can resolve the sprites output directory.
    - We can build a frame prompt for frame 1.
    - We can create and save a simple RGBA PNG image.
    """
    out_dir = get_sprites_output_dir()
    print(f"[SANITY] sprites output dir: {out_dir}")

    # Try building a prompt for frame 1 to ensure FRAME_DESCRIPTIONS is sane.
    try:
        prompt = build_frame_prompt(1)
        snippet = (prompt[:200] + "...") if len(prompt) > 200 else prompt
        print("[SANITY] Built prompt for frame 01 (first 200 chars):")
        print(snippet)
    except Exception as exc:
        print(f"[SANITY][ERROR] Failed to build frame prompt: {exc}")

    # Create a small transparent test image with a simple marker.
    img_size = (128, 128)
    img = Image.new("RGBA", img_size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Draw a red square and label it 'TEST'
    draw.rectangle((20, 20, 108, 108), outline=(255, 0, 0, 255), width=4)
    draw.text((30, 50), "TEST", fill=(255, 0, 0, 255))

    test_path = out_dir / "grenade_sanity_test.png"
    img.save(test_path)
    print(f"[SANITY] Wrote dummy sprite PNG: {test_path}")

# ---------------------------------------------------------------------------
# 6. Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # If GRENADE_SANITY is set (to any non-empty value), run the sanity test instead
    # of calling the OpenAI API. This is useful before credentials are configured.
    if os.environ.get("GRENADE_SANITY"):
        print("[INFO] Running grenade sprite sanity test (no API calls).")
        sanity_test()
    else:
        # You can control resolution here (e.g. '256x256', '512x512', '1024x1024')
        target_size = os.environ.get("GRENADE_SPRITE_SIZE", "1024x1024")
        print(f"[INFO] Generating grenade frames at size {target_size}")
        generate_all_frames(size=target_size)