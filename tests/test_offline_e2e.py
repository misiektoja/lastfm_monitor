"""Offline end-to-end test: the real CLI, one monitoring cycle and a Last.fm fixture served over loopback."""

import csv
import json
import os
import pty
import select
import subprocess
import sys
import textwrap
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CLI_PATH = PROJECT_ROOT / "lastfm_monitor.py"

API_KEY = "lastfmapikey00000000000000000000"
API_SECRET = "lastfmapisecret00000000000000000"

# One user.getRecentTracks answer in the shape Last.fm returns, with a track playing right now
RECENT_TRACKS_XML = """<?xml version="1.0" encoding="utf-8"?>
<lfm status="ok"><recenttracks user="offlineuser" page="1" perPage="2" totalPages="1" total="2">
<track nowplaying="true"><artist mbid="">Local Artist</artist><name>Local Track</name><album mbid="">Local Album</album><url>https://www.last.fm/music/Local+Artist/_/Local+Track</url></track>
<track><artist mbid="">Older Artist</artist><name>Older Track</name><album mbid="">Older Album</album><date uts="1700000000">14 Nov 2023, 22:13</date><url>https://www.last.fm/music/Older+Artist/_/Older+Track</url></track>
</recenttracks></lfm>"""


# Answers the Last.fm web service and the connectivity probe from one deterministic fixture
class OfflineLastfmHandler(BaseHTTPRequestHandler):
    posted_methods: list = []

    # Serves the connectivity probe the tool gates its startup on
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Length", "0")
        self.end_headers()

    # Serves every signed web service call with the same recent-tracks document
    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", 0))).decode("utf-8")
        type(self).posted_methods.append(next((part.split("=", 1)[1] for part in body.split("&") if part.startswith("method=")), ""))
        payload = RECENT_TRACKS_XML.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/xml")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    # Keeps the fixture server out of the captured test output
    def log_message(self, format, *args):
        return None


# Builds the config an offline run needs, with every notifier off and both intervals at one second
def write_offline_config(directory, port):
    config_path = directory / "lastfm_monitor.conf"
    config_path.write_text(
        f'LASTFM_API_KEY = "{API_KEY}"\n'
        f'LASTFM_API_SECRET = "{API_SECRET}"\n'
        f'CHECK_INTERNET_URL = "http://127.0.0.1:{port}/"\n'
        'CLEAR_SCREEN = False\n'
        'CSV_FILE = "played.csv"\n'
        'LASTFM_CHECK_INTERVAL = 1\n'
        'LASTFM_ACTIVE_CHECK_INTERVAL = 1\n'
        'ACTIVE_NOTIFICATION = False\n'
        'INACTIVE_NOTIFICATION = False\n'
        'TRACK_NOTIFICATION = False\n'
        'SONG_NOTIFICATION = False\n'
        'SONG_ON_LOOP_NOTIFICATION = False\n'
        'OFFLINE_ENTRIES_NOTIFICATION = False\n'
        'ERROR_NOTIFICATION = False\n'
        'WEBHOOK_ENABLED = False\n'
        'TRACK_SONGS = False\n'
        'USE_TRACK_DURATION_FROM_SPOTIFY = False\n',
        encoding="utf-8",
    )
    return config_path


# Builds the driver that runs the real CLI, points pylast at the fixture and stops after one cycle
def offline_run_source(config_path, port, extra_config=""):
    return textwrap.dedent(f"""
        import functools
        import runpy
        import socket
        import pylast

        # Nothing in this run may leave the machine. A version of pylast that ignores the injected
        # transport would otherwise reach the real Last.fm API and read as a fixture failure
        real_connect = socket.socket.connect

        def loopback_only(self, address):
            host = address[0] if isinstance(address, tuple) else ""
            if host not in ("127.0.0.1", "::1", "localhost"):
                raise AssertionError(f"the offline run tried to reach {{host}}")
            return real_connect(self, address)

        socket.socket.connect = loopback_only

        # Rewrites the scheme so pylast's own client reaches the plain loopback fixture, leaving every
        # other layer of the request untouched: the signing, the POST body and the XML parsing are real
        class PlainLoopbackTransport(pylast.httpx.HTTPTransport):
            def handle_request(self, request):
                request.url = request.url.copy_with(scheme="http")
                return super().handle_request(request)

        # The transport is injected into the client itself rather than mounted on the network, because
        # pylast only forwards a configured proxy on some versions and ignores it on the rest
        pylast.httpx.Client = functools.partial(pylast.httpx.Client, transport=PlainLoopbackTransport())

        real_network = pylast.LastFMNetwork

        def offline_network(*args, **kwargs):
            network = real_network(*args, **kwargs)
            network.ws_server = ("127.0.0.1:{port}", "/2.0/")
            return network

        module = runpy.run_path({str(CLI_PATH)!r}, run_name="lastfm_monitor_offline_e2e")
        runtime = module["main"].__globals__
        runtime["sys"].argv = [{str(CLI_PATH)!r}, "offlineuser", "--config-file", {str(config_path)!r}, "--env-file", "none"]
        runtime["pylast"].LastFMNetwork = offline_network
        # The first wait ends the run, so exactly one cycle is measured
        runtime["time"].sleep = lambda seconds: (_ for _ in ()).throw(SystemExit(0))
        {extra_config}
        module["main"]()
    """)


