"""Tests for Phase 1 Agent Farm tools.

Covers:
  - tools/web_fetch.py: fetch_html, fetch_pdf_bytes (httpx mocked)
  - tools/web_search.py: search_text, search_images (Tavily mocked)
"""

from __future__ import annotations

from unittest.mock import MagicMock, AsyncMock, patch

import httpx
import pytest


# ============================================================
# web_fetch
# ============================================================


class TestFetchHtml:
    async def test_success(self):
        from app.agent_farm.tools.web_fetch import fetch_html

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "<html><body>Hello</body></html>"
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.agent_farm.tools.web_fetch.httpx.AsyncClient",
                    return_value=mock_client):
            result = await fetch_html("https://example.com")

        assert result == "<html><body>Hello</body></html>"

    async def test_403_returns_none_immediately(self):
        from app.agent_farm.tools.web_fetch import fetch_html

        mock_resp = MagicMock()
        mock_resp.status_code = 403

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.agent_farm.tools.web_fetch.httpx.AsyncClient",
                    return_value=mock_client):
            result = await fetch_html("https://cabi.org/blocked")

        assert result is None
        # Should NOT retry — only 1 call
        assert mock_client.get.await_count == 1

    async def test_http_error_retries_then_returns_none(self):
        from app.agent_farm.tools.web_fetch import fetch_html

        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError(
                "Server error", request=MagicMock(), response=mock_resp,
            )
        )

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.agent_farm.tools.web_fetch.httpx.AsyncClient",
                    return_value=mock_client):
            result = await fetch_html("https://example.com/fail")

        assert result is None
        assert mock_client.get.await_count == 2  # _MAX_RETRIES = 2

    async def test_request_error_retries(self):
        from app.agent_farm.tools.web_fetch import fetch_html

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(
            side_effect=httpx.RequestError("Connection timeout"),
        )
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.agent_farm.tools.web_fetch.httpx.AsyncClient",
                    return_value=mock_client):
            result = await fetch_html("https://example.com/timeout")

        assert result is None
        assert mock_client.get.await_count == 2


class TestFetchPdfBytes:
    async def test_success_with_pdf_content_type(self):
        from app.agent_farm.tools.web_fetch import fetch_pdf_bytes

        pdf_content = b"%PDF-1.4 fake pdf content"
        mock_resp = MagicMock()
        mock_resp.headers = {"content-type": "application/pdf"}
        mock_resp.content = pdf_content
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.agent_farm.tools.web_fetch.httpx.AsyncClient",
                    return_value=mock_client):
            result = await fetch_pdf_bytes("https://fao.org/doc.pdf")

        assert result == pdf_content

    async def test_success_with_pdf_extension(self):
        from app.agent_farm.tools.web_fetch import fetch_pdf_bytes

        pdf_content = b"%PDF-1.4 data"
        mock_resp = MagicMock()
        mock_resp.headers = {"content-type": "application/octet-stream"}
        mock_resp.content = pdf_content
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.agent_farm.tools.web_fetch.httpx.AsyncClient",
                    return_value=mock_client):
            result = await fetch_pdf_bytes("https://fao.org/guide.pdf")

        assert result == pdf_content

    async def test_non_pdf_content_type_and_url_returns_none(self):
        from app.agent_farm.tools.web_fetch import fetch_pdf_bytes

        mock_resp = MagicMock()
        mock_resp.headers = {"content-type": "text/html"}
        mock_resp.content = b"<html>not a pdf</html>"
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.agent_farm.tools.web_fetch.httpx.AsyncClient",
                    return_value=mock_client):
            result = await fetch_pdf_bytes("https://example.com/page.html")

        assert result is None

    async def test_error_retries_then_returns_none(self):
        from app.agent_farm.tools.web_fetch import fetch_pdf_bytes

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(
            side_effect=httpx.RequestError("Network error"),
        )
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.agent_farm.tools.web_fetch.httpx.AsyncClient",
                    return_value=mock_client):
            result = await fetch_pdf_bytes("https://fao.org/doc.pdf")

        assert result is None
        assert mock_client.get.await_count == 2


# ============================================================
# web_search
# ============================================================


