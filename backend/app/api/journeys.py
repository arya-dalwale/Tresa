from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.models.journey import Journey
from app.models.journey_preference import JourneyPreference
from app.models.profile import Profile
from app.models.user import User
from app.schemas.journey import (
    JourneyCreate,
    JourneyResponse,
    JourneyUpdate,
    LocationInput,
)
from app.schemas.match import (
    IndividualMatchResponse,
    MatchScoreBreakdown,
    MatchesResponse,
    RecommendedGroupResponse,
)
from app.services.group_service import (
    MIN_GROUP_COMPATIBILITY,
    build_group_recommendations,
)
from app.services.journey_service import (
    create_journey,
    delete_journey,
    get_journey,
    get_user_journeys,
    update_journey,
)
from app.services.matching_service import (
    calculate_destination_distance,
    calculate_luggage_compatibility,
    calculate_origin_proximity,
    calculate_preference_score,
    calculate_time_compatibility,
    calculate_weighted_score,
    find_candidate_journeys,
    rank_candidates,
)


router = APIRouter(
    prefix="/journeys",
    tags=["Journeys"],
)


# ==========================================================
# EXISTING JOURNEY RESPONSE HELPER
# ==========================================================

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


# ==========================================================
# MATCHING API HELPERS
# ==========================================================

def _origin_distance_meters(
    db: Session,
    journey: Journey,
    candidate: Journey,
) -> float:
    """
    Return the actual PostGIS distance between two origins in meters.

    The result is used for the API's origin_distance_km field.
    It is not reconstructed from the normalized proximity score.
    """

    statement = select(
        Journey.origin.ST_Distance(candidate.origin)
    ).where(
        Journey.id == journey.id
    )

    distance_meters = db.scalar(statement)

    if distance_meters is None:
        raise ValueError(
            "Unable to calculate origin distance"
        )

    return float(distance_meters)


def _get_journey_preferences(
    db: Session,
    journey_id: UUID,
    preference_cache: dict[UUID, JourneyPreference | None],
) -> JourneyPreference | None:
    """Load and cache a journey's optional preferences."""

    if journey_id not in preference_cache:
        statement = select(JourneyPreference).where(
            JourneyPreference.journey_id == journey_id
        )

        preference_cache[journey_id] = db.scalar(statement)

    return preference_cache[journey_id]


def _calculate_component_scores(
    db: Session,
    journey: Journey,
    candidate: Journey,
    preference_cache: dict[UUID, JourneyPreference | None],
) -> dict[str, float | None]:
    """
    Calculate existing matching component scores for a journey pair.

    The destination score uses the approved V1 formula.
    Route overlap remains unavailable and is represented by None.
    """

    radius_meters = journey.radius_km * 1000.0

    if radius_meters <= 0:
        raise ValueError(
            "Journey radius_km must be greater than zero"
        )

    destination_distance_meters = calculate_destination_distance(
        db,
        journey,
        candidate,
    )

    # Approved V1 destination compatibility formula:
    # 1 - (destination distance / target search radius), clamped to 0..1.
    if destination_distance_meters >= radius_meters:
        destination_score = 0.0
    else:
        destination_score = max(
            0.0,
            min(
                1.0,
                1.0 - (
                    destination_distance_meters / radius_meters
                ),
            ),
        )

    time_score = calculate_time_compatibility(
        journey,
        candidate,
    )

    origin_score = calculate_origin_proximity(
        db,
        journey,
        candidate,
    )

    journey_preferences = _get_journey_preferences(
        db,
        journey.id,
        preference_cache,
    )

    candidate_preferences = _get_journey_preferences(
        db,
        candidate.id,
        preference_cache,
    )

    preference_score = calculate_preference_score(
        journey_preferences,
        candidate_preferences,
    )

    luggage_score = calculate_luggage_compatibility(
        journey,
        candidate,
    )

    return {
        "route": None,
        "destination": destination_score,
        "time": time_score,
        "origin_proximity": origin_score,
        "preferences": preference_score,
        "luggage": luggage_score,
    }


def _calculate_pairwise_compatibility(
    db: Session,
    left: Journey,
    right: Journey,
    preference_cache: dict[UUID, JourneyPreference | None],
) -> float:
    """
    Reuse existing component scoring and weighted scoring for group pairs.

    The UUID order is canonicalized so the same pair uses a consistent
    calculation regardless of which group candidate initiated formation.
    """

    if str(left.id) > str(right.id):
        left, right = right, left

    component_scores = _calculate_component_scores(
        db,
        left,
        right,
        preference_cache,
    )

    return calculate_weighted_score(component_scores)


# ==========================================================
# EXISTING JOURNEY CRUD ROUTES
# ==========================================================

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


# ==========================================================
# MATCHING API V1
# ==========================================================

