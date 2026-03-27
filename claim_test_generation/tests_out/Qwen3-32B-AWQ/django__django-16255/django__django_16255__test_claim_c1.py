# Checklist TODO: Ensure empty sitemap is properly configured
# Checklist TODO: Validate exception handling during get_latest_lastmod call
# Checklist TODO: Confirm return value matches expected type/scope
import pytest
from django.contrib.sitemaps import Sitemap
from datetime import datetime

def test_claim_c1():
    # Given: sitemap with no items but supports lastmod
    class TestSitemap(Sitemap):
        def items(self):
            return []
        def lastmod(self, obj):
            return datetime(2023, 1, 1)
    sitemap = TestSitemap()
    # When/Then: calling get_latest_lastmod does not raise ValueError
    result = sitemap.get_latest_lastmod()
    assert result is None
