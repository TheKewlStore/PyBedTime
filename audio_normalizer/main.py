import threading
import time
import pyaudio

from queue import Queue
from math import ceil

from pydub import AudioSegment


def lookup_device_index(audio_manager, device_name):
    info = audio_manager.get_host_api_info_by_index(0)
    num_devices = info.get('deviceCount')

    for device_id in range(0, num_devices):
        device = audio_manager.get_device_info_by_host_api_device_index(0, device_id)
        current_name = device.get('name')

        if device_name in current_name.lower():
            return device_id

    raise KeyError("No audio device with the name " + device_name)


def match_target_amplitude(sound, target_dbfs):
    if sound.dBFS == float("+inf") or sound.dBFS == float("-inf"):
        return sound

    change_in_dbfs = target_dbfs - sound.dBFS

    print("applying gain of " + str(change_in_dbfs) + " to sound segment")
    return sound.apply_gain(change_in_dbfs)


class AudioInputNormalizer(object):
    def __init__(self, audio_manager, target_dbfs=-40.0, device_name=None):
        """

        :param audio_manager:
        :type audio_manager: pyaudio.PyAudio
        :param device_name:
        :type device_name: Union[str, None]
        """
        self.audio_manger = audio_manager
        self.target_dbfs = target_dbfs
        self.input_stream = None
        self.running = False
        self.rate = 256000
        self.chunk_size = 1024

        if device_name:
            self.device_index = lookup_device_index(self.audio_manger, device_name)
        else:
            self.device_index = None

        self.input_stream = self.audio_manger.open(format=pyaudio.paInt16,
                                                   channels=2,
                                                   rate=256000,
                                                   input=True,
                                                   frames_per_buffer=1024,
                                                   input_device_index=self.device_index)
        self.record_rate_seconds = 0.1
        self.monitor_thread = threading.Thread(target=self.run)
        self.segment_queue = None
        """ :type: Queue"""

    def start_monitoring(self, segment_queue):
        """

        :param segment_queue:
        :type segment_queue: Queue
        :return:
        """
        self.segment_queue = segment_queue
        self.running = True
        self.monitor_thread.start()

    def get_next_segment(self):
        frames = []

        for i in range(0, int(self.rate / self.chunk_size * self.record_rate_seconds)):
            data = self.input_stream.read(self.chunk_size)
            frames.append(data)

        return match_target_amplitude(AudioSegment(b''.join(frames), sample_width=2, channels=2, frame_rate=256000),
                                      self.target_dbfs)

    def run(self):
        while self.running:
            self.segment_queue.put(self.get_next_segment())

        self.input_stream.stop_stream()
        self.input_stream.close()

    def stop(self):
        self.running = False


class AudioPlaybackStreamer(object):
    def __init__(self, audio_manager, device_name=None):
        """

        :param audio_manager:
        :type audio_manager: pyaudio.PyAudio
        :param device_name:
        :type device_name: Union[str, None]
        """
        self.audio_manager = audio_manager

        if device_name:
            self.device_index = lookup_device_index(self.audio_manager, device_name)
        else:
            self.device_index = None

        self.output_stream = self.audio_manager.open(format=pyaudio.paInt16,
                                                     channels=2,
                                                     rate=256000,
                                                     output=True,
                                                     frames_per_buffer=1024,
                                                     output_device_index=self.device_index)
        self.playback_thread = threading.Thread(target=self.run)
        self.running = False
        self.segment_queue = None
        """ :type: Queue"""

    def start_playback(self, segment_queue):
        self.segment_queue = segment_queue
        self.running = True
        self.playback_thread.start()

    @staticmethod
    def _make_chunks(audio_segment, chunk_length):
        """
        Breaks an AudioSegment into chunks that are <chunk_length> milliseconds
        long.
        if chunk_length is 50 then you'll get a list of 50 millisecond long audio
        segments back (except the last one, which can be shorter)
        """
        number_of_chunks = ceil(len(audio_segment) / float(chunk_length))
        return [audio_segment[index * chunk_length:(index + 1) * chunk_length]
                for index in range(int(number_of_chunks))]

    def run(self):
        while self.running:
                segment = self.segment_queue.get()
                # break audio into half-second chunks (to allows keyboard interrupts)
                for chunk in self._make_chunks(segment, 10):
                    self.output_stream.write(chunk._data)

        self.output_stream.stop_stream()
        self.output_stream.close()

    def stop(self):
        self.running = False


if __name__ == "__main__":
    aud_manager = pyaudio.PyAudio()
    normalizer = AudioInputNormalizer(aud_manager)
    streamer = AudioPlaybackStreamer(aud_manager, device_name="ns28ed200na14")
    seg_queue = Queue()

    normalizer.start_monitoring(seg_queue)
    streamer.start_playback(seg_queue)

    while True:
        command = input("Streaming normalized sound output, enter quit to stop: ")

        if command.lower() == "quit":
            break
        else:
            time.sleep(.1)

    aud_manager.terminate()
