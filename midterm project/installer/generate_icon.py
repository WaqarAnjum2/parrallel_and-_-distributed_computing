"""
Generate a professional GPU Worker Node icon (.ico) for Desktop shortcuts.
"""
from PIL import Image, ImageDraw
from pathlib import Path

def generate_worker_icon(output_path: str = "installer/worker_icon.ico") -> None:
    size = 256
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Outer rounded rect (Dark slate with cobalt border)
    # Background card
    draw.rounded_rectangle(
        [16, 16, 240, 240],
        radius=48,
        fill=(15, 23, 42, 255),  # Slate 900
        outline=(59, 130, 246, 255),  # Cobalt Blue 500
        width=8,
    )

    # Inner GPU Die / Chip
    draw.rounded_rectangle(
        [64, 64, 192, 192],
        radius=24,
        fill=(30, 41, 59, 255),
        outline=(16, 185, 129, 255),  # Emerald Green (NVIDIA style)
        width=6,
    )

    # GPU Grid Pins / Circuit Accents
    # Top & Bottom Pins
    for x in [84, 108, 132, 156]:
        draw.rectangle([x, 48, x + 12, 64], fill=(16, 185, 129, 255))
        draw.rectangle([x, 192, x + 12, 208], fill=(16, 185, 129, 255))
    # Left & Right Pins
    for y in [84, 108, 132, 156]:
        draw.rectangle([48, y, 64, y + 12], fill=(16, 185, 129, 255))
        draw.rectangle([192, y, 208, y + 12], fill=(16, 185, 129, 255))

    # Center GPU Lightning / Core
    # Draw "GPU" stylized or diamond core
    draw.polygon(
        [(128, 88), (168, 128), (128, 168), (88, 128)],
        fill=(59, 130, 246, 255),
        outline=(96, 165, 250, 255),
    )
    # Bright center dot
    draw.ellipse([120, 120, 136, 136], fill=(255, 255, 255, 255))

    p = Path(output_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    img.save(
        output_path,
        format="ICO",
        sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)],
    )
    print(f"[✓] Generated icon: {output_path}")

if __name__ == "__main__":
    generate_worker_icon()
