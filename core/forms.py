from django import forms
from .models import GitHubRepository, JenkinsServer, ProjectMapping

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
