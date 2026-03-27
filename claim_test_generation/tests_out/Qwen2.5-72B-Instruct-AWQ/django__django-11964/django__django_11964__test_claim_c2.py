# Checklist TODO: Test must create a model instance with an IntegerChoices field.
# Checklist TODO: Test must verify the field returns an integer, not an enum instance.
# Checklist TODO: Test must ensure the integer value is correct.
import pytest
from django.db import models
from django.db.models.enums import IntegerChoices

class MyEnum(IntegerChoices):
    OPTION1 = 1, 'Option 1'
    OPTION2 = 2, 'Option 2'

class MyModel(models.Model):
    my_field = models.IntegerField(choices=MyEnum.choices)

@pytest.mark.django_db
def test_claim_c2():
    # Given: A model with an IntegerField using IntegerChoices and an instance created with an enum value
    instance = MyModel(my_field=MyEnum.OPTION1)
    instance.save()

    # When: Accessing the field value via model instance attribute
    retrieved_instance = MyModel.objects.get(id=instance.id)
    field_value = retrieved_instance.my_field

    # Then: The value is an integer equal to the enum's value
    assert isinstance(field_value, int)
    assert field_value == MyEnum.OPTION1.value

    # Edge cases
    # Test with the highest and lowest values of the enum
    instance_low = MyModel(my_field=MyEnum.OPTION1)
    instance_high = MyModel(my_field=MyEnum.OPTION2)
    instance_low.save()
    instance_high.save()

    retrieved_instance_low = MyModel.objects.get(id=instance_low.id)
    retrieved_instance_high = MyModel.objects.get(id=instance_high.id)

    assert retrieved_instance_low.my_field == MyEnum.OPTION1.value
    assert retrieved_instance_high.my_field == MyEnum.OPTION2.value

    # Test with a non-existent enum value (should raise an error)
    with pytest.raises(ValueError):
        MyModel(my_field=3).save()

    # Test with a null value if the field allows it
    if MyModel._meta.get_field('my_field').null:
        instance_null = MyModel(my_field=None)
        instance_null.save()
        retrieved_instance_null = MyModel.objects.get(id=instance_null.id)
        assert retrieved_instance_null.my_field is None
