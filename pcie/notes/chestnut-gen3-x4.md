# Chestnut Gen3 x4 experiment (2026-10-31)

Build commit `95a8b5d` with:

```sh
make -C handmade wrapped CFLAGS_EXTRA=-DPCIE_EXPERIMENT_X4=1
```

Wrapped image SHA256:
`6de5477a64c000ec5f766c638b4c07bcb842cf3b391854693c1ae4d29af61361`.
The option removes the downstream width cap in both direct and tunnel setup.
Gen3 remains capped; the default build still uses x2. The failed bonding
helper experiment is excluded.

On kalo (Fedora bootc, kernel 7.2.13-200.fc44), Chestnut with a Sapphire
RX 7900 XTX reconnected and automatically authorized. Both local PCIe ends
(69:00.0 and 6a:00.0) report 8 GT/s x4. USB4 remains 20 Gb/s x1.

The existing Vulkan harness explicitly selects AMD device 1002:744c,
checks six 16 MiB transfer roundtrips and five compute dispatches over
4,194,304 elements. All checks passed. Medians exclude the first copy round
and include submission/fence overhead; these are not peak link rates.

| Firmware | Host to GPU | GPU to host |
|---|---:|---:|
| Restored x2 baseline | 1500.1 MB/s | 1665.0 MB/s |
| x4 candidate | 1654.0 MB/s | 1771.8 MB/s |

This single comparison suggests gains of 10.3% and 6.4%; it is not a
controlled repeated A/B benchmark. It does establish that this board can
negotiate x4 and pass a short transfer/compute test. It does not validate
Gen4, USB4 lane bonding, cold boots, or long-term signal margin.

The post-flash reset did not restore enumeration automatically. A USB4
cable reconnect recovered it, as with the x2 baseline. The reconnect was
after the timed UART capture expired; negotiated width is independently
confirmed by PCI configuration space and the host journal.

A further nine harness runs over approximately 64 seconds passed all 54
copy roundtrips and 45 compute checks. No matching GPU/PCIe runtime errors
were observed during the workload; the link remained at 8 GT/s x4.
The x4 candidate was left flashed. Temporary Thunderbolt debug settings
were restored and the test container stopped.
