"""PostgreSQL model tests. Opt in with FAMILY_RUN_DB_TESTS=1 after Alembic upgrade.

Every test uses an outer transaction that is rolled back, including fixture rows.
No schema creation, migration, or committed application data changes occur here.
"""
import os
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import CheckConstraint, Numeric, func, inspect, select
from sqlalchemy.exc import IntegrityError, StatementError
from sqlalchemy.orm import Session, configure_mappers

from models import (
    Base, ContributionFrequency, ContributionPayment, ContributionPeriod,
    ContributionPeriodStatus, ContributionStatus, ContributionType, FamilyMember,
    MemberContribution, PaymentMethod, Sex, User,
)


def test_models_register_and_map():
    configure_mappers()
    for model, column in (
        (ContributionType, 'default_amount'),
        (ContributionPeriod, 'amount_per_member'),
        (MemberContribution, 'amount_due'),
        (ContributionPayment, 'amount_paid'),
    ):
        assert model.__tablename__ in Base.metadata.tables
        money_type = model.__table__.c[column].type
        assert isinstance(money_type, Numeric)
        assert (money_type.precision, money_type.scale, money_type.asdecimal) == (12, 2, True)


@pytest.fixture
def session():
    if os.getenv('FAMILY_RUN_DB_TESTS') != '1':
        pytest.skip('Set FAMILY_RUN_DB_TESTS=1 to run rollback-only PostgreSQL tests')
    from config.database import engine

    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            with Session(bind=connection, join_transaction_mode='create_savepoint') as db:
                yield db
        finally:
            transaction.rollback()


@pytest.fixture
def records(session):
    suffix = uuid.uuid4().hex
    user = User(username='test_' + suffix)
    member = FamilyMember(
        family_number='T-' + suffix[:24], first_name='Test', last_name='Member', sex=Sex.FEMALE,
    )
    category = ContributionType(
        name='Test ' + suffix, default_amount=Decimal('75.25'),
        frequency=ContributionFrequency.ANNUAL, creator=user,
    )
    period = ContributionPeriod(
        contribution_type=category, title='Test period', year=2026,
        amount_per_member=Decimal('60.00'), start_date=date(2026, 1, 1),
        due_date=date(2026, 12, 31), creator=user,
    )
    obligation = MemberContribution(
        contribution_period=period, family_member=member, amount_due=Decimal('60.00'),
    )
    session.add_all([user, member, category, period, obligation])
    session.flush()
    return category, period, obligation, user, member


def payment_for(obligation, **overrides):
    values = dict(
        member_contribution_id=obligation.id, amount_paid=Decimal('20.00'),
        payment_date=date(2026, 9, 7), payment_method=PaymentMethod.CASH,
    )
    values.update(overrides)
    return ContributionPayment(**values)


def test_defaults_and_independent_amounts(session, records):
    category, period, obligation, _, _ = records
    assert period.status is ContributionPeriodStatus.DRAFT
    assert obligation.status is ContributionStatus.UNPAID
    assert category.is_active
    assert category.created_at.tzinfo is not None
    category.default_amount = Decimal('90.00')
    session.flush()
    session.expire_all()
    assert period.amount_per_member == Decimal('60.00')
    assert obligation.amount_due == Decimal('60.00')
    assert isinstance(obligation.amount_due, Decimal)


@pytest.mark.parametrize('target,column', [
    (0, 'default_amount'), (1, 'amount_per_member'), (2, 'amount_due'),
])
@pytest.mark.parametrize('value', [Decimal('-0.01'), Decimal('NaN')])
def test_invalid_obligation_amounts(session, records, target, column, value):
    with pytest.raises(IntegrityError) as error:
        with session.begin_nested():
            setattr(records[target], column, value)
            session.flush()
    assert error.value.orig.sqlstate == '23514'


@pytest.mark.parametrize('value', [Decimal('0'), Decimal('-1'), Decimal('NaN')])
def test_invalid_payment_amounts(session, records, value):
    with pytest.raises(IntegrityError) as error:
        with session.begin_nested():
            session.add(payment_for(records[2], amount_paid=value))
            session.flush()
    assert error.value.orig.diag.constraint_name == 'ck_contribution_payments_amount'


def test_zero_obligation_and_optional_dates(session, records):
    category, period, obligation, _, _ = records
    category.default_amount = None
    period.amount_per_member = Decimal('0')
    period.start_date = None
    period.year = None
    obligation.amount_due = Decimal('0')
    session.flush()


def test_due_date_cannot_precede_start(session, records):
    with pytest.raises(IntegrityError) as error:
        with session.begin_nested():
            records[1].due_date = date(2025, 12, 31)
            session.flush()
    assert error.value.orig.diag.constraint_name == 'ck_contribution_periods_dates'


