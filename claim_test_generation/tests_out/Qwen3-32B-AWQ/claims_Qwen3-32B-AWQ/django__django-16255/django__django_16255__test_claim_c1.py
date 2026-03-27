# Checklist TODO: Verify empty sitemap returns None
# Checklist TODO: Confirm no exception raised for missing items
# Checklist TODO: Test callable lastmod dependency handling
import pytest
from django.contrib.sitemaps import Sitemap

def test_claim_c1():
    # Given: Sitemap with no items and callable lastmod requiring item
    class TestSitemap(Sitemap):
        def items(self):
            return []
        def lastmod(self, item):
            return item.lastmod

    sitemap = TestSitemap()

    # When: calling get_latest_lastmod
    result = sitemap.get_latest_lastmod()

    # Then: returns None and no ValueError
    assert result is None
