from pathlib import Path

from fastapi import HTTPException


def safe_movie_path(root: Path, relative_path: str, *, must_exist: bool = True) -> Path:
    root_resolved = root.resolve(strict=must_exist)
    supplied = Path(relative_path)
    candidate_unresolved = root_resolved / supplied
    # Check every supplied component before resolving, otherwise resolve() would
    # conceal a symlink that still points somewhere beneath the root.
    current = root_resolved
    for part in supplied.parts:
        current = current / part
        if current.is_symlink():
            raise HTTPException(status_code=403, detail="Symlinked movie paths are not allowed")
    candidate = candidate_unresolved.resolve(strict=must_exist)
    try:
        candidate.relative_to(root_resolved)
    except ValueError as exc:
        raise HTTPException(status_code=403, detail="Movie path escapes the configured library") from exc
    if not candidate.is_file():
        raise HTTPException(status_code=404, detail="Movie file is unavailable")
    return candidate

