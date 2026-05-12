"""
Portable Pill Dispenser — V1
Automated pill dispenser with rotating drum, metered dispensing, and pill counting.

Architecture (bottom to top):
  1. RECTANGULAR BASE — electronics: ESP32, 18650 battery, TP4056 charger,
     MT3608 boost, with USB-C port accessible from the rear.
  2. DRUM PLATFORM — stationary plate with ONE metered dispensing slot.
     The slot is sized to pass one pill at a time. A chute guides
     pills from the slot down to the collection cup.
  3. ROTATING DRUM — 9 compartments (revolver-style). Servo rotates it.
     Each compartment has an open floor; only the one aligned over the
     metered slot dispenses. The stationary platform blocks all others.
  4. SNAP-FIT LID — single loading window. Rotate drum to fill each compartment.

Dispensing mechanism (gate disk — guarantees one pill at a time):
  - DRUM SERVO rotates drum so the target compartment is at the gate position
  - GATE DISK (thin rotating plate) sits between drum and stationary platform
  - Gate disk has ONE pill-sized pocket at the compartment ring radius
  - GATE SERVO rotates the gate disk between two positions:
      Position A (LOAD): pocket aligns under the active compartment.
        One pill drops into the pocket (pocket is only ~5mm deep = one pill).
      Position B (DROP): pocket aligns over the dispensing chute hole.
        The pill falls through the chute into the collection cup.
  - IR break-beam sensor confirms each pill as it falls
  - Repeat A→B cycle for each pill needed from that compartment
  - Different compartments can dispense different quantities per schedule
  - The gate disk physically prevents more than one pill at a time
  - Hall effect sensor + magnet provides home-index for position tracking
  - All compartments have CLOSED TOPS — pills stay sealed inside
  - Single loading window in the lid (rear side) — rotate drum to fill each one
  - Designed for ESPHome on the ESP32 → native Home Assistant integration

Pill Capacity (9 compartments, one per medicine type):
  - Compartment: 21.6mm dia × 25mm deep = ~9,140mm³
  - Round pill (~8mm × 4mm): ~27 per compartment, ~243 total
  - Capsule (~18mm × 7mm): ~7 per compartment, ~63 total
  - Supports different quantity per compartment (e.g., 1 of med A, 2 of med B)

Components:
  - ESP32 DevKit C V4: 55 × 28 × 13mm (WiFi + BLE, 3.3V logic)
  - SG90 micro servo: 23.5 × 12.5 × 31mm (drives drum via center shaft)
  - IR break-beam: 3mm LED + phototransistor (pill counter in chute)
  - 18650 Li-Ion: 18.5mm dia × 65mm (3.7V, ~3000mAh)
  - TP4056 USB-C: 26 × 17 × 4mm (battery charging)
  - MT3608 boost: 37 × 17 × 8mm (3.7V → 5V for servo)

Power: USB-C → TP4056 → 18650 (3.7V) → MT3608 → 5V servo.
       ESP32 gets 3.3V from its on-board LDO. Deep sleep between events.

Loadable by cadquery-server via show_object().
"""

import cadquery as cq
import math
from cq_server.ui import ui, show_object

# =============================================================================
# PARAMETRIC DIMENSIONS (all in mm)
# =============================================================================

# --- Tolerances ---
TOL = 0.3              # print tolerance per side
WALL = 2.5             # general wall thickness
WALL_THIN = 1.5        # thin internal partitions

# --- Drum (rotating pill carousel) ---
# 9 compartments — one per medicine type. Fits 8-9 different medicines.
# Each compartment holds ~27 round pills or ~7 capsules.
DRUM_COMPARTMENTS = 9
DRUM_COMP_DIA = 21.6         # compartment bore diameter (optimized for 9@R=48)
DRUM_COMP_DEPTH = 25         # compartment depth
DRUM_CENTER_DIA = 12         # central shaft bore (servo horn)
DRUM_OUTER_R = 48            # outer radius of the drum
DRUM_H = DRUM_COMP_DEPTH + WALL  # total drum height (~27.5mm)
DRUM_COMP_RING_R = 35        # radius of compartment center ring (optimized)

