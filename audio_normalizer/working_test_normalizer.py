import pyaudio

from math import ceil

from pydub import AudioSegment


def lookup_device_index(device_name):
    info = p.get_host_api_info_by_index(0)
    num_devices = info.get('deviceCount')

    for device_id in range(0, num_devices):
        device = p.get_device_info_by_host_api_device_index(0, device_id)
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


CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 2
RATE = 256000
RECORD_SECONDS = 0.1
ITERATIONS = 150

p = pyaudio.PyAudio()

stream = p.open(format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK)

print("* recording")

segments = []

for iteration in range(0, ITERATIONS):
    frames = []

    for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
        data = stream.read(CHUNK)
        frames.append(data)

    segments.append(AudioSegment(b''.join(frames), sample_width=2, channels=2, frame_rate=256000))

print("* done recording")

stream.stop_stream()
stream.close()

normalized_segments = []

for segment in segments:
    normalized_segments.append(match_target_amplitude(segment, -30.0))


def make_chunks(audio_segment, chunk_length):
    """
    Breaks an AudioSegment into chunks that are <chunk_length> milliseconds
    long.
    if chunk_length is 50 then you'll get a list of 50 millisecond long audio
    segments back (except the last one, which can be shorter)
    """
    number_of_chunks = ceil(len(audio_segment) / float(chunk_length))
    return [audio_segment[index * chunk_length:(index + 1) * chunk_length]
            for index in range(int(number_of_chunks))]


def _play_with_pyaudio(dev_id):
    output_stream = p.open(format=FORMAT,
                           channels=CHANNELS,
                           rate=RATE,
                           input=True,
                           frames_per_buffer=CHUNK,
                           output=True,
                           output_device_index=dev_id)

    for output_segment in normalized_segments:
        # break audio into half-second chunks (to allows keyboard interrupts)
        for chunk in make_chunks(output_segment, 5):
            output_stream.write(chunk._data)

    output_stream.stop_stream()
    output_stream.close()


while True:
    _play_with_pyaudio(lookup_device_index("ns28ed200na14"))
    command = input("Press Quit to close, or anything else to play again: ")

    if command.lower() == "quit":
        break

p.terminate()
