from flask import Flask, jsonify

app = Flask(__name__)  # Create a Flask app instance

# Define your health check endpoint
@app.route('/health')
def health():
    return jsonify({'status': 'ok'}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)  # Start the Flask app
