"""Verify that optional network work stops on local descriptor exhaustion."""

import errno

import pytest
import requests
from requests.adapters import HTTPAdapter

import lastfm_monitor as monitor


# Stops optional fallback requests when the transport reports a local resource limit
def test_optional_network_work_stops_on_resource_exhaustion(monkeypatch, capsys):
    calls = []
    http_client = vars(monitor.pylast)["httpx"]

    # Injects the real requests exception chain at its transport boundary
    def exhausted_requests(self, request, **kwargs):
        calls.append(str(request.url))
        raise requests.ConnectionError("Connection failed") from OSError(errno.EMFILE, "Too many open files")

    # Injects the real HTTPX exception chain at its transport boundary
    def exhausted_httpx(self, request):
        calls.append(str(request.url))
        raise http_client.ConnectError("Connection failed", request=request) from OSError(errno.EMFILE, "Too many open files")

    monkeypatch.setattr(HTTPAdapter, "send", exhausted_requests)
    monkeypatch.setattr(http_client.HTTPTransport, "handle_request", exhausted_httpx)
    monkeypatch.setattr(monitor, "USE_TRACK_DURATION_FROM_SPOTIFY", False)
    monkeypatch.setattr(monitor, "TRACK_SONGS", False)
    with pytest.raises(SystemExit) as stopped:
        monitor.get_track_info("Example Artist", "Example Track", "", monitor.pylast.LastFMNetwork(api_key="synthetic-key", api_secret="synthetic-secret"))
    assert stopped.value.code == 1
    assert len(calls) == 1
    assert "file descriptors" in capsys.readouterr().out
