from app import create_app, db
from app.models.user import User

app = create_app()

with app.app_context():
    # بيانات أول مستخدم
    email = "admin@example.com"
    password = "admin1234"  # تقدر تغيره
    role = "admin"  # admin, coach, athlete

    # لو الإيميل موجود بالفعل، ما يضيفش
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        print(f"⚠️ User with email '{email}' already exists.")
    else:
        user = User(
            email=email,
            name="Super Admin",  # ممكن تغير الاسم
            role=role,
            status="active"
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        print(f"✅ {role.capitalize()} created successfully!")
        print(f"📧 Email: {email}")
        print(f"🔑 Password: {password}")

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

