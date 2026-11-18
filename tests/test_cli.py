from books_etl import pipeline
from books_etl.__main__ import main


def test_failed_run_prints_the_error(tmp_path, monkeypatch, capsys):
    def boom(*args, **kwargs):
        raise RuntimeError("could not open database")

    monkeypatch.setattr(pipeline, "run", boom)
    assert main(["run", "--db", str(tmp_path / "x.db")]) == 1
    err = capsys.readouterr().err
    assert "run failed" in err
    assert "could not open database" in err  # the cause is shown, not swallowed


def test_successful_run_prints_summary(tmp_path, monkeypatch, capsys):
    summary = pipeline.RunSummary("abc", "succeeded", 5, 5, 0)
    monkeypatch.setattr(pipeline, "run", lambda *a, **k: summary)
    assert main(["run", "--db", str(tmp_path / "x.db")]) == 0
    assert "succeeded" in capsys.readouterr().out


def test_report_on_new_database_does_not_crash(tmp_path, capsys):
    assert main(["report", "run_history", "--db", str(tmp_path / "new.db")]) == 0
    assert "no rows yet" in capsys.readouterr().out
