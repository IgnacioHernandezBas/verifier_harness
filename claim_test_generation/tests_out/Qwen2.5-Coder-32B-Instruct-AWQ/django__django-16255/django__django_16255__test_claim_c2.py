# Checklist TODO: Test passes on the fixed version
# Checklist TODO: Test fails on the buggy version
# Checklist TODO: Test only checks the return value of get_latest_lastmod
import pytest
from django.contrib.sitemaps import Sitemap

def test_claim_c2():
    # Given: sitemap contains no items but supports returning lastmod for an item
    class EmptySitemap(Sitemap):
        def items(self):
            return []

        def lastmod(self, obj):
            return None  # This method is defined to support lastmod, but it won't be called

    sitemap = EmptySitemap()

    # When: calling get_latest_lastmod
    result = sitemap.get_latest_lastmod()

    # Then: returns None
    assert result is None
