"""Stage receipts for the public, read-only candle collector.

The caller's owned process supplies the hard wall-clock limit (including blocked
OS DNS calls). This module applies a shared soft deadline and finite GET budget.
It never handles orders, caches, credentials, or fallback data.
"""
from __future__ import annotations
from contextlib import contextmanager
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import http.client
import json
import math
import re
import socket
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request


class CaptureFailure(RuntimeError):
    def __init__(self, stage, error_type):
        self.stage, self.error_type = stage, error_type
        super().__init__("public_capture_" + stage.lower() + "_failed:" + error_type)


class Trace:
    def __init__(self, sink, *, total_seconds=150, max_calls=170, clock=time.monotonic,
                 sleep=time.sleep, wall_clock=time.time):
        if type(total_seconds) not in {int,float} or not math.isfinite(total_seconds) or not 0 < total_seconds <= 150:
            raise ValueError("capture_total_deadline_invalid")
        if type(max_calls) is not int or not 1 <= max_calls <= 170:
            raise ValueError("capture_request_budget_invalid")
        self.sink, self.clock, self.sleep, self.wall_clock = sink, clock, sleep, wall_clock
        self.started = clock(); self.deadline = self.started + total_seconds
        self.max_calls, self.calls, self.stage_name = max_calls, 0, "NOT_STARTED"

    def emit(self, stage, state, **fields):
        # No request/proxy headers, URL, response body, or raw error text.
        row = {"schema_version":"public-capture-stage-v1", "at":datetime.now(timezone.utc).isoformat(),
               "elapsed_seconds":max(0,self.clock()-self.started), "call":self.calls,
               "stage":stage, "state":state, **fields}
        self.sink.write(json.dumps(row,sort_keys=True,allow_nan=False)+"\n"); self.sink.flush()

    def remaining(self):
        remaining = self.deadline - self.clock()
        if remaining <= 0:
            self.emit("TOTAL_DEADLINE", "FAILED", error_type="TimeoutError")
            raise CaptureFailure("TOTAL_DEADLINE", "TimeoutError")
        return min(20,remaining)

    def claim(self):
        self.remaining()
        if self.calls >= self.max_calls:
            self.emit("REQUEST_BUDGET", "FAILED", error_type="CallLimit")
            raise CaptureFailure("REQUEST_BUDGET", "CallLimit")
        self.calls += 1

    def wait_before_retry(self, delay, *, reason, failure):
        """Respect the full requested wait; never truncate it to fit a deadline."""
        if self.calls >= self.max_calls:
            self.claim()  # Preserve the existing REQUEST_BUDGET failure contract.
        remaining = self.deadline - self.clock()
        if delay >= remaining:
            self.emit("RETRY_WAIT", "SKIPPED", reason="INSUFFICIENT_TOTAL_BUDGET",
                      failed_stage=failure.stage, error_type=failure.error_type)
            raise failure from None
        until = self.clock() + delay
        self.emit("RETRY_WAIT", "STARTED", wait_seconds=delay, reason=reason,
                  original_failed_stage=failure.stage, original_error_type=failure.error_type)
        try:
            # An interrupted/injected sleep must not cause an early retry.
            while (left := until - self.clock()) > 0:
                if left >= self.deadline - self.clock():
                    raise TimeoutError()
                self.sleep(left)
            if self.clock() >= self.deadline:
                raise TimeoutError()
        except Exception as error:
            self.emit("RETRY_WAIT", "FAILED", reason="WAIT_DID_NOT_COMPLETE_WITHIN_BUDGET",
                      wait_error_type=type(error).__name__, failed_stage=failure.stage,
                      error_type=failure.error_type)
            raise failure from None
        self.emit("RETRY_WAIT", "SUCCEEDED", original_failed_stage=failure.stage, original_error_type=failure.error_type)

    @contextmanager
    def phase(self, name):
        self.remaining(); self.stage_name = name; self.emit(name,"STARTED")
        try:
            yield
            self.remaining()
        except CaptureFailure:
            raise
        except Exception as error:
            self.emit(name,"FAILED",error_type=type(error).__name__)
            raise CaptureFailure(name,type(error).__name__) from None
        else:
            self.emit(name,"SUCCEEDED")


