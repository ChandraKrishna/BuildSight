# Backend Implementation Context

## Objective

Build a Django-based application (Python backend, Django UI) that
integrates with Jenkins and GitHub.

## Technology

-   Python 3.x
-   Django 5.x
-   SQLite (Development)
-   PostgreSQL (Production optional)
-   Bootstrap 5
-   HTML/CSS
-   No React
-   No Docker
-   No Containers
-   Jenkins REST API
-   GitHub REST API

## Suggested Project Structure

... \### Modules 1. Authentication 2. Dashboard 3. Jenkins Configuration
4. GitHub Configuration 5. Project Mapping 6. Build Synchronization 7.
Reports 8. Settings

## Implementation Order

1.  Create project
2.  Configure authentication
3.  Create base template
4.  Jenkins CRUD
5.  GitHub CRUD
6.  Project mapping
7.  Jenkins API service
8.  GitHub API service
9.  Build sync
10. Dashboard
11. Reports
12. Audit logging
13. Testing
14. Deployment (Windows/Linux without containers)

## Coding Standards

-   Service Layer
-   Repository Layer
-   Business Logic separated from Views
-   Never call external APIs directly inside views.