@pytest.fixture
def offline_lastfm_server():
    OfflineLastfmHandler.posted_methods = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), OfflineLastfmHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server.server_port, OfflineLastfmHandler
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)


# Verifies one complete run: the config is loaded, pylast talks to the fixture and the cycle reports the track
@pytest.mark.e2e
def test_one_monitoring_cycle_against_a_local_lastfm_fixture(offline_lastfm_server, tmp_path):
    port, handler = offline_lastfm_server
    config_path = write_offline_config(tmp_path, port)
    source = offline_run_source(config_path, port)
    environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    environment.pop("NO_COLOR", None)
    result = subprocess.run([sys.executable, "-c", source], cwd=tmp_path, env=environment, check=False, capture_output=True, text=True, timeout=60)

    assert result.returncode == 0, result.stdout + result.stderr
    # The startup summary describes the run the config asked for
    assert "* Target:" in result.stdout and "offlineuser" in result.stdout
    assert "* Polling intervals:" in result.stdout
    assert f"* Config:{chr(9)}" not in result.stdout and str(config_path) in result.stdout
    assert "lastfm_monitor_offlineuser.log" in result.stdout
    assert "played.csv" in result.stdout
    # The run reached the loop and reported the fixture's track
    assert "Monitoring user offlineuser" in result.stdout
    assert "Local Artist - Local Track" in result.stdout
    assert "Local Album" in result.stdout
    assert "User is currently ACTIVE" in result.stdout
    # The music links are built from the fixture's names rather than a placeholder
    assert "https://www.last.fm/music/local%2bartist/_/local%2btrack" in result.stdout
    # The scrobble history behind the playing track is listed too
    assert "Older Artist - Older Track" in result.stdout
    # No secret from the config reaches the screen
    assert API_KEY not in result.stdout and API_SECRET not in result.stdout
    # pylast really signed and sent the calls rather than being stubbed out
    assert "user.getRecentTracks" in handler.posted_methods
    assert set(handler.posted_methods) <= {"user.getRecentTracks", "track.getInfo"}
    # Every file the configured run promised is on disk, and the log carries the same cycle
    log_text = (tmp_path / "lastfm_monitor_offlineuser.log").read_text(encoding="utf-8")
    assert "Local Artist - Local Track" in log_text
    csv_rows = list(csv.reader((tmp_path / "played.csv").read_text(encoding="utf-8").splitlines()))
    assert csv_rows[0] == ["Date", "Artist", "Track", "Album"]
    assert [row[1:] for row in csv_rows[1:]] == [["Local Artist", "Local Track", "Local Album"]]
    saved_state = json.loads((tmp_path / "lastfm_offlineuser_last_activity.json").read_text(encoding="utf-8"))
    assert saved_state[1:] == ["Local Artist", "Local Track", "Local Album"]


# Runs the driver on a real terminal and returns everything the terminal received
def run_on_a_pty(source, working_directory):
    controller, terminal = pty.openpty()
    environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", TERM="xterm-256color", COLUMNS="120")
    environment.pop("NO_COLOR", None)
    process = subprocess.Popen([sys.executable, "-c", source], cwd=working_directory, env=environment, stdin=terminal, stdout=terminal, stderr=terminal, close_fds=True)
    os.close(terminal)
    chunks = []
    try:
        while True:
            if not select.select([controller], [], [], 60)[0]:
                break
            try:
                chunk = os.read(controller, 65536)
            except OSError:
                break
            if not chunk:
                break
            chunks.append(chunk)
    finally:
        os.close(controller)
        process.wait(timeout=60)
    return process.returncode, b"".join(chunks).decode("utf-8", "replace")


# Verifies the interactive run: the terminal gets colour, the log file gets the same lines without it
@pytest.mark.e2e
def test_the_same_cycle_on_a_real_terminal_colours_the_screen_and_not_the_log(offline_lastfm_server, tmp_path):
    port, _handler = offline_lastfm_server
    config_path = write_offline_config(tmp_path, port)
    config_path.write_text(config_path.read_text(encoding="utf-8") + "COLORED_OUTPUT = True\n", encoding="utf-8")
    returncode, transcript = run_on_a_pty(offline_run_source(config_path, port), tmp_path)

    assert returncode == 0, transcript
    # The screen really carries styling, and the track the fixture reported is on it
    assert "\x1b[" in transcript
    assert "Local Artist" in transcript and "Local Track" in transcript
    # The name is styled rather than the whole row, so the label stays plain
    track_line = next(line for line in transcript.splitlines() if "Local Artist - Local Track" in line and line.startswith("Track:"))
    assert track_line.startswith("Track:\t") and "\x1b[" in track_line
    # The log file records the same cycle with no escape of any kind
    log_text = (tmp_path / "lastfm_monitor_offlineuser.log").read_text(encoding="utf-8")
    assert "Local Artist - Local Track" in log_text
    assert "\x1b" not in log_text
