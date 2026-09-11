import json
import sys

from app.blocklist import cli, report_cli, scheduler_cli


class DummyReport:
    def __init__(self, kind: str):
        self.kind = kind

    def model_dump_json(self, indent=2):
        return json.dumps({"kind": self.kind}, indent=indent)


class FakeSettings:
    def __init__(self, **kwargs):
        self.database_url = kwargs.get("database_url", "sqlite:///fake.db")
        self.blocklist_dns_mode = kwargs.get("blocklist_dns_mode", "fake")
        self.blocklist_interval_seconds = kwargs.get("blocklist_interval_seconds", 300)


class FakeRepository:
    instances = []

    def __init__(self, database_url, dns_mode="fake"):
        self.database_url = database_url
        self.dns_mode = dns_mode
        self.closed = False
        type(self).instances.append(self)

    def close(self):
        self.closed = True


class FakeService:
    def __init__(self, settings, repository):
        self.settings = settings
        self.repository = repository

    def run_once(self, source_path=None):
        return DummyReport("run")


class FakeScheduler:
    instances = []

    def __init__(self, service):
        self.service = service
        self.interval_seconds = service.settings.blocklist_interval_seconds
        self.history_args = None
        self.forever_called = False
        self.stop_event = None
        type(self).instances.append(self)

    def run_cycle(self):
        return DummyReport("cycle")

    def history_report(self, days, dns_mode=None):
        self.history_args = (days, dns_mode)
        return DummyReport("history")

    def run_forever(self, stop_event):
        self.forever_called = True
        self.stop_event = stop_event


def patch_common(monkeypatch, module):
    FakeRepository.instances.clear()
    FakeScheduler.instances.clear()
    monkeypatch.setattr(module, "Settings", FakeSettings)
    monkeypatch.setattr(module, "BlocklistRepository", FakeRepository)
    monkeypatch.setattr(module, "BlocklistMonitorService", FakeService)


def test_blocklist_cli_main_writes_report(tmp_path, monkeypatch, capsys):
    patch_common(monkeypatch, cli)
    output = tmp_path / "nested" / "report.json"
    assets = tmp_path / "assets.json"
    assets.write_text('{"assets":[]}', encoding="utf-8")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "blocklist-cli",
            "--assets",
            str(assets),
            "--output",
            str(output),
            "--database-url",
            "sqlite:///custom.db",
        ],
    )

    cli.main()

    assert json.loads(output.read_text(encoding="utf-8")) == {"kind": "run"}
    assert "Çıktı:" in capsys.readouterr().out
    assert FakeRepository.instances[-1].database_url == "sqlite:///custom.db"
    assert FakeRepository.instances[-1].closed is True


def test_report_cli_main_passes_days_and_dns_mode(tmp_path, monkeypatch, capsys):
    patch_common(monkeypatch, report_cli)
    monkeypatch.setattr(report_cli, "BlocklistScheduler", FakeScheduler)
    output = tmp_path / "history.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "blocklist-report",
            "--days",
            "7",
            "--dns-mode",
            "live",
            "--output",
            str(output),
        ],
    )

    report_cli.main()

    assert json.loads(output.read_text(encoding="utf-8")) == {"kind": "history"}
    assert FakeScheduler.instances[-1].history_args == (7, "live")
    assert FakeRepository.instances[-1].closed is True
    assert "Çıktı:" in capsys.readouterr().out


def test_scheduler_cli_once_honors_overrides(tmp_path, monkeypatch, capsys):
    patch_common(monkeypatch, scheduler_cli)
    monkeypatch.setattr(scheduler_cli, "BlocklistScheduler", FakeScheduler)
    monkeypatch.setattr(scheduler_cli.signal, "signal", lambda *_args: None)
    output = tmp_path / "last-run.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "blocklist-scheduler",
            "--once",
            "--interval",
            "15",
            "--dns-mode",
            "live",
            "--database-url",
            "sqlite:///scheduler.db",
            "--output",
            str(output),
        ],
    )

    scheduler_cli.main()

    assert json.loads(output.read_text(encoding="utf-8")) == {"kind": "cycle"}
    scheduler = FakeScheduler.instances[-1]
    assert scheduler.interval_seconds == 15
    assert scheduler.service.settings.blocklist_dns_mode == "live"
    assert FakeRepository.instances[-1].database_url == "sqlite:///scheduler.db"
    assert FakeRepository.instances[-1].closed is True
    assert "Çıktı:" in capsys.readouterr().out


def test_scheduler_cli_forever_path_starts_scheduler(monkeypatch, capsys):
    patch_common(monkeypatch, scheduler_cli)
    monkeypatch.setattr(scheduler_cli, "BlocklistScheduler", FakeScheduler)
    captured_handlers = {}

    def fake_signal(signum, handler):
        captured_handlers[signum] = handler

    monkeypatch.setattr(scheduler_cli.signal, "signal", fake_signal)
    monkeypatch.setattr(sys, "argv", ["blocklist-scheduler"])

    scheduler_cli.main()

    scheduler = FakeScheduler.instances[-1]
    assert scheduler.forever_called is True
    assert scheduler.stop_event is not None
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["status"] == "started"
    assert payload["dns_mode"] == "fake"
    assert payload["interval_seconds"] == 300
    assert FakeRepository.instances[-1].closed is True
    assert len(captured_handlers) == 2
