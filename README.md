# SP-Tech Software Solution – Company Website

Django-based company website for SP-Tech Software Solution. Flagship product: **SanjivaniOne ERP**.

---

## Quick Start (Development)

```bash
# Activate virtualenv
.\venv\Scripts\Activate.ps1        # Windows
# source venv/bin/activate          # Linux/macOS

# Install dependencies
pip install -r requirements.txt

# Apply migrations
python manage.py migrate

# Seed sample products
python manage.py populate_sample_data

# Create admin user
python manage.py createsuperuser

# Run dev server
python manage.py runserver
```

Open: http://127.0.0.1:8000/

---

## Pages & URLs

| URL | Page |
|-----|------|
| `/` | Home |
| `/products/` | Product listing |
| `/sanjivanione-erp/` | SanjivaniOne ERP (flagship) |
| `/logistics-management-software/` | LMS detail |
| `/quote-sales-management-software/` | QSMS detail |
| `/about-us/` | About Us |
| `/contact/` | Contact form |
| `/blog/` | Blog listing |
| `/blog/<slug>/` | Blog post detail |
| `/admin/` | Admin panel |
| `/sitemap.xml` | XML sitemap |
| `/robots.txt` | Robots file |

---

## Admin Access

**Site login**: http://127.0.0.1:8000/contact/login/
- Username: `superAdmin`
- Password: same as the timetable super admin

After login, open **Apps**. Super admin can add more users at **Users**.

**Site login**: http://127.0.0.1:8000/contact/login/  
**Apps**: http://127.0.0.1:8000/apps/ (login required)

**Book Demo / Enquiries**: `/contact/book-demo/` · `/contact/enquiries/`

---

## Project Structure

```
SP-Tech/
├── sanjivani/          # Django project settings, urls, wsgi, asgi
├── core/               # Home & About pages; team/testimonials models
├── products/           # Product models, views, admin, sitemaps
├── blog/               # Blog posts, tags, admin, sitemaps
├── contact/            # Contact form, model, admin
├── templates/          # All HTML templates (base + per-app)
│   ├── base.html
│   ├── core/
│   ├── products/
│   ├── blog/
│   ├── contact/
│   └── robots.txt
├── static/
│   ├── assets/sp-tech-logo.png
│   ├── css/style.css
│   └── js/main.js
├── deploy/
│   ├── gunicorn.conf.py
│   ├── nginx.conf
│   └── setup.sh
├── manage.py
├── requirements.txt
└── .env
```

---

## SEO Features

- Dynamic `<title>`, `<meta description>`, `<meta keywords>` per page
- Open Graph + Twitter Card tags
- `rel="canonical"` on every page
- XML sitemap at `/sitemap.xml` (static pages + products + blog)
- `robots.txt` served by Django
- JSON-LD Schema.org markup:
  - `SoftwareApplication` on product detail pages
  - `BlogPosting` on blog post pages
  - `Organization` on contact page
- SEO-friendly slug URLs (e.g. `/logistics-management-software/`)
- WhiteNoise static file compression + long-lived cache headers

---

## Run on ports 80 + 443 with SSL (Windows)

Self-signed certificate for local / LAN use. **Run as Administrator** (ports 80/443 require elevation).

```powershell
# From project root
.\venv\Scripts\pip install -r requirements.txt
.\deploy\start_https.ps1
```

Or manually:

```powershell
.\venv\Scripts\python.exe deploy\generate_ssl_cert.py
.\venv\Scripts\python.exe deploy\run_https.py
```

- HTTP `http://127.0.0.1/` → redirects to HTTPS  
- HTTPS `https://127.0.0.1/` (browser will warn once — choose Advanced → Proceed)  
- Cert files: `deploy/certs/cert.pem` + `key.pem`

For a **public domain** with Let’s Encrypt, use the Ubuntu + Nginx section below (Certbot cannot issue trusted certs for `localhost`).

---

## Deployment (Ubuntu 22.04 + Nginx + Gunicorn)

### 1. Update `.env` for production
```
DEBUG=False
SECRET_KEY=<strong-random-key>
ALLOWED_HOSTS=sanjivani.com,www.sanjivani.com
SITE_URL=https://www.sanjivani.com
EMAIL_HOST_USER=your@email.com
EMAIL_HOST_PASSWORD=app-password
```

### 2. Run automated setup
```bash
chmod +x deploy/setup.sh
sudo ./deploy/setup.sh
```

This script:
- Installs Nginx, Certbot, Python 3
- Creates a `sanjivani` system user
- Sets up the virtualenv and installs requirements
- Runs migrations and collectstatic
- Creates a `systemd` service for Gunicorn
- Configures Nginx with SSL redirect
- Obtains a Let's Encrypt certificate

### 3. Manual SSL (if needed)
```bash
sudo certbot --nginx -d sanjivani.com -d www.sanjivani.com
```

---

## Adding Content via Admin

1. **Products** → Products → Add Product → fill name, slug, description, features
2. **Blog** → Posts → Add Post → write content, set status to "Published"
3. **Team Members** → Core → Team Members → Add
4. **Testimonials** → Core → Testimonials → Add
5. **Contact messages** → Contact → Contact Messages → read incoming enquiries

---

## Customising the Design

- Edit `static/css/style.css` – all CSS variables are at the top (`:root {}`)
- Primary colour: `--primary: #1a56db`
- Accent colour:  `--accent: #f97316`
- Fonts: Inter (body) + Poppins (headings) via Google Fonts
