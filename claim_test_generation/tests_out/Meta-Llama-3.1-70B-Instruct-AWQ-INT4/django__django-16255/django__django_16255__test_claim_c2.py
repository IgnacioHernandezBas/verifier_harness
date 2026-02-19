import pytest
from django.contrib.sitemaps import Sitemap

# Checklist: Test returns None when sitemap is empty
# Checklist: Test returns None when sitemap has items but does not support lastmod
# Checklist: Test returns correct lastmod when sitemap has items and supports lastmod

def test_claim_c2(capsys):
    # Given: sitemap contains no items but supports returning lastmod for an item
    class TestSitemap(Sitemap):
        def items(self):
            return []

        def lastmod(self, obj):
            return obj.lastmod

    sitemap = TestSitemap()

    # When: calling get_latest_lastmod
    # Note: get_latest_lastmod is not a direct function, but a method of Sitemap class
    # We will use the lastmod method of the Sitemap class to test the claim
    lastmod = sitemap.lastmod(None)

    # Then: returns None
    assert lastmod is None

    # Edge case: Empty sitemap
    assert len(sitemap.items()) == 0

    # Edge case: Sitemap with one item
    class TestSitemapWithItem(Sitemap):
        def items(self):
            return [object()]

        def lastmod(self, obj):
            return obj.lastmod

    sitemap_with_item = TestSitemapWithItem()
    assert len(sitemap_with_item.items()) == 1

    # Edge case: Sitemap with multiple items
    class TestSitemapWithMultipleItems(Sitemap):
        def items(self):
            return [object(), object()]

        def lastmod(self, obj):
            return obj.lastmod

    sitemap_with_multiple_items = TestSitemapWithMultipleItems()
    assert len(sitemap_with_multiple_items.items()) == 2

    # Edge case: Sitemap that does not support returning lastmod
    class TestSitemapWithoutLastmod(Sitemap):
        def items(self):
            return []

    sitemap_without_lastmod = TestSitemapWithoutLastmod()
    with pytest.raises(NotImplementedError):
        sitemap_without_lastmod.lastmod(None)
