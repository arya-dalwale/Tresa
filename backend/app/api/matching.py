from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.models.journey import Journey
from app.models.journey_preference import JourneyPreference
from app.models.profile import Profile
from app.models.user import User
from app.schemas.group import GroupRecommendation
from app.schemas.match import (
    MatchListResponse,
    MatchResponse,
    MatchScoreBreakdown,
)
from app.services.group_service import build_group_recommendations
from app.services.journey_service import get_journey
from app.services.matching_service import (
    calculate_destination_distance,
    calculate_luggage_compatibility,
    calculate_match_score,
    calculate_origin_proximity,
    calculate_preference_score,
    calculate_time_compatibility,
    find_candidate_journeys,
    rank_candidates,
)


router = APIRouter(
    prefix="/journeys",
    tags=["Matching"],
)


def get_journey_preference(
    db: Session,
    journey_id: UUID,
) -> JourneyPreference | None:
    return db.scalar(
        select(JourneyPreference).where(
            JourneyPreference.journey_id == journey_id
        )
    )


def calculate_destination_score(
    db: Session,
    journey: Journey,
    candidate: Journey,
) -> float:
    """
    V1 destination compatibility.

    Same destination = 1.0.

    At or beyond the target journey's radius = 0.0.

    Between those points, the score decreases linearly.
    """

    distance_meters = calculate_destination_distance(
        db=db,
        journey=journey,
        candidate=candidate,
    )

    max_distance_meters = journey.radius_km * 1000

    if max_distance_meters <= 0:
        raise ValueError(
            "Journey radius_km must be greater than zero"
        )

    if distance_meters >= max_distance_meters:
        return 0.0

    score = 1.0 - (
        distance_meters / max_distance_meters
    )

    return max(
        0.0,
        min(1.0, score),
    )


def calculate_directional_match(
    db: Session,
    journey: Journey,
    candidate: Journey,
) -> tuple[float, dict[str, float | None]]:
    """
    Calculate the V1 matching score from one journey's
    perspective toward another journey.
    """

    journey_preferences = get_journey_preference(
        db=db,
        journey_id=journey.id,
    )

    candidate_preferences = get_journey_preference(
        db=db,
        journey_id=candidate.id,
    )

    destination = calculate_destination_score(
        db=db,
        journey=journey,
        candidate=candidate,
    )

    time = calculate_time_compatibility(
        journey=journey,
        candidate=candidate,
    )

    origin_proximity = calculate_origin_proximity(
        db=db,
        journey=journey,
        candidate=candidate,
    )

    preferences = calculate_preference_score(
        journey_preferences=journey_preferences,
        candidate_preferences=candidate_preferences,
    )

    luggage = calculate_luggage_compatibility(
        journey=journey,
        candidate=candidate,
    )

    component_scores = {
        "route": None,
        "destination": destination,
        "time": time,
        "origin_proximity": origin_proximity,
        "preferences": preferences,
        "luggage": luggage,
    }

    final_score = calculate_match_score(
        component_scores
    )

    return final_score, component_scores


def is_eligible_candidate(
    score: float,
    breakdown: dict[str, float | None],
) -> bool:
    """
    Apply V1 matching eligibility before ranking
    and group recommendation.

    Route is intentionally excluded because it is
    unavailable in the current Journey model.

    Required matching components must have a positive
    compatibility score.
    """

    required_components = (
        "destination",
        "time",
        "origin_proximity",
        "preferences",
        "luggage",
    )

    if score <= 0.0:
        return False

    for component in required_components:
        component_score = breakdown.get(component)

        if component_score is None:
            return False

        if component_score <= 0.0:
            return False

    return True


def calculate_pairwise_compatibility(
    db: Session,
    left: Journey,
    right: Journey,
) -> float:
    """
    Produce a symmetric pairwise compatibility score
    for group formation.
    """

    left_score, _ = calculate_directional_match(
        db=db,
        journey=left,
        candidate=right,
    )

    right_score, _ = calculate_directional_match(
        db=db,
        journey=right,
        candidate=left,
    )

    return (left_score + right_score) / 2.0


def calculate_origin_distance_km(
    db: Session,
    journey: Journey,
    candidate: Journey,
) -> float:
    """
    Calculate the actual origin distance in kilometers
    using the Journey Geography column.

    Exact coordinates are not exposed in the API response.
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

    return float(distance_meters) / 1000.0


def build_match_response(
    db: Session,
    target: Journey,
    candidate: Journey,
    score: float,
    breakdown: dict[str, float | None],
) -> MatchResponse:
    profile = db.scalar(
        select(Profile).where(
            Profile.user_id == candidate.user_id
        )
    )

    origin_distance_km = calculate_origin_distance_km(
        db=db,
        journey=target,
        candidate=candidate,
    )

    return MatchResponse(
        journey_id=candidate.id,
        user_id=candidate.user_id,
        full_name=(
            profile.full_name
            if profile
            else None
        ),
        profile_photo_url=(
            profile.profile_photo_url
            if profile
            else None
        ),
        departure_time=candidate.departure_time,
        passengers=candidate.passengers,
        luggage=candidate.luggage,
        origin_distance_km=origin_distance_km,
        compatibility_score=score,
        score_breakdown=MatchScoreBreakdown(
            **breakdown
        ),
    )


@router.get(
    "/{journey_id}/matches",
    response_model=MatchListResponse,
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
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db),
):
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

    candidates = find_candidate_journeys(
        db=db,
        journey=target_journey,
    )

    scored_candidates: list[
        tuple[UUID, float]
    ] = []

    candidate_scores: dict[
        UUID,
        tuple[
            float,
            dict[str, float | None],
        ],
    ] = {}

    eligible_candidates: list[Journey] = []

    for candidate in candidates:
        score, breakdown = calculate_directional_match(
            db=db,
            journey=target_journey,
            candidate=candidate,
        )

        if not is_eligible_candidate(
            score=score,
            breakdown=breakdown,
        ):
            continue

        scored_candidates.append(
            (candidate.id, score)
        )

        candidate_scores[candidate.id] = (
            score,
            breakdown,
        )

        eligible_candidates.append(candidate)

    ranked_ids = rank_candidates(
        scored_candidates
    )

    candidate_by_id = {
        candidate.id: candidate
        for candidate in eligible_candidates
    }

    ranked_candidates = [
        candidate_by_id[candidate_id]
        for candidate_id, _ in ranked_ids
    ]

    matches = [
        build_match_response(
            db=db,
            target=target_journey,
            candidate=candidate,
            score=candidate_scores[
                candidate.id
            ][0],
            breakdown=candidate_scores[
                candidate.id
            ][1],
        )
        for candidate in ranked_candidates
    ]

    pairwise_cache: dict[
        tuple[UUID, UUID],
        float,
    ] = {}

    def pairwise_compatibility(
        left: Journey,
        right: Journey,
    ) -> float:
        key = tuple(
            sorted(
                (left.id, right.id),
                key=str,
            )
        )

        if key not in pairwise_cache:
            pairwise_cache[key] = (
                calculate_pairwise_compatibility(
                    db=db,
                    left=left,
                    right=right,
                )
            )

        return pairwise_cache[key]

    groups: list[GroupRecommendation] = (
        build_group_recommendations(
            target_journey=target_journey,
            ranked_candidates=ranked_candidates,
            pairwise_compatibility=pairwise_compatibility,
        )
    )

    paginated_matches = matches[
        offset: offset + limit
    ]

    return MatchListResponse(
        journey_id=target_journey.id,
        matches=paginated_matches,
        groups=groups,
        total=len(matches),
        limit=limit,
        offset=offset,
    )