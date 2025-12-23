import os
from textwrap import indent

# --- 1. Frame descriptions ----------------------------------------------------

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

# --- 2. Prompt generator ------------------------------------------------------


def build_batch_prompt(start_frame: int, end_frame: int) -> str:
    """
    Build a DALL-E prompt for frames [start_frame, end_frame], inclusive.
    Uses a vertical strip layout for better reliability.
    """
    lines = []

    # Global style / layout instructions
    lines.append(
        "Create a single PNG image that contains multiple separate animation frames, "
        "arranged as a vertical strip. Each frame must be visually isolated with "
        "blank transparent space between frames. Do NOT arrange the frames in a grid. "
        "Instead, stack them vertically, one above the other, as a tall contact sheet."
    )
    lines.append(
        "Each frame should have a transparent background and the same approximate size. "
        "Number each frame very subtly in the top-left corner using small comic digits, "
        "like '01', '02', etc., matching the frame number specified below."
    )
    lines.append(
        "Art style: comic-book style, thick black outlines, clean flat colors, "
        "slight halftone shading, crisp and readable. The subject is a small hand grenade "
        "performing a continuous animation: low lob, three small bounces, fuse charging, "
        "and then explosion. The grenade should be simple, iconic, and readable at small size. "
        "All frames must share consistent lighting, proportions, and floor position."
    )
    lines.append(
        "For this batch, draw ONLY the frames listed below. Do not invent extra frames. "
        "Each frame must clearly correspond to its described moment in the animation."
    )

    # Batch-specific frame descriptions
    lines.append("")
    lines.append("Frames to draw in this image:")

    for n in range(start_frame, end_frame + 1):
        desc = FRAME_DESCRIPTIONS[n]
        frame_label = f"{n:02d}"
        lines.append(f"- Frame {frame_label}: {desc}")

    # Optional: nudge DALL-E toward consistent framing
    lines.append("")
    lines.append(
        "Keep the grenade anchored to the same floor line in all these frames. "
        "If the grenade is in the air, show it higher above the same floor line. "
        "Do not move the floor. Do not tilt the camera. Do not change zoom."
    )

    return "\n".join(lines)


def write_prompts(output_dir: str, batch_size: int = 6):
    """
    Split 24 frames into batches and write one prompt file per batch.
    For example, with batch_size=6:
        01-06, 07-12, 13-18, 19-24
    """
    os.makedirs(output_dir, exist_ok=True)
    frame_numbers = sorted(FRAME_DESCRIPTIONS.keys())
    total = len(frame_numbers)

    batches = []
    for i in range(0, total, batch_size):
        start = frame_numbers[i]
        end = frame_numbers[min(i + batch_size - 1, total - 1)]
        batches.append((start, end))

    for start, end in batches:
        prompt = build_batch_prompt(start, end)
        filename = f"grenade_frames_{start:02d}_{end:02d}.txt"
        path = os.path.join(output_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            f.write(prompt)
        print(f"Wrote prompt for frames {start:02d}-{end:02d} to {path}")


if __name__ == "__main__":
    base_dir = os.path.dirname(__file__)
    prompts_dir = os.path.join(base_dir, "..", "assets", "prompts")
    write_prompts(prompts_dir, batch_size=6)