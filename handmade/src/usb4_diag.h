#ifndef USB4_DIAG_H
#define USB4_DIAG_H

/* Coalesced event bits. ISR paths only queue a snapshot; main prints it. */
#define U4_DIAG_LINK_ENABLE  0x01
#define U4_DIAG_POWER_OFF    0x02
#define U4_DIAG_SB_DIS       0x04
#define U4_DIAG_PD_TIMEOUT   0x08
#define U4_DIAG_TRAIN        0x10
#define U4_DIAG_BOND_POLICY  0x20

static volatile __xdata uint8_t u4_diag_pending;
static __xdata uint8_t u4_diag_sequence;
static __xdata uint8_t u4_diag_snapshot[11];
#if USB4_EXPERIMENT_BOND_DESC
/* Captured by the main-loop routing state machine before descriptor writes. */
static __xdata uint8_t u4_diag_bond_policy[5];
#endif

/* Call only from main with DPX=0 (snapshot storage is bank-0 XDATA).
 * Capture a consistent banked-register view with IRQs
 * masked briefly, then restore IE/DPX before writing any UART characters.
 * Repeated events before main runs coalesce; this is not an event counter. */
static void usb4_diag_flush(void) {
  uint8_t saved_ie, saved_dpx, i, link_info;
  if (!u4_diag_pending) return;
  saved_ie = IE;
  IE &= (uint8_t)~IE_EA;
  saved_dpx = DPX;
  DPX = 0;
  u4_diag_snapshot[0] = u4_diag_pending;
  u4_diag_pending = 0;
  u4_diag_snapshot[1] = u4_cfg.route_mode;
  u4_diag_snapshot[2] = REG_PCIE_LTSSM_STATE;
  DPX = 1;
  /* Keep the bank-1 read in internal RAM: the snapshot itself is bank-0
   * XDATA, so writing it while DPX=1 would hit the wrong memory bank. */
  link_info = REG_PHY_PCIE_LINK_INFO;
  DPX = 0;
  u4_diag_snapshot[3] = link_info;
  u4_diag_snapshot[4] = REG_SYS_CTRL_E765;
  u4_diag_snapshot[5] = REG_PHY_TIMER_CTRL_E764;
  u4_diag_snapshot[6] = REG_PCIE_LANE_CTRL_C659;
  u4_diag_snapshot[7] = REG_PCIE_PERST_CTRL;
  u4_diag_snapshot[8] = REG_HDDPC_CTRL;
  u4_diag_snapshot[9] = u4_boot.cl0_latch;
  u4_diag_snapshot[10] = u4_boot.pcie_tunnel_done;
  DPX = saved_dpx;
  IE = saved_ie;
  uart_puts("\n[U4D ");
  uart_puthex(u4_diag_sequence++);
  for (i = 0; i < sizeof(u4_diag_snapshot); i++) {
    uart_putc(' ');
    uart_puthex(u4_diag_snapshot[i]);
  }
  uart_puts("]\n");
#if USB4_EXPERIMENT_BOND_DESC
  if (u4_diag_snapshot[0] & U4_DIAG_BOND_POLICY) {
    uart_puts("[U4B");
    for (i = 0; i < sizeof(u4_diag_bond_policy); i++) {
      uart_putc(' ');
      uart_puthex(u4_diag_bond_policy[i]);
    }
    uart_puts("]\n");
  }
#endif
}

#endif