# --- Servos (2× SG90 micro servo) ---
# Servo 1 (center): rotates the drum to select compartment
# Servo 2 (offset): rotates the gate disk to load/drop one pill
SERVO_L = 23.5         # body length (X)
SERVO_W = 12.5         # body width (Y)
SERVO_H = 31           # body height (Z) with gear head
SERVO_EAR_W = 32       # width with mounting ears
SERVO_EAR_H = 2.5      # ear thickness
SERVO_EAR_Z = 16       # ear Z position from servo bottom
SERVO_SHAFT_DIA = 5    # output shaft diameter
SERVO2_X_OFFSET = 30   # gate servo X offset from center (in base)

# --- Gate disk (single-pill metering) ---
# Thin rotating disk between drum and platform.
# Has ONE pocket that captures exactly one pill at a time.
GATE_H = 5             # gate disk thickness (≈ one pill height)
GATE_R = DRUM_OUTER_R - 2     # gate disk outer radius
GATE_POCKET_DIA = DRUM_COMP_DIA + 1  # pocket diameter (slightly > compartment)
GATE_CENTER_DIA = 14   # center bore for gate servo shaft

# --- ESP32 DevKit C V4 ---
MCU_L = 55             # length
MCU_W = 28             # width
MCU_H = 13             # height with headers
MCU_USB_W = 9          # micro-USB port width
MCU_USB_H = 4          # micro-USB port height

# --- 18650 Li-Ion battery (3.7V) ---
BATT_DIA = 18.5
BATT_LEN = 65
BATT_HOLDER_WALL = 1.5

# --- TP4056 USB-C charge board ---
CHRG_L = 26
CHRG_W = 17
CHRG_H = 4

# --- MT3608 boost converter (3.7V → 5V) ---
BOOST_L = 37
BOOST_W = 17
BOOST_H = 8

# --- IR break-beam sensor (pill counter) ---
IR_DIA = 4             # mounting hole diameter (3mm LED + tolerance)
IR_Z_OFFSET = 6        # sensor center height above chute floor

# --- Hall effect sensor (drum position index) ---
# SS49E or A3144 hall sensor on the housing wall, magnet embedded in drum.
# ESPHome: binary_sensor with esp32_hall or GPIO pulse counter.
# One magnet between compartment 0 and N-1 gives a home index pulse.
HALL_SENSOR_W = 5      # sensor body width
HALL_SENSOR_H = 4      # sensor body height
HALL_SENSOR_D = 2      # sensor body depth
HALL_MAGNET_DIA = 4    # neodymium magnet diameter (press-fit into drum)

# --- Rectangular base (electronics bay) ---
# Wide enough for battery (71mm) + ESP32 (55mm) side by side,
# deep enough for the drum diameter.
BASE_W = 130           # width (X) — battery + ESP32 + margins
BASE_D = 110           # depth (Y) — matches drum diameter + walls
BASE_H = 28            # height (Z) — fits battery (18.5mm) + boards + floor

# --- Drum platform (stationary plate the drum rotates on) ---
PLATFORM_H = 5         # platform plate thickness
PLATFORM_R = DRUM_OUTER_R + 2   # slightly larger than drum

# --- Dispensing chute (angled slide from slot to collection cup) ---
CHUTE_ENTRY_W = 14     # metered slot width — just wider than one pill
CHUTE_ENTRY_L = 14     # metered slot length
CHUTE_ANGLE = 35       # chute angle (degrees from horizontal)
CHUTE_TUBE_W = 18      # internal chute tube width
CHUTE_TUBE_H = 18      # internal chute tube height

# --- Collection cup (front-accessible) ---
CUP_W = 40             # cup width (X)
CUP_D = 35             # cup depth (Y)
CUP_H = 25             # cup height (Z)
CUP_WALL = 2           # cup wall thickness
CUP_FRONT_LIP = 8      # low front lip so you can reach in

