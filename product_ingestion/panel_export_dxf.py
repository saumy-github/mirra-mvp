"""DXF export for canonical Step 2 panel outputs."""

from __future__ import annotations

from pathlib import Path

try:
    import ezdxf

    HAS_EZDXF = True
except ImportError:
    HAS_EZDXF = False


def export_panels_dxf(patterns: dict[str, list[tuple[float, float]]], measurements, output_dir: Path) -> None:
    """Export panel outlines as DXF files for CLO."""
    output_dir.mkdir(parents=True, exist_ok=True)

    if not HAS_EZDXF:
        print("Warning: ezdxf not available, skipping DXF export.")
        return

    for name, points in patterns.items():
        # Create new DXF document
        doc = ezdxf.new("R2010")
        msp = doc.modelspace()

        # Add pattern outline as POLYLINE (not LWPOLYLINE - better CLO3D compatibility)
        # CLO3D prefers standard POLYLINE entities
        points_3d = [(x, y, 0) for x, y in points]
        # Create polyline with POLYLINE entity (not lightweight)
        polyline = msp.add_polyline3d(points_3d, dxfattribs={"layer": "CutLine", "color": 7})
        polyline.close(True)

        # Add notches as small lines (better than circles for CLO3D)
        if "panel" in name:
            # Add notch at shoulder points
            shoulder_points = [point for point in points if point[1] > measurements.garment_length * 0.9]
            for point_x, point_y in shoulder_points[:2]:
                # Notch as small perpendicular line (5mm long)
                msp.add_line(
                    (point_x - 0.25, point_y, 0),
                    (point_x + 0.25, point_y, 0),
                    dxfattribs={"layer": "Notch", "color": 1},
                )
        elif "sleeve" in name:
            # Add notch at sleeve cap top
            top_y = max(point[1] for point in points)
            top_points = [point for point in points if abs(point[1] - top_y) < 1.0]
            if top_points:
                point_x, point_y = top_points[len(top_points) // 2]
                msp.add_line(
                    (point_x - 0.25, point_y, 0),
                    (point_x + 0.25, point_y, 0),
                    dxfattribs={"layer": "Notch", "color": 1},
                )

        center_x = sum(point[0] for point in points) / len(points)
        center_y = sum(point[1] for point in points) / len(points)
        # Add text label
        msp.add_text(
            name.replace("_", " ").title(),
            dxfattribs={"layer": "Text", "height": 5.0, "color": 3},
        ).set_placement((center_x, center_y, 0))

        grain_x = center_x
        grain_y_start = min(point[1] for point in points) + 5
        grain_y_end = max(point[1] for point in points) - 5
        # Add grain line (vertical line in center)
        msp.add_line(
            (grain_x, grain_y_start, 0),
            (grain_x, grain_y_end, 0),
            dxfattribs={"layer": "GrainLine", "color": 5},
        )

        output_file = output_dir / f"{name}.dxf"
        doc.saveas(output_file)
        print(f"  Wrote DXF: {output_file.name}")
