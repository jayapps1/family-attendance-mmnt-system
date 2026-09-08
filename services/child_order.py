"""Birth positions within a union, serialized with other genealogy changes."""
from models import Marriage
from repositories.base import Repository
from repositories.relationship_repository import RelationshipRepository
from utils.validators import ValidationError


class ChildOrderMixin:
    @staticmethod
    def _position(value, maximum):
        if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= maximum:
            raise ValidationError(f'Birth order must be a whole number from 1 to {maximum}.')
        return value

    @staticmethod
    def _sync_child_orders(session):
        repo = RelationshipRepository(session)
        for marriage in repo.marriages():
            repo.write_child_order(marriage.id, [r.id for r in repo.ordered_children(marriage)])

    def get_next_birth_order(self, marriage_id):
        return len(self.get_children_of_marriage(marriage_id)) + 1

    def reorder_children(self, marriage_id, child_ids, expected_order=None):
        with self.transaction() as session:
            repo = RelationshipRepository(session)
            repo.lock_domain('genealogy')
            marriage = Repository(session, Marriage).get(marriage_id, lock=True)
            current = [r.id for r in repo.ordered_children(marriage)]
            if expected_order is not None and list(expected_order) != current:
                raise ValidationError('Children changed while this form was open. Reopen Manage Child Order.')
            if len(child_ids) != len(set(child_ids)) or set(child_ids) != set(current):
                raise ValidationError('Include every current shared child exactly once.')
            repo.write_child_order(marriage_id, child_ids)
            self.audit(session, 'REORDER_CHILDREN', marriage, ', '.join(map(str, child_ids)))
            return self._couple(session, marriage)

    def set_child_birth_order(self, marriage_id, child_id, position):
        with self.transaction() as session:
            repo = RelationshipRepository(session)
            repo.lock_domain('genealogy')
            marriage = Repository(session, Marriage).get(marriage_id, lock=True)
            children = [r.id for r in repo.ordered_children(marriage)]
            self._position(position, len(children))
            if child_id not in children:
                raise ValidationError('This member is not a shared child of this couple.')
            children.remove(child_id); children.insert(position-1, child_id)
            repo.write_child_order(marriage_id, children)
            self.audit(session, 'UPDATE_CHILD_BIRTH_ORDER', marriage, str(child_id) + ' position ' + str(position))
            return self._couple(session, marriage)

    insert_child_at_position = set_child_birth_order

    def normalize_child_order(self, marriage_id):
        with self.transaction() as session:
            repo = RelationshipRepository(session)
            repo.lock_domain('genealogy')
            marriage = Repository(session, Marriage).get(marriage_id, lock=True)
            repo.write_child_order(marriage_id, [r.id for r in repo.ordered_children(marriage)])
            self.audit(session, 'REORDER_CHILDREN', marriage, 'Normalized positions')
            return self._couple(session, marriage)
