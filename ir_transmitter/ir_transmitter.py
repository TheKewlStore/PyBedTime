import json
import pigpio
import time
import subprocess
import logging
import sys
import threading


logger = logging.getLogger("ir_transmitter")


class IRTransmitter(object):
    def __init__(self, command_filepath, output_pin=17, frequency=38.0, gap_seconds=100):
        self.output_pin = output_pin
        self.pi = pigpio.pi()

        with open(command_filepath) as command_file:
            self.commands = json.load(command_file)

        self.pi.set_mode(self.output_pin, pigpio.OUTPUT)
        self.frequency = frequency
        self.gap_seconds = gap_seconds

    def transmit(self, command, end_delay=0.1):
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

                    try:
                        marks_wid[ci] = self.pi.wave_create()
                    except pigpio.error as err:
                        logger.exception("Failed to generate IR waveform for command: "
                                         + command + " - waveform was: " + str(wf), err)

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

        if end_delay:
            time.sleep(end_delay)

    def supported_commands(self):
        return self.commands.keys()

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
    def __init__(self, command_file, bedtime_volume=15, daytime_volume=25, pc_hostname="IAN-DESKTOP:8080"):
        IRTransmitter.__init__(self, command_file)

        self.powered = False
        self.display_mode = "STANDARD"
        self.bedtime_volume = bedtime_volume
        self.daytime_volume = daytime_volume
        self.batch_volume_increase = False
        self.last_powered_state_change = time.time()
        self.api_url = "http://{0}/api/".format(pc_hostname)
        self.initialized = False

        # Assume that the volume will never exceed daytime max and we're going to set it to 0
        self.current_volume = self.daytime_volume

        self.monitor_thread = threading.Thread(target=self._monitor_hdmi_events, daemon=True)

    def initialize(self):
        self.monitor_thread.start()
        self.power_on()
        self.set_volume(0)

        logger.info("InsigniaController initialized and ready for commands!")
        self.initialized = True

    def power_on(self):
        # Iterate this twice in the hopes that the tvservice monitor will update with the current tv state
        #  And then if we actually turned it off we know to turn it on again.
        if not self.powered:
            logger.info("Turning the power on first pass - not sure if it's on or not")
            self._power_cycle()

        if not self.powered:
            logger.info("turning the power on second pass - not sure if it's on or not")
            self._power_cycle()

    def _power_cycle(self):
        last_powered_state_change = self.last_powered_state_change

        self.transmit("KEY_POWER", .1)

        while last_powered_state_change == self.last_powered_state_change:
            time.sleep(.1)

        if self.powered:
            # When the tv comes on, the expected state change is on - off - on and then the tv is ready for input
            last_powered_state_change = self.last_powered_state_change

            while last_powered_state_change == self.last_powered_state_change:
                time.sleep(.1)

            assert not self.powered

            last_powered_state_change = self.last_powered_state_change

            while last_powered_state_change == self.last_powered_state_change:
                time.sleep(.1)

            assert self.powered

            # sleep for 5 seconds just to make sure it really is all good.
            time.sleep(5)
        else:
            assert not self.powered
            time.sleep(10)

    def _monitor_hdmi_events(self):
        logger.info("Beginning tvservice monitor process thread")
        args = ["tvservice", "-M"]
        process = subprocess.Popen(args, shell=False, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

        while True:
            data = process.stdout.readline().decode("ascii").lower()

            if data and data.startswith("["):
                if "cable is unplugged" in data:
                    logger.info("tvservice reported the tv turned off")
                    self.powered = False
                    self.last_powered_state_change = time.time()
                elif "is attached" in data:
                    logger.info("tvservice reported the tv turned on")
                    self.powered = True
                    self.last_powered_state_change = time.time()
                else:
                    logger.info("Found unexpected tvservice monitor message: " + data)

            time.sleep(.1)

    def increase_volume(self):
        if not self.batch_volume_increase:
            # The first volume key press just brings up the volume menu,
            # so if this isn't a batch volume increase we have to press the key twice.
            self.transmit("KEY_VOLUME_UP", 0.5)

        self.transmit("KEY_VOLUME_UP", 0.1)

        self.current_volume += 1

    def decrease_volume(self):
        if not self.batch_volume_increase:
            # The first volume key press just brings up the volume menu,
            # so if this isn't a batch volume increase we have to press the key twice.
            self.transmit("KEY_VOLUME_DOWN", 0.5)

        self.transmit("KEY_VOLUME_DOWN", 0.1)

        self.current_volume -= 1

    def set_volume(self, volume):
        self.batch_volume_increase = True

        if self.current_volume == volume:
            logger.info("Volume is already set to given value, nothing to do.")
            return

        if self.current_volume > volume:
            message = "We're over the target volume, decreasing. Current Volume: {0}, Target Volume: {1}"
            step_function = self.decrease_volume
            # Send a volume_down without decreasing the current volume counter
            self.current_volume += 1
            self.decrease_volume()
            time.sleep(.5)
        else:
            message = "We're under the target volume, increasing. Current Volume: {0}, Target Volume: {1}"
            step_function = self.increase_volume
            # Send a volume_up without increasing the current volume counter
            self.current_volume -= 1
            self.increase_volume()
            time.sleep(.5)

        while self.current_volume != volume:
            logger.debug(message.format(self.current_volume, volume))
            step_function()

        self.batch_volume_increase = False

        time.sleep(4)

    def daytime(self):
        self.power_on()
        self.set_volume(0)

        if self.display_mode == "CUSTOM":
            self.transmit("KEY_MENU", .5)
            self.transmit("KEY_DOWN", .25)
            self.transmit("KEY_OK", .25)
            self.transmit("KEY_UP", .25)
            self.transmit("KEY_OK", .25)
            self.transmit("KEY_EXIT", 1)
            self.display_mode = "STANDARD"

        self.set_volume(self.daytime_volume)

    def bedtime(self):
        self.power_on()
        self.set_volume(0)

        if self.display_mode == "STANDARD":
            self.transmit("KEY_MENU", .5)
            self.transmit("KEY_DOWN", .25)
            self.transmit("KEY_OK", .25)
            self.transmit("KEY_DOWN", .25)
            self.transmit("KEY_OK", .25)
            self.transmit("KEY_EXIT", 1)
            self.display_mode = "CUSTOM"

        self.set_volume(self.bedtime_volume)

    def update_configuration(self, configuration_data):
        self.bedtime_volume = configuration_data.get("bedtime_volume", self.bedtime_volume)
        self.daytime_volume = configuration_data.get("daytime_volume", self.daytime_volume)

        logger.info("Volume settings after config update:")
        logger.info("Bedtime volume: {0}".format(self.bedtime_volume))
        logger.info("Daytime volume: {0}".format(self.daytime_volume))


if __name__ == "__main__":
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

    controller = InsigniaController("insignia_commands.json")
    controller.bedtime()
