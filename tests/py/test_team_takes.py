from __future__ import absolute_import, division, print_function, unicode_literals

from pytest import raises
from gratipay.models.team.takes import NotAllowed, PENNY, ZERO
from gratipay.testing import Harness, D,P,T
from gratipay.testing.billing import PaydayMixin


class TeamTakesHarness(Harness, PaydayMixin):
    # Factored out to share with membership tests ...

    def setUp(self):
        self.enterprise = self.make_team('The Enterprise', available=1, receiving=2)
        self.picard = P('picard')
        self.crusher = self.make_participant( 'crusher'
                                            , email_address='crusher@example.com'
                                            , claimed_time='now'
                                            , verified_in='TT'
                                             )
        self.bruiser = self.make_participant( 'bruiser'
                                            , email_address='bruiser@example.com'
                                            , claimed_time='now'
                                            , verified_in='US'
                                             )


class GetTakeFor(TeamTakesHarness):

    def test_returns_zero_for_unknown(self):
        assert self.enterprise.get_take_for(self.crusher) == 0

    def test_returns_amount_for_known(self):
        self.enterprise.set_take_for(self.crusher, PENNY, self.picard)
        assert self.enterprise.get_take_for(self.crusher) == PENNY

    def test_returns_correct_amount_for_multiple_members(self):
        self.enterprise.set_take_for(self.crusher, PENNY, self.picard)
        self.enterprise.set_take_for(self.bruiser, PENNY, self.picard)
        self.enterprise.set_take_for(self.bruiser, PENNY * 2, self.bruiser)
        assert self.enterprise.get_take_for(self.crusher) == PENNY
        assert self.enterprise.get_take_for(self.bruiser) == PENNY * 2

    def test_returns_correct_amount_for_multiple_teams(self):
        self.enterprise.set_take_for(self.crusher, PENNY, self.picard)

        trident = self.make_team('The Trident', owner='shelby', available=5)
        trident.set_take_for(self.crusher, PENNY, P('shelby'))
        trident.set_take_for(self.crusher, PENNY * 2, self.crusher)

        assert self.enterprise.get_take_for(self.crusher) == PENNY
        assert trident.get_take_for(self.crusher) == PENNY * 2


class SetTakeFor(TeamTakesHarness):

    def test_sets_take_for(self):
        assert self.enterprise.set_take_for(self.crusher, PENNY, self.picard) == PENNY

    def test_updates_take_for_an_existing_member(self):
        self.enterprise.set_take_for(self.crusher, PENNY, self.picard)
        assert self.enterprise.set_take_for(self.crusher, 537, self.crusher) == 537

    def test_actually_sets_take(self):
        self.enterprise.set_take_for(self.crusher, PENNY, self.picard)
        assert self.enterprise.get_take_for(self.crusher) == PENNY

    def test_updates_taking(self):
        assert self.crusher.taking == ZERO
        self.enterprise.set_take_for(self.crusher, PENNY, self.picard)
        assert self.crusher.taking == PENNY

    def test_updates_distributing(self):
        assert self.enterprise.ndistributing_to == 0
        assert self.enterprise.distributing == ZERO
        self.enterprise.set_take_for(self.crusher, PENNY, self.picard)
        assert self.enterprise.ndistributing_to == 1
        assert self.enterprise.distributing == PENNY


    # permissions

    def test_lets_owner_add_member(self):
        self.enterprise.set_take_for(self.crusher, PENNY, self.picard)
        assert self.enterprise.ndistributing_to == 1

    def test_lets_owner_add_themselves(self):
        self.enterprise.set_take_for(self.picard, PENNY, self.picard)
        assert self.enterprise.ndistributing_to == 1

    def test_lets_owner_remove_member(self):
        self.enterprise.set_take_for(self.crusher, PENNY, self.picard)
        self.enterprise.set_take_for(self.crusher, ZERO, self.picard)
        assert self.enterprise.ndistributing_to == 0

    def test_lets_owner_remove_themselves(self):
        self.enterprise.set_take_for(self.picard, PENNY, self.picard)
        self.enterprise.set_take_for(self.picard, ZERO, self.picard)
        assert self.enterprise.ndistributing_to == 0

    def err(self, *a):
        return raises(NotAllowed, self.enterprise.set_take_for, *a).value.args[0]

    def test_doesnt_let_owner_increase_take_beyond_a_penny(self):
        actual = self.err(self.crusher, PENNY * 2, self.picard)
        assert actual == 'owner can only add and remove members, not otherwise set takes'

    def test_doesnt_let_anyone_else_set_a_take(self):
        actual = self.err(self.crusher, PENNY * 1, self.bruiser)
        assert actual == 'can only set own take'

    def test_doesnt_let_anyone_else_set_a_take_even_to_zero(self):
        actual = self.err(self.crusher, 0, self.bruiser)
        assert actual == 'can only set own take'

    def test_doesnt_let_anyone_set_a_take_who_is_not_already_on_the_team(self):
        actual = self.err(self.crusher, PENNY, self.crusher)
        assert actual == 'can only set take if already a member of the team'

    def test_doesnt_let_anyone_set_a_take_who_is_not_already_on_the_team_even_to_zero(self):
        actual = self.err(self.crusher, 0, self.crusher)
        assert actual == 'can only set take if already a member of the team'


    def test_vets_participant_for_suspiciousness(self):
        mallory = self.make_participant('mallory', is_suspicious=True)
        actual = self.err(mallory, 0, self.picard)
        assert actual == 'user must not be flagged as suspicious'

    def test_vets_participant_for_email(self):
        mallory = self.make_participant('mallory')
        actual = self.err(mallory, 0, self.picard)
        assert actual == 'user must have added at least one email address'

    def test_vets_participant_for_verified_identity(self):
        mallory = self.make_participant('mallory', email_address='m@example.com')
        actual = self.err(mallory, 0, self.picard)
        assert actual == 'user must have a verified identity'

    def test_vets_participant_for_claimed(self):
        mallory = self.make_participant('mallory', email_address='m@example.com', verified_in='TT')
        actual = self.err(mallory, 0, self.picard)
        assert actual == 'user must have claimed the account'


    def test_vets_recorder_for_suspiciousness(self):
        mallory = self.make_participant('mallory', is_suspicious=True)
        actual = self.err(self.crusher, 0, mallory)
        assert actual == 'user must not be flagged as suspicious'

    def test_vets_recorder_for_email(self):
        mallory = self.make_participant('mallory')
        actual = self.err(self.crusher, 0, mallory)
        assert actual == 'user must have added at least one email address'

    def test_vets_recorder_for_verified_identity(self):
        mallory = self.make_participant('mallory', email_address='m@example.com')
        actual = self.err(self.crusher, 0, mallory)
        assert actual == 'user must have a verified identity'

    def test_vets_recorder_for_claimed(self):
        mallory = self.make_participant('mallory', email_address='m@example.com', verified_in='TT')
        actual = self.err(self.crusher, 0, mallory)
        assert actual == 'user must have claimed the account'


