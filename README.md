# User Management System

A comprehensive Django REST API for user authentication, registration, profile management, and SMS-based verification. Built with modern DevOps practices supporting both local development and production deployments.

## Architecture

- **Backend**: Django REST Framework
- **Database**: PostgreSQL  
- **Authentication**: JWT tokens
- **SMS**: Configurable SMS providers (Mock/Twilio)
- **Containerization**: Docker & Docker Compose
- **Orchestration**: Kubernetes ready
- **Testing**: Comprehensive test suite with pytest

## Features

- User registration with phone number
- JWT-based authentication  
- SMS verification system
- Auto-profile creation
- Password reset functionality
- Credential updates
- Profile management
- Comprehensive API documentation
- Health checks and monitoring

## Prerequisites

- Python 3.9+
- Docker & Docker Compose
- PostgreSQL (for local development)
- kubectl & minikube (for Kubernetes)

## Development Setup

### Local Development

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd User-Management
   ```

2. **Create virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # Linux/Mac
   # OR
   venv\Scripts\activate     # Windows
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment setup**:
   ```bash
   cp .env.example .env  # Configure your environment variables
   ```

5. **Database setup**:
   ```bash
   python manage.py migrate
   python manage.py createsuperuser  # Optional
   ```

6. **Run development server**:
   ```bash
   python manage.py runserver
   ```

### Docker Compose (Recommended)

**Quick start**:
```bash
make docker-up
```

**Manual commands**:
```bash
docker-compose up --build
```

**Access**:
- Django App: http://localhost:28492
- Database: localhost:23867

**Useful commands**:
```bash
make docker-down    # Stop containers
make docker-logs    # View logs
make docker-shell   # Access Django shell
```

## Kubernetes Deployment

### Prerequisites
```bash
# Install minikube
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
sudo install minikube-linux-amd64 /usr/local/bin/minikube

# Start minikube
minikube start
```

### Deploy to Kubernetes
```bash
# Build and tag image
docker build -t user-management:latest .

# Apply Kubernetes manifests
kubectl apply -f k8s.yml

# Check deployment status
kubectl get pods -n user-management
kubectl get services -n user-management

# Access via port forwarding
kubectl port-forward service/django-service 8080:80 -n user-management
```

### Access Application
Add to `/etc/hosts`:
```
<MINIKUBE-IP> user-management.local
```

Then access: http://user-management.local

## Testing

### Run all tests
```bash
pytest -v
```

### Run specific test categories
```bash
# Registration tests
pytest accounts/test_comprehensive.py::UserRegistrationTestCase -v

# Authentication tests  
pytest accounts/test_comprehensive.py::UserAuthenticationTestCase -v

# Profile management tests
pytest accounts/test_comprehensive.py::ProfileManagementTestCase -v
```

### Coverage report
```bash
pytest --cov=accounts --cov-report=html
```

## API Endpoints

### Authentication
- `POST /api/auth/register/` - User registration
- `POST /api/auth/login/` - User login
- `POST /api/auth/token/refresh/` - Refresh JWT token
- `GET /api/auth/health/` - Health check

### SMS & Verification
- `POST /api/auth/send-verification/` - Send SMS verification
- `POST /api/auth/verify-code/` - Verify SMS code

### Password Management
- `POST /api/auth/forgot-password/` - Initiate password reset
- `POST /api/auth/reset-password/` - Complete password reset
- `POST /api/auth/change-password/` - Change password (authenticated)

### Profile Management
- `GET /api/auth/profile/` - Get user profile
- `PUT /api/auth/profile/` - Update user profile
- `PATCH /api/auth/profile/` - Partial profile update

## Environment Configuration

### Required Environment Variables
```bash
# Django
DJANGO_SECRET_KEY=your-secret-key
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,your-domain.com

# Database
DJANGO_DB_ENGINE=django.db.backends.postgresql
DJANGO_DB_NAME=user_management
DJANGO_DB_USER=postgres
DJANGO_DB_PASSWORD=your-db-password
DJANGO_DB_HOST=localhost
DJANGO_DB_PORT=5432

# SMS Configuration
SMS_PROVIDER=mock  # or 'twilio'
SMS_API_KEY=your-api-key
SMS_SENDER_ID=YourApp

# Twilio (if using)
TWILIO_ACCOUNT_SID=your-account-sid
TWILIO_AUTH_TOKEN=your-auth-token
TWILIO_FROM_NUMBER=+1234567890
```

## Project Structure

```
User-Management/
├── accounts/                 # Main Django app
│   ├── models.py            # User and Profile models
│   ├── serializers.py       # DRF serializers
│   ├── views.py             # API views
│   ├── urls.py              # URL routing
│   ├── sms_service.py       # SMS integration
│   └── test_comprehensive.py # Test suite
├── project/                 # Django project settings
├── docker-compose.yml       # Local development
├── k8s.yml                  # Kubernetes deployment
├── Dockerfile               # Container definition  
├── Makefile                 # Development shortcuts
├── requirements.txt         # Python dependencies
├── pytest.ini              # Test configuration
└── README.md               # This file
```

## Development Commands (Makefile)

```bash
make docker-up       # Start development environment
make docker-down     # Stop development environment
make docker-logs     # View container logs
make docker-shell    # Access Django shell
make test           # Run test suite
make migrate        # Run database migrations
make lint           # Code quality checks
```

## Monitoring & Health Checks

### Health Check Endpoint
```bash
curl http://localhost:28492/api/auth/health/
```

### Kubernetes Health Checks
- **Liveness Probe**: `/api/auth/health/`
- **Readiness Probe**: `/api/auth/health/`

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Troubleshooting

### Common Issues

**Port conflicts**:
```bash
# Check what's using the port
sudo lsof -i :5432
sudo lsof -i :8000

# Stop conflicting services
sudo systemctl stop postgresql
```

**Docker issues**:
```bash
# Clean up Docker
docker-compose down -v
docker system prune -f
```

**Database connection errors**:
```bash
# Reset database
docker-compose down -v
docker-compose up --build
```

For more help, check the [Issues](https://github.com/your-repo/issues) section or create a new issue.

