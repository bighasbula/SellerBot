from flask import Flask
import threading
import os

app = Flask(__name__)

@app.route('/')
def health_check():
    return {"status": "healthy", "service": "photosession-bot"}, 200

@app.route('/health')
def health():
    return {"status": "healthy", "service": "photosession-bot"}, 200

def run_health_server():
    """Run the health check server on a separate thread"""
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)

def start_health_server():
    """Start health check server in background"""
    health_thread = threading.Thread(target=run_health_server, daemon=True)
    health_thread.start()
    return health_thread
