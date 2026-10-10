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