# --- Compartment labels ---
LABEL_W = 15             # label area width (mm) — fits small adhesive label
LABEL_D = 8              # label area depth (mm)
LABEL_RECESS = 0.6       # recess depth into drum top surface
LABEL_RIM_W = 10         # rim number emboss width
LABEL_RIM_H = 6          # rim number emboss height
LABEL_RIM_DEPTH = 0.8    # engraved depth into outer rim

# --- Snap-fit lid ---
LID_H = 8
SNAP_LIP = 1.5
SNAP_HOOK = 1.2

# --- Derived dimensions ---
# Stack (bottom to top): base → platform → gate disk gap → drum → lid
# The gate disk rotates freely in a gap between platform and drum.
GATE_GAP = GATE_H + 2         # vertical space for gate disk + clearance
DRUM_CHAMBER_H = DRUM_H + 3   # drum + top clearance
TOTAL_DRUM_SECTION_H = PLATFORM_H + GATE_GAP + DRUM_CHAMBER_H + LID_H

# The drum section (cylinder) sits centered on top of the rectangular base.
TOTAL_H = BASE_H + TOTAL_DRUM_SECTION_H


# =============================================================================
# HELPERS
# =============================================================================

def compartment_positions(n, ring_r):
    """Return (x, y) positions for n compartments on a ring."""
    return [
        (ring_r * math.cos(2 * math.pi * i / n),
         ring_r * math.sin(2 * math.pi * i / n))
        for i in range(n)
    ]


# =============================================================================
# BUILD DRUM (rotating carousel — open floor compartments)
# =============================================================================

def build_drum():
    """Rotating drum with 9 CLOSED-TOP, OPEN-BOTTOM compartments.

    Capacity: 9 × ~27 round pills = ~243 total, or 9 × ~7 capsules = ~63.

    The drum has a solid top cap — pills are sealed inside each compartment.
    To load pills, the lid is removed and compartments are filled from above
    through a single loading window in the fixed cover plate (part of the
    drum housing). Rotate the drum to bring each compartment to the window.

    The drum's FLOOR has open holes at each compartment — the stationary
    platform + gate disk below control which one dispenses.

    A small magnet pocket on the outer rim provides the home index pulse
    for the hall effect sensor (position tracking for ESPHome).
    """
    # Main cylinder
    drum = (
        cq.Workplane("XY")
        .circle(DRUM_OUTER_R)
        .extrude(DRUM_H)
    )

    # Central shaft hole
    drum = drum.cut(
        cq.Workplane("XY")
        .circle(DRUM_CENTER_DIA / 2)
        .extrude(DRUM_H)
    )

    # Compartment bores — open from the BOTTOM only, closed on top.
    # The top WALL thickness of the drum acts as the sealed lid.
    for cx, cy in compartment_positions(DRUM_COMPARTMENTS, DRUM_COMP_RING_R):
        bore = (
            cq.Workplane("XY")
            .workplane(offset=-0.5)
            .center(cx, cy)
            .circle(DRUM_COMP_DIA / 2)
            .extrude(DRUM_COMP_DEPTH + 0.5)  # stops WALL below drum top
        )
        drum = drum.cut(bore)

    # ── Hall effect magnet pocket ────────────────────────────────────────
    # Small hole in the outer rim of the drum for a press-fit neodymium
    # magnet. Positioned between compartment 0 and compartment N-1 so the
    # hall sensor can detect the "home" position.
    # The magnet sits at mid-height of the drum, on the outer rim.
    magnet_angle = math.pi / DRUM_COMPARTMENTS  # halfway between comp 0 and comp N-1
    mag_x = (DRUM_OUTER_R - HALL_MAGNET_DIA / 2 - 1) * math.cos(magnet_angle)
    mag_y = (DRUM_OUTER_R - HALL_MAGNET_DIA / 2 - 1) * math.sin(magnet_angle)
    magnet_pocket = (
        cq.Workplane("XY")
        .workplane(offset=DRUM_H / 2 - HALL_MAGNET_DIA / 2)
        .center(mag_x, mag_y)
        .circle(HALL_MAGNET_DIA / 2 + 0.1)
        .extrude(HALL_MAGNET_DIA)
    )
    drum = drum.cut(magnet_pocket)

    # ── Compartment label areas — top surface ────────────────────────────
    # Recessed rectangular pads on the drum's closed top, one per
    # compartment, centered above each bore. Users stick adhesive labels
    # (medicine name) here. The recess keeps labels flush and protected.
    for i, (cx, cy) in enumerate(compartment_positions(DRUM_COMPARTMENTS, DRUM_COMP_RING_R)):
        # Angle from center to compartment — used to orient the label
        angle = math.atan2(cy, cx)
        # Build label recess on XY, rotate into position
        label = (
            cq.Workplane("XY")
            .workplane(offset=DRUM_H - LABEL_RECESS)
            .center(cx, cy)
            .rect(LABEL_W, LABEL_D)
            .extrude(LABEL_RECESS + 0.1)
        )
        # Rotate the rectangle so its long axis points radially outward
        # (more natural orientation for reading)
        label = label.rotate((0, 0, 0), (0, 0, 1), math.degrees(angle))
        drum = drum.cut(label)

    # ── Compartment numbers — outer rim ──────────────────────────────────
    # Engraved numbers (1–9) on the drum's outer cylindrical surface.
    # Each number is a shallow rectangular pocket that can be paint-filled
    # or left as-is for tactile identification.
    for i in range(DRUM_COMPARTMENTS):
        angle = 2 * math.pi * i / DRUM_COMPARTMENTS
        # Position on outer rim surface
        rim_x = (DRUM_OUTER_R - LABEL_RIM_DEPTH / 2) * math.cos(angle)
        rim_y = (DRUM_OUTER_R - LABEL_RIM_DEPTH / 2) * math.sin(angle)
        # Engraved rectangular pocket — approximates a number badge area.
        # The number itself would be paint-filled or have a printed label.
        num_pocket = (
            cq.Workplane("XY")
            .workplane(offset=DRUM_H - LABEL_RIM_H - 1)
            .center(rim_x, rim_y)
            .rect(LABEL_RIM_W, LABEL_RIM_DEPTH + 1)
            .extrude(LABEL_RIM_H)
        )
        # Rotate so the pocket face is tangent to the cylinder surface
        num_pocket = num_pocket.rotate((0, 0, 0), (0, 0, 1), math.degrees(angle))
        drum = drum.cut(num_pocket)

    return drum


