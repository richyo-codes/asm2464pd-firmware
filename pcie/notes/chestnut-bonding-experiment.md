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
