import os
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter


def create_industrial_inspection_dataset(base_dir: Path) -> dict:
    """
    Generates a realistic calibrated industrial dataset for component quality inspection.
    Includes normal precision-machined cylindrical flanges, and defective parts with:
    - Surface cracks / stress fractures
    - Porosity / slag inclusions
    - Drill hole burrs / misalignment
    - Edge chipping / gouges
    """
    inspection_dir = base_dir / "datasets" / "inspection"
    samples_dir = inspection_dir / "samples"
    samples_dir.mkdir(parents=True, exist_ok=True)

    dataset_manifest = []

    # Helper to generate metallic base disk texture
    def make_base_flange(seed: int = 42) -> Image.Image:
        np.random.seed(seed)
        size = 256
        img = Image.new("RGB", (size, size), color=(30, 35, 45))
        draw = ImageDraw.Draw(img)

        # Outer metallic rim
        draw.ellipse([28, 28, 228, 228], fill=(160, 168, 175), outline=(210, 215, 220), width=4)
        # Inner machined circular groove
        draw.ellipse([50, 50, 206, 206], fill=(130, 138, 148), outline=(100, 108, 118), width=3)
        # Central bore hole
        draw.ellipse([100, 100, 156, 156], fill=(20, 24, 30), outline=(70, 78, 88), width=3)
        
        # 4 perimeter bolt holes
        bolt_coords = [(60, 128), (196, 128), (128, 60), (128, 196)]
        for bx, by in bolt_coords:
            draw.ellipse([bx - 10, by - 10, bx + 10, by + 10], fill=(20, 24, 30), outline=(90, 98, 108), width=2)

        # Subtle brushed metal noise
        noise = np.random.normal(0, 4, (size, size, 3)).astype(np.int16)
        arr = np.array(img).astype(np.int16) + noise
        arr = np.clip(arr, 0, 255).astype(np.uint8)
        return Image.fromarray(arr)

    # 1. Normal Acceptable Samples
    for i in range(1, 7):
        img = make_base_flange(seed=100 + i)
        filename = f"sample_normal_{i:02d}.png"
        filepath = samples_dir / filename
        img.save(filepath, "PNG")
        dataset_manifest.append({
            "id": f"NORM-{i:02d}",
            "filename": filename,
            "filepath": str(filepath),
            "ground_truth": "ACCEPTABLE",
            "defect_type": "None",
            "split": "train" if i <= 3 else "test",
        })

    # 2. Defect 1: Surface Crack / Fracture (DEF-01, DEF-02)
    for i in range(1, 3):
        img = make_base_flange(seed=200 + i)
        draw = ImageDraw.Draw(img)
        # Jagged high-contrast dark fissure across machined face
        points = [(75, 120), (88, 115), (102, 125), (115, 118), (125, 122)]
        draw.line(points, fill=(15, 15, 20), width=3)
        filename = f"sample_defect_crack_{i:02d}.png"
        filepath = samples_dir / filename
        img.save(filepath, "PNG")
        dataset_manifest.append({
            "id": f"DEF-CRACK-{i:02d}",
            "filename": filename,
            "filepath": str(filepath),
            "ground_truth": "DEFECTIVE",
            "defect_type": "Surface Crack",
            "split": "train" if i == 1 else "test",
        })

    # 3. Defect 2: Porosity / Gas Pockets (DEF-03, DEF-04)
    for i in range(1, 3):
        img = make_base_flange(seed=300 + i)
        draw = ImageDraw.Draw(img)
        # Cluster of dark pitted voids
        cluster = [(80, 80), (83, 85), (88, 81), (77, 86), (85, 89)]
        for px, py in cluster:
            draw.ellipse([px - 3, py - 3, px + 3, py + 3], fill=(12, 14, 18), outline=(50, 50, 60))
        filename = f"sample_defect_porosity_{i:02d}.png"
        filepath = samples_dir / filename
        img.save(filepath, "PNG")
        dataset_manifest.append({
            "id": f"DEF-POROSITY-{i:02d}",
            "filename": filename,
            "filepath": str(filepath),
            "ground_truth": "DEFECTIVE",
            "defect_type": "Gas Porosity Void",
            "split": "train" if i == 1 else "test",
        })

    # 4. Defect 3: Edge Notch / Machining Burr (DEF-05, DEF-06)
    for i in range(1, 3):
        img = make_base_flange(seed=400 + i)
        draw = ImageDraw.Draw(img)
        # Irregular gouge notch taken out of perimeter
        draw.polygon([(28, 120), (38, 128), (28, 136)], fill=(30, 35, 45), outline=(10, 10, 15))
        filename = f"sample_defect_burr_{i:02d}.png"
        filepath = samples_dir / filename
        img.save(filepath, "PNG")
        dataset_manifest.append({
            "id": f"DEF-BURR-{i:02d}",
            "filename": filename,
            "filepath": str(filepath),
            "ground_truth": "DEFECTIVE",
            "defect_type": "Perimeter Chip",
            "split": "test",
        })

    return {"manifest": dataset_manifest, "total_samples": len(dataset_manifest)}
