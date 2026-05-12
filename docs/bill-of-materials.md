# Bill of Materials — Pill Dispenser V1

Component list for the 9-compartment automated pill dispenser. Costs in USD,
sourced from common hobbyist suppliers (Amazon US, AliExpress, DigiKey).
Prices are typical at time of writing — verify before ordering.

## Components

| # | Component | Specs | Qty | Supplier | Est. Cost (USD) |
|---|-----------|-------|-----|----------|----------------:|
| 1 | 28BYJ-48 stepper motor + ULN2003 driver board | 5V unipolar, 64:1 gearbox, ~2048 steps/rev (half-step), 300 g·cm torque, ESPHome-supported via `uln2003` platform | 2 | [Amazon](https://www.amazon.com/s?k=28byj-48+uln2003) / [AliExpress](https://www.aliexpress.com/wholesale?SearchText=28byj-48+uln2003) | $6.00 (≈$3/ea, sold as pairs) |
| 2 | IR break-beam sensor pair | 3mm IR emitter LED + phototransistor receiver, 3.3–5V, digital out via comparator or LM393 module; 3mm gap suits pill-sized falling objects | 1 pair | [Adafruit #2167](https://www.adafruit.com/product/2167) / generic AliExpress | $3.50 |
| 3 | Hall effect sensor (A3144 latching or SS49E linear) | A3144: digital, open-collector, 5V; SS49E: ratiometric analog. A3144 preferred for simple home-index detect | 1 | [Amazon](https://www.amazon.com/s?k=a3144+hall+sensor) / [DigiKey](https://www.digikey.com/) | $1.00 |
| 4 | ESP32 DevKit C V4 | Espressif ESP32-WROOM-32, dual-core 240 MHz, WiFi + BLE, USB-C, 3.3V logic, 38 pins | 1 | [Espressif](https://www.espressif.com/) / [Amazon](https://www.amazon.com/s?k=esp32+devkit+c+v4) | $8.00 |
| 5 | Neodymium disc magnet | 3–5mm diameter × 1–2mm thick, N35+ grade, axially magnetized; press-fit into drum wall | 1 (buy pack of 20) | [K&J Magnetics](https://www.kjmagnetics.com/) / [Amazon](https://www.amazon.com/s?k=3mm+neodymium+disc+magnet) | $5.00 (pack) |
| 6 | Piezo buzzer (optional) | Active 5V buzzer, 12mm dia, ~85 dB @ 10cm — for dispense confirmation beep | 1 | [Amazon](https://www.amazon.com/s?k=active+piezo+buzzer+5v) / AliExpress | $1.50 |
| 7 | USB-C power supply + cable | 5V / 2A USB-C wall adapter + 1m USB-C cable. ESP32 + 2× stepper peak draw ≈ 500–700 mA | 1 | [Amazon](https://www.amazon.com/s?k=5v+2a+usb-c+power+supply) | $8.00 |
| 8 | Jumper wires + protoboard | Dupont F-F + F-M assortment, half-size 400-point breadboard or perfboard for final wiring | 1 set | [Amazon](https://www.amazon.com/s?k=dupont+jumper+wire+breadboard+kit) | $7.00 |
| 9 | M3 screws + heat-set inserts | M3×6 / M3×10 socket-head, brass heat-set inserts for 3D-printed mounts | 1 kit | [Amazon](https://www.amazon.com/s?k=m3+heat+set+inserts+kit) | $10.00 |

**Note on stepper quantity (#1):** Two stepper+driver pairs are listed — one for
the **drum rotation** (indexing compartments) and one for the **gate disk**
(LOAD↔DROP positions). The original spec listed a single stepper; revisit if
the gate is moved back to a servo.

## Cost Summary

| Category | Subtotal |
|----------|---------:|
| Actuators (steppers + drivers) | $6.00 |
| Sensors (IR + Hall) | $4.50 |
| Compute (ESP32) | $8.00 |
| Mechanical (magnet, screws/inserts) | $15.00 |
| Power (USB-C PSU + cable) | $8.00 |
| Wiring (jumpers, protoboard) | $7.00 |
| Optional (buzzer) | $1.50 |
| **Total (with optional)** | **~$50.00** |
| **Total (without buzzer)** | **~$48.50** |

## Notes

- **Standardization:** ESP32 DevKit C V4 matches the humidifier project — one
  flashing workflow, one set of spare boards.
- **ESPHome support:** Stepper (`uln2003`), hall (`gpio` binary_sensor), IR
  break-beam (`gpio` binary_sensor with pull-up), and buzzer (`rtttl` or
  `output`) are all first-class in ESPHome.
- **Power budget:** 28BYJ-48 draws ~240 mA per phase during step; idle <5 mA.
  ESP32 with WiFi active ~160 mA. Peak ≈ 500–700 mA across both steppers if
  ever stepped simultaneously — but the firmware sequences them, so the
  realistic peak is ~400 mA. A 5V/2A supply has comfortable headroom.
- **Shipping costs not included** — bundling from a single supplier (Amazon)
  is faster but ~20% more expensive than AliExpress with 3–4 week lead time.
- **Spares:** Consider buying 2× steppers, 2× hall sensors, and 2× IR pairs
  as spares — the marginal cost is small and shipping dominates the bill.