# =============================================================================
# BUILD RECTANGULAR BASE (electronics bay)
# =============================================================================

def build_base():
    """Rectangular base housing all electronics, with collection cup."""

    base = (
        cq.Workplane("XY")
        .box(BASE_W, BASE_D, BASE_H, centered=[True, True, False])
    )
    base = base.edges("|Z").fillet(4)

    # ── Internal cavity (leave walls + floor) ────────────────────────────
    cavity = (
        cq.Workplane("XY")
        .workplane(offset=WALL)
        .box(BASE_W - WALL * 2, BASE_D - WALL * 2, BASE_H - WALL * 2,
             centered=[True, True, False])
    )
    base = base.cut(cavity)

    # ── Battery pocket (18650, horizontal along X) ───────────────────────
    # Sits in the left side of the base
    batt_x = -BASE_W / 2 + WALL + BATT_LEN / 2 + 3
    batt_y = -BASE_D / 2 + WALL + BATT_DIA / 2 + 3
    batt_pocket = (
        cq.Workplane("XY")
        .workplane(offset=WALL + 0.5)
        .center(batt_x, batt_y)
        .rect(BATT_LEN + 4, BATT_DIA + 2)
        .extrude(BATT_DIA + 2)
    )
    base = base.cut(batt_pocket)

    # ── ESP32 DevKit C V4 pocket ─────────────────────────────────────────
    # Sits in the right side of the base, USB port facing rear (+Y)
    mcu_x = BASE_W / 2 - WALL - MCU_L / 2 - 3
    mcu_y = 0
    mcu_pocket = (
        cq.Workplane("XY")
        .workplane(offset=WALL + 0.5)
        .center(mcu_x, mcu_y)
        .rect(MCU_L + TOL * 2, MCU_W + TOL * 2)
        .extrude(MCU_H + 2)
    )
    base = base.cut(mcu_pocket)

    # ── TP4056 charge board pocket ───────────────────────────────────────
    # Near the rear wall, USB-C port faces out the back
    chrg_x = 0
    chrg_y = BASE_D / 2 - WALL - CHRG_W / 2 - 2
    chrg_pocket = (
        cq.Workplane("XY")
        .workplane(offset=WALL + 0.5)
        .center(chrg_x, chrg_y)
        .rect(CHRG_L + TOL * 2, CHRG_W + TOL * 2)
        .extrude(CHRG_H + 2)
    )
    base = base.cut(chrg_pocket)

    # USB-C port opening through the rear wall
    usb_port = (
        cq.Workplane("XY")
        .workplane(offset=WALL + 2)
        .center(chrg_x, BASE_D / 2)
        .box(MCU_USB_W + 2, WALL * 3, MCU_USB_H + 2, centered=True)
    )
    base = base.cut(usb_port)

    # ── MT3608 boost converter pocket ────────────────────────────────────
    boost_x = -15
    boost_y = BASE_D / 2 - WALL - BOOST_W / 2 - 2
    boost_pocket = (
        cq.Workplane("XY")
        .workplane(offset=WALL + 0.5)
        .center(boost_x, boost_y)
        .rect(BOOST_L + TOL * 2, BOOST_W + TOL * 2)
        .extrude(BOOST_H + 2)
    )
    base = base.cut(boost_pocket)

    # ── Drum servo pocket (center — rotates the drum) ───────────────────
    servo_pocket = (
        cq.Workplane("XY")
        .workplane(offset=WALL)
        .rect(SERVO_L + TOL * 2, SERVO_W + TOL * 2)
        .extrude(SERVO_H)
    )
    base = base.cut(servo_pocket)

    # Servo ear slots
    ear_slot = (
        cq.Workplane("XY")
        .workplane(offset=WALL + SERVO_EAR_Z)
        .rect(SERVO_EAR_W + TOL * 2, SERVO_W + 4)
        .extrude(SERVO_EAR_H + TOL)
    )
    base = base.cut(ear_slot)

    # Drum servo shaft hole through the base ceiling
    shaft_hole = (
        cq.Workplane("XY")
        .workplane(offset=BASE_H - WALL - 0.5)
        .circle(SERVO_SHAFT_DIA + 2)
        .extrude(WALL + 1)
    )
    base = base.cut(shaft_hole)

    # ── Gate servo pocket (offset — rotates the gate disk) ───────────────
    gate_servo_pocket = (
        cq.Workplane("XY")
        .workplane(offset=WALL)
        .center(SERVO2_X_OFFSET, 0)
        .rect(SERVO_L + TOL * 2, SERVO_W + TOL * 2)
        .extrude(SERVO_H)
    )
    base = base.cut(gate_servo_pocket)

    # Gate servo ear slots
    gate_ear_slot = (
        cq.Workplane("XY")
        .workplane(offset=WALL + SERVO_EAR_Z)
        .center(SERVO2_X_OFFSET, 0)
        .rect(SERVO_EAR_W + TOL * 2, SERVO_W + 4)
        .extrude(SERVO_EAR_H + TOL)
    )
    base = base.cut(gate_ear_slot)

    # Gate servo shaft hole through the base ceiling
    gate_shaft_hole = (
        cq.Workplane("XY")
        .workplane(offset=BASE_H - WALL - 0.5)
        .center(SERVO2_X_OFFSET, 0)
        .circle(SERVO_SHAFT_DIA + 2)
        .extrude(WALL + 1)
    )
    base = base.cut(gate_shaft_hole)

    # ── Collection cup — open-front recess at the front of the base ──────
    # This is where dispensed pills land. The user reaches in from the front.
    cup_x = DRUM_COMP_RING_R  # directly below dispensing position
    cup_y = -BASE_D / 2 + CUP_D / 2 + WALL
    # Cup cavity
    cup = (
        cq.Workplane("XY")
        .workplane(offset=WALL)
        .center(cup_x, cup_y)
        .rect(CUP_W, CUP_D)
        .extrude(CUP_H)
    )
    base = base.cut(cup)

    # Open front — cut through the front wall so user can reach in
    cup_front = (
        cq.Workplane("XY")
        .workplane(offset=WALL + CUP_FRONT_LIP)
        .center(cup_x, -BASE_D / 2)
        .box(CUP_W - CUP_WALL * 2, WALL * 3,
             CUP_H - CUP_FRONT_LIP,
             centered=[True, True, False])
    )
    base = base.cut(cup_front)

    return base


