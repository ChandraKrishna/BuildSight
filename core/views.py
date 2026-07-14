import csv
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.http import HttpResponse
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from .forms import GitHubRepositoryForm, JenkinsServerForm, ProjectMappingForm
from .models import Build, GitHubRepository, JenkinsServer, ProjectMapping
from .repositories import ConfigurationRepository
from .services import DashboardService, GitHubService, JenkinsService, audit, encrypt

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
    context.update({'builds': page, 'page_obj': page, 'pagination_query': query.urlencode()})
    return context

@login_required
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

@login_required
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

@login_required
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

@login_required
def settings_view(request): return render(request, 'core/settings.html')
