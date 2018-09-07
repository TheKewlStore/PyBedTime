from flask import Flask, make_response


app = Flask("PyBedTime_TV_Controller")


@app.route('/api/bedtime', methods=["POST"])
def py_bedtime():

    return make_response("", 200)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
