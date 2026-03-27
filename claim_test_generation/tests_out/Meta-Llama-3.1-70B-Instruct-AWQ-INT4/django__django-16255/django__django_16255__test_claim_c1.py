import pytest
from django.contrib.sitemaps import Sitemap

# Test sketch
# {
#   "strategy": "Exercise get_latest_lastmod with callable lastmod",
#   "assertions": [
#     "returns None when sitemap has no items and lastmod is callable",
#     "does not raise ValueError when sitemap has no items and lastmod is callable"
#   ],
#   "fixtures": [
#     "capsys"
#   ],
#   "data_setup": [
#     "Create a Sitemap subclass with no items",
#     "Define a callable lastmod method that requires item input"
#   ],
#   "edge_cases": [
#     "Test with an empty sitemap",
#     "Test with a non-callable lastmod method",
#     "Test with a lastmod method that raises an exception"
#   ],
#   "checklist": [
#     "Test returns None when sitemap is empty and lastmod is callable.",
#     "Test does not raise ValueError when sitemap is empty and lastmod is callable.",
#     "Test handles edge cases correctly."
#   ]
# }

# Guardrail diagnostics
# {
#   "context": {
#     "module": "django.contrib.sitemaps",
#     "import_warning": "Module import failed in host environment; proceeding without signature hints.",
#     "repo_path": "/fs/nexus-scratch/ihbas/repos_claim_cache/django__django/444b6da7cc229a58a2c476a52e45233001dc7073"
#   },
#   "checks": [
#     {
#       "label": "import_check",
#       "passed": false,
#       "action": "Verify module path or update PYTHONPATH before running tests.",
#       "details": {
#         "error": "ModuleNotFoundError(\"No module named 'asgiref'\")",
#         "repo_path": "/fs/nexus-scratch/ihbas/repos_claim_cache/django__django/444b6da7cc229a58a2c476a52e45233001dc7073"
#       }
#     },
#     {
#       "label": "fixture_check",
#       "passed": true,
#       "action": null,
#       "details": {
#         "available_fixtures": [],
#         "count": 0
#       }
#     }
#   ]
# }

## ⚠️ NOTE: Signature Hints Unavailable
# Module import failed in host environment.
# **Use the grounding source_excerpt** in your plan context to find the actual function definition.
# Pay attention to:
# - The FIRST parameter (especially if it's 'self' or requires creating an object)
# - All required parameters and their order

## CRITICAL: Learn from Previous Failure

# Previous attempt failed with:
# assertion_failure: BUG and GOLD both fail, but with DIFFERENT error types:

def test_claim_c1(capsys):
    # Given: sitemap has no items but lastmod is a callable that requires item input
    class TestSitemap(Sitemap):
        def items(self):
            return []

        def lastmod(self, item):
            return item.lastmod

    sitemap = TestSitemap()

    # When: calling get_latest_lastmod on Sitemap subclass
    result = sitemap.get_latest_lastmod()

    # Then: returns None instead of raising ValueError
    # Checklist:
    # Test returns None when sitemap is empty and lastmod is callable.
    assert result is None  # Test returns None when sitemap is empty and lastmod is callable.

    # Test does not raise ValueError when sitemap is empty and lastmod is callable.
    with pytest.raises(ValueError):
        max([sitemap.lastmod(item) for item in sitemap.items()])

    # Test handles edge cases correctly.
    # Test with an empty sitemap
    assert sitemap.get_latest_lastmod() is None

    # Test with a non-callable lastmod method
    class TestSitemapNonCallable(Sitemap):
        def items(self):
            return []

        def lastmod(self, item):
            return "non-callable"

    sitemap_non_callable = TestSitemapNonCallable()
    with pytest.raises(TypeError):
        sitemap_non_callable.get_latest_lastmod()

    # Test with a lastmod method that raises an exception
    class TestSitemapRaisesException(Sitemap):
        def items(self):
            return []

        def lastmod(self, item):
            raise Exception("Test exception")

    sitemap_raises_exception = TestSitemapRaisesException()
    with pytest.raises(Exception):
        sitemap_raises_exception.get_latest_lastmod()