def test_unique_member_obligation(session, records):
    with pytest.raises(IntegrityError) as error:
        with session.begin_nested():
            session.add(MemberContribution(
                contribution_period_id=records[1].id, family_member_id=records[4].id,
                amount_due=Decimal('60'),
            ))
            session.flush()
    assert error.value.orig.diag.constraint_name == 'uq_member_contributions_period_member'


def test_unique_receipt(session, records):
    receipt = uuid.uuid4().hex
    session.add(payment_for(records[2], receipt_number=receipt))
    session.flush()
    with pytest.raises(IntegrityError) as error:
        with session.begin_nested():
            session.add(payment_for(records[2], receipt_number=receipt))
            session.flush()
    assert error.value.orig.diag.constraint_name == 'uq_contribution_payments_receipt'


@pytest.mark.parametrize('missing', ['reversed_at', 'reversed_by', 'reversal_reason', 'blank_reason', 'not_reversed'])
def test_reversal_requires_complete_metadata(session, records, missing):
    values = dict(is_reversed=True, reversed_at=datetime.now(timezone.utc),
                  reversed_by=records[3].id, reversal_reason='Incorrect entry')
    if missing == 'blank_reason':
        values['reversal_reason'] = '   '
    elif missing == 'not_reversed':
        values['is_reversed'] = False
    else:
        values[missing] = None
    with pytest.raises(IntegrityError) as error:
        with session.begin_nested():
            session.add(payment_for(records[2], **values))
            session.flush()
    assert error.value.orig.diag.constraint_name == 'ck_contribution_payments_reversal'


def test_installments_and_reversal_preserve_history(session, records):
    obligation = records[2]
    payments = [payment_for(obligation, amount_paid=Decimal(amount)) for amount in ('20.00', '30.00', '10.00')]
    session.add_all(payments)
    session.flush()
    total_query = select(func.sum(ContributionPayment.amount_paid)).where(
        ContributionPayment.member_contribution_id == obligation.id,
        ContributionPayment.is_reversed.is_(False),
    )
    assert session.scalar(total_query) == Decimal('60.00')
    payments[1].is_reversed = True
    payments[1].reversed_at = datetime.now(timezone.utc)
    payments[1].reversed_by = records[3].id
    payments[1].reversal_reason = 'Wrong amount entered'
    session.flush()
    session.expire_all()
    assert session.scalar(total_query) == Decimal('30.00')
    assert len(obligation.payments) == 3
    assert obligation.amount_due - session.scalar(total_query) == Decimal('30.00')
    assert payments[1].amount_paid == Decimal('30.00')
    assert payments[1].reversed_at.tzinfo is not None


@pytest.mark.parametrize('target', [0, 1, 2, 3, 4])
def test_financial_parent_deletion_is_restricted(session, records, target):
    session.add(payment_for(records[2], recorded_by=records[3].id))
    session.flush()
    # Load collections too: the ORM must not null links or cascade-delete children.
    assert records[0].periods
    assert records[1].member_contributions
    assert records[2].payments
    with pytest.raises(IntegrityError) as error:
        with session.begin_nested():
            session.delete(records[target])
            session.flush()
    expected_constraints = [
        'fk_contribution_periods_contribution_type_id',
        'fk_member_contributions_contribution_period_id',
        'fk_contribution_payments_member_contribution_id',
        'fk_contribution_payments_recorded_by',
        'fk_member_contributions_family_member_id',
    ]
    assert error.value.orig.diag.constraint_name == expected_constraints[target]


def test_invalid_payment_method(session, records):
    with pytest.raises(StatementError):
        with session.begin_nested():
            session.add(payment_for(records[2], payment_method='GATEWAY'))
            session.flush()


def test_postgresql_schema_matches_models(session):
    inspector = inspect(session.connection())
    for model in (ContributionType, ContributionPeriod, MemberContribution, ContributionPayment):
        table = model.__table__
        actual = {c['name']: c for c in inspector.get_columns(table.name)}
        assert set(actual) == set(table.c.keys())
        for column in table.c:
            assert actual[column.name]['nullable'] == column.nullable
            if isinstance(column.type, Numeric):
                actual_type = actual[column.name]['type']
                assert (actual_type.precision, actual_type.scale) == (12, 2)
        checks = {c['name'] for c in inspector.get_check_constraints(table.name)}
        assert {c.name for c in table.constraints if isinstance(c, CheckConstraint)} <= checks
        actual_fks = {fk['name']: fk for fk in inspector.get_foreign_keys(table.name)}
        for fk in table.foreign_key_constraints:
            assert actual_fks[fk.name]['options']['ondelete'] == fk.ondelete
        assert {index.name for index in table.indexes} <= {
            index['name'] for index in inspector.get_indexes(table.name)
        }
