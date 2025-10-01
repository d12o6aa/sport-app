from app import create_app
import eventlet
from app.extensions import socketio
app = create_app()

if __name__ == '__main__':
    eventlet.monkey_patch()  # Must be before other imports
    app = create_app()
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)