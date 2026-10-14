from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine, select

from app.models import Movie, Tag
from app.services.scanner import scan_library, title_from_filename


def test_title_parsing():
    assert title_from_filename(Path("The.Matrix.1999.1080p.mkv")) == ("The Matrix", 1999)


def test_scan_is_incremental_and_preserves_metadata(tmp_path: Path):
    root = tmp_path / "vault"
    root.mkdir()
    first = root / "Arrival.2016.mkv"
    first.write_bytes(b"not-real-video")
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        result = scan_library(session, root)
        assert result["discovered"] == 1
        movie = session.exec(select(Movie)).one()
        movie.tags.append(Tag(name="Thoughtful"))
        session.add(movie)
        session.commit()
        assert scan_library(session, root)["discovered"] == 0
        session.refresh(movie)
        assert movie.tags[0].name == "Thoughtful"
        first.unlink()
        scan_library(session, root)
        session.refresh(movie)
        assert movie.is_available is False


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

