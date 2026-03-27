import pytest
from django.db import models
from django.db.models import FilteredRelation
from django.db.models.fields.related import ForeignKey
from django.test.utils import Approximate

# Given: Parent/Child models with ForeignKey relation
class Parent(models.Model):
    pass


class Child(models.Model):
    parent = ForeignKey(Parent, on_delete=models.CASCADE)


@pytest.fixture
def setup_data():
    parent = Parent.objects.create()
    child = Child.objects.create(parent=parent)
    return parent, child


def test_claim_c1(setup_data):
    # Given: Populate test data with known related objects
    parent, child = setup_data

    # When: Construct queryset with FilteredRelation + select_related
    queryset = Parent.objects.annotate(
        filtered_child=FilteredRelation("child", condition=models.Q(child=child.id))
    ).select_related("filtered_child")

    # Then: Annotated field matches direct relation access
    instance = queryset.get()
    assert instance.filtered_child_id == child.id
    assert instance.filtered_child.parent_id == parent.id
    assert instance.filtered_child.parent == instance

    # Then: Query executes without EmptyResultSet errors
    assert queryset.query.contains_valid_joins

    # Then: Result iteration returns correct object count
    assert len(list(queryset)) == 1
