import webbrowser
import requests

from flask import Flask, request, make_response, abort


app = Flask("PyBedTime_PC_WebServer")
PI_HOSTNAME = "raspberrypi"
PI_PORT = 5001
PI_API_URL = 'http://{0}:{1}/api/'.format(PI_HOSTNAME, PI_PORT)


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

    return make_response("", 200)


@app.route("/api/daytime", methods=["POST"])
def daytime():
    send_pi_command("daytime")
    return make_response("", 200)


def send_pi_command(endpoint, json=None):
    response = requests.post(PI_API_URL + endpoint, json=json)
    assert response.status_code == 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
