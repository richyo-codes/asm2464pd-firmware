# Chestnut Gen4 experiment

Build with both independent opt-ins:

```sh
make -C handmade wrapped CFLAGS_EXTRA='-DPCIE_EXPERIMENT_X4=1 -DPCIE_EXPERIMENT_GEN4=1'
```

`PCIE_EXPERIMENT_GEN4` clears B403 bit0 (advertised Gen3 maximum) and sets
the low nibble of page1 0x40B0 (target speed) to 4 in both direct and USB4
tunnel bring-up. It changes no PHY/equalization tuning. Hardware may train
at a lower speed or fail; an advertised Gen4 capability is not validation.
Check both local PCIe ends' LnkSta for 16 GT/s x4, kernel errors, and actual
GPU transfer/compute results. Default builds retain Gen3 x2.

The validated short-test rollback is the Gen3 x4 image from commit95a8b5d:
SHA256 `6de5477a64c000ec5f766c638b4c07bcb842cf3b391854693c1ae4d29af61361`.
Do not include the failed descriptor-mask experiment.

## Chestnut result, 2026-10-31

Candidate built from `e7edeb5` with both options enabled, wrapped SHA256
`d7875355b3e9fdf76462e23086ec0bb5b13349e614b136e0e0c64d6dd25c1880`.
After USB4 cable reconnect at 15:49:46 UTC, automatic authorization and
RX7900XTX amdgpu initialization succeeded. Both 69:00.0 and 6a:00.0 report
**16 GT/s x4**, target 16 GT/s and EqualizationComplete+. UART U4D link byte
is `44`, corroborating Gen4 x4 independently of PCI configuration space.

USB4 remains 20 Gb/s x1; CPU-visible VRAM remains 256 MiB. These are separate
unresolved limits. The first Vulkan harness run passed all transfer and
compute checks, with synchronous median H2D 1707.3 MB/s and D2H 1865.9 MB/s.
These include submission/fence overhead and are not peak link bandwidth.
The earlier equalization failures did not reproduce on this board/GPU.
No new PHY tuning was required for this short test.

Nine repeated runs from 15:50:08 to 15:51:13 UTC passed all 54 transfer
roundtrips and 45 compute checks. Per-run median H2D ranged 1657.7–1707.3
MB/s; D2H ranged 1775.5–1865.9 MB/s. No matching GPU/PCIe errors were logged
during the workload, and the final link remained 16 GT/s x4. This is a short
validation, not a long-duration or cold-boot stability claim.

Candidate left flashed. Captures and container stopped; Thunderbolt debug
settings restored and verified against the saved initial settings. The
source defaults remain Gen3 x2; successful Gen4 testing requires both opt-ins.
