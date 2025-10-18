# migrations.py

from flask import Flask
from flask_migrate import Migrate
from app import create_app
from app.extensions import db # تأكد من أن app.extensions لا تستورد شيئًا قبل تهيئة التطبيق

# 1. إنشاء التطبيق (دون تشغيل socketio أو scheduler)
app = create_app()

# 2. تهيئة Flask-Migrate
migrate = Migrate(app, db)

# 3. إزالة monkey_patching عند تشغيل db migrate 
# لأننا هنا لا نشغل الخادم، فقط نحتاج الوصول إلى db و app

# 4. إذا لم ينجح الأمر، أضف السطر التالي للوصول إلى السياق:
# with app.app_context():
#    pass

# الآن قم بتشغيل الأمر كالتالي:
# flask --app migrations db migrate