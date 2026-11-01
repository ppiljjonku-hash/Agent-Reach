# -*- coding: utf-8 -*-
"""Contract tests for channel adapters."""

from agent_reach.channels import get_all_channels
from agent_reach.runtime.dispatch import run_action
from agent_reach.runtime.result import ReachError


def test_channel_registry_contract():
    channels = get_all_channels()
    assert channels, "channel registry must not be empty"
    names = [ch.name for ch in channels]
    assert len(names) == len(set(names)), "channel names must be unique"
    assert set(names) == {"twitter", "reddit", "youtube"}

    for ch in channels:
        assert isinstance(ch.name, str) and ch.name
        assert isinstance(ch.description, str) and ch.description
        assert ch.level in {"default", "optional", "experimental"}
        assert ch.actions, f"{ch.name} exposes no actions"
        for action in ch.actions:
            for _label, method in action.backends:
                assert callable(getattr(ch, method, None)), f"{ch.name}.{method}"


def test_channel_can_handle_contract():
    url_samples = {
        "twitter": "https://x.com/user/status/1",
        "youtube": "https://youtube.com/watch?v=abc",
        "reddit": "https://reddit.com/r/python",
    }
    for ch in get_all_channels():
        sample = url_samples[ch.name]
        result = ch.can_handle(sample)
        assert result is True


def test_backend_failure_does_not_send_query_to_another_service(monkeypatch):
    for channel in get_all_channels():
        action = next(action for action in channel.actions if action.name == 'search')
        assert not hasattr(action, 'public_web')
        assert len(action.backends) == 1
        backend, method = action.backends[0]
        def failed(**kwargs):
            raise ReachError('UPSTREAM_BROKEN', 'site tool unavailable')
        monkeypatch.setattr(channel, method, failed)
        result = run_action(channel, 'search', {'query': 'private-query'})
        assert not result['ok']
        assert result['error']['code'] == 'UPSTREAM_BROKEN'
        assert [attempt['backend'] for attempt in result['meta']['attempts']] == [backend]
