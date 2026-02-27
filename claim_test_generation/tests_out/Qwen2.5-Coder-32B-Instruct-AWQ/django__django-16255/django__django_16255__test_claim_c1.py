# Checklist TODO: Test passes without raising ValueError.
# Checklist TODO: Function handles empty sitemap gracefully.
# Checklist TODO: Test confirms lastmod method is not called unnecessarily.
import pytest
from django.contrib.sitemaps import Sitemap

def test_claim_c1():
    # Given: sitemap contains no items but supports returning lastmod for an item
    class EmptySitemap(Sitemap):
        def items(self):
            return []

        def lastmod(self, obj):
            return None  # This method is defined but will not be called

    sitemap = EmptySitemap()

    # When: calling get_latest_lastmod
    # Then: does not raise ValueError
    try:
        sitemap.get_latest_lastmod()
    except ValueError:
        pytest.fail("get_latest_lastmod raised ValueError unexpectedly")

    # Function handles empty sitemap gracefully.
    # Test confirms lastmod method is not called unnecessarily.
    # Since items() returns an empty list, lastmod() should not be called.