class GetTakeLastWeekFor(TeamTakesHarness):

    def test_gets_take_last_week_for_someone(self):
        self.enterprise.set_take_for(self.crusher, PENNY*1, self.picard)
        self.enterprise.set_take_for(self.crusher, PENNY*24, self.crusher)
        self.run_payday()
        self.enterprise.set_take_for(self.crusher, PENNY*48, self.crusher)
        assert self.enterprise.get_take_for(self.crusher) == PENNY*48  # sanity check
        assert self.enterprise.get_take_last_week_for(self.crusher) == PENNY*24

    def test_returns_zero_when_they_werent_taking(self):
        self.run_payday()
        self.enterprise.set_take_for(self.crusher, PENNY*1, self.picard)
        assert self.enterprise.get_take_for(self.crusher) == PENNY*1  # sanity check
        assert self.enterprise.get_take_last_week_for(self.crusher) == ZERO

    def test_ignores_a_currently_running_payday(self):
        self.enterprise.set_take_for(self.crusher, PENNY*1, self.picard)
        self.enterprise.set_take_for(self.crusher, PENNY*24, self.crusher)
        self.run_payday()
        self.enterprise.set_take_for(self.crusher, PENNY*48, self.crusher)
        self.start_payday()
        self.enterprise.set_take_for(self.crusher, PENNY*96, self.crusher)
        assert self.enterprise.get_take_for(self.crusher) == PENNY*96  # sanity check
        assert self.enterprise.get_take_last_week_for(self.crusher) == PENNY*24


class UpdateTaking(TeamTakesHarness):

    def test_updates_taking(self):
        self.enterprise.set_take_for(self.crusher, PENNY, self.picard)
        assert self.crusher.taking == PENNY
        self.enterprise.update_taking( {self.crusher.id: {'actual_amount': PENNY}}
                                     , {self.crusher.id: {'actual_amount': PENNY * 537}}
                                     , member=self.crusher
                                      )
        assert self.crusher.taking == PENNY * 537


