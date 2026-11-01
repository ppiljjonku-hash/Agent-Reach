import pytest

from agent_reach.channels.reddit import RedditChannel
from agent_reach.channels.twitter import TwitterChannel
from agent_reach.channels.youtube import YouTubeChannel
from agent_reach.utils.url import host_matches


@pytest.mark.parametrize('channel,domain', [
    (TwitterChannel(), 'x.com'),
    (TwitterChannel(), 'twitter.com'),
    (RedditChannel(), 'reddit.com'),
    (RedditChannel(), 'redd.it'),
    (YouTubeChannel(), 'youtube.com'),
    (YouTubeChannel(), 'youtu.be'),
])
def test_site_urls_require_exact_hosts(channel, domain):
    assert channel.can_handle(f'https://{domain}/path')
    assert channel.can_handle(f'https://www.{domain}/path')
    assert channel.can_handle(f'https://{domain.upper()}.:443/path')
    for target in (
        f'https://{domain}.evil.test/path',
        f'https://not{domain}/path',
        f'https://{domain}@evil.test/path',
        f'https://user:pass@{domain}/path',
        f'ftp://{domain}/path',
    ):
        assert not channel.can_handle(target)


@pytest.mark.parametrize('port', ['not-a-port', '65536', '-1', '999999999999'])
def test_host_matches_rejects_invalid_ports(port):
    assert not host_matches(f'https://x.com:{port}/path', 'x.com')
