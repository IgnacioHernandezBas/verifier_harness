# Checklist TODO: Verify empty sitemap with callable lastmod returns None
# Checklist TODO: Confirm get_latest_lastmod is invoked correctly
# Checklist TODO: Ensure result differentiation from non-empty cases
import pytest
from django.contrib.sitemaps import Sitemap

def test_claim_c1():
    # Given: A sitemap instance with no items and a callable lastmod
    class TestSitemap(Sitemap):
        def items(self):
            return []  # No items in sitemap

        def lastmod(self, obj):
            # Callable lastmod (not invoked in this test case)
            return None

    sitemap = TestSitemap()

    # When: get_latest_lastmod is called on the sitemap instance
    result = sitemap.get_latest_lastmod()

    # Then: The function returns None
    assert result is None
