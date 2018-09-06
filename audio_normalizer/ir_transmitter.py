import json
import pigpio
import time
import subprocess


class IRTransmitter(object):
    def __init__(self, command_file, output_pin=17, frequency=38.0, gap_seconds=100):
        self.output_pin = output_pin
        self.pi = pigpio.pi()
        self.commands = json.loads(command_file)
        self.pi.set_mode(self.output_pin, pigpio.OUTPUT)
        self.frequency = frequency
        self.gap_seconds = gap_seconds

    def supported_commands(self):
        return self.commands.keys()

    def transmit(self, command, delay=0.1):
        if command not in self.supported_commands():
            raise KeyError("Given command not supported!")

        code = self.commands[command]
        self.pi.wave_add_new()
        emit_time = time.time()

        marks_wid = {}
        spaces_wid = {}

        wave = [0] * len(code)

        for i in range(0, len(code)):
            ci = code[i]

            if i & 1:
                if ci not in spaces_wid:
                    self.pi.wave_add_generic([pigpio.pulse(0, 0, ci)])
                    spaces_wid[ci] = self.pi.wave_create()

                wave[i] = spaces_wid[ci]
            else:
                if ci not in marks_wid:
                    wf = self.carrier(self.frequency, ci)
                    self.pi.wave_add_generic(wf)
                    marks_wid[ci] = self.pi.wave_create()

                wave[i] = marks_wid[ci]

        delay = emit_time - time.time()

        if delay > 0.0:
            time.sleep(delay)

        self.pi.wave_chain(wave)

        while self.pi.wave_tx_busy():
            time.sleep(0.002)

        for i in marks_wid:
            self.pi.wave_delete(marks_wid[i])

        for i in spaces_wid:
            self.pi.wave_delete(spaces_wid[i])

        if delay:
            time.sleep(delay)

    def carrier(self, frequency, micros):
        """
        Generate carrier square wave.
        """
        wf = []
        cycle = 1000.0 / frequency
        cycles = int(round(micros / cycle))
        on = int(round(cycle / 2.0))
        sofar = 0

        for c in range(cycles):
            target = int(round((c + 1) * cycle))
            sofar += on
            off = target - sofar
            sofar += off
            wf.append(pigpio.pulse(1 << self.output_pin, 0, on))
            wf.append(pigpio.pulse(0, 1 << self.output_pin, off))

        return wf


class InsigniaController(IRTransmitter):
    def __init__(self, command_file, bedtime_volume=5, daytime_volume=20):
        IRTransmitter.__init__(self, command_file)

        self.powered = False
        self.display_mode = "CUSTOM"
        self.bedtime_volume = bedtime_volume
        self.daytime_volume = daytime_volume
        self.batch_volume_increase = False
        self.current_volume = 100  # Assume that the volume is at max and we're going to set it to 0
        self.set_volume(0)

    def _monitor_hdmi_events(self):
        args = ["tvservice", "-M"]
        process = subprocess.Popen(args, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        while True:
            data = process.stdout.readline()
            if data and data.startswith("["):
                if "cable is unplugged" in data.lower():
                    self.powered = False
                elif "is attached" in data.lower():
                    self.powered = True

    def power_on(self):
        # Iterate this twice in the hopes that tvservice monitor
        if not self.powered:
            self.transmit("KEY_POWER", 3)

        if not self.powered:
            self.transmit("KEY_POWER", 3)

    def decrease_volume(self):
        if not self.batch_volume_increase:
            # The first volume key press just brings up the volume menu,
            # so if this isn't a batch volume increase we have to press the key twice.
            self.transmit("KEY_VOLUME_DOWN")

        self.current_volume -= 1

    def increase_volume(self):
        if not self.batch_volume_increase:
            # The first volume key press just brings up the volume menu,
            # so if this isn't a batch volume increase we have to press the key twice.
            self.transmit("KEY_VOLUME_UP")

        self.transmit("KEY_VOLUME_UP")

        self.current_volume += 1

    def set_volume(self, volume):
        while self.current_volume != volume:
            if self.current_volume < volume:
                self.increase_volume()
            elif self.current_volume > volume:
                self.decrease_volume()

    def daytime(self):
        self.power_on()

        self.transmit("KEY_MENU", .25)
        self.transmit("KEY_DOWN")
        self.transmit("KEY_OK")
        self.transmit("KEY_DOWN")
        self.transmit("KEY_OK")
        self.transmit("KEY_EXIT")

    def bedtime(self):
        self.power_on()

        self.transmit("KEY_MENU", .25)
        self.transmit("KEY_DOWN")
        self.transmit("KEY_OK")
        self.transmit("KEY_UP")
        self.transmit("KEY_OK")
        self.transmit("KEY_EXIT")
