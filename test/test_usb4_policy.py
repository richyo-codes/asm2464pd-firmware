"""Execute firmware policy C on the host with MMIO and hardware actions stubbed.

This tests software decisions, not USB4 electrical training. The selected C
blocks come from production sources so changes are exercised by these tests.
"""
import re
import shutil
import subprocess
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / 'handmade' / 'src'


def block(filename, start):
    text = (SRC / filename).read_text()
    begin = text.index(start)
    brace = text.index('{', begin)
    depth = 1
    end = brace + 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[begin:end]


def run_c(tmp_path, source):
    compiler = shutil.which('gcc')
    if compiler is None:
        pytest.skip('A host C compiler is needed for firmware policy tests')
    path = tmp_path / 'policy.c'
    path.write_text('#include <stdint.h>\n#include <assert.h>\n' + source)
    executable = tmp_path / 'policy'
    subprocess.run([compiler, '-std=c99', '-O2', str(path), '-o', str(executable)], check=True, capture_output=True, text=True)
    subprocess.run([str(executable)], check=True, capture_output=True, text=True)


def test_discovery_hint_does_not_skip_entry_deadline(tmp_path):
    decision = block('main.c', 'if (u4_boot.pd_seen && !u4_pd.enter_usb_accepted && !u4_boot.sb_asserted)')
    run_c(tmp_path, r'''
#define USB3_FALLBACK_TICKS 4
struct { uint8_t pd_seen, sb_asserted; } u4_boot;
/* Keep the old field too so this test can reproduce the pre-fix bug. */
struct { uint8_t enter_usb_accepted, route_select_hint, usb3_fallback_flag; } u4_pd;
uint8_t usb4_fallback_ticks, resets, irq_accept, irq_sb;
#define CRITICAL_ENTER() do { if (irq_accept) u4_pd.enter_usb_accepted = 1; if (irq_sb) u4_boot.sb_asserted = 1; } while (0)
#define CRITICAL_EXIT() ((void)0)
static void usb4_fallback_to_usb3(void) { resets++; }
static void step(void) {
  for (int i = 0; i < 1; i++) {
''' + decision + r'''
  }
}
int main(void) {
  u4_boot.pd_seen = 1;
  u4_pd.route_select_hint = u4_pd.usb3_fallback_flag = 1;
  for (int i = 0; i < USB3_FALLBACK_TICKS; i++) { step(); assert(resets == 0); }
  /* Entry at the deadline wins over a stale main-loop observation. */
  irq_accept = 1; step(); assert(resets == 0);
  irq_accept = 0; u4_pd.enter_usb_accepted = 0;
  irq_sb = 1; step(); assert(resets == 0);
  irq_sb = 0; u4_boot.sb_asserted = 0;
  /* A host that never enters USB4 still gets a bounded fallback. */
  step(); assert(resets == 1);
  resets = 0; u4_pd.enter_usb_accepted = 1; step(); assert(resets == 0);
  u4_pd.enter_usb_accepted = 0; u4_boot.sb_asserted = 1; step(); assert(resets == 0);
  u4_boot.sb_asserted = 0; u4_boot.pd_seen = 0; step(); assert(resets == 0);
}
''')


def test_late_boot_timeout_does_not_recommit_a_live_connection(tmp_path):
    tick = block('pd.h', 'static void cc_pd_timer_tick(void) {')
    registers = ', '.join(sorted(set(re.findall(r'\bREG_[A-Z0-9_]+\b', tick))))
    run_c(tmp_path, r'''
#define MODE_FLAG_ROUTE_MASK 3
#define MODE_FLAG_USB3_DIRECT 4
#define U4_DIAG_PD_TIMEOUT 8
uint8_t u4_diag_pending;
struct { uint8_t msg_substate, role_state, enter_usb_accepted; } u4_pd;
struct { uint8_t sb_asserted; } u4_boot;
struct { uint8_t route_mode, routerop_desc0; } u4_cfg;
struct { uint8_t routerop_push_token; } u4_sb;
struct { uint8_t cc_subdemux_src; } u4_p12;
uint8_t u4_entered_usb_mode, commits;
static void cc_sb_reconnect_event(void) {}
static void pd_queue_ctrl_msg(uint8_t code) {}
static void uart_puts(const char *s) {}
static void pd_attach_hard_reset(void) {}
static void pd_drive_hard_reset(void) {}
static void cc_role_reset_default(void) {}
static uint8_t usb4_mode_entry_commit(void) { commits++; return 4; }
''' + 'uint8_t ' + registers + ';\n' + tick + r'''
int main(void) {
  /* Every live-state gate must suppress both route overwrite and commit. */
  for (int route = 0; route < 4; route++) {
    for (int accepted = 0; accepted < 2; accepted++) {
      for (int sb = 0; sb < 2; sb++) {
        u4_cfg.route_mode = route; u4_pd.enter_usb_accepted = accepted;
        u4_boot.sb_asserted = sb; commits = 0; u4_entered_usb_mode = 2;
        REG_CPU_DMA_INT = 2;
        cc_pd_timer_tick();
        if (route || accepted || sb) {
          assert(commits == 0); assert(u4_cfg.route_mode == route);
          assert(u4_entered_usb_mode == 2);
        } else {
          assert(commits == 1); assert(u4_cfg.route_mode == MODE_FLAG_USB3_DIRECT);
          assert(u4_entered_usb_mode == 4);
        }
        assert(REG_CPU_DMA_INT == 2);
      }
    }
  }
}
''')


