from django.contrib import admin
from .models import AuditLog, Build, GitHubRepository, JenkinsServer, ProjectMapping
admin.site.register([JenkinsServer, GitHubRepository, ProjectMapping, Build, AuditLog])
