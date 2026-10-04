"""
Generate a sleek Client Controller icon (.ico) with cyber-blue aesthetic.
"""
from PIL import Image, ImageDraw
from pathlib import Path

def generate_client_icon(output_path: str = "installer/client_icon.ico") -> None:
    size = 256
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Outer rounded rect (Dark blue/slate with cyan border)
    draw.rounded_rectangle(
        [16, 16, 240, 240],
        radius=48,
        fill=(15, 23, 42, 255),  # Slate 900
        outline=(56, 189, 248, 255),  # Sky / Cyan Blue
        width=8,
    )

    # Monitor Screen frame
    draw.rounded_rectangle(
        [48, 48, 208, 172],
        radius=16,
        fill=(30, 41, 59, 255),
        outline=(14, 165, 233, 255),
        width=5,
    )

    # Monitor Stand
    draw.rectangle([118, 172, 138, 204], fill=(56, 189, 248, 255))
    draw.rounded_rectangle([92, 204, 164, 216], radius=4, fill=(56, 189, 248, 255))

    # Screen Graphics: Pulse / Offloading Wave
    points = [(64, 110), (96, 110), (112, 76), (128, 144), (144, 92), (160, 110), (192, 110)]
    draw.line(points, fill=(56, 189, 248, 255), width=6)

    # Accent Dot
    draw.ellipse([140, 88, 148, 96], fill=(255, 255, 255, 255))

    p = Path(output_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    img.save(
        output_path,
        format="ICO",
        sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)],
    )
    print(f"[✓] Generated client icon: {output_path}")

if __name__ == "__main__":
    generate_client_icon()
