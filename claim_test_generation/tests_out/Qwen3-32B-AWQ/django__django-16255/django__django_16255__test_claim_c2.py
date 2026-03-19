# Checklist TODO: Test returns None for empty sitemap with callable lastmod
# Checklist TODO: Verify no implementation details are tested
# Checklist TODO: Ensure test passes on fixed version and fails on buggy version
import pytest
from django.contrib.sitemaps import Sitemap

def test_claim_c2():
    # GIVEN: A sitemap with no items and a callable lastmod method
    class TestSitemap(Sitemap):
        def items(self):
            return []
        def lastmod(self, obj):
            return obj.lastmod  # dummy callable

    sitemap = TestSitemap()

    # WHEN: get_latest_lastmod is called
    result = sitemap.get_latest_lastmod()

    # THEN: Returns None
    assert result is None
