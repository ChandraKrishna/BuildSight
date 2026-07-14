from django.conf import settings
from django.contrib.auth.models import User
from django.db import models

class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta: abstract = True

class JenkinsServer(TimestampedModel):
    name = models.CharField(max_length=120, unique=True)
    base_url = models.URLField()
    username = models.CharField(max_length=150, blank=True)
    encrypted_token = models.TextField()
    enabled = models.BooleanField(default=True)
    def __str__(self): return self.name

class GitHubRepository(TimestampedModel):
    name = models.CharField(max_length=120)
    owner = models.CharField(max_length=120)
    repository = models.CharField(max_length=120)
    encrypted_token = models.TextField()
    enabled = models.BooleanField(default=True)
    class Meta: constraints = [models.UniqueConstraint(fields=['owner', 'repository'], name='unique_github_repository')]
    def __str__(self): return f'{self.owner}/{self.repository}'

class ProjectMapping(TimestampedModel):
    name = models.CharField(max_length=120, unique=True)
    jenkins_server = models.ForeignKey(JenkinsServer, on_delete=models.CASCADE, related_name='mappings')
    github_repository = models.ForeignKey(GitHubRepository, on_delete=models.CASCADE, related_name='mappings')
    job_name = models.CharField(max_length=255)
    branch = models.CharField(max_length=255, default='main')
    enabled = models.BooleanField(default=True)
    def __str__(self): return self.name

class Build(TimestampedModel):
    class Status(models.TextChoices):
        SUCCESS='SUCCESS','Success'; FAILURE='FAILURE','Failed'; ABORTED='ABORTED','Aborted'; UNSTABLE='UNSTABLE','Unstable'; RUNNING='RUNNING','Running'
    mapping = models.ForeignKey(ProjectMapping, on_delete=models.CASCADE, related_name='builds')
    build_number = models.PositiveIntegerField()
    status = models.CharField(max_length=16, choices=Status.choices)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.PositiveIntegerField(default=0)
    url = models.URLField(blank=True)
    failure_trace = models.TextField(blank=True)
    initiated_by = models.CharField(max_length=255, blank=True)
    class Meta:
        ordering = ['-started_at', '-build_number']
        constraints = [models.UniqueConstraint(fields=['mapping', 'build_number'], name='unique_mapping_build')]

class AuditLog(models.Model):
    actor = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=100)
    target = models.CharField(max_length=255)
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta: ordering = ['-created_at']
