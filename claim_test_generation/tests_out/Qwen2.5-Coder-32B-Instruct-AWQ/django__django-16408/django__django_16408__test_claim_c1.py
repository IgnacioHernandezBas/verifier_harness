# Checklist TODO: Test setup creates expected model instances.
# Checklist TODO: Query execution and iteration produce correct results.
# Checklist TODO: Annotated field matches direct relation access.
import pytest
from django.db import models
from django.db.models import FilteredRelation

# Test setup creates expected model instances.
class Child(models.Model):
    name = models.CharField(max_length=100)

class Parent(models.Model):
    child = models.ForeignKey(Child, on_delete=models.CASCADE, related_name='parents')

@pytest.fixture
def setup_data():
    child1 = Child.objects.create(name='Child1')
    child2 = Child.objects.create(name='Child2')
    Parent.objects.create(child=child1)
    Parent.objects.create(child=child1)
    Parent.objects.create(child=child2)
    return child1, child2

def test_claim_c1(setup_data):
    # Given: A query that uses FilteredRelation with select_related to annotate a queryset with a related object.
    child1, child2 = setup_data
    queryset = Parent.objects.annotate(
        annotated_child=FilteredRelation('child')
    ).select_related('annotated_child')

    # When: The query is executed and the results are iterated over.
    results = list(queryset)

    # Then: The related object accessed through the annotated field should match the related object accessed through the direct relation.
    for parent in results:
        assert parent.annotated_child == parent.child, "Annotated field does not match direct relation access."

    # Edge case: Test with no related Child objects.
    Parent.objects.filter(child=child1).delete()
    queryset = Parent.objects.annotate(
        annotated_child=FilteredRelation('child')
    ).select_related('annotated_child')
    results = list(queryset)
    for parent in results:
        assert parent.annotated_child == parent.child, "Annotated field does not match direct relation access when no related Child objects."

    # Edge case: Test with multiple Child objects related to a single Parent.
    Parent.objects.create(child=child2)
    Parent.objects.create(child=child2)
    queryset = Parent.objects.annotate(
        annotated_child=FilteredRelation('child')
    ).select_related('annotated_child')
    results = list(queryset)
    for parent in results:
        assert parent.annotated_child == parent.child, "Annotated field does not match direct relation access with multiple Child objects."

    # Edge case: Test with complex filtering conditions in FilteredRelation.
    queryset = Parent.objects.annotate(
        annotated_child=FilteredRelation('child', condition=models.Q(child__name='Child2'))
    ).select_related('annotated_child')
    results = list(queryset)
    for parent in results:
        if parent.child.name == 'Child2':
            assert parent.annotated_child == parent.child, "Annotated field does not match direct relation access with complex filtering conditions."
        else:
            assert parent.annotated_child is None, "Annotated field should be None when complex filtering conditions do not match."
