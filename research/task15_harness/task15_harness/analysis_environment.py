"""Read-only analysis-artifact identity inspection. Never imports NumPy or launches Python."""
from pathlib import Path
from .errors import ControlError, require
from .integrity import digest, hash_file, read_json


def inspect_environment(protocol, checked=True):
    a = protocol.data()['analysis_environment_amendment']
    result = {'amendment_sha256': digest(a),
        'inventory_identity_sha256': a['replacement']['inventory_identity_sha256'],
        'environment_path': a['replacement']['environment_path'],
        'interpreter_sha256': a['python']['executable_sha256'],
        'installed_file_identity_sha256': a['numpy']['installed_file_identity_sha256'],
        'technical_status': 'TECHNICALLY_VERIFIED',
        'scientific_acceptance': 'SCIENTIFIC_ACCEPTANCE_PENDING',
        'confirmatory_analysis_authorized': False,
        'live_identity_status': 'NOT_CHECKED', 'live_identity_records': []}
    if not checked:
        return result
    records = result['live_identity_records']
    def check(path, expected, *, independent=False):
        actual = ''; status = 'VERIFIED'
        try:
            file = Path(path)
            if independent:
                require(not file.is_symlink(), 'ANALYSIS_FILE_REDIRECT', str(file))
                for parent in file.parents:
                    if parent == Path(a['replacement']['environment_path']):
                        break
                    require(not parent.is_symlink(), 'ANALYSIS_FILE_REDIRECT', str(parent))
            actual = hash_file(file)[0]
            if actual != expected:
                status = 'MISMATCH'
        except (OSError, ControlError):
            status = 'MISSING_UNREADABLE_OR_REDIRECTED'
        records.append({'path': str(path), 'expected_sha256': expected,
                        'actual_sha256': actual, 'status': status})
        return status == 'VERIFIED'
    refs = []
    def references(value):
        if isinstance(value, dict):
            if set(value) == {'path', 'sha256'}:
                refs.append(value)
            else:
                for child in value.values():
                    references(child)
        elif isinstance(value, list):
            for child in value:
                references(child)
    references(a)
    for ref in refs:
        check(ref['path'], ref['sha256'])
    for name, digest_name in [('executable','executable_sha256'),
                              ('base_executable','base_executable_sha256'),
                              ('base_runtime_path','base_runtime_sha256')]:
        check(a['python'][name], a['python'][digest_name])
    # Do not trust lock-file contents if the pinned lock itself did not verify.
    lock = a['replacement']['environment_file_lock']
    if any(r['path'] == lock['path'] and r['status'] == 'VERIFIED' for r in records):
        try:
            env = Path(a['replacement']['environment_path'])
            value = read_json(Path(lock['path']))
            require(value['root'] == str(env), 'ANALYSIS_FILE_REDIRECT', 'lock root')
            require(not env.is_symlink() and not any(p.is_symlink() for p in env.rglob('*')),
                    'ANALYSIS_FILE_REDIRECT', 'no redirected directories/files in installed tree')
            expected_paths = set()
            for item in value['files']:
                relative = Path(item['path'])
                require(not relative.is_absolute() and '..' not in relative.parts,
                        'ANALYSIS_FILE_REDIRECT', str(relative))
                require(str(relative) not in expected_paths, 'ANALYSIS_FILE_REDIRECT', 'duplicate')
                expected_paths.add(str(relative))
                check(env/relative, item['sha256'], independent=True)
            actual_paths = {str(p.relative_to(env)) for p in env.rglob('*') if p.is_file()}
            require(actual_paths == expected_paths, 'ANALYSIS_PACKAGE_IDENTITY', 'extra/missing installed files')
        except (OSError, ControlError, KeyError, TypeError):
            records.append({'path': lock['path'], 'expected_sha256': lock['sha256'],
                            'actual_sha256': '', 'status': 'INVALID_INSTALLED_LOCK_OR_TREE'})
    # Dependency lock identifies the shared Python runtime and all standalone image files.
    dep = a['python']['dependencies']
    if any(r['path'] == dep['path'] and r['status'] == 'VERIFIED' for r in records):
        for item in read_json(Path(dep['path']))['images']:
            if item['sha256'] is not None:
                check(item['path'], item['sha256'])
    result['live_identity_status'] = 'VERIFIED' if records and all(r['status']=='VERIFIED' for r in records) else 'FAILED'
    return result
