# ASM2464PD Firmware

Open-source C firmware for the ASM2464PD USB4/Thunderbolt to NVMe bridge controller.

Install SDCC to build the firmware (`sudo dnf install sdcc` on Fedora).
Both firmware Makefiles automatically detect the standard tool names and Fedora's
`sdcc-sdcc` / `sdcc-sdas8051` names. Custom tools can be selected with
`make -C handmade CC=/path/to/sdcc AS=/path/to/sdas8051` (also supported in `proxy`).

The flashing scripts require tinygrad's USB support and pyftdi. Set up and
activate a Python environment before flashing or running tests:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install git+https://github.com/tinygrad/tinygrad.git pyftdi pytest
```

To flash an existing firmware file, pass its path: `python flash.py fw_tinygrad.bin`.

On Fedora, grant the active local session access to the USB debug adapter and
controller by installing the included udev rules:

```bash
sudo install -m 644 udev/60-asm2464pd.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules
```

Unplug and reconnect the USB devices after installing the rules. USB access
errors can appear as PyUSB's "The device has no langid" exception.

Build and flash the firmware for tinygrad with

```bash
make -C handmade flash
```
Source is at `handmade/src/main.c` it's short and readable

There's a 0xF0 control message that reads/writes PCIe TLPs that gets 3.6 MB/s write, 1.8 MB/s read.
This is slow, but it can read and write anywhere on the PCIe BAR.

There's a 0xF2 DMA message that reads/writes to the 512 kB SRAM on the ASM chip.
It gets 700 MB/s read+write on 10 Gbps USB3. It is accessible on the PCIe BAR at 0x200000.
The SRAM read needs a write from the PCIe device side at 0x822000 to trigger the read.
You can see an example of this working / speed test with `pcie/test_sram_verify.py`

See CLAUDE.md for more stuff like how to run the emulator.

## USB4 connection diagnostics

Capture UART at 921600 baud alongside the host kernel journal when reproducing
connection failures. The firmware emits `[EUDO aabbccdd]` on Enter_USB, with
bytes in RX buffer order (least significant byte first).

Event-driven snapshots have this format; all fields are hexadecimal bytes:

```text
[U4D seq events route ltssm link sys train lanes perst power cl0 tunnel]
```

`seq` wraps after FF. `events` is a bitmask: 01 link enable, 02 power off,
04 sideband disconnect, 08 PD timeout, 10 PCIe training start.

| Field | Snapshot source |
| --- | --- |
| route | Firmware route mode |
| ltssm | PCIe LTSSM state |
| link | Bank 1 PCIe link info: high nibble lane count, low nibble generation |
| sys | E765 system flags (bit 1 indicates PCIe link up) |
| train | E764 training control |
| lanes | C659 PCIe lane control |
| perst | B480 PERST control |
| power | C656 HDDPC control |
| cl0 | Firmware CL0 latch |
| tunnel | Firmware PCIe tunnel completion flag |

Handlers queue event bits; the main loop snapshots state with interrupts briefly
masked, then restores interrupts and the register bank before printing. Events
can coalesce, and values describe the state when main runs, not necessarily at
the instant of the event. Existing interrupt-handler UART messages may interleave
with a snapshot. These records are diagnostic clues, not proof that a GPU has
enumerated or that PCIe Gen4 is active.

The fallback reset now reports `[USB4 fallback timeout]`. Test the entry deadline,
late timeout handling, and snapshot mechanics without hardware using:

```bash
.venv/bin/python -m pytest test/test_usb4_policy.py test/test_route_mode_invariants.py -q
```