def traced_connection(trace, address, timeout, source_address=None):
    host, port = address
    with trace.phase("DNS"):
        addresses = socket.getaddrinfo(host, port, 0, socket.SOCK_STREAM)
    last = None
    for family, kind, protocol, _, sockaddr in addresses:
        sock = None
        try:
            with trace.phase("CONNECT"):
                sock = socket.socket(family,kind,protocol)
                sock.settimeout(min(timeout,trace.remaining()))
                if source_address: sock.bind(source_address)
                sock.connect(sockaddr)
            return sock
        except CaptureFailure as error:
            last = error
            if sock is not None: sock.close()
            if error.stage == "TOTAL_DEADLINE": raise
    raise last or CaptureFailure("DNS", "NoAddresses")


class TracedHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, host, *, trace, **kwargs):
        super().__init__(host, **kwargs)
        self.trace = trace
        self._create_connection = lambda address, timeout, source_address=None: traced_connection(trace,address,timeout,source_address)

    def _tunnel(self):
        with self.trace.phase("PROXY_HTTP_CONNECT"):
            return super()._tunnel()

    def connect(self):
        http.client.HTTPConnection.connect(self)
        hostname = self._tunnel_host or self.host
        try:
            with self.trace.phase("TLS"):
                self.sock.settimeout(self.trace.remaining())
                self.sock = self._context.wrap_socket(self.sock,server_hostname=hostname)
        except Exception:
            self.close(); raise

    def request(self, *args, **kwargs):
        # Connect first so nested DNS/TCP/TLS failures retain their own stages.
        if self.sock is None: self.connect()
        with self.trace.phase("HTTP_REQUEST"):
            self.sock.settimeout(self.trace.remaining())
            return super().request(*args, **kwargs)

    def getresponse(self):
        with self.trace.phase("HTTP_HEADERS"):
            self.sock.settimeout(self.trace.remaining())
            return super().getresponse()


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise CaptureFailure("HTTP_HEADERS", "RedirectRejected")


class TracedHTTPSHandler(urllib.request.HTTPSHandler):
    def __init__(self, trace):
        super().__init__(context=ssl.create_default_context()); self.trace = trace
    def https_open(self, request):
        return self.do_open(lambda host, **kwargs: TracedHTTPSConnection(host,trace=self.trace,**kwargs),
                            request, context=self._context)


def _retry_after(headers, wall_clock):
    """Return sanitized seconds/reason; raw header text never enters diagnostics."""
    if headers is None:
        return None, "MISSING_RETRY_AFTER"
    values = headers.get_all("Retry-After") if hasattr(headers, "get_all") else [headers.get("Retry-After")]
    if not values or values == [None]:
        return None, "MISSING_RETRY_AFTER"
    if len(values) != 1 or type(values[0]) is not str:
        return None, "INVALID_RETRY_AFTER"
    value = values[0].strip()
    if re.fullmatch(r"[0-9]+", value):
        # The shared hard maximum is 150s. Huge valid values must stop, not
        # overflow into a parse failure and an early fallback retry.
        digits = value.lstrip("0") or "0"
        if len(digits) > 3 or int(digits) > 150:
            return 151, "RETRY_AFTER_EXCEEDS_MAXIMUM_BUDGET"
        return int(digits), "RETRY_AFTER_SECONDS"
    try:
        if len(value) > 128:
            raise ValueError()
        date = parsedate_to_datetime(value)
        if date.tzinfo is None:  # HTTP's obsolete asctime form means UTC.
            if not re.fullmatch(r"[A-Za-z]{3} [A-Za-z]{3} [ \d]\d \d\d:\d\d:\d\d \d{4}", value):
                raise ValueError()
            date = date.replace(tzinfo=timezone.utc)
        if date.utcoffset().total_seconds() != 0:
            raise ValueError()
        seconds = date.timestamp() - wall_clock()
        if not math.isfinite(seconds):
            raise ValueError()
        if seconds <= 0:
            return None, "EXPIRED_RETRY_AFTER_DATE"
        return seconds, "RETRY_AFTER_HTTP_DATE"
    except (ValueError, TypeError, OverflowError):
        return None, "INVALID_RETRY_AFTER"