class UpdateDistributing(TeamTakesHarness):

    def test_can_increase_distributing(self):
        self.enterprise.set_take_for(self.crusher, PENNY, self.picard)
        assert self.enterprise.distributing == PENNY
        self.enterprise.update_distributing({self.crusher.id: {'actual_amount': PENNY * 80}})
        assert self.enterprise.distributing == PENNY * 80


    def test_can_increase_ndistributing_to(self):
        assert self.enterprise.ndistributing_to == 0
        self.enterprise.update_distributing({self.crusher.id: {'actual_amount': PENNY}})
        assert self.enterprise.ndistributing_to == 1

    def test_doesnt_increase_ndistributing_to_for_an_existing_member(self):
        self.enterprise.update_distributing({self.crusher.id: {'actual_amount': PENNY}})
        self.enterprise.update_distributing({self.crusher.id: {'actual_amount': PENNY * 2}})
        self.enterprise.update_distributing({self.crusher.id: {'actual_amount': PENNY * 40}})
        self.enterprise.update_distributing({self.crusher.id: {'actual_amount': PENNY * 3}})
        assert self.enterprise.ndistributing_to == 1

    def test_can_decrease_ndistributing_to(self):
        self.enterprise.update_distributing({self.crusher.id: {'actual_amount': PENNY}})
        assert self.enterprise.ndistributing_to == 1
        self.enterprise.update_distributing({self.crusher.id: {'actual_amount': ZERO}})
        assert self.enterprise.ndistributing_to == 0

    def test_doesnt_decrease_ndistributing_to_below_zero(self):
        self.enterprise.update_distributing({self.crusher.id: {'actual_amount': PENNY}})
        assert self.enterprise.ndistributing_to == 1
        self.enterprise.update_distributing({self.crusher.id: {'actual_amount': ZERO}})
        self.enterprise.update_distributing({self.crusher.id: {'actual_amount': ZERO}})
        self.enterprise.update_distributing({self.crusher.id: {'actual_amount': ZERO}})
        self.enterprise.update_distributing({self.crusher.id: {'actual_amount': ZERO}})
        self.enterprise.update_distributing({self.crusher.id: {'actual_amount': ZERO}})
        assert self.enterprise.ndistributing_to == 0

    def test_updates_ndistributing_to_in_the_db(self):
        self.enterprise.update_distributing({self.crusher.id: {'actual_amount': PENNY}})
        fresh = T('TheEnterprise')
        assert fresh.distributing == PENNY
        assert fresh.ndistributing_to == 1


class ComputeActualTakes(TeamTakesHarness):

    def test_computes_actual_takes(self):
        self.enterprise.set_take_for(self.crusher, PENNY, self.picard)
        self.enterprise.set_take_for(self.crusher, PENNY * 80, self.crusher)
        self.enterprise.set_take_for(self.bruiser, PENNY, self.picard)
        self.enterprise.set_take_for(self.bruiser, PENNY * 30, self.bruiser)

        takes = self.enterprise.compute_actual_takes()

        assert tuple(takes) == (self.bruiser.id, self.crusher.id)

        assert takes[self.bruiser.id]['actual_amount'] == PENNY * 30
        assert takes[self.bruiser.id]['nominal_amount'] == PENNY * 30
        assert takes[self.bruiser.id]['balance'] == PENNY * 70
        assert takes[self.bruiser.id]['percentage'] == D('0.3')

        assert takes[self.crusher.id]['actual_amount'] == PENNY * 70
        assert takes[self.crusher.id]['nominal_amount'] == PENNY * 80
        assert takes[self.crusher.id]['balance'] == ZERO
        assert takes[self.crusher.id]['percentage'] == D('0.7')


class ClearTakes(TeamTakesHarness):

    def test_clears_takes(self):
        self.enterprise.set_take_for(self.crusher, PENNY, self.picard)
        self.enterprise.set_take_for(self.crusher, PENNY * 80, self.crusher)

        trident = self.make_team('The Trident', owner='shelby', available=5)
        trident.set_take_for(self.crusher, PENNY, P('shelby'))
        trident.set_take_for(self.crusher, PENNY * 2, self.crusher)

        assert self.db.one("select count(*) from current_takes") == 2
        self.crusher.clear_takes(self.db)
        assert self.db.one("select count(*) from current_takes") == 0

    def test_doesnt_choke_on_unverified_non_taking_team_owners(self):
        jdorfman = self.make_participant( 'jdorfman'
                                        , claimed_time='now'
                                        , last_paypal_result=''
                                        , email_address='jdorfman@example.com'
                                         )
        self.make_team('shml', owner='jdorfman')
        assert self.db.one("select count(*) from current_takes") == 0
        jdorfman.clear_takes(self.db)
        assert self.db.one("select count(*) from current_takes") == 0

    def test_still_clears_take_for_taking_team_owner(self):
        jdorfman = self.make_participant( 'jdorfman'
                                        , claimed_time='now'
                                        , last_paypal_result=''
                                        , email_address='jdorfman@example.com'
                                        , verified_in='US'
                                         )
        shml = self.make_team('shml', owner='jdorfman', available=5)
        shml.set_take_for(jdorfman, 1, jdorfman)
        assert self.db.one("select count(*) from current_takes") == 1
        jdorfman.clear_takes(self.db)
        assert self.db.one("select count(*) from current_takes") == 0
