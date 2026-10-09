import logging

class HardwareAbstractionLayer:
    def __init__(self, printer, config):
        self.printer = printer
        self.gcode = printer.lookup_object('gcode')
        self.profile = config.get('profile', 'anycubic')
        
    def feed_guarded(self, lane, length=0, speed=0, wait=0):
        if self.profile in ['ace2k', 'snapmaker_u1', 'voron']:
            self.gcode.run_script_from_command(f"ACE_FEED_GUARDED LANE={lane} LENGTH={length} SPEED={speed} WAIT={wait}")
        else:
            # To be implemented by specific HALs or legacy Anycubic serial logic
            pass
            
    def rollback_guarded(self, lane, length=0, speed=0, wait=0):
        if self.profile in ['ace2k', 'snapmaker_u1', 'voron']:
            self.gcode.run_script_from_command(f"ACE_ROLLBACK_GUARDED LANE={lane} LENGTH={length} SPEED={speed} WAIT={wait}")
        else:
            # To be implemented by specific HALs or legacy Anycubic serial logic
            pass
            
def load_hal(printer, config):
    return HardwareAbstractionLayer(printer, config)
