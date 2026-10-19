from itertools import combinations
from types import SimpleNamespace
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.schemas.group import GroupMember, GroupRecommendation
from app.services.group_service import (
    MAX_GROUP_PASSENGERS,
    MAX_GROUP_SIZE,
    MIN_GROUP_COMPATIBILITY,
    build_group_recommendations,
)


def make_journey(
    journey_number: int,
    *,
    user_number: int | None = None,
    passengers: int = 1,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=UUID(int=journey_number),
        user_id=UUID(int=user_number if user_number is not None else journey_number + 1000),
        passengers=passengers,
    )


def pair_key(left, right):
    return tuple(sorted((left.id, right.id), key=str))


def set_score(scores, left, right, value):
    scores[pair_key(left, right)] = value


def set_all_scores(scores, journeys, value):
    for left, right in combinations(journeys, 2):
        set_score(scores, left, right, value)


def scorer_for(scores):
    def score(left, right):
        return scores.get(pair_key(left, right), 0.0)

    return score


def member_ids(group):
    return {member.journey_id for member in group.members}


def test_returns_no_recommendation_when_there_are_no_candidates():
    target = make_journey(1)

    result = build_group_recommendations(target, [], scorer_for({}))

    assert result == []


def test_builds_two_member_group_for_compatible_candidate():
    target = make_journey(1)
    candidate = make_journey(2)
    scores = {}
    set_score(scores, target, candidate, 0.85)

    result = build_group_recommendations(target, [candidate], scorer_for(scores))

    assert len(result) == 1
    assert member_ids(result[0]) == {target.id, candidate.id}
    assert result[0].group_score == pytest.approx(0.85)
    assert result[0].total_passengers == 2


def test_pairwise_score_equal_to_threshold_is_accepted():
    target = make_journey(1)
    candidate = make_journey(2)
    scores = {}
    set_score(scores, target, candidate, MIN_GROUP_COMPATIBILITY)

    result = build_group_recommendations(target, [candidate], scorer_for(scores))

    assert len(result) == 1
    assert result[0].group_score == MIN_GROUP_COMPATIBILITY


def test_pairwise_score_below_threshold_is_rejected():
    target = make_journey(1)
    candidate = make_journey(2)
    scores = {}
    set_score(scores, target, candidate, MIN_GROUP_COMPATIBILITY - 0.01)

    result = build_group_recommendations(target, [candidate], scorer_for(scores))

    assert result == []


def test_every_candidate_must_be_compatible_with_every_group_member():
    target = make_journey(1)
    candidate_a = make_journey(2)
    candidate_b = make_journey(3)
    scores = {}
    set_score(scores, target, candidate_a, 0.9)
    set_score(scores, target, candidate_b, 0.9)
    set_score(scores, candidate_a, candidate_b, 0.59)

    result = build_group_recommendations(
        target,
        [candidate_a, candidate_b],
        scorer_for(scores),
    )

    assert all(not ({candidate_a.id, candidate_b.id} <= member_ids(group)) for group in result)
    assert any(member_ids(group) == {target.id, candidate_a.id} for group in result)
    assert any(member_ids(group) == {target.id, candidate_b.id} for group in result)


def test_candidate_excluded_from_one_combination_remains_eligible_for_another():
    target = make_journey(1)
    candidate_a = make_journey(2)
    candidate_b = make_journey(3)
    candidate_c = make_journey(4)
    scores = {}
    set_score(scores, target, candidate_a, 0.9)
    set_score(scores, target, candidate_b, 0.9)
    set_score(scores, target, candidate_c, 0.9)
    set_score(scores, candidate_a, candidate_b, 0.5)
    set_score(scores, candidate_a, candidate_c, 0.5)
    set_score(scores, candidate_b, candidate_c, 0.9)

    result = build_group_recommendations(
        target,
        [candidate_a, candidate_b, candidate_c],
        scorer_for(scores),
    )

    assert any(
        member_ids(group) == {target.id, candidate_b.id, candidate_c.id}
        for group in result
    )


def test_group_score_is_average_of_all_pairwise_scores():
    target = make_journey(1)
    candidate_a = make_journey(2)
    candidate_b = make_journey(3)
    scores = {}
    set_score(scores, target, candidate_a, 0.9)
    set_score(scores, target, candidate_b, 0.8)
    set_score(scores, candidate_a, candidate_b, 0.7)

    result = build_group_recommendations(
        target,
        [candidate_a, candidate_b],
        scorer_for(scores),
    )

    three_member_group = next(group for group in result if len(group.members) == 3)
    assert three_member_group.group_score == pytest.approx((0.9 + 0.8 + 0.7) / 3)


def test_total_passenger_capacity_is_enforced_and_candidate_can_form_another_group():
    target = make_journey(1, passengers=4)
    candidate_a = make_journey(2, passengers=1)
    candidate_b = make_journey(3, passengers=1)
    scores = {}
    set_all_scores(scores, [target, candidate_a, candidate_b], 0.9)

    result = build_group_recommendations(
        target,
        [candidate_a, candidate_b],
        scorer_for(scores),
    )

    assert result
    assert all(group.total_passengers <= MAX_GROUP_PASSENGERS for group in result)
    assert any(member_ids(group) == {target.id, candidate_a.id} for group in result)
    assert any(member_ids(group) == {target.id, candidate_b.id} for group in result)
    assert all(len(group.members) == 2 for group in result)


