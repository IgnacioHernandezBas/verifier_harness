# Checklist TODO: Test passes on fixed version.
# Checklist TODO: Test fails on buggy version.
# Checklist TODO: No internal implementation details tested.
import pytest
from django.contrib.sitemaps import Sitemap

def test_claim_c1():
    # Given: sitemap has no items but lastmod is a callable that requires item input
    class EmptySitemap(Sitemap):
        def items(self):
            return []

        def lastmod(self, obj):
            return obj.lastmod

    sitemap = EmptySitemap()

    # When: calling get_latest_lastmod on Sitemap subclass
    result = sitemap.get_latest_lastmod()

    # Then: returns None instead of raising ValueError
    assert result is None