def test_deferred_diagnostics_preserve_interrupts_banks_and_new_events(tmp_path):
    # Include the actual logging implementation; banked MMIO accessors below
    # assert that reads occur with IRQs masked in the correct DPX bank.
    header = (SRC / 'usb4_diag.h').read_text()
    # Model DPX applying to XDATA stores as well as MMIO reads. Every access
    # to the snapshot must happen in bank 0, including the link-info store.
    declaration = 'static __xdata uint8_t u4_diag_snapshot[11];'
    assert declaration in header
    header = header.replace(declaration, '''
static uint8_t snapshot_storage[11];
static uint8_t *snapshot_bank0(void) { assert(DPX == 0); return snapshot_storage; }
#define u4_diag_snapshot (*((uint8_t (*)[11])snapshot_bank0()))
''')
    run_c(tmp_path, r'''
#include <stdio.h>
#include <string.h>
#define __xdata
#define IE_EA 0x80
uint8_t IE, DPX, expected_ie, expected_dpx;
struct { uint8_t route_mode; } u4_cfg;
struct { uint8_t cl0_latch, pcie_tunnel_done; } u4_boot;
static uint8_t reg_read(uint8_t bank, uint8_t value) {
  assert(!(IE & IE_EA)); assert(DPX == bank); return value;
}
#define REG_PCIE_LTSSM_STATE reg_read(0, 0x78)
#define REG_PHY_PCIE_LINK_INFO reg_read(1, 0x23)
#define REG_SYS_CTRL_E765 reg_read(0, 2)
#define REG_PHY_TIMER_CTRL_E764 reg_read(0, 0x1c)
#define REG_PCIE_LANE_CTRL_C659 reg_read(0, 1)
#define REG_PCIE_PERST_CTRL reg_read(0, 0)
#define REG_HDDPC_CTRL reg_read(0, 0x20)
static void uart_putc(uint8_t c);
static void uart_puts(const char *s);
static void uart_puthex(uint8_t v);
''' + header + r'''
static char output[512];
static unsigned pos, inject;
static void uart_putc(uint8_t c) {
  assert(IE == expected_ie); assert(DPX == expected_dpx);
  output[pos++] = c; output[pos] = 0;
  if (inject) { inject = 0; u4_diag_pending |= U4_DIAG_SB_DIS; }
}
static void uart_puts(const char *s) { while (*s) uart_putc(*s++); }
static void uart_puthex(uint8_t v) {
  const char *digits = "0123456789ABCDEF";
  uart_putc(digits[v >> 4]); uart_putc(digits[v & 15]);
}
int main(void) {
  IE = expected_ie = 0x85; DPX = expected_dpx = 0;
  u4_cfg.route_mode = 1; u4_boot.cl0_latch = 3; u4_boot.pcie_tunnel_done = 1;
  usb4_diag_flush(); assert(pos == 0);
  u4_diag_pending = U4_DIAG_LINK_ENABLE | U4_DIAG_TRAIN;
  inject = 1; usb4_diag_flush();
  assert(strstr(output, "[U4D 00 11 01 78 23 02 1C 01 00 20 03 01]"));
  assert(u4_diag_pending == U4_DIAG_SB_DIS);
  IE = expected_ie = 0x05; DPX = expected_dpx = 0;
  usb4_diag_flush();
  assert(strstr(output, "[U4D 01 04 01 78 23 02 1C 01 00 20 03 01]"));
  assert(u4_diag_pending == 0);
  unsigned previous = pos; usb4_diag_flush(); assert(pos == previous);
}
''')


@pytest.mark.parametrize('enabled', [0, 1])
def test_bond_descriptor_experiment_is_scoped(tmp_path, enabled):
    helper = block('usb4_lanebond.h', 'static void u4lb_desc_apply_lanemask(void)')
    run_c(tmp_path, f'#define USB4_EXPERIMENT_BOND_DESC {enabled}\n' + r'''
uint8_t regs[256];
uint8_t u4lb_desc0_lanemask, u4lb_desc1, u4lb_desc2, u4lb_desc3;
#define DE_LANESEL 0x34
#define DE_CTRL 0x35
#define DE_OPCODE 0x36
#define P12_RD(off) regs[off]
#define P12_WR(off, value) (regs[off] = (value))
''' + helper + r'''
int main(void) {
  for (unsigned target = 0; target < 256; target++) {
    for (unsigned mask = 0; mask < 16; mask++) {
      for (unsigned high = 0; high < 256; high += 16) {
        regs[DE_LANESEL] = high | 15;
        regs[DE_CTRL] = 0x41;
        regs[DE_OPCODE] = target;
        u4lb_desc0_lanemask = !!(mask & 1);
        u4lb_desc1 = !!(mask & 2);
        u4lb_desc2 = !!(mask & 4);
        u4lb_desc3 = !!(mask & 8);
        u4lb_desc_apply_lanemask();
        if (USB4_EXPERIMENT_BOND_DESC && target == 0xd2 && mask == 2) {
          assert(regs[DE_LANESEL] == (high | 2));
          assert(regs[DE_CTRL] == 0x41);
          assert(regs[DE_OPCODE] == 0xd2);
        } else {
          /* Keep the existing behavior for every other transaction. */
          assert(regs[DE_LANESEL] == (high | 15));
          assert(regs[DE_CTRL] == 0x81);
          assert(regs[DE_OPCODE] == (0x80 | mask));
        }
      }
    }
  }
  return 0;
}
''')
