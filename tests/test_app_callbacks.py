"""Regression tests for callbacks across navigation and session changes."""
from concurrent.futures import Future
from types import SimpleNamespace
from ui.app import Application


class Harness:
    run = Application.run
    poll = Application.poll
    callback_is_current = Application.callback_is_current

    def __init__(self):
        self.identity = SimpleNamespace(expired=lambda minutes: False)
        self.generation = 1
        self.maintenance = False
        self.timeout_minutes = 30
        self.pending = []
        self.future = Future()
        self.executor = SimpleNamespace(submit=lambda work: self.future)
        self.status = SimpleNamespace(set=lambda value: None)
        self.after = lambda *args: None


def test_settings_callback_survives_navigation():
    app, results = Harness(), []
    app.run(lambda: None, results.append, session_wide=True)
    app.generation += 1
    app.future.set_result({'session_timeout_minutes': 5})
    app.poll()
    assert results == [{'session_timeout_minutes': 5}]


def test_settings_from_previous_session_are_discarded():
    app, results = Harness(), []
    app.run(lambda: None, results.append, session_wide=True)
    app.identity = SimpleNamespace(expired=lambda minutes: False)
    app.future.set_result('stale settings')
    app.poll()
    assert not results


def test_screen_callback_does_not_update_another_screen():
    app, results = Harness(), []
    app.run(lambda: None, results.append)
    app.generation += 1
    app.future.set_result('old screen data')
    app.poll()
    assert not results


def test_restore_maintenance_blocks_new_work():
    app = Harness()
    app.maintenance = True
    app.run(lambda: None)
    assert not app.pending
