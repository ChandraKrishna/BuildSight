from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.db import models
from .models import DisplayPreference, GitHubRepository, JenkinsServer, ProjectMapping

class GlassForm(forms.ModelForm):
    enabled = forms.BooleanField(required=False, label='Active configuration', help_text='Check this box to make the configuration active. Uncheck it to keep it inactive.')
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-check-input' if isinstance(field.widget, forms.CheckboxInput) else 'form-control'

class JenkinsServerForm(GlassForm):
    token = forms.CharField(widget=forms.PasswordInput(render_value=True), required=False, help_text='Leave empty to keep the current token when editing.')
    class Meta:
        model = JenkinsServer
        fields = ['name', 'base_url', 'username', 'enabled']
        labels = {'base_url': 'Jenkins server URL'}
        help_texts = {'base_url': 'Enter the full URL of the Jenkins server, for example https://jenkins.example.com.'}

class GitHubRepositoryForm(GlassForm):
    token = forms.CharField(widget=forms.PasswordInput(render_value=True), required=False, help_text='Leave empty to keep the current token when editing.')
    class Meta: model = GitHubRepository; fields = ['name', 'owner', 'repository', 'enabled']

class ProjectMappingForm(GlassForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['jenkins_server'].label = 'Jenkins server (actual URL)'
        self.fields['jenkins_server'].help_text = 'Choose the configured Jenkins server. Its actual URL is displayed below its name.'
        self.fields['jenkins_server'].queryset = JenkinsServer.objects.order_by('name')
        self.fields['jenkins_server'].label_from_instance = lambda server: f'{server.name} — {server.base_url}'
    class Meta:
        model = ProjectMapping
        fields = ['name', 'jenkins_server', 'github_repository', 'job_name', 'branch', 'enabled']
        help_texts = {'job_name': 'Use the exact Jenkins job name, nested path (folder/job), or paste the job URL.'}

class DatabaseRestoreForm(forms.Form):
    backup_file = forms.FileField(label='Backup JSON file')
    confirm_replace = forms.BooleanField(required=True, label='I understand that current project data will be replaced')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['backup_file'].widget.attrs['class'] = 'form-control'
        self.fields['backup_file'].widget.attrs['accept'] = '.json,application/json'
        self.fields['confirm_replace'].widget.attrs['class'] = 'form-check-input'

class DisplayPreferenceForm(forms.ModelForm):
    class Meta:
        model = DisplayPreference
        fields = ['dashboard_default_days', 'report_default_days']
        labels = {'dashboard_default_days': 'Dashboard default days', 'report_default_days': 'Reports default days'}
        help_texts = {'dashboard_default_days': 'Number of latest calendar days shown by default on Dashboard.', 'report_default_days': 'Number of latest calendar days shown by default in Reports.'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control', 'min': 1, 'max': 365})

    def clean(self):
        cleaned = super().clean()
        for name in ('dashboard_default_days', 'report_default_days'):
            if cleaned.get(name) is not None and not 1 <= cleaned[name] <= 365:
                self.add_error(name, 'Enter a value from 1 to 365 days.')
        return cleaned

class ManagedUserCreationForm(UserCreationForm):
    class Role(models.TextChoices):
        READ_ONLY = 'readonly', 'Read-only staff'
        ADMIN = 'admin', 'Administrator'

    email = forms.EmailField(required=False)
    role = forms.ChoiceField(choices=Role.choices, initial=Role.READ_ONLY, label='Access role')

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-select' if field is self.fields['role'] else 'form-control'

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.is_staff = True
        user.is_superuser = self.cleaned_data['role'] == self.Role.ADMIN
        if commit: user.save()
        return user
