# 🏋️ Sports Platform Backend

A comprehensive, production-ready backend system for managing sports platforms with athletes, coaches, subscriptions, workouts, and real-time interactions.

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0+-green.svg)](https://flask.palletsprojects.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-13+-blue.svg)](https://www.postgresql.org/)
[![License](https://img.shields.io/badge/License-Proprietary-red.svg)]()

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Key Features](#-key-features)
- [Tech Stack](#-tech-stack)
- [System Architecture](#-system-architecture)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Database Setup](#-database-setup)
- [Running the Application](#-running-the-application)
- [API Documentation](#-api-documentation)
- [Security](#-security)
- [Payment Integration](#-payment-integration)
- [Real-time Features](#-real-time-features)
- [Testing](#-testing)
- [Deployment](#-deployment)
- [Troubleshooting](#-troubleshooting)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🎯 Overview

This backend platform provides a complete solution for sports training management, enabling seamless interaction between athletes and coaches through a secure, scalable REST API with real-time capabilities.

### Use Cases

- **Athletes**: Subscribe to coaches, access workout plans, track progress, upload media
- **Coaches**: Manage athlete rosters, create custom workouts, monitor performance, receive payments
- **Admins**: Full system control, user management, platform analytics, subscription oversight

---

## ✨ Key Features

### 🔐 Authentication & Authorization
- **JWT-based authentication** with secure httpOnly cookies
- **Role-based access control** (Admin, Coach, Athlete)
- **CSRF protection** on all state-changing operations
- **Password reset** via email tokens
- **Session management** with token refresh

### 👥 User Management
- Complete user CRUD operations
- Profile management with image uploads
- Role assignment and permissions
- User search and filtering
- Account suspension/activation

### 💪 Workout Management
- Create, edit, and delete workout plans
- Attach media files (images, videos)
- Categorize workouts by type
- Assign workouts to specific athletes
- Track workout completion status

### 💳 Subscription & Payments
- Flexible subscription plans
- Multiple payment gateway support:
  - **Paymob** (card payments)
  - **PayPal** (international payments)
- Automated webhook handling
- Subscription status tracking
- Payment history and receipts

### 📤 File Management
- Secure file uploads with validation
- Support for images (profile pictures, workout media)
- Configurable file size limits
- File type restrictions for security

### 💬 Real-time Communication
- **Socket.IO** integration for live updates
- Real-time notifications
- Live messaging between coaches and athletes
- Workout progress updates

### 📊 Analytics & Reporting
- User activity tracking
- Subscription metrics
- Workout completion rates
- Revenue reports

---

## 🛠 Tech Stack

### Backend Framework
- **Flask 3.0+** - Lightweight WSGI web application framework
- **Flask-RESTful** - REST API development
- **Flask-JWT-Extended** - JWT authentication
- **Flask-SocketIO** - WebSocket support with eventlet

### Database
- **PostgreSQL 13+** - Primary relational database
- **Flask-SQLAlchemy** - ORM for database operations
- **Flask-Migrate** - Database migrations using Alembic

### Serialization & Validation
- **Flask-Marshmallow** - Object serialization/deserialization
- **Marshmallow-SQLAlchemy** - SQLAlchemy integration

### Production Server
- **Gunicorn** - WSGI HTTP server
- **Eventlet** - Concurrent networking library for Socket.IO

### Additional Libraries
- **python-dotenv** - Environment variable management
- **Werkzeug** - WSGI utilities and security helpers
- **PyJWT** - JSON Web Token implementation

---

## 🏗 System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         Client Layer                        │
│              (Web App / Mobile App / Admin Panel)           │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ HTTPS/WSS
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                      API Gateway Layer                       │
│                    (NGINX / Load Balancer)                   │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                    Application Layer                         │
│  ┌────────────┐  ┌─────────────┐  ┌──────────────────┐    │
│  │   Routes   │  │  Services   │  │  Socket.IO       │    │
│  │  (API      │─▶│  (Business  │  │  (Real-time)     │    │
│  │  Endpoints)│  │   Logic)    │  │                  │    │
│  └────────────┘  └─────────────┘  └──────────────────┘    │
│                                                              │
│  ┌────────────┐  ┌─────────────┐  ┌──────────────────┐    │
│  │   Models   │  │   Schemas   │  │    Utils         │    │
│  │  (ORM)     │  │ (Validation)│  │  (Helpers)       │    │
│  └────────────┘  └─────────────┘  └──────────────────┘    │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                     Data Layer                               │
│  ┌─────────────────────┐    ┌──────────────────────┐       │
│  │   PostgreSQL DB     │    │   File Storage       │       │
│  │   (User Data,       │    │   (Uploads, Media)   │       │
│  │    Workouts, etc)   │    │                      │       │
│  └─────────────────────┘    └──────────────────────┘       │
└─────────────────────────────────────────────────────────────┘
                       │
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                  External Services                           │
│  ┌──────────┐  ┌──────────┐  ┌─────────────────────┐      │
│  │  Paymob  │  │  PayPal  │  │  Email Service      │      │
│  │ (Payment)│  │(Payment) │  │  (Notifications)    │      │
│  └──────────┘  └──────────┘  └─────────────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
sports-platform-backend/
│
├── app/                          # Main application package
│   ├── __init__.py              # App factory and initialization
│   ├── config.py                # Configuration classes (Dev/Prod/Test)
│   │
│   ├── routes/                  # API endpoints (Blueprints)
│   │   ├── __init__.py
│   │   ├── auth.py             # Authentication routes
│   │   ├── admin.py            # Admin management routes
│   │   ├── coach.py            # Coach-specific routes
│   │   ├── athlete.py          # Athlete-specific routes
│   │   └── common.py           # Shared routes
│   │
│   ├── models/                  # Database models (SQLAlchemy)
│   │   ├── __init__.py
│   │   ├── user.py             # User model
│   │   ├── workout.py          # Workout model
│   │   ├── subscription.py     # Subscription model
│   │   └── payment.py          # Payment model
│   │
│   ├── schemas/                 # Serialization schemas (Marshmallow)
│   │   ├── __init__.py
│   │   ├── user_schema.py
│   │   ├── workout_schema.py
│   │   └── subscription_schema.py
│   │
│   ├── services/                # Business logic layer
│   │   ├── __init__.py
│   │   ├── auth_service.py
│   │   ├── payment_service.py
│   │   └── notification_service.py
│   │
│   ├── utils/                   # Helper functions
│   │   ├── __init__.py
│   │   ├── decorators.py       # Custom decorators
│   │   ├── validators.py       # Input validation
│   │   └── helpers.py          # General utilities
│   │
│   ├── templates/               # Email templates (if using)
│   │   └── email/
│   │
│   └── static/                  # Static assets
│       └── uploads/             # Uploaded files
│
├── migrations/                  # Database migrations (Alembic)
│   ├── versions/
│   └── alembic.ini
│
├── tests/                       # Test suite
│   ├── __init__.py
│   ├── test_auth.py
│   ├── test_users.py
│   └── test_workouts.py
│
├── uploads/                     # User-uploaded files
│   ├── profiles/
│   └── workouts/
│
├── logs/                        # Application logs
│
├── .env.example                 # Environment variables template
├── .gitignore                   # Git ignore rules
├── requirements.txt             # Python dependencies
├── run.py                       # Application entry point
├── gunicorn_config.py          # Gunicorn configuration
├── README.md                    # This file
└── LICENSE                      # License information
```

---

## 🚀 Installation

### Prerequisites

- **Python 3.10+**
- **PostgreSQL 13+**
- **pip** (Python package manager)
- **virtualenv** (recommended)
- **Git**

### Step-by-Step Installation

#### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/sports-platform-backend.git
cd sports-platform-backend
```

#### 2. Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Linux/Mac:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

#### 3. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

#### 4. Set Up PostgreSQL Database

```bash
# Login to PostgreSQL
psql -U postgres

# Create database
CREATE DATABASE sports_platform;

# Create user (optional)
CREATE USER sports_user WITH PASSWORD 'your_password';

# Grant privileges
GRANT ALL PRIVILEGES ON DATABASE sports_platform TO sports_user;

# Exit
\q
```

#### 5. Configure Environment Variables

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your settings
nano .env  # or use your preferred editor
```

---

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the root directory with the following variables:

```ini
# ===========================
# Flask Configuration
# ===========================
FLASK_ENV=production                    # Options: development, production, testing
FLASK_APP=run.py
SECRET_KEY=your-super-secret-key-here-change-this-in-production
DEBUG=False                             # Set to True only in development

# ===========================
# Database Configuration
# ===========================
# Format: postgresql://username:password@host:port/database
DATABASE_URL=postgresql://sports_user:your_password@localhost:5432/sports_platform

# ===========================
# JWT Configuration
# ===========================
JWT_SECRET_KEY=your-jwt-secret-key-change-this-in-production
JWT_ACCESS_TOKEN_EXPIRES=3600           # 1 hour in seconds
JWT_REFRESH_TOKEN_EXPIRES=2592000      # 30 days in seconds
JWT_TOKEN_LOCATION=cookies
JWT_COOKIE_SECURE=True                  # Set to False in development (HTTP)
JWT_COOKIE_CSRF_PROTECT=True
JWT_COOKIE_SAMESITE=Lax

# ===========================
# Application URLs
# ===========================
APP_BASE_URL=https://yourdomain.com
FRONTEND_URL=https://app.yourdomain.com

# ===========================
# CORS Configuration
# ===========================
CORS_ORIGINS=https://app.yourdomain.com,https://admin.yourdomain.com

# ===========================
# File Upload Configuration
# ===========================
MAX_CONTENT_LENGTH=16777216             # 16MB in bytes
UPLOAD_FOLDER=uploads
ALLOWED_EXTENSIONS=jpg,jpeg,png,gif,mp4,mov

# ===========================
# Email Configuration (Optional)
# ===========================
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
MAIL_DEFAULT_SENDER=noreply@yourdomain.com

# ===========================
# Payment Gateway: Paymob
# ===========================
PAYMOB_API_KEY=your-paymob-api-key
PAYMOB_INTEGRATION_ID_CARD=your-integration-id
PAYMOB_IFRAME_ID=your-iframe-id
PAYMOB_HMAC_SECRET=your-hmac-secret
PAYMOB_CALLBACK_URL=https://yourdomain.com/athlete/webhook/paymob

# ===========================
# Payment Gateway: PayPal
# ===========================
PAYPAL_CLIENT_ID=your-paypal-client-id
PAYPAL_SECRET=your-paypal-secret
PAYPAL_MODE=live                        # Options: sandbox, live
PAYPAL_WEBHOOK_URL=https://yourdomain.com/athlete/webhook/paypal

# ===========================
# Logging Configuration
# ===========================
LOG_LEVEL=INFO                          # Options: DEBUG, INFO, WARNING, ERROR
LOG_FILE=logs/app.log

# ===========================
# Redis (Optional - for caching/sessions)
# ===========================
REDIS_URL=redis://localhost:6379/0
```

### Configuration Classes

The application uses three configuration environments (defined in `app/config.py`):

- **DevelopmentConfig**: Debug enabled, relaxed security
- **ProductionConfig**: Debug disabled, strict security
- **TestingConfig**: In-memory SQLite database

---

## 🗄 Database Setup

### Running Migrations

```bash
# Initialize migrations (first time only)
flask db init

# Create a new migration
flask db migrate -m "Initial migration"

# Apply migrations to database
flask db upgrade

# Rollback last migration (if needed)
flask db downgrade
```

### Database Schema Overview

```sql
-- Users table (coaches, athletes, admins)
users (
  id, email, password_hash, role, full_name,
  profile_picture, created_at, updated_at
)

-- Subscriptions
subscriptions (
  id, athlete_id, coach_id, plan_type,
  start_date, end_date, status, payment_id
)

-- Workouts
workouts (
  id, coach_id, title, description,
  category, media_files, created_at
)

-- Workout Assignments
workout_assignments (
  id, workout_id, athlete_id, assigned_date,
  completion_status, notes
)

-- Payments
payments (
  id, user_id, amount, currency, gateway,
  transaction_id, status, created_at
)
```

### Creating the First Admin User

Since there's no automatic admin creation for security reasons, create one manually:

```bash
# Option 1: Using Python shell
flask shell

>>> from app.models.user import User
>>> from app import db
>>> admin = User(
...     email='admin@yourdomain.com',
...     full_name='Admin User',
...     role='admin'
... )
>>> admin.set_password('secure_password_here')
>>> db.session.add(admin)
>>> db.session.commit()
>>> exit()
```

---

## ▶️ Running the Application

### Development Mode

```bash
# Set environment
export FLASK_ENV=development

# Run with Flask development server
python run.py

# Or use Flask CLI
flask run --host=0.0.0.0 --port=5000
```

The application will be available at `http://localhost:5000`

### Production Mode

```bash
# Set environment
export FLASK_ENV=production

# Run with Gunicorn
gunicorn -c gunicorn_config.py run:app

# Or with specific settings
gunicorn \
  --bind 0.0.0.0:8000 \
  --workers 4 \
  --worker-class eventlet \
  --timeout 120 \
  --access-logfile logs/access.log \
  --error-logfile logs/error.log \
  run:app
```

### Using Process Manager (Recommended for Production)

Create a systemd service file `/etc/systemd/system/sports-platform.service`:

```ini
[Unit]
Description=Sports Platform Backend
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/sports-platform
Environment="PATH=/var/www/sports-platform/venv/bin"
ExecStart=/var/www/sports-platform/venv/bin/gunicorn -c gunicorn_config.py run:app

[Install]
WantedBy=multi-user.target
```

Then start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl start sports-platform
sudo systemctl enable sports-platform
sudo systemctl status sports-platform
```

---

## 📚 API Documentation

### Base URL

```
Production: https://api.yourdomain.com
Development: http://localhost:5000
```

### Authentication Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/auth/register` | Register new user | No |
| POST | `/auth/login` | Login user | No |
| POST | `/auth/logout` | Logout user | Yes |
| POST | `/auth/refresh` | Refresh access token | Yes |
| POST | `/auth/forgot-password` | Request password reset | No |
| POST | `/auth/reset-password` | Reset password with token | No |

### User Management Endpoints

| Method | Endpoint | Description | Roles |
|--------|----------|-------------|-------|
| GET | `/users/profile` | Get current user profile | All |
| PUT | `/users/profile` | Update profile | All |
| POST | `/users/profile/picture` | Upload profile picture | All |
| GET | `/admin/users` | List all users | Admin |
| DELETE | `/admin/users/:id` | Delete user | Admin |

### Workout Endpoints

| Method | Endpoint | Description | Roles |
|--------|----------|-------------|-------|
| GET | `/coach/workouts` | List coach's workouts | Coach |
| POST | `/coach/workouts` | Create new workout | Coach |
| GET | `/coach/workouts/:id` | Get workout details | Coach |
| PUT | `/coach/workouts/:id` | Update workout | Coach |
| DELETE | `/coach/workouts/:id` | Delete workout | Coach |
| GET | `/athlete/workouts` | List assigned workouts | Athlete |

### Subscription Endpoints

| Method | Endpoint | Description | Roles |
|--------|----------|-------------|-------|
| POST | `/athlete/subscribe` | Subscribe to coach | Athlete |
| GET | `/athlete/subscriptions` | List subscriptions | Athlete |
| POST | `/athlete/payment/paymob` | Initiate Paymob payment | Athlete |
| POST | `/athlete/payment/paypal` | Initiate PayPal payment | Athlete |

### Webhook Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/athlete/webhook/paymob` | Paymob payment callback | No (verified by HMAC) |
| POST | `/athlete/webhook/paypal` | PayPal payment callback | No (verified by signature) |

### Example Request/Response

#### Register User

**Request:**
```http
POST /auth/register
Content-Type: application/json

{
  "email": "athlete@example.com",
  "password": "SecurePass123!",
  "full_name": "John Athlete",
  "role": "athlete"
}
```

**Response:**
```json
{
  "success": true,
  "message": "User registered successfully",
  "data": {
    "id": 1,
    "email": "athlete@example.com",
    "full_name": "John Athlete",
    "role": "athlete",
    "created_at": "2025-01-14T10:30:00Z"
  }
}
```

---

## 🔐 Security

### Authentication Flow

1. **Registration**: User creates account with email/password
2. **Login**: Server validates credentials and issues JWT tokens
3. **Access Token**: Short-lived token (1 hour) stored in httpOnly cookie
4. **Refresh Token**: Long-lived token (30 days) for obtaining new access tokens
5. **CSRF Protection**: All state-changing requests require valid CSRF token

### Security Best Practices Implemented

✅ **Password Security**
- Passwords hashed using Werkzeug's `generate_password_hash`
- Minimum password requirements enforced
- Password reset via secure email tokens

✅ **Token Security**
- JWTs stored in httpOnly cookies (not accessible via JavaScript)
- CSRF tokens required for all POST/PUT/DELETE requests
- Token expiration and automatic refresh

✅ **Input Validation**
- All inputs validated using Marshmallow schemas
- SQL injection prevention via SQLAlchemy ORM
- File upload restrictions (type, size)

✅ **HTTPS Enforcement**
- Secure cookies only transmitted over HTTPS
- HSTS headers recommended in production

✅ **Rate Limiting**
- Consider implementing Flask-Limiter for API rate limiting
- Protects against brute force attacks

✅ **CORS Configuration**
- Strict CORS policy with allowed origins
- Credentials support enabled only for trusted domains

### Security Checklist

```
□ All environment variables set securely
□ SECRET_KEY and JWT_SECRET_KEY are strong random values
□ Database credentials are not default
□ HTTPS enabled in production
□ JWT_COOKIE_SECURE=True in production
□ Debug mode disabled in production
□ File upload directory outside web root
□ Regular security updates and dependency scanning
□ Database backups configured
□ Logging and monitoring enabled
```

---

## 💳 Payment Integration

### Paymob Integration

#### Setup Process

1. **Get API Credentials** from Paymob dashboard
2. **Configure Environment Variables** in `.env`
3. **Set Webhook URL** in Paymob dashboard: `https://yourdomain.com/athlete/webhook/paymob`

#### Payment Flow

```
1. User initiates payment → POST /athlete/payment/paymob
2. Backend creates payment order with Paymob API
3. Backend returns payment URL with token
4. User redirected to Paymob payment page
5. User completes payment
6. Paymob sends webhook to backend
7. Backend verifies HMAC signature
8. Backend updates subscription status
9. User redirected to success/failure page
```

#### Webhook Verification

```python
# The system automatically verifies Paymob webhooks using HMAC
# Configured in PAYMOB_HMAC_SECRET environment variable
```

### PayPal Integration

#### Setup Process

1. **Create PayPal App** in Developer Dashboard
2. **Get Client ID and Secret**
3. **Configure Environment Variables**
4. **Set Webhook URL**: `https://yourdomain.com/athlete/webhook/paypal`

#### Payment Flow

```
1. User initiates payment → POST /athlete/payment/paypal
2. Backend creates PayPal order
3. User redirected to PayPal
4. User approves payment
5. PayPal sends webhook notification
6. Backend verifies webhook signature
7. Backend captures payment
8. Subscription activated
```

---

## 💬 Real-time Features

### Socket.IO Integration

#### Client Connection

```javascript
import io from 'socket.io-client';

const socket = io('https://yourdomain.com', {
  withCredentials: true,
  auth: {
    token: 'your-jwt-token'
  }
});

// Listen for events
socket.on('notification', (data) => {
  console.log('New notification:', data);
});

socket.on('workout_assigned', (data) => {
  console.log('New workout assigned:', data);
});
```

#### Server Events

```python
# Emit notification to specific user
from app import socketio

socketio.emit('notification', {
    'title': 'New Workout',
    'message': 'Your coach assigned a new workout'
}, room=user_id)
```

#### Available Events

- `notification`: General notifications
- `workout_assigned`: New workout assignment
- `subscription_updated`: Subscription status change
- `message`: Direct messages between users

---

## 🧪 Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_auth.py

# Run with verbose output
pytest -v

# Run and stop on first failure
pytest -x
```

### Test Structure

```python
# tests/test_auth.py
def test_user_registration(client):
    """Test user registration endpoint"""
    response = client.post('/auth/register', json={
        'email': 'test@example.com',
        'password': 'TestPass123!',
        'full_name': 'Test User',
        'role': 'athlete'
    })
    assert response.status_code == 201
    assert response.json['success'] is True
```

### Writing Tests

- Use `pytest` fixtures for database setup
- Test uses in-memory SQLite database
- Mock external API calls (Paymob, PayPal)
- Test both success and failure scenarios

---

## 🚀 Deployment

### Deployment on Ubuntu Server

#### 1. Server Preparation

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install python3.10 python3-pip python3-venv postgresql nginx -y

# Install certbot for SSL
sudo apt install certbot python3-certbot-nginx -y
```

#### 2. Application Setup

```bash
# Create application directory
sudo mkdir -p /var/www/sports-platform
sudo chown $USER:$USER /var/www/sports-platform

# Upload code to server
cd /var/www/sports-platform
git clone your-repository-url .

# Create virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
nano .env  # Edit with production values
```

#### 3. Database Setup

```bash
# Create database and user
sudo -u postgres psql
CREATE DATABASE sports_platform;
CREATE USER sports_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE sports_platform TO sports_user;
\q

# Run migrations
flask db upgrade
```

#### 4. NGINX Configuration

Create `/etc/nginx/sites-available/sports-platform`:

```nginx
upstream sports_app {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name api.yourdomain.com;

    client_max_body_size 16M;

    location / {
        proxy_pass http://sports_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /socket.io {
        proxy_pass http://sports_app/socket.io;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }

    location /static {
        alias /var/www/sports-platform/app/static;
        expires 30d;
    }
}
```

Enable the site:

```bash
sudo ln -s /etc/nginx/sites-available/sports-platform /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

#### 5. SSL Certificate

```bash
sudo certbot --nginx -d api.yourdomain.com
```

#### 6. Start Application

```bash
# Using systemd service (see earlier section)
sudo systemctl start sports-platform
sudo systemctl enable sports-platform
```

### Deployment Checklist

```
□ Server secured (firewall, SSH keys)
□ PostgreSQL installed and configured
□ Application code deployed
□ Virtual environment created
□ Dependencies installed
□ Environment variables configured
□ Database migrations applied
□ NGINX configured
□ SSL certificate installed
□ Systemd service created
□ Application running
□ Logs being written
□ Backups configured
□ Monitoring set up
```

---

## 🔧 Troubleshooting

### Common Issues

#### Database Connection Error

```
Error: could not connect to server: Connection refused
```

**Solution:**
- Check PostgreSQL is running: `sudo systemctl status postgresql`
- Verify DATABASE_URL in `.env`
- Ensure database and user exist

#### JWT Token Issues

```
Error: Signature verification failed
```

**Solution:**
- Ensure JWT_SECRET_KEY is consistent
- Check token hasn't expired
- Verify cookie settings (secure, samesite)

#### File Upload Fails

```
Error: Request Entity Too Large
```

**Solution:**
- Check MAX_CONTENT_LENGTH in `.env`
- Verify NGINX client_max_body_size
- Ensure upload directory has write permissions

#### Socket.IO Connection Failed

```
Error: WebSocket connection failed
```

**Solution:**
- Check CORS configuration
- Verify eventlet is installed
- Ensure NGINX proxy settings for WebSocket

### Logging

View application logs:

```bash
# Systemd service logs
sudo journalctl -u sports-platform -f

# Application logs
tail -f logs/app.log

# NGINX logs
sudo tail -f /var/log/nginx/error.log
sudo tail -f /var/log/nginx/access.log
```

---

## 🤝 Contributing

This is a proprietary project delivered as custom software. Contributions are not currently accepted.

For questions or issues, please contact the project maintainer.

---

## 📄 License

**Proprietary Software**

This software is provided as a custom solution. All rights reserved.

**Restrictions:**
- ❌ No redistribution
- ❌ No commercial reuse
- ❌ No modification without permission
- ✅ Use only as delivered to client

For licensing inquiries, contact: [your-email@example.com]

---

## 📞 Support

### Documentation
- API Documentation: `https://api.yourdomain.com/docs`
- Developer Guide: `docs/developer-guide.md`

### Contact
- **Email**: support@yourdomain.com
- **Technical Support**: For setup assistance or deployment questions

### Reporting Issues
When reporting issues, include:
1. Python version
2. Operating system
3. Error messages and logs
4. Steps to reproduce

---

## 🙏 Acknowledgments

Built with:
- Flask and the amazing Python community
- PostgreSQL
- Socket.IO
- All open-source libraries listed in requirements.txt