"""Tests for tournament bracket generation (``tournaments/utils.py``).

``TournamentRandomizer`` is the machinery behind "Generate Matches": it seeds
approved registrations into round-robin groups or elimination brackets. The
pairings are randomised, so the tests assert structural invariants (who plays
whom, how many times, how the bracket is linked) rather than exact opponents.

Note: elimination round labels are one round behind the actual round (the
second round of a singles bracket is also labelled ``round_of_16`` and the
final match is labelled ``quarter_final``) — asserted as-is for behaviour
parity, since views/templates rely on these values.
"""

from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from accounts.models import User
from tournaments.models import Match, Registration, Team, Tournament
from tournaments.utils import TournamentRandomizer


def make_tournament(**overrides):
    """A singles round-robin tournament that is allowed to generate matches."""
    now = timezone.now()
    payload = {
        'name': 'Test Cup', 'category': 'singles', 'format': 'round_robin',
        'skill_level': 'all_levels',
        'registration_start': now - timedelta(days=1),
        'registration_end': now + timedelta(days=1),
        'tournament_start': now + timedelta(days=7),
        'max_participants': 32, 'min_participants': 4,
        'players_per_group': 4,
    }
    payload.update(overrides)
    return Tournament.objects.create(**payload)


def register(tournament, username, status='approved'):
    user = User.objects.create_user(username=username, password='Str0ng-Pickle-Pass!')
    return Registration.objects.create(
        tournament=tournament, user=user, status=status,
        skill_level=tournament.skill_level,
    )


def approved(tournament, usernames):
    return [register(tournament, name) for name in usernames]


class CanGenerateMatchesTests(TestCase):
    def setUp(self):
        self.tournament = make_tournament(min_participants=4)

    def test_fewer_approved_registrations_than_the_minimum_is_refused(self):
        approved(self.tournament, ['p1', 'p2', 'p3'])

        self.assertFalse(self.tournament.can_generate_matches())

    def test_enough_approved_registrations_unlocks_match_generation(self):
        approved(self.tournament, ['p1', 'p2', 'p3', 'p4'])

        self.assertTrue(self.tournament.can_generate_matches())

    def test_pending_registrations_do_not_count_towards_the_minimum(self):
        approved(self.tournament, ['p1', 'p2', 'p3'])
        register(self.tournament, 'latecomer', status='pending')

        self.assertFalse(self.tournament.can_generate_matches())

    def test_rejected_and_withdrawn_registrations_do_not_count_either(self):
        register(self.tournament, 'reject', status='rejected')
        register(self.tournament, 'quitter', status='withdrawn')
        approved(self.tournament, ['p1', 'p2', 'p3', 'p4'])

        self.assertTrue(self.tournament.can_generate_matches())


class RoundRobinSinglesTests(TestCase):
    def setUp(self):
        self.tournament = make_tournament(format='round_robin', players_per_group=4)

    def test_every_player_plays_every_other_player_once(self):
        approved(self.tournament, ['p1', 'p2', 'p3', 'p4'])

        matches = TournamentRandomizer.create_singles_matches(self.tournament)

        self.assertEqual(len(matches), 6)  # 4 choose 2
        pairs = {frozenset((m.player1_id, m.player2_id)) for m in matches}
        self.assertEqual(len(pairs), 6)
        for match in matches:
            self.assertEqual(match.round_name, 'group_stage')
            self.assertEqual(match.status, 'scheduled')
            self.assertEqual(match.tournament, self.tournament)

    def test_players_are_split_into_named_groups_when_the_field_is_large(self):
        approved(self.tournament, [f'p{i}' for i in range(1, 7)])

        TournamentRandomizer.create_singles_matches(self.tournament)

        groups = set(
            Match.objects.filter(tournament=self.tournament)
            .values_list('group_name', flat=True)
        )
        self.assertEqual(groups, {'A', 'B'})
        for match in Match.objects.filter(tournament=self.tournament):
            qs = Match.objects.filter(
                tournament=self.tournament, group_name=match.group_name,
            )
            group_players = set(qs.values_list('player1_id', flat=True))
            group_players.update(qs.values_list('player2_id', flat=True))
            self.assertLessEqual(len(group_players), 4)  # players_per_group

    def test_unapproved_registrations_never_get_matches(self):
        register(self.tournament, 'waitlisted', status='pending')
        approved(self.tournament, ['in1', 'in2', 'in3', 'in4'])

        TournamentRandomizer.create_singles_matches(self.tournament)

        player_ids = set()
        for match in Match.objects.filter(tournament=self.tournament):
            player_ids.update([match.player1_id, match.player2_id])
        self.assertNotIn(
            User.objects.get(username='waitlisted').id, player_ids,
        )


