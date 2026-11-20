"""SVG export for canonical Step 2 panel outputs."""
from __future__ import annotations

from pathlib import Path


def export_panels_svg(
    layouts: "dict[str, object]",
    output_dir: Path,
) -> None:
    """Export panel outlines as SVG previews.

    Accepts either:
    - dict[str, PieceLayout]  (new — calls layout.polygon())
    - dict[str, list[tuple]]  (legacy — used directly)
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    for name, item in layouts.items():
        # Support both PieceLayout objects and raw point lists
        if hasattr(item, "polygon"):
            points = item.polygon()
        else:
            points = item

        if not points:
            continue

        min_x = min(p[0] for p in points)
        max_x = max(p[0] for p in points)
        min_y = min(p[1] for p in points)
        max_y = max(p[1] for p in points)

        margin = 5
        width = max_x - min_x + margin * 2
        height = max_y - min_y + margin * 2
        scale = 10.0

        origin_x = (-min_x + margin) * scale

        svg_width = width * scale
        svg_height = height * scale

        svg_content = f"""<?xml version="1.0" encoding="UTF-8"?>
    <svg xmlns="http://www.w3.org/2000/svg"
         width="{svg_width}"
         height="{svg_height}"
         viewBox="0 0 {svg_width} {svg_height}">
        <!-- Background -->
        <rect x="0" y="0" width="{svg_width}" height="{svg_height}" fill="white" stroke="none"/>
        <!-- Grid (1cm squares) -->
        <g id="grid" stroke="#e0e0e0" stroke-width="0.5">
"""
        for grid_x in range(int(min_x - margin), int(max_x + margin + 1)):
            line_x = grid_x * scale + origin_x
            svg_content += f'        <line x1="{line_x}" y1="0" x2="{line_x}" y2="{svg_height}"/>\n'
        for grid_y in range(int(min_y - margin), int(max_y + margin + 1)):
            line_y = (max_y - grid_y + margin) * scale
            svg_content += f'        <line x1="0" y1="{line_y}" x2="{svg_width}" y2="{line_y}"/>\n'

        svg_content += "    </g>\n\n"

        path_data = "M " + " L ".join(
            f"{p[0] * scale + origin_x},{(max_y - p[1] + margin) * scale}" for p in points
        ) + " Z"
        svg_content += f"""    <!-- Pattern Outline -->
    <path d="{path_data}"
          fill="#f0f8ff"
          stroke="#000080"
          stroke-width="2.0"/>

"""
        center_x = sum(p[0] for p in points) / len(points)
        center_y = sum(p[1] for p in points) / len(points)
        grain_y_start = min_y + 5
        grain_y_end = max_y - 5
        grain_center_x = center_x * scale + origin_x
        grain_start_y = (max_y - grain_y_start + margin) * scale
        grain_end_y = (max_y - grain_y_end + margin) * scale

        svg_content += f"""    <line x1="{grain_center_x}" y1="{grain_start_y}"
          x2="{grain_center_x}" y2="{grain_end_y}"
          stroke="#ff0000" stroke-width="1.5" stroke-dasharray="5,5"/>
        <polygon points="{grain_center_x},{grain_end_y} {grain_center_x - 0.5 * scale},{grain_end_y + 1 * scale} {grain_center_x + 0.5 * scale},{grain_end_y + 1 * scale}"
             fill="#ff0000"/>

    """
        svg_content += f"""    <!-- Label -->
        <text x="{center_x * scale + origin_x}" y="{(max_y - center_y + margin) * scale}"
          font-family="Arial" font-size="40"
          text-anchor="middle" dominant-baseline="middle"
          fill="#000080" font-weight="bold">
        {name.replace('_', ' ').title()}
        </text>

        <!-- Dimensions -->
        <text x="{center_x * scale + origin_x}" y="{(max_y - min_y + margin * 2 - 1) * scale}"
          font-family="Arial" font-size="20"
          text-anchor="middle" fill="#666">
        Width: {(max_x - min_x):.1f}cm x Height: {(max_y - min_y):.1f}cm
        </text>
    </svg>"""

        output_file = output_dir / f"{name}.svg"
        output_file.write_text(svg_content, encoding="utf-8")
        print(f"  Wrote SVG: {output_file.name}")
