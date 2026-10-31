# Chestnut targeted bonding-descriptor experiment

Build with `CFLAGS_EXTRA='-DPCIE_EXPERIMENT_X4=1 -DPCIE_EXPERIMENT_GEN4=1 -DUSB4_EXPERIMENT_BOND_DESC=1'`.
The bonding option defaults to zero and is unvalidated until hardware testing.

Only a pending descriptor update with target D2 and scratch masks
00 01 00 00 gets the stock e00c/a2ff byte-enable treatment. This preserves
the target/control and updates byte enables at 1234. Other transactions
retain the existing behavior. The previous global helper correction broke
router enumeration and was removed; this experiment tests a narrower scope.
The software capability decision still chooses whether to set or clear BE.

Deferred `[U4B host_width device_cap enabled_lanes bond_latch lane_gate]`
logs five hexadecimal bytes captured before the lane0 descriptor update.
It is emitted from main after IRQ state restoration alongside U4D event20.
These fields distinguish a policy decision from a descriptor publication
failure; they do not establish that electrical bonding succeeded.

Tests execute the helper with the option both off and on across every
destination, byte-enable combination and selector high nibble. They verify
that only the intended transaction changes. Nine focused tests and the
wrapped build pass. Experimental build uses156/160 XDATA bytes.

Rollback is the working Gen4x4 firmware d7875355b3e9fdf76462e23086ec0bb5b13349e614b136e0e0c64d6dd25c1880.
Check router enumeration, PORT_CS_18.BE, host lane count, GPU PCIe link and
Vulkan correctness after reconnect. Roll back if enumeration regresses.

## Hardware result, 2026-10-31

Candidate commit `2ab0624` with all three options enabled, SHA256
`656123fa256438e758e82f633d2e898e2611b63fc498167d3c74e9e4e1b62563`.
USB4 reconnect at 16:02:30 UTC enumerated the router and GPU and authorized
automatically. Both directions now report **40 Gb/s = 2 lanes x 20 Gb/s**.
Local PCIe remains **16 GT/s x4**.

UART `[U4B F3 F3 03 01 02]` records matching host/device capabilities,
both lanes enabled and bonding latch1. UART then reports `Lane Bonded`.
Device port1 PORT_CS_18 changed from0x10 to0x110 (BE set); PHY CS1 changed
from0x4814001c to0x4824003c (target and current dual width). Kernel logs
`link width set to symmetric, dual lanes`.

This supports the descriptor publication defect as the cause of the
single-lane behavior in this configuration. It does not explain why the
broader helper correction broke enumeration; other descriptor contexts
still require separate investigation. The scoped experiment is retained.

Nine repeated Vulkan runs from16:02:53 to16:03:57UTC passed all54 transfer
roundtrips and45 compute checks. Per-run median H2D2397.2–2563.0MB/s,
D2H3278.0–3559.2MB/s; median across runs2496.2/3361.3MB/s respectively.
The first run measured2523.5/3559.2MB/s versus the earlier single-lane Gen4
first run1707.3/1865.9MB/s. These are short sequential comparisons, not a
controlled long-term A/B benchmark. No matching runtime GPU/PCIe errors
were observed. Final USB4 remained40Gb/s in both directions and PCIe16GT/sx4.

Candidate remains flashed; captures/container stopped and Thunderbolt debug
settings restored. Default builds remain unchanged (all experiment flags0).
Cold starts, host reboot recovery and long-duration stability remain untested
for this candidate. The existing256MiB visible-VRAM/BAR allocation issue is
separate and remains unresolved.
