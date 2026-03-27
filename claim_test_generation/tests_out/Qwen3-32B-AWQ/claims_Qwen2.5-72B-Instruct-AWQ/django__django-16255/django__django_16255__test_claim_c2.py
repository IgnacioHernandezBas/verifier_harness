# Checklist TODO: Create sitemap with empty items list
# Checklist TODO: Ensure lastmod is a callable method
# Checklist TODO: Verify returns None when no items exist
import pytest
from django.contrib.sitemaps import Sitemap

def test_claim_c2():
    # Create sitemap with empty items list
    class EmptySitemap(Sitemap):
        def items(self):
            return []
        def lastmod(self, obj):
            return obj.lastmod  # Callable method as per claim

    sitemap = EmptySitemap()
    
    # WHEN: get_latest_lastmod is called
    result = sitemap.get_latest_lastmod()
    
    # THEN: Returns None
    assert result is None
