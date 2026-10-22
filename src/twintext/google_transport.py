"""Bounded, redirect-free HTTP requests with a reusable connection pool."""

import ssl
import weakref
from contextlib import contextmanager
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import getproxies, proxy_bypass

import httpx


class BoundedResponse:
    def __init__(self, response):
        self.response = response

    def read(self, maximum):
        output = bytearray()
        for chunk in self.response.iter_bytes(chunk_size=65536):
            output.extend(chunk[:maximum - len(output)])
            if len(output) >= maximum:
                break
        return bytes(output)


class GoogleTransport:
    def __init__(self):
        self.client = None
        self.cleanup = None

    @contextmanager
    def open(self, request, timeout):
        try:
            if self.client is None:
                proxies = getproxies()  # Includes Windows system proxy settings.
                host = urlsplit(request.full_url).hostname or ""
                proxy = None if proxy_bypass(host) else proxies.get("https") or proxies.get("all")
                self.client = httpx.Client(
                    follow_redirects=False, trust_env=True, proxy=proxy,
                    verify=ssl.create_default_context(),
                    limits=httpx.Limits(max_connections=1, max_keepalive_connections=1,
                                       keepalive_expiry=60),
                )
                self.cleanup = weakref.finalize(self, self.client.close)
            # Pool connections, without introducing persistent Google cookies.
            self.client.cookies.clear()
            with self.client.stream("GET", request.full_url, timeout=timeout) as response:
                if not 200 <= response.status_code < 300:
                    raise HTTPError(request.full_url, response.status_code,
                                    "Google Free HTTP error", response.headers, None)
                yield BoundedResponse(response)
        except HTTPError:
            raise
        except httpx.TimeoutException:
            raise TimeoutError("Google Free request timed out.") from None
        except httpx.HTTPError as exc:
            cause = exc
            while cause is not None:
                if isinstance(cause, ssl.SSLCertVerificationError):
                    raise URLError(cause) from None
                cause = cause.__cause__
            raise URLError("Google Free network request failed.") from None
        except (httpx.InvalidURL, ValueError, OSError):
            raise URLError("Google Free network configuration failed.") from None
        finally:
            if self.client is not None:
                self.client.cookies.clear()

    def close(self):
        if self.client is not None:
            self.cleanup()
            self.client = None
