import eventlet
eventlet.monkey_patch()

from app import create_app
from app.extensions import socketio, db, migrate

app = create_app()
migrate.init_app(app, db)

if __name__ == "__main__":
    socketio.run(app, debug=True, port=5000)