# =============================================================================
# BUILD DRUM HOUSING (cylinder on top of base: platform + drum chamber + lid)
# =============================================================================

def build_drum_housing():
    """Cylindrical section: stationary platform, gate disk gap, drum chamber.

    Stack (bottom to top within this section):
      - Platform (solid disk with dispensing hole + gate servo shaft hole)
      - Gate disk gap (where the gate disk rotates)
      - Drum chamber (where the drum rotates)
    """

    z0 = BASE_H  # bottom of drum section

    # ── Drum chamber outer wall (cylinder for full height) ───────────────
    chamber = (
        cq.Workplane("XY")
        .workplane(offset=z0)
        .circle(PLATFORM_R + WALL)
        .circle(PLATFORM_R + WALL - WALL)
        .extrude(TOTAL_DRUM_SECTION_H - LID_H)
    )

    # ── Stationary platform (solid disk) ─────────────────────────────────
    # This blocks all compartment/gate positions EXCEPT the dispensing hole.
    platform = (
        cq.Workplane("XY")
        .workplane(offset=z0)
        .circle(PLATFORM_R)
        .extrude(PLATFORM_H)
    )
    chamber = chamber.union(platform)

    # Drum servo shaft hole through the platform
    shaft_through = (
        cq.Workplane("XY")
        .workplane(offset=z0 - 0.5)
        .circle(SERVO_SHAFT_DIA + 2)
        .extrude(PLATFORM_H + GATE_GAP + 1)
    )
    chamber = chamber.cut(shaft_through)

    # Gate servo shaft hole through the platform (offset)
    gate_shaft = (
        cq.Workplane("XY")
        .workplane(offset=z0 - 0.5)
        .center(SERVO2_X_OFFSET, 0)
        .circle(SERVO_SHAFT_DIA + 2)
        .extrude(PLATFORM_H + GATE_GAP + 1)
    )
    chamber = chamber.cut(gate_shaft)

    # ── Dispensing hole in the platform ───────────────────────────────────
    # This is the ONE position where pills can fall through.
    # The gate disk's pocket must align here to drop a pill.
    # Position: compartment[0] at (DRUM_COMP_RING_R, 0)
    disp_x, disp_y = compartment_positions(DRUM_COMPARTMENTS, DRUM_COMP_RING_R)[0]
    disp_hole = (
        cq.Workplane("XY")
        .workplane(offset=z0 - 0.5)
        .center(disp_x, disp_y)
        .circle(GATE_POCKET_DIA / 2)
        .extrude(PLATFORM_H + 1)
    )
    chamber = chamber.cut(disp_hole)

    # ── Dispensing chute — vertical drop from platform to collection cup ──
    chute_top_z = z0
    chute_bot_z = WALL + CUP_FRONT_LIP + CHUTE_TUBE_H
    chute_drop = chute_top_z - chute_bot_z

    chute_vert = (
        cq.Workplane("XY")
        .workplane(offset=chute_bot_z)
        .center(disp_x, disp_y)
        .rect(CHUTE_TUBE_W, CHUTE_TUBE_H)
        .extrude(chute_drop + 1)
    )
    chamber = chamber.cut(chute_vert)

    # ── IR break-beam sensor mounts (pill counter) ───────────────────────
    # In the chute, just below the platform. Counts each pill that drops.
    ir_z = z0 - IR_Z_OFFSET
    # LED side (+Y)
    ir_led = (
        cq.Workplane("XY")
        .workplane(offset=ir_z)
        .center(disp_x, disp_y + CHUTE_TUBE_H / 2)
        .circle(IR_DIA / 2)
        .extrude(PLATFORM_R + WALL + 1)
    )
    chamber = chamber.cut(ir_led)
    # Phototransistor side (-Y)
    ir_recv = (
        cq.Workplane("XY")
        .workplane(offset=ir_z)
        .center(disp_x, disp_y - CHUTE_TUBE_H / 2)
        .circle(IR_DIA / 2)
        .extrude(PLATFORM_R + WALL + 1)
    )
    chamber = chamber.cut(ir_recv)

    # ── Hall effect sensor pocket ────────────────────────────────────────
    # Recessed into the inner wall of the drum chamber at the drum's
    # mid-height. The magnet in the drum rim passes by this sensor once
    # per revolution, giving ESPHome a home-index pulse.
    drum_mid_z = z0 + PLATFORM_H + GATE_GAP + DRUM_H / 2
    # Sensor sits on the inner wall at angle matching the magnet
    hall_angle = math.pi / DRUM_COMPARTMENTS
    hall_r = PLATFORM_R + WALL - HALL_SENSOR_D  # recessed into wall
    hall_x = hall_r * math.cos(hall_angle)
    hall_y = hall_r * math.sin(hall_angle)
    hall_pocket = (
        cq.Workplane("XY")
        .workplane(offset=drum_mid_z - HALL_SENSOR_H / 2)
        .center(hall_x, hall_y)
        .rect(HALL_SENSOR_W, HALL_SENSOR_D + 2)
        .extrude(HALL_SENSOR_H)
    )
    chamber = chamber.cut(hall_pocket)

    # Wire channel from hall sensor down to electronics bay
    hall_wire = (
        cq.Workplane("XY")
        .workplane(offset=z0 - 0.5)
        .center(hall_x, hall_y)
        .rect(3, 3)
        .extrude(drum_mid_z - z0 + 1)
    )
    chamber = chamber.cut(hall_wire)

    # ── Snap-fit lip at top for the lid ──────────────────────────────────
    lip_z = z0 + TOTAL_DRUM_SECTION_H - LID_H
    lip = (
        cq.Workplane("XY")
        .workplane(offset=lip_z - SNAP_LIP)
        .circle(PLATFORM_R + WALL - WALL + SNAP_LIP)
        .circle(PLATFORM_R + WALL - WALL)
        .extrude(SNAP_LIP)
    )
    chamber = chamber.union(lip)

    return chamber


