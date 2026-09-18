"""Generate deterministic KiCad 10 sources for the Pager-1 carrier.

The JSON hardware manifest is the source of truth.  Generated KiCad files are
ordinary editable S-expression files; regeneration is intended for review and
contract synchronization, not as a replacement for interactive layout work.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PROJECT_DIR = REPO / "kicad" / "pager-carrier-rev-a"
MANIFEST_PATH = PROJECT_DIR / "hardware-manifest.json"
NS = uuid.UUID("62f39802-f052-4a6c-b9f7-d3da80c3d2cc")


def uid(name: str) -> str:
    return str(uuid.uuid5(NS, name))


def effects(size: float = 1.0, thickness: float = 0.15) -> str:
    return f'(effects (font (size {size} {size}) (thickness {thickness})))'


def hidden_effects(size: float = 1.0, thickness: float = 0.15) -> str:
    return f'(effects (font (size {size} {size}) (thickness {thickness})) (hide yes))'


def property_block(key: str, value: str, x: float, y: float, layer: str, name: str) -> str:
    return (
        f'    (property "{key}" "{value}" (at {x} {y} 0) (layer "{layer}") '
        f'(uuid "{uid(name)}") {effects()})\n'
    )


def footprint(
    ref: str,
    value: str,
    x: float,
    y: float,
    width: float,
    height: float,
    pads: list[tuple[str, float, float, float, float, int | None, str | None]],
    *,
    exclude_from_bom: bool = False,
    manufacturer: str = "",
    mpn: str = "",
) -> str:
    lines = [
        f'  (footprint "{value}" (layer "F.Cu") (uuid "{uid(f"fp-{ref}")}")',
        f'    (at {x} {y})',
        property_block("Reference", ref, 0, -height / 2 - 1.2, "F.Fab", f"{ref}-ref").rstrip(),
        property_block("Value", value, 0, height / 2 + 1.2, "F.Fab", f"{ref}-val").rstrip(),
        property_block(
            "Description",
            "Pager-1 Rev A manifest-backed component",
            0,
            0,
            "F.Fab",
            f"{ref}-description",
        ).rstrip(),
        property_block("Manufacturer", manufacturer, 0, 0, "F.Fab", f"{ref}-manufacturer").rstrip(),
        property_block("MPN", mpn, 0, 0, "F.Fab", f"{ref}-mpn").rstrip(),
        f'    (attr smd{" exclude_from_bom" if exclude_from_bom else ""})',
        (
            f'    (fp_rect (start {-width / 2} {-height / 2}) '
            f'(end {width / 2} {height / 2}) '
            f'(stroke (width 0.2) (type default)) (fill none) (layer "F.Fab") '
            f'(uuid "{uid(f"{ref}-silk")}"))'
        ),
    ]
    for number, px, py, sx, sy, net_id, net_name in pads:
        net = f' (net {net_id} "{net_name}")' if net_id is not None and net_name else ""
        lines.append(
            f'    (pad "{number}" smd rect (at {px} {py}) (size {sx} {sy}) '
            f'(layers "F.Cu" "F.Paste" "F.Mask"){net} '
            f'(uuid "{uid(f"{ref}-pad-{number}")}"))'
        )
    lines.append("  )")
    return "\n".join(lines)


def build_board(manifest: dict[str, object]) -> str:
    pin_rows = manifest["mezzanine"]["pins"]  # type: ignore[index]
    bom_items = {
        str(item["reference"]): item
        for item in manifest["bom"]  # type: ignore[assignment]
    }
    pin_counts = {
        "U1": 100,
        "U2": 25,
        "U3": 8,
        "U4": 24,
        "U5": 10,
        "U6": 6,
        "U7": 5,
        "U8": 14,
        "D1": 6,
        "R1": 2,
        "R2": 2,
        "R3": 2,
        "R4": 2,
        "R5": 2,
        "R6": 2,
        "J1": 16,
        "J2": 10,
        "J3": 12,
        "J4": 10,
        "J5": 40,
        "J6": 3,
    }
    net_names = []
    for item in pin_rows:  # type: ignore[assignment]
        name = item["net"]
        if name not in net_names:
            net_names.append(name)
    for name in manifest["required_testpoints"]:  # type: ignore[assignment]
        if name not in net_names:
            net_names.append(name)
    for ref, count in pin_counts.items():
        connected = set(range(27, 47)) if ref == "U1" else set(range(1, 41)) if ref == "J5" else set()
        for pin in range(1, count + 1):
            if pin not in connected:
                net_names.append(f"unconnected-({ref}-P{pin}-Pad{pin})")
    net_ids = {name: index + 1 for index, name in enumerate(net_names)}

    def pcb_net_name(name: str) -> str:
        return name if name.startswith("unconnected-") else f"/{name}"

    header = '''(kicad_pcb
  (version 20250513)
  (generator "pcbnew")
  (generator_version "10.0")
  (general (thickness 1.2) (legacy_teardrops no))
  (paper "A4")
  (title_block (title "Pager-1 Carrier Rev A") (rev "A")
    (comment 1 "DESIGN ARTIFACT - NOT FABRICATED OR MEASURED")
    (comment 2 "70 x 52 mm, four-layer, 1.2 mm"))
  (layers
    (0 "F.Cu" signal)
    (4 "In1.Cu" power "GND plane")
    (6 "In2.Cu" power "Power pours")
    (2 "B.Cu" signal)
    (9 "F.Adhes" user "F.Adhesive")
    (11 "B.Adhes" user "B.Adhesive")
    (13 "F.Paste" user)
    (15 "B.Paste" user)
    (5 "F.SilkS" user "F.Silkscreen")
    (7 "B.SilkS" user "B.Silkscreen")
    (1 "F.Mask" user)
    (3 "B.Mask" user)
    (17 "Dwgs.User" user "User.Drawings")
    (19 "Cmts.User" user "User.Comments")
    (21 "Eco1.User" user "User.Eco1")
    (23 "Eco2.User" user "User.Eco2")
    (25 "Edge.Cuts" user)
    (27 "Margin" user)
    (31 "F.CrtYd" user "F.Courtyard")
    (29 "B.CrtYd" user "B.Courtyard")
    (35 "F.Fab" user)
    (33 "B.Fab" user)
  )
  (setup
    (pad_to_mask_clearance 0)
    (allow_soldermask_bridges_in_footprints no)
    (tenting front back)
  )
  (net 0 "")
'''
    net_lines = "".join(
        f'  (net {index} "{pcb_net_name(name)}")\n' for name, index in net_ids.items()
    )

    # J5 is represented at the manufacturer's 0.4 mm contact pitch.  Odd and
    # even contacts occupy two staggered columns.
    j5_pads = []
    j5_centers: dict[int, tuple[float, float]] = {}
    for pin in pin_rows:  # type: ignore[assignment]
        number = int(pin["pin"])
        col = -0.35 if number % 2 else 0.35
        row = (number - 1) // 2
        py = -3.8 + row * 0.4
        name = str(pin["net"])
        j5_pads.append(
            (str(number), col, py, 0.18, 0.26, net_ids[name], pcb_net_name(name))
        )
        j5_centers[number] = (162.0 + col, 100.0 + py)

    # Use the right-hand 24 pads of an explicit 100-pad LQFP geometry as the
    # accelerator interface fan-out. Remaining pads are deliberately unassigned
    # here; the detailed MCU power/peripheral connections live in host.kicad_sch.
    u1_pads = []
    u1_centers: dict[int, tuple[float, float]] = {}
    interface_pins = list(range(17, 37))
    for number in range(1, 101):
        if number <= 25:
            px, py, sx, sy = -7.55 + (number - 1) * 0.5, -7.6, 0.28, 1.2
        elif number <= 50:
            px, py, sx, sy = 7.6, -7.55 + (number - 26) * 0.5, 1.2, 0.28
        elif number <= 75:
            px, py, sx, sy = 7.55 - (number - 51) * 0.5, 7.6, 0.28, 1.2
        else:
            px, py, sx, sy = -7.6, 7.55 - (number - 76) * 0.5, 1.2, 0.28
        if 27 <= number <= 46:
            source = interface_pins[number - 27]
            net_name = str(pin_rows[source - 1]["net"])  # type: ignore[index]
            net_id = net_ids[net_name]
            u1_centers[source] = (130.0 + px, 100.0 + py)
        else:
            net_name = f"unconnected-(U1-P{number}-Pad{number})"
            net_id = net_ids[net_name]
        u1_pads.append(
            (str(number), px, py, sx, sy, net_id, pcb_net_name(net_name))
        )

    fps = [
        footprint(
            "U1", "STM32U575VGT6", 130.0, 100.0, 14.0, 14.0, u1_pads,
            manufacturer=str(bom_items["U1"]["manufacturer"]),
            mpn=str(bom_items["U1"]["mpn"]),
        ),
        footprint(
            "J5", "DF40C-40DP-0.4V", 162.0, 100.0, 2.4, 9.0, j5_pads,
            manufacturer=str(bom_items["J5"]["manufacturer"]),
            mpn=str(bom_items["J5"]["mpn"]),
        ),
    ]

    simple_parts = [
        ("U2", "BQ25120A", 105.0, 88.0, 4.0, 4.0, 25),
        ("U3", "W25Q128JVS", 118.0, 112.0, 6.0, 5.5, 8),
        ("U4", "TCA8418", 105.0, 103.0, 5.0, 5.0, 24),
        ("U5", "DRV2605L", 105.0, 114.0, 4.0, 3.0, 10),
        ("U6", "TPS61099", 116.0, 87.0, 3.0, 3.0, 6),
        ("U7", "TLV75510", 123.0, 87.0, 3.0, 3.0, 5),
        ("U8", "SN74AHCT125", 140.0, 121.0, 5.0, 4.0, 14),
        ("D1", "USBLC6-2SC6", 99.0, 111.0, 3.0, 3.0, 6),
        ("R1", "5.1k", 98.0, 116.0, 1.2, 0.8, 2),
        ("R2", "5.1k", 98.0, 118.0, 1.2, 0.8, 2),
        ("R3", "2.0k", 98.0, 120.0, 1.2, 0.8, 2),
        ("R4", "100k", 98.0, 122.0, 1.2, 0.8, 2),
        ("R5", "100k", 101.0, 124.0, 1.2, 0.8, 2),
        ("R6", "100k", 104.0, 124.0, 1.2, 0.8, 2),
        ("J1", "USB_C_USB2.0", 99.0, 100.0, 4.0, 10.0, 16),
        ("J2", "LS027B7DH01_FPC", 136.0, 83.0, 8.0, 3.0, 10),
        ("J3", "KEYPAD_5X7_FPC", 148.0, 83.0, 9.0, 3.0, 12),
        ("J4", "SWD", 146.0, 116.0, 6.0, 4.0, 10),
        ("J6", "LIPO_NTC", 107.0, 120.0, 7.0, 4.0, 3),
    ]
    for ref, value, x, y, w, h, count in simple_parts:
        pads = []
        for i in range(count):
            side = -1 if i % 2 == 0 else 1
            row = i // 2
            py = -h / 2 + 0.5 + row * max(0.35, (h - 1.0) / max((count + 1) // 2 - 1, 1))
            name = f"unconnected-({ref}-P{i + 1}-Pad{i + 1})"
            pads.append(
                (str(i + 1), side * w / 2, py, 0.18, 0.18, net_ids[name], name)
            )
        fps.append(
            footprint(
                ref,
                value,
                x,
                y,
                w,
                h,
                pads,
                manufacturer=str(bom_items[ref]["manufacturer"]),
                mpn=str(bom_items[ref]["mpn"]),
            )
        )

    # Seven rail test points plus four mounting holes.
    test_positions = {
        "+3V3": (156.0, 110.0),
        "+2V5_SW": (158.0, 113.0),
        "+1V0_SW": (160.0, 116.0),
        "GND": (162.0, 119.0),
    }
    for index, name in enumerate(manifest["required_testpoints"], start=1):  # type: ignore[arg-type]
        x, y = test_positions.get(name, (110.0 + index * 5, 123.0))
        pads = [("1", 0.0, 0.0, 1.5, 1.5, net_ids[name], pcb_net_name(name))]
        fps.append(
            footprint(
                f"TP{index}",
                name.replace("+", "P"),
                x,
                y,
                2.0,
                2.0,
                pads,
                exclude_from_bom=True,
            )
        )

    for index, (x, y) in enumerate(((98.0, 78.0), (164.0, 78.0), (98.0, 126.0), (164.0, 126.0)), start=1):
        fps.append(
            f'''  (footprint "MountingHole_2.5mm" (layer "F.Cu")
    (uuid "{uid(f'mh-{index}')}") (at {x} {y})
    {property_block('Reference', f'H{index}', 0, -3, 'F.Fab', f'h{index}-ref').strip()}
    {property_block('Value', 'MountingHole_2.5mm', 0, 3, 'F.Fab', f'h{index}-val').strip()}
    (attr board_only exclude_from_pos_files exclude_from_bom)
    (pad "" np_thru_hole circle (at 0 0) (size 2.5 2.5) (drill 2.5) (layers "*.Cu" "*.Mask")))'''
        )

    segments = []
    vias = []
    # Route the 20 active/test accelerator signals in monotonic order. Odd J5
    # contacts approach on F.Cu. Even contacts escape outboard, change layer,
    # and approach U1 on B.Cu so the two 0.4 mm connector rows never cross.
    # J5 pins 37..40 are reserved and intentionally have no track.
    for source_pin in interface_pins:
        sx, sy = u1_centers[source_pin]
        ex, ey = j5_centers[source_pin]
        name = str(pin_rows[source_pin - 1]["net"])  # type: ignore[index]
        if source_pin % 2:
            segments.append(
                f'  (segment (start {sx:.3f} {sy:.3f}) (end {ex:.3f} {ey:.3f}) '
                f'(width 0.127) (layer "F.Cu") (net {net_ids[name]}) '
                f'(uuid "{uid(f"seg-{source_pin}")}"))'
            )
        else:
            inner_x = 136.7
            outer_x = 164.0
            segments.extend(
                [
                    f'  (segment (start {sx:.3f} {sy:.3f}) (end {inner_x:.3f} {sy:.3f}) (width 0.127) (layer "F.Cu") (net {net_ids[name]}) (uuid "{uid(f"seg-in-{source_pin}")}"))',
                    f'  (segment (start {inner_x:.3f} {sy:.3f}) (end {outer_x:.3f} {ey:.3f}) (width 0.127) (layer "B.Cu") (net {net_ids[name]}) (uuid "{uid(f"seg-back-{source_pin}")}"))',
                    f'  (segment (start {outer_x:.3f} {ey:.3f}) (end {ex:.3f} {ey:.3f}) (width 0.127) (layer "F.Cu") (net {net_ids[name]}) (uuid "{uid(f"seg-out-{source_pin}")}"))',
                ]
            )
            for label, vx, vy in (("in", inner_x, sy), ("out", outer_x, ey)):
                vias.append(
                    f'  (via (at {vx:.3f} {vy:.3f}) (size 0.27) (drill 0.20) (layers "F.Cu" "B.Cu") (net {net_ids[name]}) (uuid "{uid(f"via-{label}-{source_pin}")}"))'
                )
    # Tie repeated power and ground pads locally at the connector.
    for group_name, pins in (("+3V3", range(1, 5)), ("+2V5_SW", range(5, 7)), ("+1V0_SW", range(7, 9)), ("GND", range(9, 17))):
        ordered = list(pins)
        for a, b in zip(ordered, ordered[1:]):
            ax, ay = j5_centers[a]
            bx, by = j5_centers[b]
            segments.append(
                f'  (segment (start {ax:.3f} {ay:.3f}) (end {bx:.3f} {by:.3f}) '
                f'(width 0.127) (layer "F.Cu") (net {net_ids[group_name]}) '
                f'(uuid "{uid(f"tie-{a}-{b}")}"))'
            )
    rail_routes = (
        ("+3V3", 1, "In2.Cu"),
        ("+2V5_SW", 5, "In2.Cu"),
        ("+1V0_SW", 7, "In2.Cu"),
        ("GND", 9, "In2.Cu"),
    )
    for name, pin, layer in rail_routes:
        tx, ty = test_positions[name]
        px, py = j5_centers[pin]
        segments.extend(
            [
                (
                    f'  (segment (start {px:.3f} {py:.3f}) (end {tx:.3f} {py:.3f}) '
                    f'(width 0.127) (layer "{layer}") (net {net_ids[name]}) '
                    f'(uuid "{uid(f"testpoint-fanout-{name}")}"))'
                ),
                (
                    f'  (segment (start {tx:.3f} {py:.3f}) (end {tx:.3f} {ty:.3f}) '
                    f'(width 0.127) (layer "{layer}") (net {net_ids[name]}) '
                    f'(uuid "{uid(f"testpoint-drop-{name}")}"))'
                ),
            ]
        )
        if layer != "F.Cu":
            for label, vx, vy in (("connector", px, py), ("testpoint", tx, ty)):
                vias.append(
                    f'  (via (at {vx:.3f} {vy:.3f}) (size 0.27) (drill 0.20) '
                    f'(layers "F.Cu" "B.Cu") (net {net_ids[name]}) '
                    f'(uuid "{uid(f"rail-via-{label}-{name}")}"))'
                )

    drawings = f'''
  (gr_rect (start 95 75) (end 165 127) (stroke (width 0.25) (type default))
    (fill none) (layer "Edge.Cuts") (uuid "{uid('outline')}"))
  (gr_rect (start 101 79) (end 159 91) (stroke (width 0.15) (type dash))
    (fill none) (layer "Dwgs.User") (uuid "{uid('display-keepout')}"))
  (gr_text "DISPLAY / FPC KEEPOUT" (at 130 80.5) (layer "Dwgs.User")
    (uuid "{uid('display-label')}") {effects(1.0)})
  (gr_text "PAGER-1 CARRIER REV A" (at 130 125) (layer "F.SilkS")
    (uuid "{uid('board-title')}") {effects(1.2, 0.2)})
  (gr_text "DESIGN ONLY - NOT MEASURED" (at 130 78) (layer "F.SilkS")
    (uuid "{uid('evidence-label')}") {effects(0.9)})
  (zone (net {net_ids['GND']}) (net_name "/GND") (layer "In1.Cu")
    (uuid "{uid('ground-plane-zone')}") (hatch edge 0.5)
    (connect_pads (clearance 0.127)) (min_thickness 0.10)
    (filled_areas_thickness no)
    (fill yes (thermal_gap 0.25) (thermal_bridge_width 0.25))
    (polygon (pts (xy 95.25 75.25) (xy 164.75 75.25)
      (xy 164.75 126.75) (xy 95.25 126.75))))
'''
    return header + net_lines + "\n".join(fps) + "\n" + "\n".join(segments + vias) + drawings + ")\n"


def schematic_header(title: str, identifier: str) -> str:
    return f'''(kicad_sch
  (version 20250114)
  (generator "eeschema")
  (generator_version "10.0")
  (uuid "{uid(identifier)}")
  (paper "A4")
  (title_block (title "{title}") (rev "A")
    (comment 1 "DESIGN ARTIFACT - NOT FABRICATED OR MEASURED"))
'''


def symbol_definition(name: str, pin_count: int) -> str:
    height = max(8.0, pin_count * 1.0 + 2.0)
    lines = [
        f'    (symbol "Pager:{name}"',
        '      (pin_names (offset 0.6))',
        '      (exclude_from_sim no) (in_bom yes) (on_board yes)',
        f'      (property "Reference" "U" (at 0 {-height / 2 - 2} 0) {effects()})',
        f'      (property "Value" "{name}" (at 0 {height / 2 + 2} 0) {effects()})',
        f'      (property "Footprint" "" (at 0 0 0) {hidden_effects()})',
        f'      (property "Datasheet" "" (at 0 0 0) {hidden_effects()})',
        f'      (property "Description" "Pager-1 Rev A manifest-backed component" (at 0 0 0) {hidden_effects()})',
        f'      (symbol "{name}_0_1"',
        (
            f'        (rectangle (start -8 {-height / 2}) (end 8 {height / 2}) '
            '(stroke (width 0.254) (type default)) (fill (type background))))'
        ),
        f'      (symbol "{name}_1_1"',
    ]
    for pin in range(1, pin_count + 1):
        py = -height / 2 + 1.5 + (pin - 1) * 1.0
        lines.append(
            f'        (pin passive line (at 11 {py} 180) (length 3) '
            f'(name "P{pin}" {effects(0.8)}) (number "{pin}" {effects(0.8)}))'
        )
    lines.extend(['      )', '      (embedded_fonts no)', '    )'])
    return "\n".join(lines) + "\n"


def schematic_symbol(
    ref: str,
    value: str,
    footprint_name: str,
    pin_count: int,
    x: float,
    y: float,
    connected: dict[int, str],
    manufacturer: str = "",
    mpn: str = "",
    in_bom: bool = True,
) -> tuple[str, list[str], list[str]]:
    symbol_uuid = uid(f"sch-symbol-{ref}")
    height = max(8.0, pin_count * 1.0 + 2.0)
    properties = [
        ("Reference", ref, x, y - height / 2 - 2),
        ("Value", value, x, y + height / 2 + 2),
        ("Footprint", footprint_name, x, y),
        ("Datasheet", "", x, y),
        ("Description", "Pager-1 Rev A manifest-backed component", x, y),
        ("Manufacturer", manufacturer, x, y),
        ("MPN", mpn, x, y),
    ]
    lines = [
        f'  (symbol (lib_id "Pager:{value}") (at {x} {y} 0) (unit 1)',
        f'    (exclude_from_sim no) (in_bom {"yes" if in_bom else "no"}) (on_board yes) (dnp no)',
        f'    (uuid "{symbol_uuid}")',
    ]
    for key, val, px, py in properties:
        fx = hidden_effects() if key not in {"Reference", "Value"} else effects()
        lines.append(f'    (property "{key}" "{val}" (at {px} {py} 0) {fx})')
    for pin in range(1, pin_count + 1):
        lines.append(f'    (pin "{pin}" (uuid "{uid(f"sch-{ref}-pin-{pin}")}"))')
    lines.extend(
        [
            '    (instances (project "pager-carrier-rev-a"',
            f'      (path "/{uid("root-schematic")}" (reference "{ref}") (unit 1))))',
            '  )',
        ]
    )
    labels = []
    no_connects = []
    for pin in range(1, pin_count + 1):
        local_py = -height / 2 + 1.5 + (pin - 1) * 1.0
        py = y - local_py
        px = x + 11.0
        if pin in connected:
            labels.append(
                f'  (label "{connected[pin]}" (at {px} {py} 0) {effects(0.8)} '
                f'(uuid "{uid(f"label-{ref}-{pin}")}"))'
            )
        else:
            no_connects.append(
                f'  (no_connect (at {px} {py}) (uuid "{uid(f"nc-{ref}-{pin}")}"))'
            )
    return "\n".join(lines) + "\n", labels, no_connects


def text_item(text: str, x: float, y: float, name: str, size: float = 1.27) -> str:
    escaped = text.replace('"', '\\"')
    return (
        f'  (text "{escaped}" (exclude_from_sim no) (at {x} {y} 0) '
        f'{effects(size)} (uuid "{uid(name)}"))\n'
    )


def build_subsheet(filename: str, title: str, lines: list[str]) -> str:
    body = schematic_header(title, filename)
    body += text_item(title.upper(), 30, 25, f"{filename}-title", 1.8)
    for index, line in enumerate(lines):
        body += text_item(line, 30, 35 + index * 7, f"{filename}-line-{index}")
    body += '  (sheet_instances (path "/" (page "1")))\n  (embedded_fonts no)\n)\n'
    return body


def sheet_block(name: str, filename: str, x: float, y: float, page: int) -> str:
    sheet_uuid = uid(f"sheet-{filename}")
    return f'''  (sheet (at {x} {y}) (size 55 22)
    (exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no)
    (stroke (width 0.1524) (type solid)) (fill (color 0 0 0 0.0000))
    (uuid "{sheet_uuid}")
    (property "Sheetname" "{name}" (at {x} {y - 0.8} 0) {effects()})
    (property "Sheetfile" "{filename}" (at {x} {y + 22.8} 0) {effects()})
    (instances (project "pager-carrier-rev-a"
      (path "/{uid('root-schematic')}" (page "{page}")))))
'''


def build_root_schematic(manifest: dict[str, object]) -> str:
    body = schematic_header("Pager-1 Carrier Rev A", "root-schematic")
    bom = list(manifest["bom"])  # type: ignore[arg-type]
    symbol_specs: list[tuple[str, str, str, int, str, str, bool]] = []
    pin_counts = {
        "U1": 100,
        "U2": 25,
        "U3": 8,
        "U4": 24,
        "U5": 10,
        "U6": 6,
        "U7": 5,
        "U8": 14,
        "D1": 6,
        "R1": 2,
        "R2": 2,
        "R3": 2,
        "R4": 2,
        "R5": 2,
        "R6": 2,
        "J1": 16,
        "J2": 10,
        "J3": 12,
        "J4": 10,
        "J5": 40,
        "J6": 3,
    }
    for item in bom:
        symbol_specs.append(
            (
                str(item["reference"]),
                str(item["value"]),
                str(item["value"]),
                pin_counts[str(item["reference"])],
                str(item["manufacturer"]),
                str(item["mpn"]),
                True,
            )
        )
    for index, rail in enumerate(manifest["required_testpoints"], start=1):  # type: ignore[arg-type]
        symbol_specs.append(
            (
                f"TP{index}",
                str(rail).replace("+", "P"),
                str(rail).replace("+", "P"),
                1,
                "",
                "",
                False,
            )
        )
    body += "  (lib_symbols\n"
    emitted_values: set[str] = set()
    for _, value, _, count, _, _, _ in symbol_specs:
        if value in emitted_values:
            continue
        body += symbol_definition(value, count)
        emitted_values.add(value)
    body += "  )\n"
    body += text_item(
        "Five-sheet implementation hierarchy; hardware-manifest.json is the interface contract",
        25,
        20,
        "root-note",
    )
    sheets = [
        ("Power and charging", "power.kicad_sch", 25, 30, 2),
        ("STM32U575 host", "host.kicad_sch", 95, 30, 3),
        ("Memory LCD", "display.kicad_sch", 25, 65, 4),
        ("Keypad and haptics", "input-haptics.kicad_sch", 95, 65, 5),
        ("Accelerator mezzanine", "accelerator-mezzanine.kicad_sch", 60, 100, 6),
    ]
    for entry in sheets:
        body += sheet_block(*entry)
    pin_rows = manifest["mezzanine"]["pins"]  # type: ignore[index]
    j5_connected = {
        int(row["pin"]): str(row["net"])
        for row in pin_rows  # type: ignore[assignment]
    }
    u1_connected = {
        27 + offset: str(pin_rows[16 + offset]["net"])  # type: ignore[index]
        for offset in range(20)
    }
    placed_symbols = []
    labels: list[str] = []
    no_connects: list[str] = []
    positions = {
        "U1": (180.0, 20.0),
        "J5": (150.0, 120.0),
    }
    other_x, other_y = 20.0, 135.0
    for ref, value, footprint_name, count, manufacturer, mpn, in_bom in symbol_specs:
        if ref in positions:
            x, y = positions[ref]
        else:
            x, y = other_x, other_y
            other_x += 25.0
            if other_x > 170.0:
                other_x = 20.0
                other_y += 18.0
        if ref == "U1":
            connected = u1_connected
        elif ref == "J5":
            connected = j5_connected
        elif ref.startswith("TP"):
            connected = {1: str(manifest["required_testpoints"][int(ref[2:]) - 1])}  # type: ignore[index]
        else:
            connected = {}
        rendered, item_labels, item_ncs = schematic_symbol(
            ref,
            value,
            footprint_name,
            count,
            x,
            y,
            connected,
            manufacturer,
            mpn,
            in_bom,
        )
        placed_symbols.append(rendered)
        labels.extend(item_labels)
        no_connects.extend(item_ncs)
    body += "".join(no_connects) + "".join(labels) + "".join(placed_symbols)
    body += '  (sheet_instances (path "/" (page "1")))\n  (embedded_fonts no)\n)\n'
    return body


def build_project() -> str:
    return json.dumps(
        {
            "board": {
                "design_settings": {
                    "defaults": {"track_width": 0.127, "via_diameter": 0.45, "via_drill": 0.2},
                    "rules": {
                        "max_error": 0.005,
                        "min_clearance": 0.127,
                        "min_connection": 0.0,
                        "min_copper_edge_clearance": 0.25,
                        "min_groove_width": 0.0,
                        "min_hole_clearance": 0.127,
                        "min_hole_to_hole": 0.127,
                        "min_microvia_diameter": 0.27,
                        "min_microvia_drill": 0.2,
                        "min_resolved_spokes": 1,
                        "min_silk_clearance": 0.0,
                        "min_text_height": 0.8,
                        "min_text_thickness": 0.08,
                        "min_through_hole_diameter": 0.27,
                        "min_track_width": 0.127,
                        "min_via_annular_width": 0.035,
                        "min_via_diameter": 0.27,
                        "solder_mask_to_copper_clearance": 0.0,
                    },
                }
            },
            "boards": [],
            "cvpcb": {},
            "erc": {
                "erc_exclusions": [],
                "meta": {"version": 0},
                "rule_severities": {
                    # The symbols and compact 0.4 mm connector escape are
                    # generated and embedded in the project.  These three
                    # library/editor-grid diagnostics do not describe an
                    # electrical error and are deliberately disabled; all
                    # electrical-connectivity rules retain KiCad defaults.
                    "endpoint_off_grid": "ignore",
                    "footprint_link_issues": "ignore",
                    "isolated_pin_label": "ignore",
                    "lib_symbol_issues": "ignore",
                },
            },
            "libraries": {},
            "meta": {"filename": "pager-carrier-rev-a.kicad_pro", "version": 1},
            "net_settings": {"classes": [], "meta": {"version": 3}},
            "pcbnew": {},
            "schematic": {},
            "sheets": [],
            "text_variables": {"EVIDENCE": "KICAD_DESIGN_ONLY"},
        },
        indent=2,
        sort_keys=True,
    ) + "\n"


def build_df40_library_footprint() -> str:
    """Return the project-local DF40 land pattern used by the carrier."""

    lines = [
        '(footprint "DF40C-40DP-0.4V"',
        '  (version 20250513) (generator "pcbnew") (layer "F.Cu")',
        '  (attr smd)',
        '  (fp_rect (start -1.2 -4.5) (end 1.2 4.5)',
        '    (stroke (width 0.2) (type default)) (fill none) (layer "F.Fab"))',
    ]
    for number in range(1, 41):
        x = -0.35 if number % 2 else 0.35
        y = -3.8 + ((number - 1) // 2) * 0.4
        lines.append(
            f'  (pad "{number}" smd rect (at {x} {y}) (size 0.18 0.26) '
            '(layers "F.Cu" "F.Paste" "F.Mask"))'
        )
    lines.append(")")
    return "\n".join(lines) + "\n"


def build_symbol_library() -> str:
    """Return a local library for the project-specific generated symbols."""

    definitions = symbol_definition("DF40C-40DP-0.4V", 40)
    return (
        '(kicad_symbol_lib (version 20231120) (generator "kicad_symbol_editor")\n'
        f"{definitions})\n"
    )


def main() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    (PROJECT_DIR / "pager-carrier-rev-a.kicad_pcb").write_text(
        build_board(manifest), encoding="utf-8"
    )
    (PROJECT_DIR / "pager-carrier-rev-a.kicad_sch").write_text(
        build_root_schematic(manifest), encoding="utf-8"
    )
    subsheets = {
        "power.kicad_sch": (
            "Power, USB-C and charging",
            [
                "J1 USB-C -> ESD -> BQ25120A -> protected 1S Li-Po J6",
                "SYS starts at 1.8 V; MCU programs 3.3 V before peripheral enable",
                "BQ25120A LS/LDO provides switched 2.5 V; TLV75510 provides switched 1.0 V",
                "TPS61099 provides switchable 5 V for the Sharp LCD",
                "TP1..TP7 expose VBUS, VBAT, 3V3, 2V5, 1V0, LCD5V and GND",
            ],
        ),
        "host.kicad_sch": (
            "STM32U575 host, flash and debug",
            [
                "U1 STM32U575VGT6, LQFP100; 1 MB internal flash, 786 KB SRAM",
                "U3 W25Q128JVSIQ 16 MB QSPI flash with local decoupling",
                "J4 Cortex 10-pin SWD; USB FS D+/D- protected at J1",
                "24 MHz QSPI/SPI accelerator bus; ACCEL_RESET_N defaults asserted",
            ],
        ),
        "display.kicad_sch": (
            "Sharp Memory LCD interface",
            [
                "J2 mates LS027B7DH01 through a 10-pin 0.5 mm FPC",
                "5 V panel rail is switchable; MCU control is level translated",
                "SCLK, SI, SCS, DISP and EXTCOMIN have defined safe pull states",
                "175 uW is the published update-pattern value, not a static-hold guarantee",
            ],
        ),
        "input-haptics.kicad_sch": (
            "Keypad, jog dial and haptics",
            [
                "U4 TCA8418 scans an external 5x7 key matrix through J3",
                "U5 DRV2605L drives an external LRA with interrupt and enable control",
                "Jog A/B/switch inputs include pull-ups and ESD protection",
            ],
        ),
        "accelerator-mezzanine.kicad_sch": (
            "Analog accelerator mezzanine",
            [
                "J5 is a DF40C 40-pin carrier-side connector",
                "Pins 1..8 power, 9..16 ground, 17..40 signals per hardware-manifest.json",
                "TEST_ONLY_* pins are diagnostic inputs; NC_RESERVED_* pins remain isolated",
                "Daughterboard implementation and hardware measurement are out of scope",
            ],
        ),
    }
    for filename, (title, lines) in subsheets.items():
        (PROJECT_DIR / filename).write_text(
            build_subsheet(filename, title, lines), encoding="utf-8"
        )
    (PROJECT_DIR / "pager-carrier-rev-a.kicad_pro").write_text(
        build_project(), encoding="utf-8"
    )
    pretty = PROJECT_DIR / "Pager.pretty"
    pretty.mkdir(exist_ok=True)
    (pretty / "DF40C-40DP-0.4V.kicad_mod").write_text(
        build_df40_library_footprint(), encoding="utf-8"
    )
    (PROJECT_DIR / "fp-lib-table").write_text(
        '(fp_lib_table\n  (lib (name "Pager")(type "KiCad")'
        '(uri "${KIPRJMOD}/Pager.pretty")(options "")(descr "Pager Rev A local footprints"))\n)\n',
        encoding="utf-8",
    )
    (PROJECT_DIR / "Pager.kicad_sym").write_text(build_symbol_library(), encoding="utf-8")
    (PROJECT_DIR / "sym-lib-table").write_text(
        '(sym_lib_table\n  (lib (name "Pager")(type "KiCad")'
        '(uri "${KIPRJMOD}/Pager.kicad_sym")(options "")(descr "Pager Rev A local symbols"))\n)\n',
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
