"""Scan tracked Git history for private credentials without printing their values."""
import base64
import json
import re
import subprocess
import sys

PATTERNS = [
    re.compile(rb"(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})"),
    re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(rb"(?:AKIA|ASIA)[A-Z0-9]{16}"),
    re.compile(rb"(?:sb_secret_[A-Za-z0-9_-]{20,}|1//[A-Za-z0-9_-]{40,})"),
    re.compile(rb"(?i)(?:SUPABASE_KEY|OPENAQ_API_KEY|refresh_token|client_secret)[\"\']?\s*[:=]\s*[\"\']([A-Za-z0-9_./-]{25,})[\"\']"),
]
JWT = re.compile(rb"eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+")

def private_content(content):
    if any(pattern.search(content) for pattern in PATTERNS):
        return True
    for match in JWT.finditer(content):
        try:
            payload = match.group().split(b'.')[1]
            claims = json.loads(base64.urlsafe_b64decode(payload + b'=' * (-len(payload) % 4)))
            if claims.get('role') == 'service_role':
                return True
        except (ValueError, TypeError):
            continue
    return False


def main():
    objects = subprocess.check_output(['git', 'rev-list', '--objects', '--all']).splitlines()
    names = {}
    problems = []
    for line in objects:
        parts = line.decode('utf-8', errors='replace').split(' ', 1)
        if len(parts) != 2:
            continue
        oid, name = parts
        names[oid] = name
        base = name.rsplit('/', 1)[-1]
        if base in {'.env', '.env.local', '.env.production'} or name.startswith(('.tools/', 'venv/')):
            problems.append((oid, name, 'private local file tracked in history'))
    process = subprocess.Popen(['git', 'cat-file', '--batch'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    scanned = 0
    try:
        for oid, name in names.items():
            process.stdin.write((oid + '\n').encode()); process.stdin.flush()
            header = process.stdout.readline().split()
            content = process.stdout.read(int(header[2])); process.stdout.read(1)
            if header[1] != b'blob':
                continue
            scanned += 1
            if private_content(content):
                problems.append((oid, name, 'possible private credential'))
    finally:
        process.stdin.close(); process.wait()
    if problems:
        for oid, name, reason in problems:
            print(f'{reason}: {name} (object {oid[:12]})')
        return 1
    print(f'PASS: {scanned} historical file versions checked; no matching private credential or local secret file detected.')
    print('Public Supabase anon keys are allowed; service_role tokens are rejected.')
    return 0

if __name__ == '__main__':
    sys.exit(main())