# =============================================================================
# BUILD GATE DISK (single-pill metering mechanism)
# =============================================================================

def build_gate_disk():
    """Thin rotating disk with ONE pill-sized pocket.

    Sits in the gap between the stationary platform and the drum.
    Driven by the gate servo (offset shaft).

    Operation:
      Position A — pocket under active compartment: one pill drops in.
      Position B — pocket over dispensing hole: pill falls through to chute.

    The pocket depth (GATE_H = 5mm) physically limits it to one pill.
    The solid disk surface blocks all other compartment holes.
    """

    gate = (
        cq.Workplane("XY")
        .circle(GATE_R)
        .extrude(GATE_H)
    )

    # Center bore — rides on the drum servo shaft (free-spinning)
    center_bore = (
        cq.Workplane("XY")
        .circle(GATE_CENTER_DIA / 2)
        .extrude(GATE_H)
    )
    gate = gate.cut(center_bore)

    # Gate servo drive hole (offset — this is where the gate servo
    # shaft connects to rotate the gate disk)
    drive_hole = (
        cq.Workplane("XY")
        .center(SERVO2_X_OFFSET, 0)
        .circle(SERVO_SHAFT_DIA / 2 + TOL)
        .extrude(GATE_H)
    )
    gate = gate.cut(drive_hole)

    # Single pill pocket — at the compartment ring radius
    # This is the ONLY opening in the gate disk.
    # Position it at angle 0 (at DRUM_COMP_RING_R, 0) as the "load" position.
    pocket_x, pocket_y = DRUM_COMP_RING_R, 0
    pocket = (
        cq.Workplane("XY")
        .workplane(offset=-0.5)
        .center(pocket_x, pocket_y)
        .circle(GATE_POCKET_DIA / 2)
        .extrude(GATE_H + 1)
    )
    gate = gate.cut(pocket)

    return gate