class SingleEliminationSinglesTests(TestCase):
    def setUp(self):
        self.tournament = make_tournament(format='single_elimination')

    def test_eight_players_produce_all_bracket_rounds(self):
        approved(self.tournament, [f'p{i}' for i in range(1, 9)])

        matches = TournamentRandomizer.create_singles_matches(self.tournament)

        self.assertEqual(len(matches), 7)  # 4 first round + 2 + 1
        first_round = Match.objects.filter(
            tournament=self.tournament, round_name='round_of_16',
        )
        # Off-by-one quirk kept for behaviour parity: the round_names list is
        # indexed one round late, so the second round is ALSO labelled
        # 'round_of_16' and the final match is labelled 'quarter_final'.
        self.assertEqual(first_round.count(), 6)  # 4 seeded + 2 placeholders
        finals = Match.objects.filter(tournament=self.tournament, round_name='quarter_final')
        self.assertEqual(finals.count(), 1)
        self.assertEqual(
            Match.objects.filter(tournament=self.tournament).count(), 7,
        )

    def test_first_round_pairings_cover_every_player_exactly_once(self):
        players = [register(self.tournament, f'p{i}').user for i in range(1, 9)]

        TournamentRandomizer.create_singles_matches(self.tournament)

        seeded_round = Match.objects.filter(
            tournament=self.tournament, round_name='round_of_16',
            player1__isnull=False, player2__isnull=False,
        )
        self.assertEqual(seeded_round.count(), 4)
        seeded = set()
        for match in seeded_round:
            seeded.update([match.player1_id, match.player2_id])
        self.assertEqual(seeded, {p.id for p in players})

    def test_first_round_winners_feed_the_rest_of_the_bracket(self):
        approved(self.tournament, [f'p{i}' for i in range(1, 9)])

        TournamentRandomizer.create_singles_matches(self.tournament)

        first_round = Match.objects.filter(
            tournament=self.tournament, round_name='round_of_16',
            player1__isnull=False, player2__isnull=False,
        )
        later = Match.objects.filter(tournament=self.tournament).exclude(
            id__in=first_round,
        )
        self.assertEqual(first_round.count(), 4)
        self.assertEqual(later.count(), 3)
        for match in first_round:
            self.assertIsNotNone(match.next_match_id)
            self.assertEqual(match.next_match.tournament, self.tournament)
        # First round feeds the two semis; the semis feed the final.
        first_targets = {match.next_match_id for match in first_round}
        self.assertEqual(
            first_targets,
            set(later.exclude(round_name='quarter_final').values_list('id', flat=True)),
        )
        final = Match.objects.get(tournament=self.tournament, round_name='quarter_final')
        # The semis share the 'round_of_16' label with round 1 (off-by-one
        # quirk), so identify them by exclusion instead of by round name.
        semis = later.exclude(round_name='quarter_final')
        self.assertEqual(semis.count(), 2)
        self.assertEqual({m.next_match_id for m in semis}, {final.id})

    def test_bye_players_skip_the_first_round(self):
        players = [register(self.tournament, f'p{i}').user for i in range(1, 7)]  # 6

        TournamentRandomizer.create_singles_matches(self.tournament)

        seeded_round = Match.objects.filter(
            tournament=self.tournament, round_name='round_of_16',
            player1__isnull=False, player2__isnull=False,
        )
        self.assertEqual(seeded_round.count(), 2)  # 8-slot bracket, 6 players
        seeded = set()
        for match in seeded_round:
            seeded.update([match.player1_id, match.player2_id])
        self.assertEqual(len(seeded), 4)  # only non-bye players get first-round matches
        placeholders = Match.objects.filter(
            tournament=self.tournament,
            player1__isnull=True, player2__isnull=True,
        )
        # 2 first-round matches + 1 final placeholder; the 2 byes sit behind
        # the two winners, so only the empty final exists at this stage.
        self.assertEqual(placeholders.count(), 1)


