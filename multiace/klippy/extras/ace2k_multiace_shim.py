import logging

class Ace2kMultiaceShim:
    def __init__(self, config):
        self.printer = config.get_printer()
        self.reactor = self.printer.get_reactor()
        self.gcode = self.printer.lookup_object('gcode')
        
        self.gcode.register_command('ACE_FEED_GUARDED', self.cmd_ACE_FEED_GUARDED,
                                    desc="Feed until sensor triggers")
        self.gcode.register_command('ACE_ROLLBACK_GUARDED', self.cmd_ACE_ROLLBACK_GUARDED,
                                    desc="Rollback until sensor triggers")
        
        self.poll_timer = self.reactor.register_timer(self._poll_sensor)
        self.active = False
        self.sensor = None
        self.expected_state = False

    def _poll_sensor(self, eventtime):
        if not self.active or self.sensor is None:
            return self.reactor.NEVER
        
        status = self.sensor.get_status(eventtime)
        is_detected = status.get('filament_detected', False)
        
        if is_detected == self.expected_state:
            self.active = False
            self.gcode.run_script_from_command("ACE_STOP")
            return self.reactor.NEVER
            
        return eventtime + 0.05

    def _start_guarded_move(self, gcmd, move_cmd, expected_state):
        sensor_name = gcmd.get('SENSOR')
        self.sensor = None
        for prefix in ("filament_switch_sensor", "filament_motion_sensor"):
            try:
                self.sensor = self.printer.lookup_object(f"{prefix} {sensor_name}")
                break
            except Exception:
                pass
                
        if self.sensor is None:
            gcmd.respond_info(f"Could not find sensor {sensor_name}")
            return

        self.expected_state = expected_state
        self.active = True
        
        length = gcmd.get_float('LENGTH', 0.0)
        speed = gcmd.get_float('SPEED', 0.0)
        
        # Pass through optional parameters if provided, but at least trigger the move
        self.gcode.run_script_from_command(f"{move_cmd} LENGTH={length} SPEED={speed}")
        
        self.reactor.update_timer(self.poll_timer, self.reactor.NOW)

    def cmd_ACE_FEED_GUARDED(self, gcmd):
        self._start_guarded_move(gcmd, "ACE_FEED", expected_state=True)

    def cmd_ACE_ROLLBACK_GUARDED(self, gcmd):
        self._start_guarded_move(gcmd, "ACE_ROLLBACK", expected_state=False)

def load_config(config):
    return Ace2kMultiaceShim(config)
