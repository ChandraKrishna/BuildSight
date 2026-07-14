# BuildSight

**BuildSight** is a Django-based web application that provides a
centralized dashboard for monitoring, managing, and analyzing **Jenkins
pipeline jobs integrated with GitHub**. It enables teams to configure
multiple Jenkins servers and GitHub repositories, map CI/CD pipelines,
synchronize build history, and gain actionable insights into build
executions.

------------------------------------------------------------------------

## ✨ Features

-   🔐 Secure user authentication and role-based access
-   ⚙️ Configure and manage multiple Jenkins servers
-   🔑 Secure storage of Jenkins and GitHub credentials
-   📂 Configure GitHub repositories and branches
-   🔗 Map Jenkins pipeline jobs with GitHub repositories
-   🔄 Synchronize Jenkins build history
-   📊 Interactive dashboard for build monitoring
-   📈 Build execution insights and historical trends
-   ❌ Failed build analysis and success rate tracking
-   📋 Detailed build reports and execution logs
-   🔍 Search and filter builds by project, status, branch, and date
-   🚀 REST API integration with Jenkins and GitHub
-   🎨 Modern responsive UI built with Django

------------------------------------------------------------------------

## 🛠️ Technology Stack

  Component                Technology
  ------------------------ ------------------------------------
  Backend                  Python 3.11+
  Framework                Django 5.x
  Database (Development)   SQLite
  Database (Production)    PostgreSQL
  Frontend                 HTML, CSS, Bootstrap 5, JavaScript
  Version Control          Git & GitHub
  CI/CD                    Jenkins REST API

------------------------------------------------------------------------

## 📁 Project Structure

``` text
BuildSight/
├── context/
├── core/
├── jenkins_dashboard/
├── static/
├── templates/
├── db.sqlite3
├── manage.py
├── requirements.txt
└── README.md
```

------------------------------------------------------------------------

## 🚀 Getting Started

### 1. Clone the Repository

``` bash
git clone <repository-url>
cd BuildSight
```

### 2. Create a Virtual Environment

``` bash
python -m venv .venv
```

### 3. Activate the Virtual Environment

**Windows**

``` bash
.venv\Scripts\activate
```

**Linux/macOS**

``` bash
source .venv/bin/activate
```

### 4. Install Dependencies

``` bash
pip install -r requirements.txt
```

### 5. Apply Database Migrations

``` bash
python manage.py makemigrations
python manage.py migrate
```

### 6. Create an Administrator Account

``` bash
python manage.py createsuperuser
```

### 7. Run the Development Server

``` bash
python manage.py runserver
```

Open your browser:

`http://127.0.0.1:8000/`

------------------------------------------------------------------------

## ⚙️ Configuration

Set the following environment variables in production:

-   `DJANGO_SECRET_KEY`
-   `CREDENTIAL_ENCRYPTION_KEY`
-   `DEBUG=False`

Replace SQLite with PostgreSQL for production deployments.

------------------------------------------------------------------------

## 🔄 Application Workflow

1.  Login to BuildSight
2.  Configure Jenkins server(s)
3.  Configure GitHub repository and branch
4.  Add Jenkins and GitHub credentials
5.  Map Jenkins jobs to GitHub repositories
6.  Synchronize build history
7.  Monitor build executions
8.  Analyze build insights and reports

------------------------------------------------------------------------

## 📊 Dashboard Capabilities

-   Overall build summary
-   Successful vs failed builds
-   Recent build executions
-   Build history timeline
-   Build duration trends
-   Job-wise execution statistics
-   Repository-wise pipeline status
-   Branch-wise build information

------------------------------------------------------------------------

## 🔒 Security

-   Encrypted credential storage
-   CSRF protection
-   Django authentication
-   Secure session management
-   Environment-based secret configuration

------------------------------------------------------------------------

## 📌 Future Enhancements

-   AI-powered build insights
-   Email notifications
-   Slack & Microsoft Teams integration
-   GitHub webhook support
-   Pipeline execution analytics
-   Scheduled synchronization
-   Build health score
-   Multi-user access management
-   REST API support
-   Docker deployment
-   Kubernetes deployment

------------------------------------------------------------------------

## 📄 License

Source-available under the [BuildSight Source-Available No-Modifications License](LICENSE).
Use, copying, and sharing of complete unmodified copies is allowed; modifications
and derivative works are not permitted.

------------------------------------------------------------------------

## 👤 Author

**Krishna Chandra**

BuildSight provides a centralized dashboard for GitHub-integrated
Jenkins CI/CD pipelines, enabling teams to monitor builds, analyze
performance, and improve delivery efficiency.
