"""Reading the caller's address from X-Forwarded-For without trusting the part
of it the caller writes."""

from starlette.requests import Request

from app.core.client_ip import client_ip
from app.core.config import get_settings


def _request(forwarded_for: str | None, peer: str = "169.254.1.1") -> Request:
    headers = [(b"x-forwarded-for", forwarded_for.encode())] if forwarded_for is not None else []
    return Request({"type": "http", "headers": headers, "client": (peer, 12345)})


def test_with_no_proxy_the_socket_peer_is_used_and_the_header_ignored(monkeypatch):
    monkeypatch.setattr(get_settings(), "trusted_proxy_hops", 0)

    assert client_ip(_request("1.2.3.4", peer="127.0.0.1")) == "127.0.0.1"


def test_behind_one_proxy_the_entry_it_appended_is_used(monkeypatch):
    monkeypatch.setattr(get_settings(), "trusted_proxy_hops", 1)

    assert client_ip(_request("203.0.113.7")) == "203.0.113.7"


def test_entries_the_client_sent_itself_are_ignored(monkeypatch):
    monkeypatch.setattr(get_settings(), "trusted_proxy_hops", 1)

    assert client_ip(_request("6.6.6.6, 7.7.7.7, 203.0.113.7")) == "203.0.113.7"


def test_a_missing_header_falls_back_to_the_peer(monkeypatch):
    monkeypatch.setattr(get_settings(), "trusted_proxy_hops", 1)

    assert client_ip(_request(None)) == "169.254.1.1"


def test_behind_two_proxies_the_second_from_the_right_is_used(monkeypatch):
    monkeypatch.setattr(get_settings(), "trusted_proxy_hops", 2)

    assert client_ip(_request("6.6.6.6, 203.0.113.7, 35.191.0.1")) == "203.0.113.7"
