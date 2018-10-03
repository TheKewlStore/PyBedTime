import webbrowser
import pyaudio
import requests
import time
import os

from Queue import Queue

from flask import Flask, request, make_response, abort

from audio_normalizer.audio_normalizer import AudioInputNormalizer, AudioPlaybackStreamer


input_device = "VirtualCableOutput"
output_device = "TV"


aud_manager = pyaudio.PyAudio()
normalizer = AudioInputNormalizer(aud_manager, device_name=input_device)
streamer = AudioPlaybackStreamer(aud_manager, device_name=output_device)
seg_queue = Queue()
app = Flask("PyBedTime_PC_WebServer")
PI_HOSTNAME = "raspberrypi"
PI_API_URL = 'http://{0}/api/'.format(PI_HOSTNAME)


@app.route('/api/open_webpage', methods=["POST"])
def open_webpage():
    if not request.json or 'url' not in request.json:
        abort(400)

    json_object = request.json
    print(json_object)

    webbrowser.open_new_tab(json_object["url"])

    return make_response("", 200)


@app.route("/api/bedtime", methods=["POST"])
def bedtime():
    if not request.json or "url" not in request.json:
        abort(400)

    json_object = request.json
    print(json_object)

    send_pi_command("bedtime")
    webbrowser.open_new_tab(json_object["url"])

    os.system("displayswitch.exe/internal")
    os.system("..\\lib\\nircmd.exe setdefaultsounddevice \"VirtualCableInput\" 1")

    normalizer.start_monitoring(seg_queue)
    streamer.start_playback(seg_queue)

    return make_response("", 200)


@app.route("/api/daytime", methods=["POST"])
def daytime():
    normalizer.stop()
    streamer.stop()

    os.system("displayswitch.exe/clone")
    os.system("..\\lib\\nircmd.exe setdefaultsounddevice \"TV\" 1")
    time.sleep(10)
    send_pi_command("daytime")
    return make_response("", 200)


def send_pi_command(endpoint, json=None):
    response = requests.post(PI_API_URL + endpoint, json=json)
    assert response.status_code == 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
