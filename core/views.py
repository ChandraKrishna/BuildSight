import csv
import json
import os
import tempfile
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.core.paginator import Paginator
from django.core.management import call_command
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from .forms import DatabaseRestoreForm, DisplayPreferenceForm, GitHubRepositoryForm, JenkinsServerForm, ManagedUserCreationForm, ProjectMappingForm
from .models import AuditLog, Build, DisplayPreference, GitHubRepository, JenkinsServer, ProjectMapping
from .repositories import ConfigurationRepository
from .services import DashboardService, GitHubService, JenkinsService, audit, encrypt

superuser_required = user_passes_test(lambda user: user.is_superuser)

def login_view(request):
    if request.user.is_authenticated: return redirect('dashboard')
    form = AuthenticationForm(request, data=request.POST or None)
    for field in form.fields.values():
        field.widget.attrs.update({'class': 'form-control', 'autocomplete': 'username' if field is form.fields.get('username') else 'current-password'})
    if request.method == 'POST' and form.is_valid():
        login(request, form.get_user()); return redirect('dashboard')
    return render(request, 'registration/login.html', {'form': form})

@login_required
def dashboard(request):
    return render(request, 'core/dashboard.html', paginate_builds(DashboardService.overview(request.GET), request))

def paginate_builds(context, request):
    page = Paginator(context['builds'], 50).get_page(request.GET.get('page'))
    query = request.GET.copy()
    query.pop('page', None)
    context.update({'builds': page, 'page_obj': page, 'page_numbers': page.paginator.get_elided_page_range(number=page.number, on_each_side=2, on_ends=1), 'pagination_query': query.urlencode()})
    return context

@superuser_required
def configuration(request, kind, pk=None):
    model, form_class, label = {'jenkins': (JenkinsServer, JenkinsServerForm, 'Jenkins server'), 'github': (GitHubRepository, GitHubRepositoryForm, 'GitHub repository'), 'mapping': (ProjectMapping, ProjectMappingForm, 'project mapping')}[kind]
    instance = get_object_or_404(model, pk=pk) if pk else None
    if request.method == 'POST':
        form = form_class(request.POST, instance=instance)
        if form.is_valid():
            entity = form.save(commit=False)
            if kind in ('jenkins', 'github') and form.cleaned_data['token']: entity.encrypted_token = encrypt(form.cleaned_data['token'])
            if not instance and kind in ('jenkins', 'github') and not entity.encrypted_token:
                form.add_error('token', 'A token is required for a new configuration.')
            else:
                entity.save(); audit(request.user, 'updated' if instance else 'created', f'{label}: {entity}'); messages.success(request, f'{label.title()} saved.'); return redirect(f'{kind}_list')
    else: form = form_class(instance=instance)
    return render(request, 'core/config_form.html', {'form': form, 'label': label, 'editing': bool(instance)})

@login_required
def jenkins_list(request): return render(request, 'core/config_list.html', {'title':'Jenkins Servers','kind':'jenkins','items': ConfigurationRepository.servers()})
@login_required
def github_list(request): return render(request, 'core/config_list.html', {'title':'GitHub Repositories','kind':'github','items': ConfigurationRepository.repositories()})
@login_required
def mapping_list(request): return render(request, 'core/config_list.html', {'title':'Project Mappings','kind':'mapping','items': ProjectMapping.objects.select_related('jenkins_server','github_repository')})

@superuser_required
def validate_connection(request, kind, pk):
    entity = get_object_or_404(JenkinsServer if kind == 'jenkins' else GitHubRepository, pk=pk)
    if not entity.enabled:
        messages.warning(request, 'This configuration is inactive. Mark it active before validating its connection.')
        return redirect(f'{kind}_list')
    try:
        (JenkinsService(entity) if kind == 'jenkins' else GitHubService(entity)).validate(); messages.success(request, 'Connection validated successfully.')
    except Exception as exc: messages.error(request, f'Validation failed: {exc}')
    audit(request.user, 'validated_connection', str(entity), service=kind)
    return redirect(f'{kind}_list')

