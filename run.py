from app import create_app
import eventlet
from app.extensions import socketio
from app.extensions import db, migrate

app = create_app()
app = create_app()
migrate.init_app(app, db)
if __name__ == '__main__':
    eventlet.monkey_patch()
    app = create_app()
    
    socketio.run(app, debug=True, port=5000)