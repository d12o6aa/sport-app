from app import create_app, db
from app.models.user import User
import secrets
from werkzeug.security import generate_password_hash

app = create_app()

with app.app_context():
    email = "test@example2.com"
    plain_password = secrets.token_urlsafe(16)
    print("📧 The email is:", email)
    print("🔑 The generated password is:", plain_password)

    user = User(email=email, role='coach')
    user.set_password(plain_password)

    db.session.add(user)
    db.session.commit()


# test@example.com
# e-ZQUuh8QcSP6FE3Cjpn4Q

# test@example2.com
# UGMAwy3A_VREUN7APH7tXg

