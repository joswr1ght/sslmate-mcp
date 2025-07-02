import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from sslmate_mcp import SSLMateClient, SSLMateCertificate, SSLMateMCPServer


@pytest.fixture
def ssl_mate_client():
    """Fixture for SSLMateClient instance"""
    return SSLMateClient("test-api-key")


@pytest.fixture
def sample_certificate_data():
    """Fixture for sample certificate data"""
    return {
        "id": "cert-12345",
        "common_name": "example.com",
        "subject_alt_names": ["www.example.com", "api.example.com"],
        "issuer": "Let's Encrypt Authority X3",
        "serial_number": "03:5D:A7:E5:5F:82:8F:3C:0D:1B:7C:1F:2E:4A:8D:9B:3C:2F",
        "not_before": "2024-01-01T00:00:00Z",
        "not_after": "2024-04-01T00:00:00Z",
        "fingerprint_sha1": "A1:B2:C3:D4:E5:F6:07:08:09:10:11:12:13:14:15:16:17:18:19:20",
        "fingerprint_sha256": "A1:B2:C3:D4:E5:F6:07:08:09:10:11:12:13:14:15:16:17:18:19:20:21:22:23:24:25:26:27:28:29:30:31:32",
        "status": "active"
    }


class TestSSLMateCertificate:
    """Test cases for SSLMateCertificate model"""

    def test_certificate_creation(self, sample_certificate_data):
        """Test creating a certificate from data"""
        cert = SSLMateCertificate(**sample_certificate_data)

        assert cert.id == "cert-12345"
        assert cert.common_name == "example.com"
        assert len(cert.subject_alt_names) == 2
        assert cert.issuer == "Let's Encrypt Authority X3"
        assert cert.status == "active"

    def test_certificate_with_empty_san(self):
        """Test certificate creation with empty subject alt names"""
        data = {
            "id": "cert-123",
            "common_name": "test.com",
            "issuer": "Test CA",
            "serial_number": "123456",
            "not_before": "2024-01-01T00:00:00Z",
            "not_after": "2024-04-01T00:00:00Z",
            "fingerprint_sha1": "A1:B2:C3:D4:E5:F6:07:08:09:10:11:12:13:14:15:16:17:18:19:20",
            "fingerprint_sha256": "A1:B2:C3:D4:E5:F6:07:08:09:10:11:12:13:14:15:16:17:18:19:20:21:22:23:24:25:26:27:28:29:30:31:32",
            "status": "active"
        }

        cert = SSLMateCertificate(**data)
        assert cert.subject_alt_names == []


class TestSSLMateClient:
    """Test cases for SSLMateClient"""

    @pytest.mark.asyncio
    async def test_search_certificates_success(self, ssl_mate_client, sample_certificate_data):
        """Test successful certificate search"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "certificates": [sample_certificate_data]
        }
        mock_response.raise_for_status.return_value = None

        with patch.object(ssl_mate_client.client, 'get', return_value=mock_response) as mock_get:
            certificates = await ssl_mate_client.search_certificates("example.com")

            assert len(certificates) == 1
            assert certificates[0].id == "cert-12345"
            assert certificates[0].common_name == "example.com"

            mock_get.assert_called_once_with(
                "/certificates/search",
                params={
                    "q": "example.com",
                    "limit": 100,
                    "include_expired": False
                }
            )

    @pytest.mark.asyncio
    async def test_search_certificates_with_options(self, ssl_mate_client, sample_certificate_data):
        """Test certificate search with custom options"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "certificates": [sample_certificate_data]
        }
        mock_response.raise_for_status.return_value = None

        with patch.object(ssl_mate_client.client, 'get', return_value=mock_response) as mock_get:
            certificates = await ssl_mate_client.search_certificates(
                "example.com",
                limit=50,
                include_expired=True
            )

            mock_get.assert_called_once_with(
                "/certificates/search",
                params={
                    "q": "example.com",
                    "limit": 50,
                    "include_expired": True
                }
            )

    @pytest.mark.asyncio
    async def test_search_certificates_http_error(self, ssl_mate_client):
        """Test certificate search with HTTP error"""
        with patch.object(ssl_mate_client.client, 'get') as mock_get:
            mock_get.side_effect = httpx.HTTPError("API Error")

            with pytest.raises(httpx.HTTPError):
                await ssl_mate_client.search_certificates("example.com")

    @pytest.mark.asyncio
    async def test_get_certificate_details_success(self, ssl_mate_client, sample_certificate_data):
        """Test successful certificate details retrieval"""
        mock_response = MagicMock()
        mock_response.json.return_value = sample_certificate_data
        mock_response.raise_for_status.return_value = None

        with patch.object(ssl_mate_client.client, 'get', return_value=mock_response) as mock_get:
            certificate = await ssl_mate_client.get_certificate_details("cert-12345")

            assert certificate is not None
            assert certificate.id == "cert-12345"
            assert certificate.common_name == "example.com"

            mock_get.assert_called_once_with("/certificates/cert-12345")

    @pytest.mark.asyncio
    async def test_get_certificate_details_not_found(self, ssl_mate_client):
        """Test certificate details retrieval when certificate not found"""
        with patch.object(ssl_mate_client.client, 'get') as mock_get:
            mock_get.side_effect = httpx.HTTPError("Not Found")

            certificate = await ssl_mate_client.get_certificate_details("cert-nonexistent")
            assert certificate is None

    @pytest.mark.asyncio
    async def test_client_close(self, ssl_mate_client):
        """Test client cleanup"""
        with patch.object(ssl_mate_client.client, 'aclose') as mock_close:
            await ssl_mate_client.close()
            mock_close.assert_called_once()


class TestSSLMateMCPServer:
    """Test cases for SSLMateMCPServer"""

    @pytest.fixture
    def mcp_server(self):
        """Fixture for MCP server instance"""
        return SSLMateMCPServer("test-api-key", 8080)

    def test_server_initialization(self, mcp_server):
        """Test server initialization"""
        assert mcp_server.api_key == "test-api-key"
        assert mcp_server.port == 8080
        assert mcp_server.sslmate_client is not None
        assert mcp_server.mcp_server is not None

    @pytest.mark.asyncio
    async def test_server_start_stop(self, mcp_server):
        """Test server start and stop"""
        with patch.object(mcp_server.mcp_server, 'start') as mock_start, \
             patch.object(mcp_server.mcp_server, 'stop') as mock_stop, \
             patch.object(mcp_server.sslmate_client, 'close') as mock_close:

            await mcp_server.start()
            mock_start.assert_called_once_with(port=8080)

            await mcp_server.stop()
            mock_stop.assert_called_once()
            mock_close.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])
