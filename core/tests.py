from django.contrib.auth.models import User
from datetime import timedelta
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from unittest.mock import Mock, patch
from .models import Build, GitHubRepository, JenkinsServer, ProjectMapping
from .services import JenkinsService, decrypt, encrypt

class DashboardTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('operator', password='safe-password')
        server = JenkinsServer.objects.create(name='CI', base_url='https://ci.example.test', encrypted_token=encrypt('jenkins-token'))
        repo = GitHubRepository.objects.create(name='Dashboard', owner='acme', repository='dashboard', encrypted_token=encrypt('github-token'))
        mapping = ProjectMapping.objects.create(name='Dashboard CI', jenkins_server=server, github_repository=repo, job_name='dashboard', branch='main')
        Build.objects.create(mapping=mapping, build_number=12, status=Build.Status.SUCCESS, started_at=timezone.now())

    def test_tokens_are_not_stored_as_plain_text(self):
        token = encrypt('secret')
        self.assertNotEqual(token, 'secret')
        self.assertEqual(decrypt(token), 'secret')

    def test_dashboard_requires_login_then_renders_counts(self):
        mapping = ProjectMapping.objects.get(name='Dashboard CI')
        Build.objects.create(mapping=mapping, build_number=10, status=Build.Status.FAILURE, started_at=timezone.now() - timedelta(days=4))
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 302)
        self.client.login(username='operator', password='safe-password')
        response = self.client.get(reverse('dashboard'))
        self.assertContains(response, 'Build overview')
        self.assertContains(response, 'Dashboard CI')
        self.assertContains(response, '#12')
        self.assertNotIn(b'>#10<', response.content)

    def test_login_inputs_use_bootstrap_alignment(self):
        response = self.client.get(reverse('login'))
        self.assertContains(response, 'class="form-control"', count=2)

    def test_mapping_form_displays_the_saved_jenkins_server_url(self):
        self.client.login(username='operator', password='safe-password')
        response = self.client.get(reverse('mapping_new'))
        self.assertContains(response, 'Jenkins server (actual URL)')
        self.assertContains(response, 'CI — https://ci.example.test')

    def test_sign_out_redirects_to_login(self):
        self.client.login(username='operator', password='safe-password')
        response = self.client.post(reverse('logout'))
        self.assertRedirects(response, reverse('login'))
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_report_defaults_to_the_last_three_days_and_filters(self):
        mapping = ProjectMapping.objects.get(name='Dashboard CI')
        Build.objects.create(mapping=mapping, build_number=11, status=Build.Status.FAILURE, started_at=timezone.now() - timedelta(days=4))
        self.client.login(username='operator', password='safe-password')
        response = self.client.get(reverse('reports'))
        self.assertContains(response, '#12')
        self.assertNotContains(response, '#11')
        response = self.client.get(reverse('reports'), {'start': (timezone.localdate() - timedelta(days=5)).isoformat()})
        self.assertContains(response, '#11')

    def test_dashboard_and_report_paginate_fifty_builds_per_page(self):
        mapping = ProjectMapping.objects.get(name='Dashboard CI')
        for number in range(13, 64):
            Build.objects.create(mapping=mapping, build_number=number, status=Build.Status.SUCCESS, started_at=timezone.now())
        self.client.login(username='operator', password='safe-password')
        dashboard = self.client.get(reverse('dashboard'), {'page': 2})
        report = self.client.get(reverse('reports'), {'page': 2})
        self.assertContains(dashboard, '#12')
        self.assertContains(report, '#12')
        self.assertContains(dashboard, 'page=1')
        self.assertContains(report, 'page=1')

    def test_report_shows_diagnostics_for_unsuccessful_builds(self):
        mapping = ProjectMapping.objects.get(name='Dashboard CI')
        Build.objects.create(mapping=mapping, build_number=99, status=Build.Status.FAILURE, started_at=timezone.now(), initiated_by='Krishna', failure_trace='ERROR: Test step failed')
        self.client.login(username='operator', password='safe-password')
        response = self.client.get(reverse('reports'))
        self.assertContains(response, 'Drill down')
        self.assertContains(response, 'Krishna')
        self.assertContains(response, 'ERROR: Test step failed')

    @patch('core.services.requests.get')
    def test_github_validation_removes_clone_suffix(self, get):
        get.return_value = Mock(raise_for_status=Mock())
        repository = GitHubRepository.objects.get(repository='dashboard')
        repository.repository = 'dashboard.git'
        from .services import GitHubService
        GitHubService(repository).validate()
        self.assertEqual(get.call_args.args[0], 'https://api.github.com/repos/acme/dashboard')

    def test_jenkins_job_path_accepts_folders_and_urls(self):
        self.assertEqual(JenkinsService._job_path('folder/release-build'), 'job/folder/job/release-build')
        self.assertEqual(JenkinsService._job_path('http://ci.test/job/folder/job/release-build/'), 'job/folder/job/release-build')
