from agent_reach.channels import youtube
from agent_reach.runtime.dispatch import run_action
from agent_reach.runtime.run import CommandFailed


def test_youtube_bot_challenge_does_not_instruct_a_login(monkeypatch):
    def blocked(*args, **kwargs):
        raise CommandFailed('UPSTREAM_BROKEN', 'YouTube challenge', stderr='Sign in to confirm you are not a bot')
    monkeypatch.setattr(youtube, 'run_cmd', blocked)
    result = run_action(youtube.YouTubeChannel(), 'read', {'target': 'jNQXAC9IVRw'})
    assert result['error']['code'] == 'PLATFORM_BLOCKED'
    assert 'does not establish' in result['error']['hint']
