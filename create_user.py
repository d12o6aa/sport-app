from app import create_app, db
from app.models.user import User
import secrets
from werkzeug.security import generate_password_hash

app = create_app()

with app.app_context():
    email = "test2@example.com"
    plain_password = secrets.token_urlsafe(16)
    print("📧 The email is:", email)
    print("🔑 The generated password is:", plain_password)

    user = User(email=email, role='admin', is_active=True,is_superadmin=True)
    user.set_password(plain_password)

    db.session.add(user)
    db.session.commit()

# admin
# test@example.com
# UT3rHoAnp12A1aLlpdeZXw

# test2@example.com
# tzMUJvyz76Umibsxd2WsRw


# coach
# test@example2.com
# aI5S_PhVWFJKwTCv_BIdJw

# athlete
# athlete@example2.com
# pvRvs3sn7pCoLPqTYPV47w

