from flask import Flask, request, jsonify
import threading

app = Flask(__name__)


@app.route('/generate', methods=['POST'])
def generate():
    data = request.get_json(force=True)
    prompt = data.get('prompt', '')
    # Very small deterministic "model" for testing
    if 'hello' in prompt.lower():
        text = 'print("Hello, world")'
    else:
        text = '# Generated response for prompt:\n' + prompt
    return jsonify({'text': text})


def run(port: int = 7860):
    # Run Flask in a thread-safe way for tests
    app.run(host='0.0.0.0', port=port, threaded=True)


if __name__ == '__main__':
    run()
