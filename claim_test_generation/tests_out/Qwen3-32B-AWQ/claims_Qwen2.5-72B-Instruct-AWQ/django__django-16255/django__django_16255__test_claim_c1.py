# Checklist TODO: Verify no ValueError raised for empty sitemap with lastmod
# Checklist TODO: Test uses real sitemap implementation without mocks
# Checklist TODO: Test passes without requiring Django framework setup
import pytest
from django.contrib.sitemaps import Sitemap

# Given: A sitemap with no items and a callable lastmod method
class EmptySitemap(Sitemap):
    def items(self):
        # Ensure sitemap has no items
        return []

    def lastmod(self, item):
        # Ensure lastmod is a callable that returns None
        return None

def test_claim_c1():
    # Given: A sitemap with no items and a callable lastmod method
    sitemap = EmptySitemap()
    # When/Then: get_latest_lastmod is called and no ValueError is raised
    sitemap.get_latest_lastmod()