class KingQueenSinglesTests(TestCase):
    def setUp(self):
        self.tournament = make_tournament(format='king_queen')

    def test_only_approved_players_are_paired_in_the_first_rotation(self):
        approved(self.tournament, ['p1', 'p2', 'p3', 'p4', 'p5'])
        register(self.tournament, 'waitlisted', status='pending')

        matches = TournamentRandomizer.create_singles_matches(self.tournament)

        player_ids = set()
        for match in matches:
            self.assertEqual(match.round_name, 'qualifier')
            self.assertEqual(match.status, 'scheduled')
            self.assertIsNotNone(match.player1_id)
            self.assertIsNotNone(match.player2_id)
            player_ids.update([match.player1_id, match.player2_id])
        # Odd fields leave the last shuffled player unpaired in round 1.
        self.assertEqual(len(player_ids), 4)
        self.assertNotIn(
            User.objects.get(username='waitlisted').id, player_ids,
        )


class DoublesTeamGenerationTests(TestCase):
    def setUp(self):
        self.tournament = make_tournament(
            category='doubles', format='round_robin', players_per_group=4,
        )

    def test_random_teaming_pairs_players_two_by_two_and_links_registrations(self):
        players = [register(self.tournament, f'd{i}').user for i in range(1, 7)]  # 6 -> 3 teams

        TournamentRandomizer.create_doubles_matches(self.tournament)

        teams = list(Team.objects.filter(tournament=self.tournament))
        self.assertEqual(len(teams), 3)
        paired_ids = set()
        for team in teams:
            self.assertIsNotNone(team.player2_id)
            self.assertTrue(team.is_auto_assigned)
            paired_ids.update([team.player1_id, team.player2_id])
        self.assertEqual(paired_ids, {p.id for p in players})
        for player in players:
            registration = Registration.objects.get(tournament=self.tournament, user=player)
            self.assertIsNotNone(registration.team_id)

    def test_round_robin_doubles_gives_every_team_a_match_against_each_other(self):
        approved(self.tournament, [f'd{i}' for i in range(1, 5)])  # 4 players -> 2 teams

        matches = TournamentRandomizer.create_doubles_matches(self.tournament)

        # Returns matches, not teams; 2 teams face each other once.
        self.assertEqual(len(matches), 1)
        match = matches[0]
        self.assertEqual(match.round_name, 'group_stage')
        self.assertEqual(match.status, 'scheduled')
        self.assertIsNotNone(match.team1_id)
        self.assertIsNotNone(match.team2_id)
        self.assertEqual(Team.objects.filter(tournament=self.tournament).count(), 2)


class FormatDispatchTests(TestCase):
    def test_every_supported_singles_format_creates_matches(self):
        for fmt, count in (
            ('round_robin', 6), ('single_elimination', 3), ('king_queen', 2),
            ('double_elimination', 3),  # winners bracket == single elimination
        ):
            with self.subTest(format=fmt):
                tournament = make_tournament(
                    name=f'Cup {fmt}', format=fmt, players_per_group=4,
                )
                # Usernames are globally unique, so they must vary per subtest.
                approved(tournament, [f'{fmt[:2]}{i}' for i in range(1, 5)])

                matches = TournamentRandomizer.create_singles_matches(tournament)

                self.assertEqual(len(matches), count)
                self.assertTrue(
                    Match.objects.filter(tournament=tournament).exists(),
                )

    def test_mixed_doubles_has_no_singles_dispatch(self):
        tournament = make_tournament(format='mixed_doubles')
        approved(tournament, ['p1', 'p2', 'p3', 'p4'])

        matches = TournamentRandomizer.create_singles_matches(tournament)

        self.assertEqual(matches, [])
        self.assertFalse(Match.objects.filter(tournament=tournament).exists())

    def test_doubles_elimination_reuses_the_first_round_round_name(self):
        tournament = make_tournament(category='doubles', format='single_elimination')
        approved(tournament, [f'd{i}' for i in range(1, 5)])  # 4 players -> 2 teams

        matches = TournamentRandomizer.create_doubles_matches(tournament)

        # Unlike the singles bracket, doubles elimination creates only round 1
        # (no later rounds / next_match links) and labels it 'round_of_16'.
        self.assertEqual(len(matches), 1)
        for match in matches:
            self.assertEqual(match.round_name, 'round_of_16')
            self.assertIsNotNone(match.team1_id)
            self.assertIsNotNone(match.team2_id)

