from agent_reach.channels import get_all_channels, get_channel


def test_registry_contains_only_requested_channels():
    assert {channel.name for channel in get_all_channels()} == {'twitter', 'reddit', 'youtube'}
    assert get_channel('twitter').name == 'twitter'
    assert get_channel('unknown') is None


def test_channels_do_not_handle_general_web_urls():
    for channel in get_all_channels():
        assert not channel.can_handle('https://example.com/article')