def get_public_page(url, trace, *, max_attempts=1, opener=None):
    parsed = urllib.parse.urlsplit(url)
    if (parsed.scheme != "https" or parsed.netloc != "www.okx.com" or parsed.path != "/api/v5/market/history-candles"
            or parsed.fragment or set(urllib.parse.parse_qs(parsed.query)) != {"instId","bar","limit","after"}):
        raise ValueError("capture_only_explicit_public_candle_route_allowed")
    if type(max_attempts) is not int or not 1 <= max_attempts <= 3:
        raise ValueError("capture_attempt_budget_invalid")
    opener = opener or urllib.request.build_opener(NoRedirect(),TracedHTTPSHandler(trace))
    for attempt in range(1,max_attempts+1):
        retry_delay, retry_reason = None, "NO_HTTP_RETRY_AFTER"
        trace.claim(); trace.emit("GET_ATTEMPT","STARTED",attempt=attempt)
        try:
            request = urllib.request.Request(url,headers={"User-Agent":"Hakimi-Research-Public-Capture/2"},method="GET")
            try:
                response = opener.open(request,timeout=trace.remaining())
            except urllib.error.HTTPError as error:
                trace.emit("HTTP_HEADERS","FAILED",status_code=error.code)
                if error.code in {429, 502, 503, 504} and attempt < max_attempts:
                    retry_delay, retry_reason = _retry_after(error.headers, trace.wall_clock)
                error.close()
                raise CaptureFailure("HTTP_HEADERS", "HTTP_"+str(error.code)) from None
            with response:
                if response.status != 200 or response.url != url:
                    raise CaptureFailure("HTTP_HEADERS","UnexpectedResponse")
                with trace.phase("RESPONSE_READ"):
                    raw = response.read(8*1024*1024+1)
                if len(raw) > 8*1024*1024:
                    raise CaptureFailure("CONTENT_VALIDATION","SizeLimit")
            trace.emit("GET_ATTEMPT","SUCCEEDED",attempt=attempt)
            return raw
        except CaptureFailure as error:
            trace.emit("GET_ATTEMPT","FAILED",attempt=attempt,failed_stage=error.stage,error_type=error.error_type)
            retryable = error.stage in {"DNS","CONNECT","RESPONSE_READ"} or error.error_type in {"HTTP_429","HTTP_502","HTTP_503","HTTP_504"}
            retryable = retryable or (error.stage in {"TLS","HTTP_REQUEST","HTTP_HEADERS","PROXY_HTTP_CONNECT"}
                and error.error_type in {"TimeoutError","ConnectionResetError","RemoteDisconnected","BrokenPipeError"})
            if not retryable or attempt == max_attempts: raise
            # Explicit retries only: deterministic 1s, then 2s backoff when no
            # valid server delay exists. All waiting shares the 150s deadline.
            trace.wait_before_retry(retry_delay if retry_delay is not None else 2 ** (attempt - 1),
                                    reason=retry_reason, failure=error)
        except Exception as error:
            trace.emit("GET_ATTEMPT","FAILED",attempt=attempt,failed_stage="UNCLASSIFIED_TRANSPORT",error_type=type(error).__name__)
            raise CaptureFailure("UNCLASSIFIED_TRANSPORT",type(error).__name__) from None