@router.get(
    "/{journey_id}/matches",
    response_model=MatchesResponse,
)
def get_journey_matches(
    journey_id: UUID,
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
    offset: int = Query(
        default=0,
        ge=0,
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Return ranked individual journey matches and recommended groups.

    Requires Bearer JWT authentication and ownership of the target journey.

    Exact origin and destination coordinates are not included in the response.
    """

    # ------------------------------------------------------
    # 1. Retrieve the target journey and enforce ownership.
    # ------------------------------------------------------

    target_journey = get_journey(
        db=db,
        journey_id=journey_id,
    )

    if target_journey is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Journey not found",
        )

    if target_journey.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this journey",
        )

    # Cache preferences for reuse across individual and group scoring.
    preference_cache: dict[UUID, JourneyPreference | None] = {}

    # ------------------------------------------------------
    # 2. Retrieve candidates using the existing eligibility
    #    query, then explicitly guard status and origin radius.
    # ------------------------------------------------------

    discovered_candidates = find_candidate_journeys(
        db,
        target_journey,
    )

    eligible_candidates: list[Journey] = []

    component_scores_by_id: dict[
        UUID,
        dict[str, float | None],
    ] = {}

    compatibility_scores_by_id: dict[UUID, float] = {}

    origin_distances_by_id: dict[UUID, float] = {}

    target_radius_meters = target_journey.radius_km * 1000.0

    for candidate in discovered_candidates:
        # Do not let completed or cancelled journeys reach group formation.
        if candidate.status not in ("planned", "active"):
            continue

        # Use actual PostGIS distance to explicitly enforce the origin radius.
        actual_origin_distance_meters = _origin_distance_meters(
            db,
            target_journey,
            candidate,
        )

        if actual_origin_distance_meters > target_radius_meters:
            continue

        component_scores = _calculate_component_scores(
            db,
            target_journey,
            candidate,
            preference_cache,
        )

        compatibility_score = calculate_weighted_score(
            component_scores
        )

        eligible_candidates.append(candidate)

        component_scores_by_id[candidate.id] = component_scores
        compatibility_scores_by_id[candidate.id] = compatibility_score
        origin_distances_by_id[candidate.id] = (
            actual_origin_distance_meters
        )

    # ------------------------------------------------------
    # 3. Rank eligible individual matches using the existing
    #    ranking implementation.
    # ------------------------------------------------------

    ranked_ids_and_scores = rank_candidates(
        [
            (
                candidate.id,
                compatibility_scores_by_id[candidate.id],
            )
            for candidate in eligible_candidates
        ]
    )

    journeys_by_id = {
        candidate.id: candidate
        for candidate in eligible_candidates
    }

    ranked_candidates = [
        journeys_by_id[candidate_id]
        for candidate_id, _score in ranked_ids_and_scores
    ]

    # ------------------------------------------------------
    # 4. Build privacy-safe individual match responses.
    # ------------------------------------------------------

    individual_matches: list[IndividualMatchResponse] = []

    for candidate in ranked_candidates:
        profile_statement = select(Profile).where(
            Profile.user_id == candidate.user_id
        )

        profile = db.scalar(profile_statement)

        component_scores = component_scores_by_id[candidate.id]

        individual_matches.append(
            IndividualMatchResponse(
                journey_id=candidate.id,
                user_id=candidate.user_id,
                full_name=(
                    profile.full_name
                    if profile is not None
                    else None
                ),
                profile_photo_url=(
                    profile.profile_photo_url
                    if profile is not None
                    else None
                ),
                departure_time=candidate.departure_time,
                passengers=candidate.passengers,
                luggage=candidate.luggage,
                # Actual PostGIS distance in meters, converted to kilometers.
                origin_distance_km=(
                    origin_distances_by_id[candidate.id] / 1000.0
                ),
                compatibility_score=(
                    compatibility_scores_by_id[candidate.id]
                ),
                score_breakdown=MatchScoreBreakdown(
                    **component_scores
                ),
            )
        )

    # ------------------------------------------------------
    # 5. Filter candidates by pairwise matching eligibility
    #    before passing them to Group Recommendation V1.
    # ------------------------------------------------------

    def pairwise_compatibility(
        left: Journey,
        right: Journey,
    ) -> float:
        return _calculate_pairwise_compatibility(
            db,
            left,
            right,
            preference_cache,
        )

    group_eligible_candidates = [
        candidate
        for candidate in ranked_candidates
        if pairwise_compatibility(
            target_journey,
            candidate,
        ) >= MIN_GROUP_COMPATIBILITY
    ]

    # ------------------------------------------------------
    # 6. Reuse the existing Group Recommendation V1 service.
    # ------------------------------------------------------

    group_recommendations = build_group_recommendations(
        target_journey=target_journey,
        ranked_candidates=group_eligible_candidates,
        pairwise_compatibility=pairwise_compatibility,
    )

    recommended_groups = [
        RecommendedGroupResponse(
            members=recommendation.members,
            group_size=len(recommendation.members),
            total_passengers=recommendation.total_passengers,
            group_compatibility_score=recommendation.group_score,
            member_journey_ids=[
                member.journey_id
                for member in recommendation.members
            ],
        )
        for recommendation in group_recommendations
    ]

    # ------------------------------------------------------
    # 7. Apply pagination to both ranked response lists.
    #    Group formation itself uses the full eligible list.
    # ------------------------------------------------------

    paginated_matches = individual_matches[
        offset: offset + limit
    ]

    paginated_groups = recommended_groups[
        offset: offset + limit
    ]

    return MatchesResponse(
        matches=paginated_matches,
        groups=paginated_groups,
    )


# ==========================================================
# EXISTING JOURNEY UPDATE AND DELETE ROUTES
# ==========================================================

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