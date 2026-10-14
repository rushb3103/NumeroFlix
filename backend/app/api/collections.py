from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.core.database import get_session
from app.models import Collection, Movie
from app.schemas import CollectionCreate, MembershipUpdate

router = APIRouter(prefix="/collections", tags=["collections"])


def serialize_collection(item: Collection) -> dict:
    return {**item.model_dump(), "movie_count": len(item.movies)}


@router.get("")
def list_collections(session: Session = Depends(get_session)):
    return [serialize_collection(item) for item in session.exec(select(Collection).order_by(Collection.name)).all()]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_collection(payload: CollectionCreate, session: Session = Depends(get_session)):
    item = Collection(**payload.model_dump())
    session.add(item)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status_code=409, detail="A collection with that name already exists") from exc
    session.refresh(item)
    return serialize_collection(item)


@router.put("/{collection_id}")
def update_collection(collection_id: int, payload: CollectionCreate, session: Session = Depends(get_session)):
    item = session.get(Collection, collection_id)
    if not item:
        raise HTTPException(status_code=404, detail="Collection not found")
    item.name, item.description = payload.name, payload.description
    session.add(item)
    session.commit()
    session.refresh(item)
    return serialize_collection(item)


@router.post("/{collection_id}/movies")
def add_movies(collection_id: int, payload: MembershipUpdate, session: Session = Depends(get_session)):
    item = session.get(Collection, collection_id)
    if not item:
        raise HTTPException(status_code=404, detail="Collection not found")
    movies = session.exec(select(Movie).where(Movie.id.in_(payload.movie_ids))).all()
    existing = {movie.id for movie in item.movies}
    item.movies.extend(movie for movie in movies if movie.id not in existing)
    session.add(item)
    session.commit()
    return serialize_collection(item)


@router.delete("/{collection_id}/movies/{movie_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_movie(collection_id: int, movie_id: int, session: Session = Depends(get_session)):
    item = session.get(Collection, collection_id)
    if not item:
        raise HTTPException(status_code=404, detail="Collection not found")
    item.movies = [movie for movie in item.movies if movie.id != movie_id]
    session.add(item)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/{collection_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_collection(collection_id: int, session: Session = Depends(get_session)):
    item = session.get(Collection, collection_id)
    if not item:
        raise HTTPException(status_code=404, detail="Collection not found")
    session.delete(item)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

