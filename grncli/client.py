from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any

import httpx

if TYPE_CHECKING:
    from grncli.session import Session

LOG = logging.getLogger(__name__)

_STATUS_MESSAGES = {
    400: 'Bad Request',
    401: 'Unauthorized',
    403: 'Forbidden',
    404: 'Not Found',
    409: 'Conflict',
    429: 'Too Many Requests',
    500: 'Internal Server Error',
    502: 'Bad Gateway',
    503: 'Service Unavailable',
    504: 'Gateway Timeout',
}


def _format_error(response: httpx.Response) -> str:
    status = response.status_code
    status_text = _STATUS_MESSAGES.get(status, 'Error')

    # Try to extract message from JSON response
    detail = ''
    try:
        data = response.json()
        if isinstance(data, dict):
            detail = (
                data.get('message')
                or data.get('error')
                or data.get('detail')
                or ''
            )
            # VKS API sometimes returns errors in 'errors' array
            if not detail and 'errors' in data:
                errors = data['errors']
                if isinstance(errors, list) and errors:
                    detail = errors[0].get('message', '')
    except Exception:
        detail = response.text.strip() if response.text else ''

    if detail:
        return f"API error (HTTP {status} {status_text}): {detail}"
    return f"API error (HTTP {status} {status_text})"


# Retry config
MAX_RETRIES = 3
RETRY_BASE_DELAY = 1  # seconds
RETRYABLE_STATUS_CODES = {500, 502, 503, 504}


class GreenodeClient:
    """HTTP client for Greenode APIs with auto token refresh and retry."""

    def __init__(self, session: Session, service_name: str):
        self._session = session
        self._base_url = session.get_endpoint(service_name)
        self._token_manager = session.get_token_manager()
        self._timeout = session.get_timeout()
        self._verify = session.verify_ssl

    def _headers(self, token: str) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    def _request(
        self,
        method: str,
        path: str,
        raw: bool = False,
        **kwargs: Any,
    ) -> Any:
        url = f"{self._base_url}{path}"
        token = self._token_manager.get_token()
        last_error = None

        for attempt in range(MAX_RETRIES + 1):
            try:
                response = httpx.request(
                    method, url, headers=self._headers(token),
                    timeout=self._timeout, verify=self._verify, **kwargs
                )
            except (httpx.ConnectTimeout, httpx.ReadTimeout,
                    httpx.ConnectError) as e:
                last_error = e
                if attempt < MAX_RETRIES:
                    delay = RETRY_BASE_DELAY * (2 ** attempt)
                    LOG.debug(
                        "Request timeout/error (attempt %d/%d), "
                        "retrying in %ds: %s",
                        attempt + 1, MAX_RETRIES + 1, delay, e,
                    )
                    time.sleep(delay)
                    continue
                raise RuntimeError(
                    f"Request failed after {MAX_RETRIES + 1} attempts: {e}"
                ) from e

            # 401 — refresh token and retry once
            if response.status_code == 401:
                token = self._token_manager.refresh_token()
                response = httpx.request(
                    method, url, headers=self._headers(token),
                    timeout=self._timeout, verify=self._verify, **kwargs
                )

            # Retryable server errors (5xx)
            if response.status_code in RETRYABLE_STATUS_CODES:
                if attempt < MAX_RETRIES:
                    delay = RETRY_BASE_DELAY * (2 ** attempt)
                    LOG.debug(
                        "Server error %d (attempt %d/%d), "
                        "retrying in %ds",
                        response.status_code,
                        attempt + 1, MAX_RETRIES + 1, delay,
                    )
                    time.sleep(delay)
                    continue

            # Non-retryable errors
            if response.status_code >= 400:
                raise RuntimeError(_format_error(response))

            if raw:
                return response.text
            return response.json()

        # Should not reach here, but just in case
        raise RuntimeError(
            f"Request failed after {MAX_RETRIES + 1} attempts"
        )

    def get(self, path: str, **kwargs: Any) -> Any:
        return self._request("GET", path, **kwargs)

    def post(self, path: str, **kwargs: Any) -> Any:
        return self._request("POST", path, **kwargs)

    def put(self, path: str, **kwargs: Any) -> Any:
        return self._request("PUT", path, **kwargs)

    def delete(self, path: str, **kwargs: Any) -> Any:
        return self._request("DELETE", path, **kwargs)

    def get_raw(self, path: str, **kwargs: Any) -> str:
        return self._request("GET", path, raw=True, **kwargs)

    def get_all_pages(
        self, path: str, page_size: int = 50, **kwargs: Any,
    ) -> dict[str, Any]:
        """Fetch all pages and merge items into a single result."""
        all_items = []
        page = 0
        while True:
            params = kwargs.pop('params', {}) if 'params' in kwargs else {}
            params['page'] = page
            params['pageSize'] = page_size
            result = self.get(path, params=params, **kwargs)
            items = result.get('items', [])
            all_items.extend(items)
            total = result.get('total', 0)
            if len(all_items) >= total or not items:
                break
            page += 1
        return {'items': all_items, 'total': len(all_items)}
