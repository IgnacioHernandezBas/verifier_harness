import pytest
from django.contrib.sitemaps import Sitemap

# Given: sitemap contains no items but supports returning lastmod for an item
class CallableLastmodNoItemsSitemap(Sitemap):
    def items(self):
        return []

    def lastmod(self, obj):
        return obj.lastmod

# When: calling get_latest_lastmod
# Then: returns None
def test_claim_c2():
    # Test passes with an empty sitemap.
    sitemap = CallableLastmodNoItemsSitemap()
    
    # Function returns None as expected.
    assert sitemap.get_latest_lastmod() is None
    
    # No errors occur during execution.
