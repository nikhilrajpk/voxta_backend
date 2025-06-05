# Voxta Backend

Welcome to the backend repository of **Voxta**, a real-time chat application that connects users based on shared interests. Built with **Django** and **Django Channels**, this service is deployed using **Docker** on an **AWS EC2 instance**, and powers the Voxta frontend available at [https://voxta-frontend.nikhilrajpk.in](https://voxta-frontend.nikhilrajpk.in).

## 🌟 Features

* **User Authentication**: JWT-based login and registration with Django REST Framework and SimpleJWT.
* **Real-Time Chat**: WebSocket-based communication using Django Channels and Redis.
* **Interest Matching**: Manage interest requests (sent, received, accepted) for meaningful connections.
* **REST API**: Exposes endpoints for users, interests, and messages.
* **Secure Deployment**: HTTPS enabled with Certbot, behind Nginx reverse proxy, containerized with Docker.

## 🔧 Tech Stack

| Layer            | Tech Stack                        |
| ---------------- | --------------------------------- |
| Framework        | Django 4.x, Django REST Framework |
| WebSockets       | Django Channels                   |
| Database         | PostgreSQL                        |
| Caching          | Redis                             |
| Auth             | SimpleJWT                         |
| Containerization | Docker                            |
| Web Server       | Nginx                             |
| Deployment       | AWS EC2 (t2.medium, Ubuntu 22.04) |
| SSL              | Certbot (Let's Encrypt)           |
| Version Control  | Git                               |

---

## 🚀 Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/nikhilrajpk/voxta_backend.git
cd voxta_backend
```

### 2. Create `.env` File

Create a `.env` file in the root directory:

```env
SECRET_KEY=your-secret-key
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1,ec2-98-81-117-89.compute-1.amazonaws.com,voxta-backend.nikhilrajpk.in,98.81.117.89
CORS_ALLOWED_ORIGINS=https://voxta-frontend.nikhilrajpk.in
DB_NAME=voxta
DB_USER=postgres
DB_PASSWORD=your-db-password
DB_HOST=172.17.0.1
DB_PORT=5432
REDIS_HOST=172.17.0.1
REDIS_PORT=6379
```

Generate a secure secret key:

```bash
python3 -c 'import secrets; print(secrets.token_urlsafe(50))'
```

### 3. Install Local Dependencies (Optional)

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. Set Up PostgreSQL and Redis

```bash
sudo apt update
sudo apt install postgresql redis-server
sudo -u postgres psql -c "CREATE DATABASE voxta;"
sudo -u postgres psql -c "ALTER USER postgres WITH PASSWORD 'your-db-password';"
```

Edit Redis config:

```bash
sudo nano /etc/redis/redis.conf
# Change these lines:
bind 127.0.0.1 172.17.0.1 ::1
protected-mode no
sudo systemctl restart redis
```

### 5. Run with Docker

```bash
docker build -t voxta-backend .
docker run -d \
  --name voxta \
  -p 8000:8000 \
  -v $(pwd)/Uploads:/app/Uploads \
  -v $(pwd)/staticfiles:/app/staticfiles \
  --env-file .env \
  --add-host host.docker.internal:host-gateway \
  voxta-backend
```

### 6. Apply Migrations & Collect Static Files

```bash
docker exec voxta python manage.py migrate
docker exec voxta python manage.py collectstatic --noinput
```

---

## ☁️ Deployment on AWS EC2

### 1. Launch EC2

* Instance Type: `t2.medium`
* OS: Ubuntu 22.04
* Allow ports: 22 (SSH), 80 (HTTP), 443 (HTTPS)

### 2. Connect to Instance

```bash
ssh -i your-key.pem ubuntu@ec2-98-81-117-89.compute-1.amazonaws.com
```

### 3. Install Requirements

```bash
sudo apt update
sudo apt install docker.io nginx certbot python3-certbot-nginx
sudo systemctl start docker
sudo systemctl enable docker
```

### 4. Clone and Run

```bash
git clone https://github.com/nikhilrajpk/voxta_backend.git
cd voxta_backend
# Add .env file
# Follow Docker run and migration steps
```

### 5. Nginx Configuration

Create file:

```bash
sudo nano /etc/nginx/sites-available/voxta
```

Paste:

```nginx
upstream daphne {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name ec2-98-81-117-89.compute-1.amazonaws.com voxta-backend.nikhilrajpk.in 98.81.117.89;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name ec2-98-81-117-89.compute-1.amazonaws.com voxta-backend.nikhilrajpk.in 98.81.117.89;

    ssl_certificate /etc/letsencrypt/live/voxta-backend.nikhilrajpk.in/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/voxta-backend.nikhilrajpk.in/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    location / {
        proxy_pass http://daphne;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_connect_timeout 300s;
    }

    location /ws/ {
        proxy_pass http://daphne;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400s;
        proxy_send_timeout 86400s;
    }

    location /static/ {
        alias /home/ubuntu/voxta_backend/staticfiles/;
    }

    location /media/ {
        alias /home/ubuntu/voxta_backend/Uploads/;
    }
}
```

Enable site:

```bash
sudo ln -s /etc/nginx/sites-available/voxta /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 6. Enable HTTPS

```bash
sudo certbot --nginx -d voxta-backend.nikhilrajpk.in
```

### 7. Monitor Logs

```bash
docker logs voxta
sudo tail -f /var/log/nginx/error.log
```

---

## 🗂️ Project Structure

```
voxta_backend/
├── user_app/
│   ├── consumers.py        # WebSocket consumer logic
│   ├── middleware.py       # JWT middleware
│   ├── models.py           # User, Message, InterestRequest models
│   ├── serializers.py      # API serializers
│   └── views.py            # API views
├── voxta_backend/
│   ├── settings.py         # Django settings
│   ├── asgi.py             # ASGI configuration
│   └── urls.py             # URL routing
├── staticfiles/            # Static files for production
├── Uploads/                # Media uploads
├── .env                    # Environment configuration
├── Dockerfile              # Docker setup
├── requirements.txt        # Python dependencies
└── README.md               # Project documentation
```

---

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch:

   ```bash
   git checkout -b feature-name
   ```
3. Commit your changes:

   ```bash
   git commit -m "Add feature"
   ```
4. Push to the branch:

   ```bash
   git push origin feature-name
   ```
5. Open a pull request

## 🐞 Issues

Use [GitHub Issues](https://github.com/nikhilrajpk/voxta_backend/issues) to report bugs or request features.

## 📄 License

Licensed under the [MIT License](LICENSE).

## 📬 Contact

For questions or feedback, reach out to [Nikhil Raj](https://nikhilrajpk.in).
