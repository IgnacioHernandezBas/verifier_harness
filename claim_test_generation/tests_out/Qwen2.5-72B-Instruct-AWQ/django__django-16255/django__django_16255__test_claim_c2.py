import pytest
from django.contrib.sitemaps import Sitemap

# Test must create a sitemap with no items.
class EmptySitemap(Sitemap):
    def items(self):
        return []

    def lastmod(self, obj):
        return obj.lastmod

# Test must call get_latest_lastmod and assert it returns None.
def test_claim_c2():
    # Given: sitemap contains no items but supports returning lastmod for an item
    sitemap = EmptySitemap()
    
    # When: calling get_latest_lastmod
    result = sitemap.get_latest_lastmod()
    
    # Then: returns None
    assert result is None

# Test must not rely on internal implementation details.
