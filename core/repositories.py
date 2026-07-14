"""Persistence boundary: services use these helpers, never views."""
from django.db.models import Count
from .models import Build, DisplayPreference, GitHubRepository, JenkinsServer, ProjectMapping

class DashboardRepository:
    @staticmethod
    def mappings(): return ProjectMapping.objects.select_related('jenkins_server', 'github_repository')
    @staticmethod
    def builds(filters=None): return Build.objects.select_related('mapping').filter(**(filters or {}))
    @staticmethod
    def status_counts(filters=None): return DashboardRepository.builds(filters).values('status').annotate(total=Count('id'))

class ConfigurationRepository:
    servers = staticmethod(lambda: JenkinsServer.objects.all())
    repositories = staticmethod(lambda: GitHubRepository.objects.all())

class SettingsRepository:
    display_preference = staticmethod(DisplayPreference.get_solo)
