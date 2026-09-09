# multiace/klipper/extras/ace_rotisserie.py
"""
ACE 2 Pro Spool Rotisserie / Dry-Rolling Engine for multiACE.

Enables active, continuous spool rotation during filament drying:
- 'sweep': for threaded, ready lanes. Rolls back and forth on the ACE side of the
  park position so filament never advances toward the hub or risks tangling.
- 'spin': for unthreaded, empty lanes with tip secured. Rotates continuously in
  one direction using coupled feed-motor rollback.
- 'off': excluded.

Safety Interlocks:
- 'spin' strictly refuses if the slot reads 'ready' (preventing winding fed filament).
- 'sweep' strictly refuses if the slot reads 'empty' or uncalibrated.
- Suspends rolling immediately during active printing or toolchanges.
"""

import logging
import time

class AceRotisserie:
    def __init__(self, ace):
        self.ace = ace
        self.printer = ace.printer
        self.reactor = ace.reactor
        self.gcode = ace.gcode

        # Settings: (ace_idx, slot_idx) -> 'off' | 'sweep' | 'spin'
        self._modes = {}
        self._sweep_dir = {}  # 1 = rollback, 0 = forward
        self.interval = 300.0  # seconds between roll cycles
        self.leg = 150         # mm of sweep travel
        self.speed = 15        # mm/s
        self.is_active = False
        self._timer = None
        self._reserved_slots = set()

        self._register_commands()

    def _register_commands(self):
        self.gcode.register_command('ACE_DRYROLL_SET', self.cmd_ACE_DRYROLL_SET,
                                    desc='[multiACE] Set spool rotisserie mode. Usage: ACE_DRYROLL_SET [ACE=0] SLOT=0 MODE=sweep|spin|off')
        self.gcode.register_command('ACE_DRYROLL_CONFIG', self.cmd_ACE_DRYROLL_CONFIG,
                                    desc='[multiACE] Configure rotisserie parameters. Usage: ACE_DRYROLL_CONFIG [INTERVAL=300] [LEG=150] [SPEED=15]')
        self.gcode.register_command('ACE_DRYROLL_START', self.cmd_ACE_DRYROLL_START,
                                    desc='[multiACE] Start spool rotisserie rolling for active drying. Usage: ACE_DRYROLL_START [ACE=0]')
        self.gcode.register_command('ACE_DRYROLL_STOP', self.cmd_ACE_DRYROLL_STOP,
                                    desc='[multiACE] Stop spool rotisserie rolling. Usage: ACE_DRYROLL_STOP [ACE=0]')
        self.gcode.register_command('ACE_DRYROLL_PREPARE', self.cmd_ACE_DRYROLL_PREPARE,
                                    desc='[multiACE] PRINT_START hook: reserve print tools, park them, leave idle lanes roasting. Usage: ACE_DRYROLL_PREPARE [TOOLS=0,1]')

    def get_mode(self, ace_idx, slot):
        return self._modes.get((ace_idx, slot), 'off')

    def set_mode(self, ace_idx, slot, mode):
        m = str(mode).strip().lower()
        if m not in ('off', 'sweep', 'spin'):
            raise self.gcode.error("[multiACE] Invalid rotisserie mode '%s'. Must be 'off', 'sweep', or 'spin'." % mode)
        self._modes[(ace_idx, slot)] = m
        logging.info("[multiACE] [rotisserie] ACE %d slot %d mode set to '%s'", ace_idx, slot, m)

    def cmd_ACE_DRYROLL_SET(self, gcmd):
        ace_idx = gcmd.get_int('ACE', 0, minval=0, maxval=3)
        slot = gcmd.get_int('SLOT', minval=0, maxval=3)
        mode = gcmd.get('MODE', 'sweep')
        self.set_mode(ace_idx, slot, mode)
        gcmd.respond_info("[multiACE] Spool rotisserie ACE %d Slot %d set to '%s'" % (ace_idx, slot, mode.upper()))

    def cmd_ACE_DRYROLL_CONFIG(self, gcmd):
        self.interval = gcmd.get_float('INTERVAL', self.interval, minval=10.0, maxval=3600.0)
        self.leg = gcmd.get_int('LEG', self.leg, minval=10, maxval=1000)
        self.speed = gcmd.get_int('SPEED', self.speed, minval=5, maxval=60)
        gcmd.respond_info("[multiACE] Rotisserie config: interval=%.1fs, leg=%dmm, speed=%dmm/s" %
                          (self.interval, self.leg, self.speed))

    def cmd_ACE_DRYROLL_START(self, gcmd):
        self.start()
        gcmd.respond_info("[multiACE] Spool rotisserie started.")

    def cmd_ACE_DRYROLL_STOP(self, gcmd):
        self.stop()
        gcmd.respond_info("[multiACE] Spool rotisserie stopped.")

    def cmd_ACE_DRYROLL_PREPARE(self, gcmd):
        tools_str = gcmd.get('TOOLS', None)
        self._reserved_slots.clear()
        if tools_str:
            for t in tools_str.split(','):
                try:
                    slot = int(t.strip())
                    self._reserved_slots.add((0, slot))
                except ValueError:
                    pass
        gcmd.respond_info("[multiACE] Rotisserie reserved print slots: %s. Unreserved slots continue roasting." %
                          list(self._reserved_slots))

    def start(self):
        if self._timer is not None:
            return
        self.is_active = True
        self._timer = self.reactor.register_timer(self._tick, self.reactor.NOW)
        logging.info("[multiACE] [rotisserie] Rotisserie timer registered")

    def stop(self):
        self.is_active = False
        if self._timer is not None:
            self.reactor.unregister_timer(self._timer)
            self._timer = None
        logging.info("[multiACE] [rotisserie] Rotisserie stopped")

    def _is_printing(self):
        try:
            ps = self.printer.lookup_object('print_stats', None)
            return ps is not None and getattr(ps, 'state', '') in ('printing', 'paused')
        except Exception:
            return False

    def _get_slot_status(self, ace_idx, slot):
        info = self.ace._info_per_ace.get(ace_idx, {})
        slots = info.get('slots', [])
        if slot < len(slots) and isinstance(slots[slot], dict):
            return slots[slot].get('status', '')
        return ''

    def _tick(self, eventtime):
        if not self.is_active:
            return self.reactor.NEVER

        if getattr(self.ace, '_swap_in_progress', False) or self._is_printing():
            return eventtime + self.interval

        for (ace_idx, slot), mode in list(self._modes.items()):
            if mode == 'off':
                continue
            if (ace_idx, slot) in self._reserved_slots:
                continue

            status = self._get_slot_status(ace_idx, slot)

            if mode == 'spin':
                if status == 'ready':
                    logging.warning("[multiACE] [rotisserie] Refusing 'spin' on ACE %d slot %d: slot is THREADED (status=ready). Set mode to 'sweep' or unthread.", ace_idx, slot)
                    continue
                self._command_roll(ace_idx, slot, length=self.leg, speed=self.speed, mode=1)

            elif mode == 'sweep':
                if status != 'ready':
                    logging.info("[multiACE] [rotisserie] Skipping 'sweep' on ACE %d slot %d: slot is not ready (status=%s)", ace_idx, slot, status)
                    continue
                cur_dir = self._sweep_dir.get((ace_idx, slot), 1)
                self._command_roll(ace_idx, slot, length=self.leg, speed=self.speed, mode=cur_dir)
                self._sweep_dir[(ace_idx, slot)] = 0 if cur_dir == 1 else 1

        return eventtime + self.interval

    def _command_roll(self, ace_idx, slot, length, speed, mode):
        try:
            self.ace.send_request_to(
                ace_idx,
                {'method': 'feed_or_rollback_raw',
                 'params': {'index': slot, 'speed': int(speed), 'length': int(length), 'mode': int(mode)}},
                lambda self, response: None
            )
        except Exception as e:
            logging.info("[multiACE] [rotisserie] roll command failed for ACE %d slot %d: %s", ace_idx, slot, e)

    def get_status(self):
        return {
            'active': self.is_active,
            'interval': self.interval,
            'leg': self.leg,
            'speed': self.speed,
            'modes': {f"{a}_{s}": m for (a, s), m in self._modes.items()}
        }