@superuser_required
def synchronize(request, pk):
    mapping = get_object_or_404(ProjectMapping, pk=pk)
    if not mapping.enabled or not mapping.jenkins_server.enabled or not mapping.github_repository.enabled:
        messages.warning(request, 'This mapping or one of its integrations is inactive. Mark all three active before synchronizing.')
        return redirect('mapping_list')
    try: JenkinsService(mapping.jenkins_server).sync(mapping); messages.success(request, f'{mapping.name} synchronized.')
    except Exception as exc: messages.error(request, f'Synchronization failed: {exc}')
    audit(request.user, 'synchronized_builds', str(mapping)); return redirect('mapping_list')

@login_required
def reports(request):
    context = DashboardService.report(request.GET)
    builds = context['builds']
    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv'); response['Content-Disposition'] = 'attachment; filename="build-report.csv"'
        writer = csv.writer(response); writer.writerow(['Project','Build','Status','Started','Duration (sec)'])
        for build in builds: writer.writerow([build.mapping.name, build.build_number, build.status, build.started_at, build.duration_seconds])
        return response
    return render(request, 'core/reports.html', paginate_builds(context, request))

def settings_context(**overrides):
    context = {'restore_form': DatabaseRestoreForm(), 'display_form': DisplayPreferenceForm(instance=DisplayPreference.get_solo()), 'user_form': ManagedUserCreationForm(), 'managed_users': User.objects.order_by('username'), 'is_admin': True}
    context.update(overrides)
    return context

@login_required
def settings_view(request): return render(request, 'core/settings.html', settings_context(is_admin=request.user.is_superuser))

@superuser_required
def database_backup(request):
    response = HttpResponse(content_type='application/json')
    response['Content-Disposition'] = 'attachment; filename="buildsight-backup.json"'
    call_command('dumpdata', 'core.displaypreference', 'core.jenkinsserver', 'core.githubrepository', 'core.projectmapping', 'core.build', indent=2, stdout=response)
    audit(request.user, 'exported_database_backup', 'project data')
    return response

@superuser_required
def database_restore(request):
    if request.method != 'POST': return redirect('settings')
    form = DatabaseRestoreForm(request.POST, request.FILES)
    if not form.is_valid():
        return render(request, 'core/settings.html', settings_context(restore_form=form))
    uploaded = form.cleaned_data['backup_file']
    if uploaded.size > 20 * 1024 * 1024:
        form.add_error('backup_file', 'Backup files must be 20 MB or smaller.')
        return render(request, 'core/settings.html', settings_context(restore_form=form))
    raw = uploaded.read()
    try: json.loads(raw.decode('utf-8'))
    except (UnicodeDecodeError, json.JSONDecodeError):
        form.add_error('backup_file', 'Upload a valid BuildSight JSON backup file.')
        return render(request, 'core/settings.html', settings_context(restore_form=form))
    temporary_file = None
    try:
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.json', delete=False) as temporary_file:
            temporary_file.write(raw)
        with transaction.atomic():
            AuditLog.objects.all().delete()
            Build.objects.all().delete()
            ProjectMapping.objects.all().delete()
            GitHubRepository.objects.all().delete()
            JenkinsServer.objects.all().delete()
            DisplayPreference.objects.all().delete()
            call_command('loaddata', temporary_file.name, verbosity=0)
        audit(request.user, 'restored_database_backup', uploaded.name)
        messages.success(request, 'Project data restored successfully.')
        return redirect('settings')
    except Exception as exc:
        form.add_error('backup_file', f'Restore failed: {exc}')
        return render(request, 'core/settings.html', settings_context(restore_form=form))
    finally:
        if temporary_file and os.path.exists(temporary_file.name): os.unlink(temporary_file.name)

@superuser_required
def update_display_preferences(request):
    if request.method != 'POST': return redirect('settings')
    form = DisplayPreferenceForm(request.POST, instance=DisplayPreference.get_solo())
    if form.is_valid():
        form.save()
        audit(request.user, 'updated_display_preferences', 'dashboard and reports')
        messages.success(request, 'Default date ranges updated.')
        return redirect('settings')
    return render(request, 'core/settings.html', settings_context(display_form=form))

@superuser_required
def create_managed_user(request):
    if request.method != 'POST': return redirect('settings')
    form = ManagedUserCreationForm(request.POST)
    if form.is_valid():
        user = form.save()
        audit(request.user, 'created_user', user.username, role=form.cleaned_data['role'])
        messages.success(request, f'User {user.username} created successfully.')
        return redirect('settings')
    return render(request, 'core/settings.html', settings_context(user_form=form))
