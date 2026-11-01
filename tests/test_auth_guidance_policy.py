import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _policy_documents():
    return [ROOT / 'README.md', *list((ROOT / 'docs').rglob('*.md')),
            *list((ROOT / 'agent_reach/skill').rglob('*.md'))]


def test_guidance_does_not_install_unrelated_pypi_package():
    bare_install = re.compile(r'\bpip\s+install(?:\s+--upgrade)?\s+[\'"]?agent-reach(?:\[[^\]]+\])?\b', re.I)
    for path in _policy_documents():
        for line in path.read_text().splitlines():
            assert not bare_install.search(line), (path, line)


def test_guidance_does_not_put_secrets_in_arguments():
    for path in _policy_documents():
        text = path.read_text()
        for marker in ('agent-reach configure groq-key gsk_', 'agent-reach configure openai-key sk-'):
            assert marker not in text, path
