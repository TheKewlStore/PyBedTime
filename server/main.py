import webbrowser

from flask import Flask, request, make_response, abort

from server.default_configuration import DefaultConfiguration


app = Flask(DefaultConfiguration.APPLICATION_NAME)
app.config.from_object(DefaultConfiguration)


@app.route('/api/open_webpage', methods=["POST"])
def open_webpage():
    if not request.json or 'url' not in request.json:
        abort(400)

    json_object = request.json
    print(json_object)

    webbrowser.open_new_tab(json_object["url"])

    return make_response("", 200)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
