# Checklist TODO: Test must create a sitemap with no items and a callable lastmod.
# Checklist TODO: Test must call get_latest_lastmod on the sitemap instance.
# Checklist TODO: Test must assert that the result is None.
import pytest
from django.contrib.sitemaps import Sitemap

class CallableLastmodNoItemsSitemap(Sitemap):
    def items(self):
        return []

    def lastmod(self, obj):
        return obj.lastmod

@pytest.fixture
def sitemap_instance():
    return CallableLastmodNoItemsSitemap()

def test_claim_c1(sitemap_instance):
    # GIVEN: A sitemap instance with no items and a callable lastmod attribute.
    # WHEN: get_latest_lastmod is called on the sitemap instance.
    result = sitemap_instance.get_latest_lastmod()
    # THEN: The function returns None.
    assert result is None
