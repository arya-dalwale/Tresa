from collections.abc import Callable, Sequence
from decimal import Decimal
from itertools import combinations
from math import isfinite
from uuid import UUID

from app.models.journey import Journey
from app.schemas.group import GroupMember, GroupRecommendation


MIN_GROUP_SIZE = 2
MAX_GROUP_SIZE = 5
MAX_GROUP_PASSENGERS = 5
MIN_GROUP_COMPATIBILITY = 0.60


JourneyPairwiseScorer = Callable[[Journey, Journey], float]
JourneyDetails = tuple[UUID, UUID, int]
PairKey = tuple[UUID, UUID]


def _journey_details(journey: Journey) -> JourneyDetails:
    """Validate and extract the fields needed for a group recommendation."""
    journey_id = getattr(journey, "id", None)
    user_id = getattr(journey, "user_id", None)
    passengers = getattr(journey, "passengers", None)

    if not isinstance(journey_id, UUID):
        raise ValueError("Every journey must have a valid UUID id")
    if not isinstance(user_id, UUID):
        raise ValueError("Every journey must have a valid UUID user_id")
    if isinstance(passengers, bool) or not isinstance(passengers, int) or passengers < 1:
        raise ValueError("Journey passengers must be a positive integer")

    return journey_id, user_id, passengers


def _pair_key(left_id: UUID, right_id: UUID) -> PairKey:
    """Return an order-independent key for a pair of journey IDs."""
    return tuple(sorted((left_id, right_id), key=str))  # type: ignore[return-value]


def build_group_recommendations(
    target_journey: Journey,
    ranked_candidates: Sequence[Journey],
    pairwise_compatibility: JourneyPairwiseScorer,
) -> list[GroupRecommendation]:
    """Build deterministic greedy groups for an already-matched journey.

    ``ranked_candidates`` must contain only candidates that have passed the
    existing matching eligibility pipeline, already ordered by the existing
    matching ranker. This function deliberately does not repeat or change
    candidate filtering, component scoring, weighted scoring, or ranking.

    ``pairwise_compatibility`` must return the existing normalized pairwise
    compatibility score (0.0 to 1.0) for two journeys. Pairwise scores are
    treated as symmetric; the callback is called in a canonical UUID order
    and its result is cached for consistent formation and scoring.

    The target journey is included in each recommendation. Each seed candidate
    starts a greedy combination; candidates are considered in ranked order.
    Candidates rejected from one combination can still join other combinations.
    """
    target_id, target_user_id, target_passengers = _journey_details(target_journey)
    if target_passengers > MAX_GROUP_PASSENGERS:
        return []

    candidate_details = [_journey_details(candidate) for candidate in ranked_candidates]
    pair_score_cache: dict[PairKey, float] = {}

    def get_pairwise_score(left: Journey, right: Journey) -> float:
        left_id = _journey_details(left)[0]
        right_id = _journey_details(right)[0]
        key = _pair_key(left_id, right_id)
        if key not in pair_score_cache:
            # Use canonical order so results do not depend on which group was seeded first.
            first, second = (left, right) if str(left_id) <= str(right_id) else (right, left)
            raw_score = pairwise_compatibility(first, second)
            if (
                isinstance(raw_score, bool)
                or not isinstance(raw_score, (int, float))
                or not isfinite(float(raw_score))
                or not 0.0 <= float(raw_score) <= 1.0
            ):
                raise ValueError(
                    "Pairwise compatibility must be a finite score between 0.0 and 1.0"
                )
            pair_score_cache[key] = float(raw_score)
        return pair_score_cache[key]

    recommendations_by_members: dict[tuple[UUID, ...], GroupRecommendation] = {}

    for seed_index, seed in enumerate(ranked_candidates):
        seed_id, seed_user_id, seed_passengers = candidate_details[seed_index]

        # A group always includes the target; it cannot contain the same journey
        # or user twice, and the seed must fit and be compatible with the target.
        if seed_id == target_id or seed_user_id == target_user_id:
            continue
        if seed_passengers > MAX_GROUP_PASSENGERS:
            continue
        if target_passengers + seed_passengers > MAX_GROUP_PASSENGERS:
            continue
        if get_pairwise_score(target_journey, seed) < MIN_GROUP_COMPATIBILITY:
            continue

        group_members: list[Journey] = [target_journey, seed]
        group_total_passengers = target_passengers + seed_passengers

        # Revisit the full ranked sequence for each seed. This allows a candidate
        # rejected from one combination to participate in a different one.
        for candidate_index, candidate in enumerate(ranked_candidates):
            if candidate_index == seed_index:
                continue
            if len(group_members) >= MAX_GROUP_SIZE:
                break

            candidate_id, candidate_user_id, candidate_passengers = candidate_details[candidate_index]
            if candidate_id == target_id or candidate_user_id == target_user_id:
                continue
            if any(
                existing_details[0] == candidate_id
                or existing_details[1] == candidate_user_id
                for existing_details in (
                    _journey_details(member) for member in group_members
                )
            ):
                continue
            if candidate_passengers > MAX_GROUP_PASSENGERS:
                continue
            if group_total_passengers + candidate_passengers > MAX_GROUP_PASSENGERS:
                continue

            # A candidate must meet the threshold with every current member.
            compatibility_scores = [
                get_pairwise_score(existing_member, candidate)
                for existing_member in group_members
            ]
            if any(score < MIN_GROUP_COMPATIBILITY for score in compatibility_scores):
                continue

            group_members.append(candidate)
            group_total_passengers += candidate_passengers

        if len(group_members) < MIN_GROUP_SIZE:
            continue

        all_pair_scores = [
            get_pairwise_score(left, right)
            for left, right in combinations(group_members, 2)
        ]
        # Decimal averaging avoids tiny binary-float differences changing the
        # required secondary/UUID ranking when the mathematical scores are equal.
        group_score = float(
            sum((Decimal(str(score)) for score in all_pair_scores), Decimal("0"))
            / Decimal(len(all_pair_scores))
        )

        members = [
            GroupMember(
                journey_id=journey_id,
                user_id=user_id,
                passengers=passengers,
            )
            for journey_id, user_id, passengers in (
                _journey_details(member) for member in group_members
            )
        ]
        recommendation = GroupRecommendation(
            members=members,
            group_score=group_score,
            total_passengers=group_total_passengers,
        )

        # Canonical set keys remove duplicates formed by different greedy seeds.
        group_key = tuple(sorted((member.journey_id for member in members), key=str))
        recommendations_by_members.setdefault(group_key, recommendation)

    return sorted(
        recommendations_by_members.values(),
        key=lambda recommendation: (
            -recommendation.group_score,
            -len(recommendation.members),
            tuple(sorted(str(member.journey_id) for member in recommendation.members)),
        ),
    )
