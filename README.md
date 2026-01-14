# 🏋️ Sports Platform Backend

A production-ready REST API for managing sports training platforms with athletes, coaches, subscriptions, and real-time features.

---

## 🎯 What This Does

- **Athletes** can subscribe to coaches, access workouts, and track progress
- **Coaches** can manage athletes, create workout plans, and receive payments
- **Admins** have full control over users, subscriptions, and platform settings
- **Real-time** notifications and messaging via WebSocket
- **Payments** integrated with Paymob and PayPal

---

## 🛠 Tech Stack

- **Python 3.10+** with Flask
- **PostgreSQL** database
- **JWT** authentication (httpOnly cookies)
- **Socket.IO** for real-time features
- **Gunicorn** for production deployment

---

## 🚀 Quick Start

### 1. Install Requirements

```bash
# Clone repository
git clone <your-repo-url>
cd sports-platform-backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Set Up Database

```bash
# Install PostgreSQL if not installed
# Create database
createdb sports_platform

# Or using psql:
psql -U postgres
CREATE DATABASE sports_platform;
\q
```

### 3. Configure Environment

```bash
# Copy example file
cp .env.example .env

# Edit .env with your settings
nano .env
```

**Required settings in `.env`:**

```ini
# Flask
SECRET_KEY=your-random-secret-key-here
FLASK_ENV=development

# Database
DATABASE_URL=postgresql://username:password@localhost:5432/sports_platform

# JWT
JWT_SECRET_KEY=your-jwt-secret-key-here

# URLs
APP_BASE_URL=http://localhost:5000
FRONTEND_URL=http://localhost:3000

# Payments (optional for testing)
PAYMOB_API_KEY=your-paymob-key
PAYPAL_CLIENT_ID=your-paypal-id
```

### 4. Initialize Database

```bash
# Run migrations
flask db upgrade

# Create first admin user
flask shell
>>> from app.models.user import User
>>> from app import db
>>> admin = User(email='admin@example.com', full_name='Admin', role='admin')
>>> admin.set_password('admin123')
>>> db.session.add(admin)
>>> db.session.commit()
>>> exit()
```

### 5. Run Application

**Development:**
```bash
python run.py
```

**Production:**
```bash
gunicorn -k eventlet -w 1 -b 0.0.0.0:8000 run:app
```

Access at: `http://localhost:5000` (or `8000` for production)

---

## 📁 Project Structure

```
sports-platform-backend/
├── app/
│   ├── routes/          # API endpoints
│   ├── models/          # Database models
│   ├── services/        # Business logic
│   ├── schemas/         # Data validation
│   └── config.py        # Configuration
├── migrations/          # Database migrations
├── uploads/             # Uploaded files
├── .env                 # Environment variables (create this)
├── requirements.txt     # Python dependencies
└── run.py              # Application entry point
```

---

## 🔌 API Endpoints

### Authentication
- `POST /auth/register` - Register new user
- `POST /auth/login` - Login
- `POST /auth/logout` - Logout

### Users
- `GET /users/profile` - Get current user
- `PUT /users/profile` - Update profile
- `POST /users/profile/picture` - Upload profile picture

### Workouts (Coach)
- `GET /coach/workouts` - List all workouts
- `POST /coach/workouts` - Create workout
- `PUT /coach/workouts/:id` - Update workout
- `DELETE /coach/workouts/:id` - Delete workout

### Workouts (Athlete)
- `GET /athlete/workouts` - Get assigned workouts
- `POST /athlete/subscribe` - Subscribe to coach

### Payments
- `POST /athlete/payment/paymob` - Pay with Paymob
- `POST /athlete/payment/paypal` - Pay with PayPal

### Webhooks
- `POST /athlete/webhook/paymob` - Paymob callback
- `POST /athlete/webhook/paypal` - PayPal callback

---

## 🔐 Security Notes

- JWT tokens stored in **httpOnly cookies** (secure by default)
- **CSRF protection** enabled for all POST/PUT/DELETE requests
- Passwords hashed with Werkzeug
- File uploads restricted by type and size
- **HTTPS required** in production

---

## 🚀 Production Deployment

### On Ubuntu/Debian Server

**1. Install Dependencies**
```bash
sudo apt update
sudo apt install python3.10 python3-pip python3-venv postgresql nginx -y
```

**2. Set Up Application**
```bash
cd /var/www/sports-platform
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**3. Configure Database**
```bash
sudo -u postgres createdb sports_platform
flask db upgrade
```

**4. Set Up Systemd Service**

Create `/etc/systemd/system/sports-platform.service`:
```ini
[Unit]
Description=Sports Platform API
After=network.target

[Service]
User=www-data
WorkingDirectory=/var/www/sports-platform
Environment="PATH=/var/www/sports-platform/venv/bin"
ExecStart=/var/www/sports-platform/venv/bin/gunicorn -k eventlet -w 1 -b 127.0.0.1:8000 run:app

[Install]
WantedBy=multi-user.target
```

Start service:
```bash
sudo systemctl daemon-reload
sudo systemctl start sports-platform
sudo systemctl enable sports-platform
```

**5. Configure NGINX**

Create `/etc/nginx/sites-available/sports-platform`:
```nginx
server {
    listen 80;
    server_name api.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /socket.io {
        proxy_pass http://127.0.0.1:8000/socket.io;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

Enable and restart:
```bash
sudo ln -s /etc/nginx/sites-available/sports-platform /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

**6. Install SSL Certificate**
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d api.yourdomain.com
```

---

## 🔧 Common Issues

### Database Connection Error
```
psycopg2.OperationalError: could not connect to server
```
**Fix:** Check `DATABASE_URL` in `.env` and ensure PostgreSQL is running

### Import Error
```
ModuleNotFoundError: No module named 'flask'
```
**Fix:** Activate virtual environment: `source venv/bin/activate`

### JWT Token Issues
```
Signature verification failed
```
**Fix:** Ensure `JWT_SECRET_KEY` is set and consistent

### File Upload Fails
```
Request Entity Too Large
```
**Fix:** Increase `MAX_CONTENT_LENGTH` in `.env` and NGINX `client_max_body_size`

---

## 📞 Support

For setup assistance or technical questions, contact the development team.

**Before reaching out, please check:**
- All environment variables are set correctly
- Database is created and migrations are applied
- Virtual environment is activated
- Error logs in `logs/app.log`

---

## 📄 License

Proprietary software. All rights reserved.  
Unauthorized redistribution or modification is prohibited.

---

**Version:** 1.0.0  
**Last Updated:** January 2025