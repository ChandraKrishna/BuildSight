import base64
import hashlib
from datetime import datetime, timedelta, timezone as dt_timezone
from urllib.parse import quote
from urllib.parse import unquote, urlparse
import requests
from cryptography.fernet import Fernet
from django.conf import settings
from django.utils import timezone
from .models import AuditLog, Build
from .repositories import DashboardRepository

def _fernet():
    source = settings.CREDENTIAL_ENCRYPTION_KEY or settings.SECRET_KEY
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(source.encode()).digest()))
def encrypt(value): return _fernet().encrypt(value.encode()).decode() if value else ''
def decrypt(value): return _fernet().decrypt(value.encode()).decode() if value else ''
def audit(actor, action, target, **details): AuditLog.objects.create(actor=actor if getattr(actor, 'is_authenticated', False) else None, action=action, target=target, details=details)

class JenkinsService:
    def __init__(self, server): self.server = server
    def _request(self, path):
        auth = (self.server.username, decrypt(self.server.encrypted_token)) if self.server.username else None
        return requests.get(f'{self.server.base_url.rstrip("/")}/{path.lstrip("/")}', auth=auth, timeout=15, headers={'Accept': 'application/json'})
    def validate(self):
        response = self._request('api/json'); response.raise_for_status(); return True
    def sync(self, mapping):
        job_path = self._job_path(mapping.job_name)
        response = self._request(f'{job_path}/api/json?tree=builds[number,result,timestamp,duration,building,url,actions[causes[shortDescription,userId,userName]]]')
        if response.status_code == 404:
            raise ValueError(f'Jenkins could not find or authorize the job "{mapping.job_name}". Use the exact job path (for example, folder-name/job-name) and confirm the configured Jenkins user or API token has Job/Read permission.')
        response.raise_for_status()
        for item in response.json().get('builds', []):
            status = 'RUNNING' if item.get('building') else (item.get('result') or 'ABORTED')
            if status not in Build.Status.values: status = 'ABORTED'
            started = datetime.fromtimestamp(item.get('timestamp', 0) / 1000, tz=dt_timezone.utc) if item.get('timestamp') else None
            initiated_by = self._build_initiator(item)
            trace = self._console_trace(job_path, item['number']) if status != Build.Status.SUCCESS else ''
            Build.objects.update_or_create(mapping=mapping, build_number=item['number'], defaults={'status': status, 'started_at': started, 'duration_seconds': int(item.get('duration', 0) / 1000), 'completed_at': None, 'url': item.get('url', ''), 'failure_trace': trace, 'initiated_by': initiated_by})

    def _console_trace(self, job_path, build_number):
        try:
            response = self._request(f'{job_path}/{build_number}/consoleText')
            response.raise_for_status()
            return response.text[-12000:]
        except requests.RequestException:
            return 'Jenkins console output was unavailable for this build.'

    @staticmethod
    def _build_initiator(build):
        for action in build.get('actions') or []:
            for cause in action.get('causes') or []:
                actor = cause.get('userName') or cause.get('userId')
                if actor:
                    return actor
                if cause.get('shortDescription'):
                    return cause['shortDescription']
        return ''

    @staticmethod
    def _job_path(job_name):
        """Convert a Jenkins job name, nested path, or browser URL to API path."""
        parsed = urlparse(job_name)
        raw_path = parsed.path if parsed.scheme else job_name
        parts = [unquote(part) for part in raw_path.strip('/').split('/') if part and part != 'job']
        if not parts:
            raise ValueError('A Jenkins job name is required.')
        return '/'.join(f'job/{quote(part, safe="")}' for part in parts)

class GitHubService:
    def __init__(self, repository): self.repository = repository
    def validate(self):
        token = decrypt(self.repository.encrypted_token)
        # GitHub clone URLs commonly end in .git; the REST repository endpoint does not.
        repository_name = self.repository.repository.removesuffix('.git').strip('/')
        response = requests.get(f'https://api.github.com/repos/{quote(self.repository.owner, safe="")}/{quote(repository_name, safe="")}', headers={'Authorization': f'Bearer {token}', 'Accept': 'application/vnd.github+json'}, timeout=15)
        response.raise_for_status(); return True

class DashboardService:
    @staticmethod
    def build_filters(params, default_to_last_three_days=False):
        filters = {}
        if params.get('project'): filters['mapping_id'] = params['project']
        if params.get('branch'): filters['mapping__branch'] = params['branch']
        if params.get('start'): filters['started_at__date__gte'] = params['start']
        if params.get('end'): filters['started_at__date__lte'] = params['end']
        if default_to_last_three_days and not params.get('start') and not params.get('end'):
            filters['started_at__date__gte'] = timezone.localdate() - timedelta(days=2)
        return filters

    @staticmethod
    def overview(params):
        filters = DashboardService.build_filters(params, default_to_last_three_days=True)
        counts = {item['status']: item['total'] for item in DashboardRepository.status_counts(filters)}
        return {'builds': DashboardRepository.builds(filters), 'mappings': DashboardRepository.mappings(), 'counts': counts, 'total_projects': DashboardRepository.mappings().count(), 'filters': params, 'default_start': timezone.localdate() - timedelta(days=2)}

    @staticmethod
    def report(params):
        filters = DashboardService.build_filters(params, default_to_last_three_days=True)
        return {'builds': DashboardRepository.builds(filters), 'mappings': DashboardRepository.mappings(), 'filters': params, 'default_start': timezone.localdate() - timedelta(days=2)}