def test_group_never_exceeds_five_members():
    target = make_journey(1)
    candidates = [make_journey(number) for number in range(2, 9)]
    scores = {}
    set_all_scores(scores, [target, *candidates], 0.9)

    result = build_group_recommendations(target, candidates, scorer_for(scores))

    assert result
    assert max(len(group.members) for group in result) == MAX_GROUP_SIZE
    assert all(len(group.members) <= MAX_GROUP_SIZE for group in result)


def test_no_group_contains_duplicate_journey_or_user():
    target = make_journey(1, user_number=100)
    candidate_a = make_journey(2, user_number=200)
    candidate_b = make_journey(3, user_number=200)
    candidate_c = make_journey(4, user_number=400)
    candidate_same_as_target_user = make_journey(5, user_number=100)
    candidates = [candidate_a, candidate_b, candidate_c, candidate_same_as_target_user]
    scores = {}
    set_all_scores(scores, [target, *candidates], 0.9)

    result = build_group_recommendations(target, candidates, scorer_for(scores))

    assert result
    for group in result:
        journey_ids = [member.journey_id for member in group.members]
        user_ids = [member.user_id for member in group.members]
        assert len(journey_ids) == len(set(journey_ids))
        assert len(user_ids) == len(set(user_ids))


def test_group_ranking_uses_score_before_group_size():
    target = make_journey(1)
    candidate_a = make_journey(2)
    candidate_b = make_journey(3)
    scores = {}
    candidate_c = make_journey(4)
    set_score(scores, target, candidate_a, 0.9)
    set_score(scores, target, candidate_b, 0.7)
    set_score(scores, target, candidate_c, 0.7)
    set_score(scores, candidate_a, candidate_b, 0.59)
    set_score(scores, candidate_a, candidate_c, 0.59)
    set_score(scores, candidate_b, candidate_c, 0.7)

    result = build_group_recommendations(
        target,
        [candidate_a, candidate_b, candidate_c],
        scorer_for(scores),
    )

    assert result[0].group_score > result[1].group_score
    assert len(result[0].members) == 2
    assert len(result[1].members) == 3


def test_equal_scores_rank_larger_groups_first():
    target = make_journey(1)
    candidate_a, candidate_b, candidate_c = [
        make_journey(number) for number in (2, 3, 4)
    ]
    scores = {}
    set_score(scores, target, candidate_a, 0.8)
    set_score(scores, target, candidate_b, 0.8)
    set_score(scores, target, candidate_c, 0.8)
    set_score(scores, candidate_a, candidate_b, 0.59)
    set_score(scores, candidate_a, candidate_c, 0.59)
    set_score(scores, candidate_b, candidate_c, 0.8)

    result = build_group_recommendations(
        target, [candidate_a, candidate_b, candidate_c], scorer_for(scores)
    )

    assert len(result) >= 2
    assert all(group.group_score == pytest.approx(0.8) for group in result)
    sizes = [len(group.members) for group in result]
    assert sizes == sorted(sizes, reverse=True)


def test_equal_score_and_size_use_deterministic_uuid_ordering():
    target = make_journey(1)
    candidates = [make_journey(number) for number in (4, 2, 3)]
    scores = {}
    for candidate in candidates:
        set_score(scores, target, candidate, 0.8)
    for left, right in combinations(candidates, 2):
        set_score(scores, left, right, 0.1)

    result = build_group_recommendations(target, candidates, scorer_for(scores))

    recommendation_keys = [
        tuple(sorted(str(member.journey_id) for member in group.members))
        for group in result
    ]
    assert recommendation_keys == sorted(recommendation_keys)


def test_invalid_pairwise_score_is_rejected():
    target = make_journey(1)
    candidate = make_journey(2)

    with pytest.raises(ValueError, match="between 0.0 and 1.0"):
        build_group_recommendations(
            target,
            [candidate],
            lambda _left, _right: 1.01,
        )


def test_target_over_passenger_capacity_returns_no_recommendation():
    target = make_journey(1, passengers=6)
    candidate = make_journey(2)

    result = build_group_recommendations(
        target,
        [candidate],
        lambda _left, _right: 1.0,
    )

    assert result == []


def test_group_schema_rejects_duplicate_users():
    user_id = UUID(int=200)
    with pytest.raises(ValidationError, match="duplicate users"):
        GroupRecommendation(
            members=[
                GroupMember(journey_id=UUID(int=1), user_id=user_id, passengers=1),
                GroupMember(journey_id=UUID(int=2), user_id=user_id, passengers=1),
            ],
            group_score=0.8,
            total_passengers=2,
        )


def test_group_schema_rejects_incorrect_total_passengers():
    with pytest.raises(ValidationError, match="total_passengers"):
        GroupRecommendation(
            members=[
                GroupMember(journey_id=UUID(int=1), user_id=UUID(int=101), passengers=2),
                GroupMember(journey_id=UUID(int=2), user_id=UUID(int=102), passengers=1),
            ],
            group_score=0.8,
            total_passengers=2,
        )
