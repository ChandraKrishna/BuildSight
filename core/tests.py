from django.contrib.auth.models import User
from datetime import timedelta
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone
from unittest.mock import Mock, patch
from .models import Build, DisplayPreference, GitHubRepository, JenkinsServer, ProjectMapping
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
        self.user.is_superuser = True
        self.user.save()
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
        preference = DisplayPreference.get_solo()
        preference.report_default_days = 5
        preference.save()
        response = self.client.get(reverse('reports'), {'start': (timezone.localdate() - timedelta(days=4)).isoformat()})
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
        self.assertContains(dashboard, '50 per page')
        self.assertContains(report, '50 per page')

    def test_report_shows_diagnostics_for_unsuccessful_builds(self):
        mapping = ProjectMapping.objects.get(name='Dashboard CI')
        Build.objects.create(mapping=mapping, build_number=99, status=Build.Status.FAILURE, started_at=timezone.now(), initiated_by='Krishna', failure_trace='ERROR: Test step failed')
        self.client.login(username='operator', password='safe-password')
        response = self.client.get(reverse('reports'))
        self.assertContains(response, 'Drill down')
        self.assertContains(response, 'Krishna')
        self.assertContains(response, 'ERROR: Test step failed')

    def test_staff_can_export_and_restore_project_data(self):
        self.user.is_staff = True
        self.user.is_superuser = True
        self.user.save()
        self.client.login(username='operator', password='safe-password')
        backup = self.client.get(reverse('database_backup'))
        self.assertEqual(backup.status_code, 200)
        self.assertIn(b'core.jenkinsserver', backup.content)
        Build.objects.all().delete()
        ProjectMapping.objects.all().delete()
        GitHubRepository.objects.all().delete()
        JenkinsServer.objects.all().delete()
        restored = self.client.post(reverse('database_restore'), {'backup_file': SimpleUploadedFile('buildsight-backup.json', backup.content, content_type='application/json'), 'confirm_replace': 'on'})
        self.assertRedirects(restored, reverse('settings'))
        self.assertTrue(ProjectMapping.objects.filter(name='Dashboard CI').exists())

    def test_non_staff_cannot_export_database_data(self):
        self.client.login(username='operator', password='safe-password')
        response = self.client.get(reverse('database_backup'))
        self.assertEqual(response.status_code, 302)

    def test_staff_can_configure_dashboard_and_report_default_ranges(self):
        self.user.is_staff = True
        self.user.is_superuser = True
        self.user.save()
        self.client.login(username='operator', password='safe-password')
        response = self.client.post(reverse('display_preferences'), {'dashboard_default_days': 7, 'report_default_days': 14})
        self.assertRedirects(response, reverse('settings'))
        preference = DisplayPreference.get_solo()
        self.assertEqual(preference.dashboard_default_days, 7)
        self.assertEqual(preference.report_default_days, 14)

    def test_staff_user_is_read_only_in_the_application(self):
        self.user.is_staff = True
        self.user.save()
        self.client.login(username='operator', password='safe-password')
        listing = self.client.get(reverse('jenkins_list'))
        self.assertNotContains(listing, 'Add jenkins')
        response = self.client.get(reverse('jenkins_new'))
        self.assertEqual(response.status_code, 302)

    def test_superuser_can_create_a_read_only_staff_user(self):
        self.user.is_superuser = True
        self.user.save()
        self.client.login(username='operator', password='safe-password')
        response = self.client.post(reverse('create_managed_user'), {'username': 'viewer', 'email': 'viewer@example.test', 'role': 'readonly', 'password1': 'A-safe-password-123', 'password2': 'A-safe-password-123'})
        self.assertRedirects(response, reverse('settings'))
        viewer = User.objects.get(username='viewer')
        self.assertTrue(viewer.is_staff)
        self.assertFalse(viewer.is_superuser)

    def test_reports_apply_its_own_configured_default_range(self):
        preference = DisplayPreference.get_solo()
        preference.dashboard_default_days = 1
        preference.report_default_days = 5
        preference.save()
        mapping = ProjectMapping.objects.get(name='Dashboard CI')
        Build.objects.create(mapping=mapping, build_number=20, status=Build.Status.SUCCESS, started_at=timezone.now() - timedelta(days=4))
        self.client.login(username='operator', password='safe-password')
        dashboard = self.client.get(reverse('dashboard'))
        report = self.client.get(reverse('reports'))
        self.assertNotContains(dashboard, '#20</td>')
        self.assertContains(report, '#20')
        self.assertContains(report, 'DEFAULT: LAST 5 DAYS')

    def test_date_filters_are_limited_to_the_configured_day_window(self):
        preference = DisplayPreference.get_solo()
        preference.dashboard_default_days = 3
        preference.report_default_days = 3
        preference.save()
        self.client.login(username='operator', password='safe-password')
        too_old = (timezone.localdate() - timedelta(days=30)).isoformat()
        allowed_start = (timezone.localdate() - timedelta(days=2)).isoformat()
        dashboard = self.client.get(reverse('dashboard'), {'start': too_old})
        report = self.client.get(reverse('reports'), {'start': too_old})
        self.assertContains(dashboard, f'value="{allowed_start}"')
        self.assertContains(report, f'value="{allowed_start}"')
        self.assertContains(report, f'min="{allowed_start}"')

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