# =============================================================================
# BUILD LID (snap-fit, with loading windows)
# =============================================================================

def build_lid():
    """Snap-fit lid with ONE loading window.

    Since the drum has closed tops on all compartments, there's a single
    loading window in the lid. To fill a specific compartment, remove the
    lid, rotate the drum to bring that compartment to the window position,
    then pour pills in. The compartment's solid top keeps everything
    sealed when the lid is on.

    The loading position is at the REAR of the unit (-X direction,
    opposite the dispensing side) so loading and dispensing don't conflict.
    """

    z0 = BASE_H
    lid_z = z0 + TOTAL_DRUM_SECTION_H - LID_H

    lid = (
        cq.Workplane("XY")
        .workplane(offset=lid_z)
        .circle(PLATFORM_R + WALL)
        .extrude(LID_H)
    )
    lid = lid.edges(">Z").fillet(2)

    # Inner cavity
    inner = (
        cq.Workplane("XY")
        .workplane(offset=lid_z - 0.5)
        .circle(PLATFORM_R + WALL - WALL)
        .extrude(LID_H - WALL + 0.5)
    )
    lid = lid.cut(inner)

    # Snap groove
    groove = (
        cq.Workplane("XY")
        .workplane(offset=lid_z - SNAP_LIP - 0.5)
        .circle(PLATFORM_R + WALL - WALL + SNAP_LIP + SNAP_HOOK)
        .circle(PLATFORM_R + WALL - WALL + SNAP_LIP - TOL)
        .extrude(SNAP_LIP + 0.5)
    )
    lid = lid.cut(groove)

    # Single loading window — at the REAR (-X), opposite the dispensing
    # chute (+X). This is where you fill compartments from above.
    # The drum's closed top means only the compartment at this position
    # is accessible.
    load_x = -DRUM_COMP_RING_R  # rear side
    load_y = 0
    lid_top_z = lid_z + LID_H
    window = (
        cq.Workplane("XY")
        .workplane(offset=lid_top_z - LID_H - 0.5)
        .center(load_x, load_y)
        .circle(DRUM_COMP_DIA / 2 + 1)
        .extrude(LID_H + 1)
    )
    lid = lid.cut(window)

    # Funnel chamfer around the loading window for easy pill pouring
    funnel = (
        cq.Workplane("XY")
        .workplane(offset=lid_top_z + 0.1)
        .center(load_x, load_y)
        .circle(DRUM_COMP_DIA / 2 + 4)
        .workplane(offset=-3)
        .center(load_x, load_y)
        .circle(DRUM_COMP_DIA / 2 + 1)
        .loft()
    )
    lid = lid.cut(funnel)

    return lid


# =============================================================================
# BUILD AND DISPLAY
# =============================================================================

# Z positions for the rotating parts:
# Gate disk sits in the gap above the platform
gate_z = BASE_H + PLATFORM_H + 1  # 1mm clearance above platform
# Drum sits above the gate disk gap
drum_z = BASE_H + PLATFORM_H + GATE_GAP + 1  # above gate gap

base = build_base()
drum_housing = build_drum_housing()
gate_disk = build_gate_disk().translate((0, 0, gate_z))
drum = build_drum().translate((0, 0, drum_z))
lid = build_lid()

show_object(base, name="base",
            options={"color": (0.2, 0.2, 0.22, 0.95)})
show_object(drum_housing, name="drum_housing",
            options={"color": (0.85, 0.85, 0.88, 0.85)})
show_object(gate_disk, name="gate_disk",
            options={"color": (0.9, 0.6, 0.2, 0.9)})
show_object(drum, name="drum",
            options={"color": (0.3, 0.7, 0.4, 0.85)})
show_object(lid, name="lid",
            options={"color": (0.85, 0.85, 0.88, 0.5)})
