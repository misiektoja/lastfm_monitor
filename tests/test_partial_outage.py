"""Exercise partial Last.fm outages through real pylast and HTTP transports."""
import json
import os
from pathlib import Path
import subprocess
import sys
import textwrap


# Keeps a successful history request from clearing an outage in the following now-playing request
def test_now_playing_outage_survives_successful_history(tmp_path):
    root = Path(__file__).resolve().parents[1]
    driver = textwrap.dedent("""
        import json
        import time
        import socket
        import requests
        import pylast
        from pylast import httpx
        import lastfm_monitor as monitor

        clock = [1700000000]
        cycle = [1]
        calls = [0]
        startup = [True]
        deliveries = []
        empty = '<lfm status="ok"><recenttracks user="offlineuser" page="1" perPage="1" totalPages="1" total="0"></recenttracks></lfm>'
        history = '<lfm status="ok"><recenttracks user="offlineuser" page="1" perPage="1" totalPages="1" total="1"><track><artist>Artist</artist><name>Track</name><album>Album</album><date uts="1600000000">13 Sep 2020</date></track></recenttracks></lfm>'

        # Supplies realistic XML and HTTP errors without replacing pylast clients or iterators
        def respond(transport, request):
            print("REQUEST", cycle[0], calls[0], startup[0])
            calls[0] += 1
            if startup[0]:
                if calls[0] == 2:
                    startup[0] = False
                    calls[0] = 0
                return httpx.Response(200, request=request, text=empty)
            if cycle[0] == 4:
                return httpx.Response(200, request=request, text=empty)
            if calls[0] == 1:
                return httpx.Response(200, request=request, text=history)
            return httpx.Response(503, request=request, text="Temporarily unavailable")

        # Captures delivery at the HTTP boundary while using the real notifier
        def deliver(session, request, **kwargs):
            deliveries.append(cycle[0])
            response = requests.Response()
            response.request = request
            response.status_code = 200
            response._content = b'{}'
            return response

        # Advances the clock by one normal poll and stops after the second outage earns an alert
        def sleep(seconds):
            if seconds < 600:
                clock[0] += seconds
                return
            cycle[0] += 1
            calls[0] = 0
            clock[0] += 600
            if cycle[0] > 6:
                raise SystemExit(0)

        # Stops any dependency that bypasses the injected HTTP transport
        def refuse_socket(*args, **kwargs):
            raise AssertionError("Unexpected real network connection")

        socket.socket.connect = refuse_socket
        httpx.HTTPTransport.handle_request = respond
        requests.Session.send = deliver
        time.sleep = sleep
        time.time = lambda: clock[0]
        monitor.DEBUG_MODE = True
        monitor.LOCAL_TIMEZONE = "UTC"
        monitor.LASTFM_CHECK_INTERVAL = 600
        monitor.LASTFM_ACTIVE_CHECK_INTERVAL = 600
        monitor.TRACK_FOLLOWERS = monitor.TRACK_FOLLOWINGS = False
        monitor.TRACK_BIO = monitor.TRACK_DISPLAY_NAME = False
        monitor.ERROR_NOTIFICATION = False
        monitor.WEBHOOK_ENABLED = True
        monitor.WEBHOOK_ERROR_NOTIFICATION = True
        monitor.WEBHOOK_PROVIDER = "ntfy"
        monitor.WEBHOOK_URL = "https://ntfy.sh/synthetic-test-topic"
        monitor.NTFY_ACCESS_TOKEN = ""
        network = pylast.LastFMNetwork(api_key="synthetic-key", api_secret="synthetic-secret")
        try:
            monitor.lastfm_monitor_user(network.get_user("offlineuser"), network, "offlineuser", [], "")
        except SystemExit:
            pass
        print("DELIVERIES=" + json.dumps(deliveries))
    """)
    environment = dict(os.environ, PYTHONPATH=str(root), PYTHONDONTWRITEBYTECODE="1")
    result = subprocess.run([sys.executable, "-c", driver], cwd=tmp_path, env=environment, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    deliveries = json.loads(next(line.split("=", 1)[1] for line in result.stdout.splitlines() if line.startswith("DELIVERIES=")))
    assert deliveries == [2, 6], result.stdout + result.stderr