class TestSearchText:
    def test_success(self):
        mock_client = MagicMock()
        mock_client.search.return_value = {
            "results": [
                {"title": "Result 1", "url": "https://a.com", "content": "text", "score": 0.9},
                {"title": "Result 2", "url": "https://b.com", "content": "more", "score": 0.7},
            ]
        }

        with patch("app.agent_farm.tools.web_search._get_client",
                    return_value=mock_client):
            from app.agent_farm.tools.web_search import search_text
            results = search_text("cassava disease treatment")

        assert len(results) == 2
        assert results[0]["title"] == "Result 1"

    def test_include_domains_passed(self):
        mock_client = MagicMock()
        mock_client.search.return_value = {"results": []}

        with patch("app.agent_farm.tools.web_search._get_client",
                    return_value=mock_client):
            from app.agent_farm.tools.web_search import search_text
            search_text("query", include_domains=["fao.org"])

        call_kwargs = mock_client.search.call_args[1]
        assert call_kwargs["include_domains"] == ["fao.org"]

    def test_none_domains_become_empty_list(self):
        mock_client = MagicMock()
        mock_client.search.return_value = {"results": []}

        with patch("app.agent_farm.tools.web_search._get_client",
                    return_value=mock_client):
            from app.agent_farm.tools.web_search import search_text
            search_text("query")

        call_kwargs = mock_client.search.call_args[1]
        assert call_kwargs["include_domains"] == []
        assert call_kwargs["exclude_domains"] == []

    def test_search_depth_is_advanced(self):
        mock_client = MagicMock()
        mock_client.search.return_value = {"results": []}

        with patch("app.agent_farm.tools.web_search._get_client",
                    return_value=mock_client):
            from app.agent_farm.tools.web_search import search_text
            search_text("query")

        call_kwargs = mock_client.search.call_args[1]
        assert call_kwargs["search_depth"] == "advanced"

    def test_exception_returns_empty_list(self):
        mock_client = MagicMock()
        mock_client.search.side_effect = Exception("API error")

        with patch("app.agent_farm.tools.web_search._get_client",
                    return_value=mock_client):
            from app.agent_farm.tools.web_search import search_text
            results = search_text("query")

        assert results == []

    def test_max_results_passed(self):
        mock_client = MagicMock()
        mock_client.search.return_value = {"results": []}

        with patch("app.agent_farm.tools.web_search._get_client",
                    return_value=mock_client):
            from app.agent_farm.tools.web_search import search_text
            search_text("query", max_results=3)

        call_kwargs = mock_client.search.call_args[1]
        assert call_kwargs["max_results"] == 3


class TestSearchImages:
    def test_string_urls_normalized(self):
        mock_client = MagicMock()
        mock_client.search.return_value = {
            "images": [
                "https://example.com/img1.jpg",
                "https://example.com/img2.png",
            ]
        }

        with patch("app.agent_farm.tools.web_search._get_client",
                    return_value=mock_client):
            from app.agent_farm.tools.web_search import search_images
            results = search_images("cassava disease photo")

        assert len(results) == 2
        assert results[0] == {"url": "https://example.com/img1.jpg"}

    def test_dict_urls_preserved(self):
        mock_client = MagicMock()
        mock_client.search.return_value = {
            "images": [
                {"url": "https://example.com/img.jpg", "description": "Photo"},
            ]
        }

        with patch("app.agent_farm.tools.web_search._get_client",
                    return_value=mock_client):
            from app.agent_farm.tools.web_search import search_images
            results = search_images("query")

        assert len(results) == 1
        assert results[0]["url"] == "https://example.com/img.jpg"
        assert results[0]["description"] == "Photo"

    def test_mixed_types(self):
        mock_client = MagicMock()
        mock_client.search.return_value = {
            "images": [
                "https://example.com/str.jpg",
                {"url": "https://example.com/dict.jpg"},
            ]
        }

        with patch("app.agent_farm.tools.web_search._get_client",
                    return_value=mock_client):
            from app.agent_farm.tools.web_search import search_images
            results = search_images("query")

        assert len(results) == 2

    def test_exception_returns_empty_list(self):
        mock_client = MagicMock()
        mock_client.search.side_effect = Exception("API key invalid")

        with patch("app.agent_farm.tools.web_search._get_client",
                    return_value=mock_client):
            from app.agent_farm.tools.web_search import search_images
            results = search_images("query")

        assert results == []

    def test_search_depth_is_basic(self):
        mock_client = MagicMock()
        mock_client.search.return_value = {"images": []}

        with patch("app.agent_farm.tools.web_search._get_client",
                    return_value=mock_client):
            from app.agent_farm.tools.web_search import search_images
            search_images("query")

        call_kwargs = mock_client.search.call_args[1]
        assert call_kwargs["search_depth"] == "basic"
        assert call_kwargs["include_images"] is True


class TestGetClient:
    def test_raises_without_api_key(self):
        with patch("app.agent_farm.tools.web_search.settings") as mock_settings:
            mock_settings.tavily_api_key = ""
            from app.agent_farm.tools.web_search import _get_client
            with pytest.raises(RuntimeError, match="TAVILY_API_KEY"):
                _get_client()

    def test_raises_with_none_key(self):
        with patch("app.agent_farm.tools.web_search.settings") as mock_settings:
            mock_settings.tavily_api_key = None
            from app.agent_farm.tools.web_search import _get_client
            with pytest.raises(RuntimeError):
                _get_client()
