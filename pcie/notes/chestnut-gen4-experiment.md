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
