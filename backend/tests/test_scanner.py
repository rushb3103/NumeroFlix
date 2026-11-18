from pathlib import Path
from threading import Event

import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from app.models import Collection, CollectionMovie, Movie, MovieTag, Tag, WatchProgress
from app.services.scanner import scan_library, title_from_filename


def test_title_parsing():
    assert title_from_filename(Path("The.Matrix.1999.1080p.mkv")) == ("The Matrix", 1999)


def test_scan_is_incremental_and_preserves_metadata(tmp_path: Path, monkeypatch):
    root = tmp_path / "vault"
    root.mkdir()
    first = root / "Arrival.2016.mkv"
    first.write_bytes(b"not-real-video")
    probes = []

    def probe(path, executable):
        probes.append((path, executable))
        return "640x360" if path.stat().st_size == 14 else "1920x1080"

    monkeypatch.setattr("app.services.scanner.first_frame_resolution", probe)
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        result = scan_library(session, root)
        assert result["discovered"] == 1
        movie = session.exec(select(Movie)).one()
        assert movie.file_size == 14
        assert movie.first_frame_resolution == "640x360"
        movie.tags.append(Tag(name="Thoughtful"))
        movie.collections.append(Collection(name="Sci-fi"))
        movie.progress = WatchProgress(movie_id=movie.id, position_seconds=7)
        session.add(movie)
        session.commit()
        assert scan_library(session, root)["discovered"] == 0
        assert probes == [(first, "ffmpeg")]
        session.refresh(movie)
        assert movie.tags[0].name == "Thoughtful"
        first.write_bytes(b"replacement")
        assert scan_library(session, root, ffmpeg_path="configured-ffmpeg")["updated"] == 1
        assert movie.file_size == 11
        assert movie.first_frame_resolution == "1920x1080"
        assert probes[-1] == (first, "configured-ffmpeg")

        first.unlink()
        session.add(Movie(title="Legacy unavailable", relative_path="absent.mp4", is_available=False))
        session.commit()
        assert scan_library(session, root)["removed"] == 2
        for model in (Movie, MovieTag, CollectionMovie, WatchProgress):
            assert session.exec(select(model)).all() == []


def test_incomplete_scans_keep_catalog(tmp_path: Path, monkeypatch):
    (tmp_path / "new.mp4").touch()
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    monkeypatch.setattr("app.services.scanner.first_frame_resolution", lambda *_: "640x360")
    with Session(engine) as session:
        session.add(Movie(title="Missing", relative_path="missing.mp4"))
        session.commit()
        cancel = Event()
        result = scan_library(session, tmp_path, cancel, lambda *_: cancel.set())
        assert result["cancelled"]
        assert session.exec(select(Movie.relative_path)).all() == ["missing.mp4"]

        def unreadable_folder(self, *, on_error):
            yield self, ["locked"], ["new.mp4"]
            on_error(PermissionError("Cannot read locked folder"))

        monkeypatch.setattr(Path, "walk", unreadable_folder)
        with pytest.raises(PermissionError):
            scan_library(session, tmp_path)
        assert session.exec(select(Movie.relative_path)).all() == ["missing.mp4"]


def test_disconnected_root_preserves_catalog(tmp_path: Path):
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        movie = Movie(title="Preserved", relative_path="movie.mp4", file_extension=".mp4")
        session.add(movie)
        session.commit()
        try:
            scan_library(session, tmp_path / "locked")
        except FileNotFoundError:
            pass
        session.refresh(movie)
        assert movie.is_available is True


def test_scan_merges_case_variant_duplicate_records(tmp_path: Path):
    root = tmp_path / "vault"
    root.mkdir()
    (root / "Film.1080p.mp4").write_bytes(b"video")
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        first = Movie(title="Film", relative_path="film.1080p.mp4", file_extension=".mp4")
        second = Movie(title="Film duplicate", relative_path="Film.1080p.mp4", file_extension=".mp4", is_favorite=True)
        session.add(first)
        session.add(second)
        session.commit()
        result = scan_library(session, root)
        movies = session.exec(select(Movie)).all()
        assert result["duplicates_removed"] == 1
        assert len(movies) == 1
        assert movies[0].is_favorite is True
        assert movies[0].resolution == "1080p"


def test_scan_hides_identical_copies_in_different_folders(tmp_path: Path):
    root = tmp_path / "vault"
    first_dir = root / "first"
    second_dir = root / "second"
    first_dir.mkdir(parents=True)
    second_dir.mkdir()
    first = first_dir / "Same.Movie.1080p.mp4"
    second = second_dir / "Same.Movie.1080p.mp4"
    first.write_bytes(b"identical-video")
    second.write_bytes(b"identical-video")
    second.touch()
    first.touch()
    shared_time = first.stat().st_mtime_ns
    import os
    os.utime(second, ns=(shared_time, shared_time))
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        result = scan_library(session, root)
        movies = session.exec(select(Movie)).all()
        assert len(movies) == 1
        assert result["duplicates_skipped"] == 1
        movie_id = movies[0].id
        primary = root / movies[0].relative_path
        primary.unlink()
        assert scan_library(session, root)["removed"] == 0
        surviving = session.exec(select(Movie)).one()
        assert surviving.id == movie_id
        assert (root / surviving.relative_path).is_file()

