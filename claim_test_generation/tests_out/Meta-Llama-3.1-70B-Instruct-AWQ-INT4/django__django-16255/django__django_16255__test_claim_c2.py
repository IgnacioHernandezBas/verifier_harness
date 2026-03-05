import pytest
from django.contrib.sitemaps import Sitemap

# Checklist: Test passes with a sitemap containing no items and a callable lastmod method
def test_claim_c2():
    # Given: A sitemap with no items and a callable lastmod method
    class TestSitemap(Sitemap):
        def items(self):
            return []
        
        def lastmod(self, obj):
            return None

    sitemap = TestSitemap()

    # When: get_latest_lastmod is called
    # Note: get_latest_lastmod is not a standalone function, it's a method of Sitemap class
    latest_lastmod = sitemap.get_latest_lastmod()

    # Then: Returns None
    assert latest_lastmod is None

# Checklist: Test fails with a sitemap containing items or a non-callable lastmod method
def test_claim_c2_fail():
    # Given: A sitemap with items and a callable lastmod method
    class TestSitemap(Sitemap):
        def items(self):
            return [1, 2, 3]
        
        def lastmod(self, obj):
            return None

    sitemap = TestSitemap()

    # When: get_latest_lastmod is called
    latest_lastmod = sitemap.get_latest_lastmod()

    # Then: Does not return None
    assert latest_lastmod is not None

    # Given: A sitemap with no items and a non-callable lastmod method
    class TestSitemap(Sitemap):
        def items(self):
            return []
        
        lastmod = None

    sitemap = TestSitemap()

    # When: get_latest_lastmod is called
    with pytest.raises(AttributeError):
        sitemap.get_latest_lastmod()

# Checklist: Test correctly handles a sitemap that does not support lastmod
def test_claim_c2_no_lastmod():
    # Given: A sitemap that does not support lastmod
    class TestSitemap(Sitemap):
        def items(self):
            return []
        
        def get_latest_lastmod(self):
            raise NotImplementedError

    sitemap = TestSitemap()

    # When: get_latest_lastmod is called
    with pytest.raises(NotImplementedError):
        sitemap.get_latest_lastmod()
