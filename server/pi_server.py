import logging
import sys

from flask import Flask, make_response, request
from ir_transmitter.ir_transmitter import InsigniaController


logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
app = Flask("PyBedTime_TV_Controller")
insignia_controller = InsigniaController("/home/pi/PyBedTime/insignia_commands.json")
insignia_controller.daytime()


@app.route('/api/bedtime', methods=["POST"])
def py_bedtime():
    if not insignia_controller.initialized:
        return make_response("Insignia controller not ready for commands yet!", 500)

    insignia_controller.bedtime()
    return make_response("", 200)


@app.route("/api/daytime", methods=["POST"])
def py_daytime():
    if not insignia_controller.initialized:
        return make_response("Insignia controller not ready for commands yet!", 500)

    insignia_controller.daytime()
    return make_response("", 200)


@app.route("/api/pi/configuration", methods=["POST"])
def py_configuration():
    if not insignia_controller.initialized:
        return make_response("Insignia controller not ready for commands yet!", 500)

    if not request.json:
        return make_response("No valid configuration provided!", 400)

    insignia_controller.update_configuration(request.json)
    return make_response("", 200)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
