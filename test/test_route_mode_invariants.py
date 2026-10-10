"""Invariants around u4_cfg.route_mode, the USB4 route/link-mode state byte.

Every one of these encodes a bug that actually shipped and cost real debugging
time.  They are source-text assertions, not behavioural: the behaviour needs a
USB4 host, a dock and a GPU, so CI cannot reach it.  The point is to make the
next person's failure a red test instead of a silent dead GPU.

Background, once, so the assertions below read as more than trivia:

  route_mode holds the USB4 route.  MODE_FLAG_ROUTE_MASK is 0x03, so a real
  route only ever occupies bits 0-1 (plus bit 7).  The value 0x04 is NOT a
  route -- it is MODE_FLAG_USB3_DIRECT, "USB3 direct, no USB4 tunnel".

  The tunnel-event dispatch gates on (route_mode & 0x81), which is what stock
  ASMedia firmware does.  Excluding 0x04 there is correct: in USB3-direct mode
  there is no tunnel to bring up.
"""
import re
from pathlib import Path

SRC = Path(__file__).parent.parent / 'handmade' / 'src'


def read(name):
    return (SRC / name).read_text()


def strip_comments(text):
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.S)
    return re.sub(r'//[^\n]*', '', text)


def test_usb3_direct_marker_never_clobbers_a_live_route():
    """A PD sender-response timeout also fires long after USB4 is up.

    Writing MODE_FLAG_USB3_DIRECT unconditionally there overwrote a live route
    (observed: 0x01) with a value meaning "no tunnel", which gated the tunnel-event
    dispatch off and left PERST asserted -- the GPU never came out of reset.
    Every write of that marker must first check no route is established.
    """
    body = strip_comments(read('pd.h'))
    for m in re.finditer(r'route_mode\s*=\s*(?:MODE_FLAG_USB3_DIRECT|0x0?4\b|4\b)', body):
        window = body[max(0, m.start() - 400):m.start()]
        assert 'MODE_FLAG_ROUTE_MASK' in window, (
            "an unguarded write of the USB3-direct marker to route_mode at offset "
            f"{m.start()} in pd.h -- guard it with (route_mode & MODE_FLAG_ROUTE_MASK) == 0, "
            "or a late timeout will overwrite a live USB4 route")


def test_tunnel_gate_stays_at_the_stock_mask():
    """0x87 was a workaround for the corrupted route above, not a fix.

    Widening the gate to admit 0x04 means enabling the PCIe tunnel while the
    firmware's own state says there is no tunnel.  Stock uses 0x81; so do we.
    """
    body = strip_comments(read('usb4_lanebond.h'))
    assert 'route_mode & 0x87' not in body.replace(' ', '').replace('route_mode&0x87', 'route_mode & 0x87'), \
        "route_mode is gated with 0x87 again -- fix whatever corrupts route_mode instead"
    assert not re.search(r'route_mode\s*&\s*0x87', body), \
        "route_mode is gated with 0x87 again -- fix whatever corrupts route_mode instead"


def test_w1c_tunnel_events_are_acked_outside_the_route_gate():
    """The 0x10/0x08 tunnel events are write-1-to-clear.

    Acking inside the route gate meant a gated-off event stayed pending forever
    and starved the else-if chain.  Stock ASMedia firmware acks first and only
    then decides whether to dispatch; the ack must not sit behind a route test.
    """
    body = strip_comments(read('usb4_lanebond.h'))
    fn = body[body.index('u4lb_tunnel_event_dispatch'):]
    fn = fn[:fn.index('\n}')]
    for bit in ('0x10', '0x08'):
        ack = f'P1_WR(P1_USB4_TUNNEL_EVENT_STATUS_1508, {bit})'
        assert ack in fn, f"missing unconditional W1C ack for {bit}"
        before = fn[:fn.index(ack)]
        branch = before.rsplit('if (p1508', 1)[-1]
        assert 'route_mode' not in branch, (
            f"the {bit} ack sits behind a route_mode test -- a gated-off event will "
            "stay pending forever and wedge the dispatch chain")


def test_the_usb3_direct_bit_is_named_not_magic():
    """0x04 in route_mode is MODE_FLAG_USB3_DIRECT.

    Written as a bare 4 it reads like a route number, which is how it ended up
    being gated against a route mask in the first place.
    """
    body = strip_comments(read('pd.h'))
    assert not re.search(r'route_mode\s*(?:\|)?=\s*(?:0x0?4|4)\s*;', body), \
        "use MODE_FLAG_USB3_DIRECT so the meaning of this value is visible at the write site"
