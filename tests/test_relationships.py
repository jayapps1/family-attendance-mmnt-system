import pytest
from services.family_service import FamilyService
from services.relationship_service import RelationshipService
from tests.service_helpers import service_context


def test_cycles_duplicates_self_and_marriage(db):
    context = service_context(db)
    family, relationships = FamilyService(*context), RelationshipService(*context)
    ids = [family.create(first_name=name, last_name="Test", sex="MALE")["id"] for name in ("A", "B", "C")]
    relationships.save(ids[0], ids[1], "FATHER")
    relationships.save(ids[1], ids[2], "FATHER")
    for parent, child in ((ids[0], ids[0]), (ids[0], ids[1]), (ids[2], ids[0])):
        with pytest.raises(ValueError):
            relationships.save(parent, child, "FATHER")
    assert len(relationships.tree(ids[0])["descendants"]) == 2
    with pytest.raises(ValueError):
        relationships.save_marriage(ids[0], ids[0])
    relationships.save_marriage(ids[0], ids[2])
    with pytest.raises(ValueError):
        relationships.save_marriage(ids[2], ids[0])
