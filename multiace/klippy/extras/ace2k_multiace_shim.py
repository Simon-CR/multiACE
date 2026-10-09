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
        self.active_lane = None
        self.sensor = None
        self.expected_state = False
        self.timeout_time = 0.0

    def _poll_sensor(self, eventtime):
        if self.active_lane is None or self.sensor is None:
            return self.reactor.NEVER
        
        if eventtime > self.timeout_time:
            self.gcode.respond_info(f"Guarded move timed out for lane {self.active_lane}")
            self.active_lane = None
            return self.reactor.NEVER
        
        status = self.sensor.get_status(eventtime)
        is_detected = status.get('filament_detected', False)
        
        if is_detected == self.expected_state:
            lane = self.active_lane
            self.active_lane = None
            try:
                self.gcode.run_script_from_command(f"ACE_STOP LANE={lane}")
            except Exception as e:
                self.gcode.respond_info(f"ACE_STOP failed: {str(e)}")
            return self.reactor.NEVER
            
        return eventtime + 0.05

    def _start_guarded_move(self, gcmd, move_cmd, expected_state):
        if self.active_lane is not None:
            raise gcmd.error("A guarded move is already in progress")

        sensor_name = gcmd.get('SENSOR')
        lane = gcmd.get('LANE')
        
        self.sensor = None
        for prefix in ("filament_switch_sensor", "filament_motion_sensor"):
            try:
                self.sensor = self.printer.lookup_object(f"{prefix} {sensor_name}")
                break
            except Exception:
                pass
                
        if self.sensor is None:
            raise gcmd.error(f"Could not find sensor {sensor_name}")

        self.expected_state = expected_state
        self.active_lane = lane
        
        length = gcmd.get_float('LENGTH', 0.0)
        speed = gcmd.get_float('SPEED', 0.0)
        wait = gcmd.get_int('WAIT', 0)
        
        if speed > 0:
            timeout = (length / speed) + 10.0
        else:
            timeout = 60.0
            
        self.timeout_time = self.reactor.NOW + timeout
        
        # Pass through optional parameters if provided, but at least trigger the move
        self.gcode.run_script_from_command(f"{move_cmd} LANE={lane} LENGTH={length} SPEED={speed} WAIT={wait}")
        
        self.reactor.update_timer(self.poll_timer, self.reactor.NOW)

    def cmd_ACE_FEED_GUARDED(self, gcmd):
        self._start_guarded_move(gcmd, "ACE_FEED", expected_state=True)

    def cmd_ACE_ROLLBACK_GUARDED(self, gcmd):
        self._start_guarded_move(gcmd, "ACE_ROLLBACK", expected_state=False)

def load_config(config):
    return Ace2kMultiaceShim(config)
