from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.models.journey import Journey
from app.models.user import User
from app.schemas.journey import (
    JourneyCreate,
    JourneyResponse,
    JourneyUpdate,
    LocationInput,
)
from app.services.journey_service import (
    create_journey,
    delete_journey,
    get_journey,
    get_user_journeys,
    update_journey,
)


router = APIRouter(
    prefix="/journeys",
    tags=["Journeys"],
)


def journey_to_response(
    db: Session,
    journey: Journey,
) -> JourneyResponse:
    origin = db.execute(
        select(
            func.ST_Y(journey.origin),
            func.ST_X(journey.origin),
        )
    ).one()

    destination = db.execute(
        select(
            func.ST_Y(journey.destination),
            func.ST_X(journey.destination),
        )
    ).one()

    return JourneyResponse(
        id=journey.id,
        user_id=journey.user_id,
        origin=LocationInput(
            latitude=origin[0],
            longitude=origin[1],
        ),
        destination=LocationInput(
            latitude=destination[0],
            longitude=destination[1],
        ),
        departure_time=journey.departure_time,
        passengers=journey.passengers,
        luggage=journey.luggage,
        radius_km=journey.radius_km,
        status=journey.status,
        created_at=journey.created_at,
        updated_at=journey.updated_at,
    )


@router.post(
    "",
    response_model=JourneyResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_my_journey(
    request: JourneyCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    journey = create_journey(
        db=db,
        user_id=current_user.id,
        data=request,
    )

    return journey_to_response(db, journey)


@router.get(
    "",
    response_model=list[JourneyResponse],
)
def get_my_journeys(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    journeys = get_user_journeys(
        db=db,
        user_id=current_user.id,
    )

    return [
        journey_to_response(db, journey)
        for journey in journeys
    ]


@router.get(
    "/{journey_id}",
    response_model=JourneyResponse,
)
def get_my_journey(
    journey_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    journey = get_journey(
        db=db,
        journey_id=journey_id,
    )

    if journey is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Journey not found",
        )

    if journey.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this journey",
        )

    return journey_to_response(db, journey)


@router.patch(
    "/{journey_id}",
    response_model=JourneyResponse,
)
def update_my_journey(
    journey_id: UUID,
    request: JourneyUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    journey = get_journey(
        db=db,
        journey_id=journey_id,
    )

    if journey is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Journey not found",
        )

    if journey.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot modify this journey",
        )

    journey = update_journey(
        db=db,
        journey=journey,
        data=request,
    )

    return journey_to_response(db, journey)


@router.delete(
    "/{journey_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_my_journey(
    journey_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    journey = get_journey(
        db=db,
        journey_id=journey_id,
    )

    if journey is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Journey not found",
        )

    if journey.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot delete this journey",
        )

    delete_journey(
        db=db,
        journey=journey,
    )

    return None