"""Secrets embedded in URLs must not reach user-facing diagnostics."""



from agent_reach.utils.text import scrub_url_credentials


def test_errors_redact_cookie_and_authorization_headers():
    from agent_reach.backends.opencli import _opencli_error
    error = _opencli_error('Cookie: auth_token=private-cookie; ct0=private-csrf\nAuthorization: Bearer private-key', '')
    assert 'private-' not in error.message


def test_nested_result_credentials_are_redacted_without_changing_content():
    from agent_reach.runtime.result import make_item
    item = make_item(text='public post', raw={
        'title': 'public title', 'auth_token': 'private-token',
        'headers': {'Authorization': 'Bearer private-key'},
        'cookies': [{'name': 'sid', 'value': 'private-cookie'}],
        'url': 'https://reddit.com/r/python?token=private-url',
        'nested': [{'name': 'ct0', 'value': 'private-csrf'}],
    })
    assert 'private-' not in repr(item)
    assert item['text'] == 'public post' and item['raw']['title'] == 'public title'


def test_cli_redacts_management_output(capsys):
    from agent_reach.runtime.cli import _emit
    assert _emit({'ok': True, 'result': {'api_key': 'private-key'}}) == 0
    assert 'private-key' not in capsys.readouterr().out


def test_scrubs_userinfo_and_sensitive_query_values():
    raw = (
        "proxy http://user:pass@proxy.example:8080 failed; "
        "upstream https://api.example.test/path?access_token=secret"
        "&page=2&api_key=another-secret"
    )

    scrubbed = scrub_url_credentials(raw)

    assert "user:pass" not in scrubbed
    assert "secret" not in scrubbed
    assert "another-secret" not in scrubbed
    assert "http://***@proxy.example:8080" in scrubbed
    assert "access_token=***" in scrubbed
    assert "page=2" in scrubbed
    assert "api_key=***" in scrubbed


def test_scrubs_multiple_schemes_and_fragment_tokens():
    raw = (
        "socks5://token@host:1080 "
        "https://example.test/#auth_token=fragment-secret"
    )

    scrubbed = scrub_url_credentials(ValueError(raw))

    assert scrubbed == (
        "socks5://***@host:1080 "
        "https://example.test/#auth_token=***"
    )


def test_scrubs_bare_user_password_host_diagnostics():
    raw = "proxy handshake for user:pass@proxy.test failed"
    assert scrub_url_credentials(raw) == "proxy handshake for ***@proxy.test failed"


def test_leaves_non_secret_urls_and_plain_text_unchanged():
    raw = "See https://example.test/search?q=python&page=2 after timeout"
    assert scrub_url_credentials(raw) == raw



