from pathlib import Path
import subprocess

inkscape = r"C:\Program Files\Inkscape\bin\inkscape.exe"

input_dir = Path(__file__).parent
output_dir = input_dir / "png"
output_dir.mkdir(parents=True, exist_ok=True)

for svg in input_dir.glob("*.svg"):
    output = output_dir / f"{svg.stem}.png"

    print(f"Converting: {svg.name}")

    subprocess.run([
        inkscape,
        str(svg),
        "--export-type=png",
        "--export-filename", str(output),
        "--export-width=128",
    ], check=True)

    print(f"  -> {output}")