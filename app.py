
_BUNDLE_VERSION = 'cff6d059b86988e15acf3d1ccbe1ec7cc02a3e225f2f44df2ecf3179f658e3dd'
_FRONTEND_SOURCES = {'frontend.settings': '"""Server-only frontend configuration; never return these values to the browser."""\n'
                      'import os\n'
                      'import re\n'
                      'from dataclasses import dataclass, field\n'
                      'from urllib.parse import urlsplit\n'
                      '\n'
                      'import requests\n'
                      'import streamlit as st\n'
                      '\n'
                      '\n'
                      'class ConfigurationError(requests.RequestException):\n'
                      '    """Intentionally contains no URL, key, password or upstream response."""\n'
                      '\n'
                      '\n'
                      'def secret(name, default=""):\n'
                      '    value = os.environ.get(name)\n'
                      '    if value is not None:\n'
                      '        return value\n'
                      '    try:\n'
                      '        return str(st.secrets.get(name, default))\n'
                      '    except (FileNotFoundError, KeyError, st.errors.StreamlitSecretNotFoundError):\n'
                      '        return default\n'
                      '\n'
                      '\n'
                      '@dataclass(frozen=True)\n'
                      'class Settings:\n'
                      '    api_url: str = field(repr=False)\n'
                      '    key_id: str = field(repr=False)\n'
                      '    signing_secret: str = field(repr=False)\n'
                      '    password_hash: str = field(repr=False)\n'
                      '    local_http: bool = False\n'
                      '\n'
                      '\n'
                      'def load_settings():\n'
                      '    url = secret("FINQ_API_URL", "http://127.0.0.1:8000").strip().rstrip("/")\n'
                      '    try:\n'
                      '        parsed = urlsplit(url)\n'
                      '        port = parsed.port\n'
                      '    except ValueError:\n'
                      '        raise ConfigurationError("The app connection needs setup.") from None\n'
                      '    local = parsed.hostname in {"127.0.0.1", "localhost", "::1"}\n'
                      '    allow_local = secret("FINQ_ALLOW_LOCAL_HTTP").lower() in {"1", "true", "yes"}\n'
                      '    if (parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or '
                      'parsed.password\n'
                      '            or parsed.query or parsed.fragment or parsed.path not in {"", "/"}\n'
                      '            or (parsed.scheme != "https" and not (local and allow_local))\n'
                      '            or any(c.isspace() for c in url) or (port is not None and not 1 <= port <= '
                      '65535)):\n'
                      '        raise ConfigurationError("The app connection needs secure setup.")\n'
                      '    key_id = secret("FINQ_API_KEY_ID")\n'
                      '    signing_secret = secret("FINQ_API_SIGNING_SECRET")\n'
                      '    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", key_id) or len(signing_secret.encode("utf-8")) '
                      '< 32:\n'
                      '        raise ConfigurationError("The app connection needs setup.")\n'
                      '    return Settings(url, key_id, signing_secret, secret("FINQ_APP_PASSWORD_HASH"), local and '
                      'parsed.scheme == "http")\n',
 'frontend.transport': '"""Authenticated server-to-server API calls, including exact multipart bytes."""\n'
                       'import hashlib\n'
                       'import hmac\n'
                       'import re\n'
                       'import secrets\n'
                       'import time\n'
                       'from urllib.parse import urlsplit\n'
                       '\n'
                       'import requests\n'
                       '\n'
                       'from frontend.settings import ConfigurationError, load_settings\n'
                       '\n'
                       '\n'
                       'MAX_BODY = 11 * 1024 * 1024\n'
                       '\n'
                       '\n'
                       'def sign_prepared(prepared, key_id, signing_secret, *, timestamp=None, nonce=None):\n'
                       '    body = prepared.body or b""\n'
                       '    if isinstance(body, str):\n'
                       '        body = body.encode("utf-8")\n'
                       '        prepared.body = body\n'
                       '        prepared.headers["Content-Length"] = str(len(body))\n'
                       '    if not isinstance(body, bytes) or len(body) > MAX_BODY:\n'
                       '        raise requests.RequestException("The upload is too large. Use a file smaller than 10 '
                       'MB.")\n'
                       '    timestamp = str(int(time.time()) if timestamp is None else timestamp)\n'
                       '    nonce = nonce or secrets.token_hex(16)\n'
                       '    canonical = "\\n".join(["finq-v1", prepared.method.upper(), prepared.path_url, timestamp, '
                       'nonce,\n'
                       '                            hashlib.sha256(body).hexdigest()])\n'
                       '    signature = hmac.new(signing_secret.encode("utf-8"), canonical.encode("utf-8"), '
                       'hashlib.sha256).hexdigest()\n'
                       '    prepared.headers.update({"X-Finq-Key-Id": key_id, "X-Finq-Timestamp": timestamp,\n'
                       '                             "X-Finq-Nonce": nonce, "X-Finq-Signature": signature})\n'
                       '    return prepared\n'
                       '\n'
                       '\n'
                       'def request(method, path, **kwargs):\n'
                       '    settings = load_settings()\n'
                       '    # Paths are application-defined. Never turn this into an arbitrary URL proxy.\n'
                       '    parsed = urlsplit(path)\n'
                       '    if (not isinstance(path, str) or not path.startswith("/") or path.startswith("//")\n'
                       '            or parsed.scheme or parsed.netloc or parsed.fragment or "\\\\" in path\n'
                       '            or re.search(r"[\\x00-\\x20\\x7f]", path)):\n'
                       '        raise ConfigurationError("The requested action is unavailable.")\n'
                       '    timeout = kwargs.pop("timeout", 20)\n'
                       '    if set(kwargs) - {"params", "data", "json", "files"}:\n'
                       '        raise ConfigurationError("The requested action is unavailable.")\n'
                       '    with requests.Session() as session:\n'
                       '        # Ignore ambient proxy/netrc settings; never send the signing key elsewhere.\n'
                       '        session.trust_env = False\n'
                       '        prepared = session.prepare_request(requests.Request(method.upper(), settings.api_url + '
                       'path, **kwargs))\n'
                       '        sign_prepared(prepared, settings.key_id, settings.signing_secret)\n'
                       '        try:\n'
                       '            response = session.send(prepared, timeout=timeout, allow_redirects=False, '
                       'verify=True)\n'
                       '        except requests.RequestException:\n'
                       '            raise requests.RequestException("The app is temporarily unavailable. Please try '
                       'again shortly.") from None\n'
                       '    if 300 <= response.status_code < 400:\n'
                       '        raise requests.RequestException("The app connection needs setup.")\n'
                       '    return response\n'
                       '\n'
                       '\n'
                       'def get(path, **kwargs):\n'
                       '    return request("GET", path, **kwargs)\n',
 'frontend.access': '"""A private-workspace login in front of every API request and report view."""\n'
                    'from collections import deque\n'
                    'import hashlib\n'
                    'import hmac\n'
                    'import re\n'
                    'import threading\n'
                    'import time\n'
                    '\n'
                    'import streamlit as st\n'
                    '\n'
                    'from frontend.settings import ConfigurationError, load_settings\n'
                    '\n'
                    '\n'
                    'ABSOLUTE_SESSION_SECONDS = 8 * 3600\n'
                    'IDLE_SESSION_SECONDS = 30 * 60\n'
                    'ATTEMPT_WINDOW_SECONDS = 15 * 60\n'
                    '_attempts = deque()\n'
                    '_lock = threading.RLock()\n'
                    '\n'
                    '\n'
                    'def valid_password_hash(value):\n'
                    '    return bool(re.fullmatch(r"pbkdf2_sha256\\$600000\\$[0-9a-f]{32}\\$[0-9a-f]{64}", value or '
                    '""))\n'
                    '\n'
                    '\n'
                    'def verify_password(password, encoded):\n'
                    '    if not valid_password_hash(encoded) or not isinstance(password, str) or len(password) > '
                    '1024:\n'
                    '        return False\n'
                    '    _, iterations, salt, expected = encoded.split("$")\n'
                    '    actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), '
                    'int(iterations)).hex()\n'
                    '    return hmac.compare_digest(actual, expected)\n'
                    '\n'
                    '\n'
                    'def _retry_after(now):\n'
                    '    with _lock:\n'
                    '        while _attempts and _attempts[0] <= now - ATTEMPT_WINDOW_SECONDS:\n'
                    '            _attempts.popleft()\n'
                    '        return max(0, int(_attempts[0] + ATTEMPT_WINDOW_SECONDS - now) + 1) if len(_attempts) >= '
                    '5 else 0\n'
                    '\n'
                    '\n'
                    'def _claim_attempt(now):\n'
                    '    with _lock:\n'
                    '        if _retry_after(now):\n'
                    '            return False\n'
                    '        _attempts.append(now)\n'
                    '        return True\n'
                    '\n'
                    '\n'
                    'def _logout():\n'
                    '    st.session_state.clear()\n'
                    '\n'
                    '\n'
                    'def _session_valid(settings, state, now):\n'
                    '    fingerprint = hashlib.sha256((settings.api_url + settings.key_id + settings.signing_secret + '
                    'settings.password_hash).encode()).hexdigest()\n'
                    '    return (state.get("fingerprint") == fingerprint and 0 <= now - state.get("created", 0) < '
                    'ABSOLUTE_SESSION_SECONDS\n'
                    '            and 0 <= now - state.get("active", 0) < IDLE_SESSION_SECONDS)\n'
                    '\n'
                    '\n'
                    'def require_session():\n'
                    '    """Fragments must not keep making calls after login expires or keys rotate."""\n'
                    '    try:\n'
                    '        valid = _session_valid(load_settings(), st.session_state.get("_access") or {}, '
                    'time.time())\n'
                    '    except ConfigurationError:\n'
                    '        valid = False\n'
                    '    if not valid:\n'
                    '        st.session_state.clear()\n'
                    '        st.rerun()\n'
                    '\n'
                    '\n'
                    '@st.fragment(run_every=30)\n'
                    'def session_watchdog():\n'
                    '    require_session()\n'
                    '\n'
                    '\n'
                    'def require_access():\n'
                    '    try:\n'
                    '        settings = load_settings()\n'
                    '        if not valid_password_hash(settings.password_hash):\n'
                    '            raise ConfigurationError("Sign-in needs setup.")\n'
                    '    except ConfigurationError:\n'
                    '        st.title("Intent to Outreach")\n'
                    '        st.error("The app needs secure connection and sign-in setup. Contact your '
                    'administrator.")\n'
                    '        st.stop()\n'
                    '    fingerprint = hashlib.sha256((settings.api_url + settings.key_id + settings.signing_secret + '
                    'settings.password_hash).encode()).hexdigest()\n'
                    '    now = time.time()\n'
                    '    state = st.session_state.get("_access") or {}\n'
                    '    authenticated = _session_valid(settings, state, now)\n'
                    '    if authenticated:\n'
                    '        st.session_state._access = {**state, "active": now}\n'
                    '        session_watchdog()\n'
                    '        with st.sidebar:\n'
                    '            st.button("Sign out", key="_sign_out", on_click=_logout)\n'
                    '        return\n'
                    '    if state:\n'
                    '        st.session_state.clear()\n'
                    '    st.title("Intent to Outreach")\n'
                    '    st.caption("Sign in to your team\'s campaign workspace.")\n'
                    '    wait = _retry_after(now)\n'
                    '    if wait:\n'
                    '        st.warning(f"Too many sign-in attempts. Try again in {(wait + 59) // 60} minutes.")\n'
                    '    with st.form("workspace_login", clear_on_submit=True):\n'
                    '        password = st.text_input("Workspace password", type="password", key="_login_password")\n'
                    '        submitted = st.form_submit_button("Sign in", type="primary", disabled=bool(wait))\n'
                    '    if submitted and _claim_attempt(now):\n'
                    '        okay = verify_password(password, settings.password_hash)\n'
                    '        st.session_state.pop("_login_password", None)\n'
                    '        if okay:\n'
                    '            with _lock:\n'
                    '                if now in _attempts:\n'
                    '                    _attempts.remove(now)\n'
                    '            st.session_state.clear()\n'
                    '            st.session_state._access = {"fingerprint": fingerprint, "created": now, "active": '
                    'now}\n'
                    '            st.rerun()\n'
                    '        st.error("The password was not accepted.")\n'
                    '    st.stop()\n',
 'frontend.presentation': '"""Non-secret presentation values; the backend remains authoritative."""\n'
                          'import ipaddress\n'
                          'import re\n'
                          'from urllib.parse import urlsplit\n'
                          '\n'
                          '\n'
                          '# The narrow client guard is intentional defense against a mismatched older API.\n'
                          '# Actual envelope enforcement belongs to the backend, never this UI.\n'
                          'TEST_RECIPIENT = "kartik.sharma@nextq.ai"\n'
                          'TEST_SENDER = "rahul.shah@nextquarter.com"\n'
                          'SENDER_NAMES = {"rahul.shah@nextquarter.com": "Rahul Shah", "ben.aspero@nextquarter.com": '
                          '"Ben Aspero",\n'
                          '                "puneet.gaur@nextquarter.com": "Puneet Gaur"}\n'
                          'SENDERS = tuple(SENDER_NAMES)\n'
                          '\n'
                          'INTERNAL_REPORT_FIELDS = frozenset({\n'
                          '    "Revenue Confidence", "Revenue Explanation", "Revenue Estimate USD", "Topic ID", "Metro '
                          'Country", "Metro State",\n'
                          '    "Model Roles", "model_roles", "Campaign ID", "Campaign Id", "campaign_id", "Run ID", '
                          '"Run Id", "run_id",\n'
                          '    "Export Version", "export_version", "Policy Version", "policy_version", "Prompt '
                          'Version", "prompt_version",\n'
                          '    "Repair Attempt", "repair_attempt", "attempt",\n'
                          '})\n'
                          '\n'
                          '\n'
                          'def normalize_customer_website(value):\n'
                          '    """Immediate form feedback only; API repeats authoritative validation."""\n'
                          '    if not isinstance(value, str) or not value.strip():\n'
                          '        raise ValueError("Enter a public customer website.")\n'
                          '    value = value.strip()\n'
                          '    if any(c.isspace() for c in value) or "@" in value or "*" in value:\n'
                          '        raise ValueError("Enter a public customer website.")\n'
                          '    try:\n'
                          '        parsed = urlsplit(value if "://" in value else "//" + value)\n'
                          '        if parsed.scheme and parsed.scheme.lower() not in {"http", "https"}:\n'
                          '            raise ValueError()\n'
                          '        hostname = (parsed.hostname or '
                          '"").rstrip(".").lower().encode("idna").decode("ascii")\n'
                          '        parsed.port\n'
                          '    except (ValueError, UnicodeError):\n'
                          '        raise ValueError("Enter a public customer website.") from None\n'
                          '    hostname = hostname.removeprefix("www.")\n'
                          '    try:\n'
                          '        ipaddress.ip_address(hostname)\n'
                          '    except ValueError:\n'
                          '        pass\n'
                          '    else:\n'
                          '        raise ValueError("Enter a public customer website.")\n'
                          '    labels = hostname.split(".")\n'
                          '    private = ("localhost", "local", "localdomain", "internal", "lan", "home", "home.arpa", '
                          '"onion", "invalid")\n'
                          '    if (len(hostname) > 253 or len(labels) < 2\n'
                          '            or any(not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", part) for part '
                          'in labels)\n'
                          '            or not re.fullmatch(r"(?:[a-z]{2,63}|xn--[a-z0-9-]+)", labels[-1])\n'
                          '            or any(hostname == p or hostname.endswith("." + p) for p in private)):\n'
                          '        raise ValueError("Enter a public customer website.")\n'
                          '    return "https://" + hostname\n',
 'frontend.state': '"""Wizard state transformations, independent of Streamlit widgets."""\n'
                   'import re\n'
                   '\n'
                   'DEFAULT_DRAFT = {\n'
                   '    "industries": [], "sizes": [], "revenue_tiers": [], "topics": [], "countries": [],\n'
                   '    "fill_revenue": True, "include_unknown_revenue": True,\n'
                   '    "company_score_min": 70, "company_score_max": 100,\n'
                   '    "metro_score_min": 0, "metro_score_max": 100,\n'
                   '    "suppressed_domains": [], "suppression_list_ids": [], "exclude_edu": False,\n'
                   '    "topic_mappings": [],\n'
                   '}\n'
                   '\n'
                   'def migrate_draft(old, options):\n'
                   '    """Clear obsolete filters and translate the former employee categories."""\n'
                   '    draft = {key: old.get(key, value.copy() if isinstance(value, list) else value)\n'
                   '             for key, value in DEFAULT_DRAFT.items()}\n'
                   '    draft.update(fill_revenue=True, include_unknown_revenue=True)\n'
                   '    notices = []\n'
                   '    valid_tiers = {tier["id"] for tier in options["revenue_tiers"]}\n'
                   '    retained = [tier for tier in draft["revenue_tiers"] if tier in valid_tiers]\n'
                   '    if old.get("revenue_bands") or retained != draft["revenue_tiers"]:\n'
                   '        notices.append("Revenue tiers have changed. Your old revenue selections were cleared; '
                   'please select the new tiers.")\n'
                   '    draft["revenue_tiers"] = retained\n'
                   '    labels = options["size_bands"]\n'
                   '    aliases = {"1-9": [0], "10-49": [1], "50-199": [2], "200-999": [3, 4],\n'
                   '               "200-499": [3], "500-999": [4], "1000-4999": [5], "5000-10000": [6], "10000+": '
                   '[7]}\n'
                   '    sizes = []\n'
                   '    for value in draft["sizes"]:\n'
                   '        if value in labels:\n'
                   '            sizes.append(value)\n'
                   '            continue\n'
                   '        compact = re.sub(r"[\\s,]", "", value.replace("–", "-").replace("—", "-").replace("â€“", '
                   '"-"))\n'
                   '        sizes.extend(labels[index] for index in aliases.get(compact, []) if index < len(labels))\n'
                   '    draft["sizes"] = list(dict.fromkeys(sizes))\n'
                   '    if draft["sizes"] != old.get("sizes", []):\n'
                   '        notices.append("Employee selections were updated. The old 200–999 group is now Medium and '
                   'Medium-Large.")\n'
                   '    draft["countries"] = [country for country in draft["countries"] if country in '
                   'options["countries"]]\n'
                   '    return draft, notices\n'
                   '\n'
                   'def regional_countries(regions, selected_regions, manual_additions=(), manual_removals=()):\n'
                   '    base = {country for region in selected_regions for country in regions.get(region, [])}\n'
                   '    return sorted((base | set(manual_additions)) - set(manual_removals))\n'
                   '\n'
                   'def update_country_overrides(previous, current, additions, removals):\n'
                   '    added = set(current) - set(previous)\n'
                   '    removed = set(previous) - set(current)\n'
                   '    return sorted((set(additions) | added) - removed), sorted((set(removals) | removed) - added)\n'
                   '\n'
                   'def search_payload(draft):\n'
                   '    """Never send obsolete UI-only state or removed persona filters."""\n'
                   '    return {**{key: draft[key] for key in DEFAULT_DRAFT},\n'
                   '            "fill_revenue": True, "include_unknown_revenue": True}\n',
 'frontend.progress': '"""Measured search progress, with a conservative legacy response fallback."""\n'
                      'import math\n'
                      'import re\n'
                      '\n'
                      'TERMINAL = {"complete", "cancelled", "failed"}\n'
                      'COUNT_KEYS = ("accounts", "topic_rows", "metro_rows")\n'
                      'FILTER_STAGES = {"preview", "exclusions", "details", "metros", "geography", "revenue"}\n'
                      'STAGE_LABELS = {\n'
                      '    "queued": "Waiting to start", "preview": "Finding topic matches",\n'
                      '    "exclusions": "Checking account eligibility", "details": "Applying company filters",\n'
                      '    "week_alignment": "Checking the reporting week", "metros": "Checking metro scores",\n'
                      '    "geography": "Filtering surge countries", "revenue": "Checking company revenue",\n'
                      '    "previous_week": "Comparing last week\'s scores", "mapping": "Mapping offerings and '
                      'summarizing accounts",\n'
                      '    "excel": "Preparing your Excel report", "complete": "Your report is ready",\n'
                      '    "cancelled": "Search cancelled", "failed": "Search needs attention",\n'
                      '    "awaiting_revenue_confirmation": "Waiting for revenue confirmation",\n'
                      '}\n'
                      '\n'
                      '\n'
                      'def measured_count(value):\n'
                      '    if isinstance(value, bool) or not isinstance(value, (int, float)):\n'
                      '        return None\n'
                      '    return int(value) if math.isfinite(value) and value >= 0 and value == int(value) else None\n'
                      '\n'
                      '\n'
                      'def display_count(value):\n'
                      '    value = measured_count(value)\n'
                      '    return f"{value:,}" if value is not None else "—"\n'
                      '\n'
                      '\n'
                      'def duration(seconds):\n'
                      '    if isinstance(seconds, bool) or not isinstance(seconds, (int, float)) or not '
                      'math.isfinite(seconds):\n'
                      '        return "—"\n'
                      '    hours, remainder = divmod(max(0, int(seconds)), 3600)\n'
                      '    minutes, seconds = divmod(remainder, 60)\n'
                      '    if hours:\n'
                      '        return f"{hours}h {minutes:02d}m"\n'
                      '    return f"{minutes}m {seconds:02d}s" if minutes else f"{seconds}s"\n'
                      '\n'
                      '\n'
                      'def legacy_stage(job):\n'
                      '    status = job.get("status", "queued")\n'
                      '    if status in TERMINAL or status in {"queued", "awaiting_revenue_confirmation"}:\n'
                      '        return status\n'
                      '    message = job.get("message", "").casefold()\n'
                      '    for needle, stage in (("revenue", "revenue"), ("last week", "previous_week"),\n'
                      '                          ("four-sheet", "excel"), ("formatting", "excel"),\n'
                      '                          ("offerings", "mapping"), ("summaries", "mapping"),\n'
                      '                          ("surge location", "geography"), ("metro", "metros"),\n'
                      '                          ("company details", "details"), ("finding accounts", "preview")):\n'
                      '        if needle in message:\n'
                      '            return stage\n'
                      '    return "running"\n'
                      '\n'
                      '\n'
                      'def _counts(values):\n'
                      '    return {key: measured_count((values or {}).get(key)) for key in COUNT_KEYS}\n'
                      '\n'
                      '\n'
                      'def _legacy_checkpoints(job):\n'
                      '    counts = job.get("counts") or {}\n'
                      '    checkpoints = []\n'
                      '    for stage, label, fields in (\n'
                      '        ("preview", "Initial topic matches", {"accounts": "preview_accounts", "topic_rows": '
                      '"preview_topic_rows"}),\n'
                      '        ("details", "Company filters", {"topic_rows": "detail_topic_rows"}),\n'
                      '        ("geography", "Metro scores & geography", {"accounts": "accounts_after_geography"}),\n'
                      '    ):\n'
                      '        if any(value in counts for value in fields.values()):\n'
                      '            checkpoints.append({"id": stage, "label": label,\n'
                      '                                "counts": _counts({key: counts.get(value) for key, value in '
                      'fields.items()}), "removed": {}})\n'
                      '    return checkpoints\n'
                      '\n'
                      '\n'
                      'def _legacy_revenue(job, stage):\n'
                      '    counts = job.get("counts") or {}\n'
                      '    cached, uncached = measured_count(counts.get("revenue_cached")), '
                      'measured_count(counts.get("revenue_uncached"))\n'
                      '    total = cached + uncached if cached is not None and uncached is not None else None\n'
                      '    completed = None\n'
                      '    match = re.search(r"Revenue:\\s*([\\d,]+)\\s*/\\s*([\\d,]+)\\s*companies", '
                      'job.get("message", ""), re.IGNORECASE)\n'
                      '    if match:\n'
                      '        completed, total = (int(value.replace(",", "")) for value in match.groups())\n'
                      '    elif total is not None:\n'
                      '        if stage in {"previous_week", "mapping", "excel", "complete"}:\n'
                      '            completed = total\n'
                      '        elif job.get("status") == "awaiting_revenue_confirmation":\n'
                      '            completed = cached\n'
                      '    if total is None:\n'
                      '        return None\n'
                      '    return {"completed": min(completed, total) if completed is not None else None, "total": '
                      'total, "cached": cached,\n'
                      '            "research_completed": max(0, completed - cached) if completed is not None and '
                      'cached is not None else None,\n'
                      '            "research_total": uncached}\n'
                      '\n'
                      '\n'
                      'def progress_view(job, *, now, observed_at=None, request=None):\n'
                      '    stage = legacy_stage(job)\n'
                      '    stage_label = STAGE_LABELS.get(stage, "Search in progress")\n'
                      '    checkpoints = _legacy_checkpoints(job)\n'
                      '    current, sources = _counts({}), {key: "Not available yet" for key in COUNT_KEYS}\n'
                      '    for checkpoint in checkpoints:\n'
                      '        if checkpoint["id"] == "preview":\n'
                      '            continue  # Initial matches never claim that accounts survived filters.\n'
                      '        for key, value in checkpoint["counts"].items():\n'
                      '            if value is not None:\n'
                      '                current[key], sources[key] = value, checkpoint["label"]\n'
                      '    elapsed = max(0, now - observed_at) if observed_at is not None else None\n'
                      '    elapsed_label, stage_elapsed = "Tracking for", None\n'
                      '    revenue = _legacy_revenue(job, stage)\n'
                      '    telemetry = job.get("telemetry") or {}\n'
                      '    if telemetry.get("version") == 1:\n'
                      '        stages = {item["id"]: item for item in telemetry.get("stages", [])}\n'
                      '        stage = telemetry.get("current_stage") or stage\n'
                      '        stage_info = stages.get(stage, {})\n'
                      '        stage_label = STAGE_LABELS.get(stage) or stage_info.get("label") or "Search in '
                      'progress"\n'
                      '        stage_elapsed, elapsed = stage_info.get("elapsed_seconds"), '
                      'telemetry.get("elapsed_seconds")\n'
                      '        elapsed_label = "Elapsed"\n'
                      '        checkpoint_id = telemetry.get("counts_stage")\n'
                      '        current = _counts(telemetry.get("current_counts")) if checkpoint_id != "preview" else '
                      '_counts({})\n'
                      '        checkpoint_label = STAGE_LABELS.get(checkpoint_id) or stages.get(checkpoint_id, '
                      '{}).get("label") or "Latest results"\n'
                      '        sources = {key: checkpoint_label if current[key] is not None else "Not available yet" '
                      'for key in COUNT_KEYS}\n'
                      '        checkpoints = [{"id": item["id"], "label": STAGE_LABELS.get(item["id"]) or '
                      'item.get("label") or item["id"],\n'
                      '                        "counts": _counts(item["counts"]), "removed": item.get("removed") or '
                      '{}}\n'
                      '                       for item in telemetry.get("stages", [])\n'
                      '                       if item["id"] in FILTER_STAGES and item.get("counts") is not None]\n'
                      '        if telemetry.get("revenue"):\n'
                      '            revenue = {key: measured_count(telemetry["revenue"].get(key)) for key in\n'
                      '                       ("completed", "total", "cached", "research_completed", '
                      '"research_total")}\n'
                      '            if revenue["total"] is None:\n'
                      '                revenue = None\n'
                      '    if job.get("status") in TERMINAL or job.get("status") == "awaiting_revenue_confirmation":\n'
                      '        stage_label = STAGE_LABELS[job["status"]]\n'
                      '    if stage == "exclusions" and request is not None:\n'
                      '        domains = bool(request.get("suppressed_domains") or '
                      'request.get("suppression_list_ids"))\n'
                      '        edu = bool(request.get("exclude_edu"))\n'
                      '        stage_label = ("Applying domain and education exclusions" if domains and edu else\n'
                      '                       "Applying your domain exclusions" if domains else "Excluding .edu '
                      'domains" if edu else\n'
                      '                       "Checking account eligibility")\n'
                      '        if not domains and not edu:\n'
                      '            checkpoints = [item for item in checkpoints if item["id"] != "exclusions"]\n'
                      '    if job.get("result_counts") is not None:\n'
                      '        current = _counts(job["result_counts"])\n'
                      '        sources = {key: "Final report" if current[key] is not None else "Not available yet" for '
                      'key in COUNT_KEYS}\n'
                      '        if checkpoints:\n'
                      '            checkpoints.append({"id": "complete", "label": "Final report", "counts": '
                      'current.copy(), "removed": {}})\n'
                      '    exclusions = []\n'
                      '    for key, label in (("suppressed_accounts", "suppressed accounts"), '
                      '("edu_excluded_accounts", ".edu accounts"),\n'
                      '                       ("missing_metro_rows_excluded", "missing/invalid metro entries"),\n'
                      '                       ("metro_range_rows_excluded", "metro entries outside the score range"),\n'
                      '                       ("duplicate_metro_rows_removed", "duplicate metro observations")):\n'
                      '        value = measured_count((job.get("counts") or {}).get(key))\n'
                      '        if value:\n'
                      '            exclusions.append(f"{value:,} {label}")\n'
                      '    return {"stage": stage, "stage_label": stage_label, "current": current, "sources": '
                      'sources,\n'
                      '            "checkpoints": checkpoints, "elapsed_seconds": elapsed, "elapsed_label": '
                      'elapsed_label,\n'
                      '            "stage_elapsed_seconds": stage_elapsed, "revenue": revenue, "exclusions": '
                      'exclusions}\n'
                      '\n'
                      '\n'
                      'def journey_rows(view):\n'
                      '    rows = []\n'
                      '    for checkpoint in view["checkpoints"]:\n'
                      '        removed = checkpoint.get("removed") or {}\n'
                      '        measured_losses = [(measured_count(removed.get(key)), label) for key, label in\n'
                      '                           (("accounts", "accounts"), ("topic_rows", "topic rows"), '
                      '("metro_rows", "metros"))]\n'
                      '        losses = [f"{value:,} {label}" for value, label in measured_losses if value is not None '
                      'and value > 0]\n'
                      '        loss_text = " · ".join(losses) if losses else ("0" if any(value is not None for value, '
                      '_ in measured_losses) else "—")\n'
                      '        rows.append({"Filter step": checkpoint["label"], "Accounts": '
                      'display_count(checkpoint["counts"].get("accounts")),\n'
                      '                     "Topic rows": display_count(checkpoint["counts"].get("topic_rows")),\n'
                      '                     "Metro observations": '
                      'display_count(checkpoint["counts"].get("metro_rows")), "Removed at this step": loss_text})\n'
                      '    return rows\n',
 'frontend.controls': '"""Shared confirmation and request feedback for stopping work."""\n'
                      'from __future__ import annotations\n'
                      '\n'
                      'import time\n'
                      'import streamlit as st\n'
                      '\n'
                      '\n'
                      'def cancel_control(api, path, scope, *, label="Cancel build", noun="campaign preparation", '
                      'cancelling=False,\n'
                      '                   terminal=False, payload=None, message=None, confirm_note=None, '
                      'pending_note=None):\n'
                      '    """A click asks; only an explicit Yes dispatches one cancellation request."""\n'
                      '    key = f"cancel_state_{scope}"\n'
                      '    error_key = f"cancel_error_{scope}"\n'
                      '    state = st.session_state.get(key) or {}\n'
                      '    if terminal:\n'
                      '        st.session_state.pop(key, None)\n'
                      '        st.session_state.pop(error_key, None)\n'
                      '        return False\n'
                      '    if cancelling or state.get("phase") in {"requesting", "sent"}:\n'
                      '        st.info(message or "Cancelling — no new work will start. Waiting for the current '
                      'request to stop or finish safely.")\n'
                      '        if state.get("phase") == "requesting":\n'
                      '            # Record the dispatch before the request so a rerun cannot duplicate it.\n'
                      '            st.session_state[key] = {**state, "phase": "sent"}\n'
                      '            response = api("POST", path, json=payload or {}, timeout=10, '
                      'error_state=error_key)\n'
                      '            if response is None or getattr(response, "ok", True) is False:\n'
                      '                st.session_state[key] = {**state, "phase": "failed"}\n'
                      '                st.rerun()\n'
                      '            st.rerun()\n'
                      '        st.caption(pending_note or "Completed results are kept. This screen will confirm when '
                      'preparation has stopped.")\n'
                      '        return True\n'
                      '    if state.get("phase") == "failed":\n'
                      '        st.warning("Cancellation has not been confirmed. Preparation may still be running.")\n'
                      '        if st.button("Retry cancellation", key=f"cancel_retry_{scope}"):\n'
                      '            st.session_state[key] = {"phase": "requesting", "requested_at": time.time()}\n'
                      '            st.rerun()\n'
                      '        return False\n'
                      '    if state.get("phase") != "confirm":\n'
                      '        if st.button(label, key=f"cancel_open_{scope}"):\n'
                      '            st.session_state[key] = {"phase": "confirm"}\n'
                      '            st.rerun()\n'
                      '        return False\n'
                      '    with st.container(border=True):\n'
                      '        st.write(f"Cancel {noun}?")\n'
                      '        st.caption(confirm_note or "Completed results will remain available.")\n'
                      '        yes, no = st.columns(2)\n'
                      '        if yes.button("Yes, cancel", type="primary", key=f"cancel_yes_{scope}"):\n'
                      '            st.session_state[key] = {"phase": "requesting", "requested_at": time.time()}\n'
                      '            st.rerun()\n'
                      '        if no.button("No, keep going", key=f"cancel_no_{scope}"):\n'
                      '            st.session_state.pop(key, None)\n'
                      '            st.rerun()\n'
                      '    return False\n',
 'frontend.campaigns': '"""Compact campaign controls, isolated from the four-screen account wizard."""\n'
                       '\n'
                       'from copy import deepcopy\n'
                       'import hashlib\n'
                       'import json\n'
                       'import re\n'
                       'import time\n'
                       '\n'
                       'import pandas as pd\n'
                       'import streamlit as st\n'
                       '\n'
                       'from frontend.presentation import normalize_customer_website, TEST_RECIPIENT\n'
                       'from frontend import access\n'
                       'from frontend.controls import cancel_control\n'
                       '\n'
                       '\n'
                       'TERMINAL = {"complete", "completed", "partial", "failed", "cancelled", "interrupted", '
                       '"data_pending"}\n'
                       'BRIEF_READY = {"complete", "approved"}\n'
                       'BRIEF_ACTIVE = {"running", "queued"}\n'
                       'TAXONOMY = ["diagnostic", "supporting", "broad", "ambiguous"]\n'
                       '\n'
                       '\n'
                       'def public_service_message(value):\n'
                       '    """Describe known pipeline failures without altering customer facts or copy."""\n'
                       '    message = str(value or "")\n'
                       '    replacements = {\n'
                       '        "Configure the Anthropic API key for required Opus campaign stages.": "Company '
                       'research needs setup before you can build a campaign.",\n'
                       '        "Install the configured Anthropic SDK before running campaigns.": "Company research '
                       'needs setup before you can build a campaign.",\n'
                       '        "Configure the OpenAI API key for required Sol campaign stages.": "Email drafting '
                       'needs setup before you can build a campaign.",\n'
                       '        "Campaign tasks support only the required Opus and Sol models.": "Campaign preparation '
                       'is unavailable until its setup is corrected.",\n'
                       '        "Opus did not complete the structured stage.": "Research did not finish. Retry to '
                       'continue.",\n'
                       '        "Sol did not complete the structured stage.": "Writing did not finish. Retry to '
                       'continue.",\n'
                       '        "Opus research ended without a complete result.": "Research did not finish. Retry to '
                       'continue.",\n'
                       '        "Customer website research requires Anthropic and OpenAI credentials.": "Product '
                       'research needs setup before it can start.",\n'
                       '        "Backend is shutting down.": "The service is temporarily unavailable. Try again '
                       'shortly.",\n'
                       '        "Campaign complete; sending was simulated. No emails were sent.": "Campaign processing '
                       'finished. No emails were sent.",\n'
                       '        "Simulation successful - no emails were sent": "No emails were sent.",\n'
                       '        "The model stage exceeded its ten-minute deadline.": "This step took too long to '
                       'finish. Retry to continue.",\n'
                       '        "Provider returned invalid structured JSON.": "This step returned an unusable result. '
                       'Retry to continue.",\n'
                       '        "Provider returned an unsupported response object.": "This step returned an unusable '
                       'result. Retry to continue.",\n'
                       '        "Research exceeded its three continuation limit.": "Research did not finish. Retry to '
                       'continue.",\n'
                       '        "Waiting for aligned current/helper data for the requested week. No paid work has '
                       'started.": "Waiting for the requested week\'s intent data to be ready. Paid research has not '
                       'started.",\n'
                       '        "Apollo API key is not configured.": "Contact sourcing needs setup before it can '
                       'start.",\n'
                       '        "Apollo endpoint is not authorized.": "Contact sourcing is unavailable until its setup '
                       'is corrected.",\n'
                       '        "Apollo returned invalid JSON.": "Contact sourcing returned an unusable result. Retry '
                       'to continue.",\n'
                       '        "Apollo returned an unexpected response.": "Contact sourcing returned an unusable '
                       'result. Retry to continue.",\n'
                       '        "Apollo enrichment response omitted its match records.": "Contact verification '
                       'returned incomplete results. Retry to continue.",\n'
                       '        "Apollo enrichment identity/count mismatch; no negative results were cached.": '
                       '"Contact verification returned inconsistent results. Unverified contacts have been '
                       'excluded.",\n'
                       '        "Apollo search returned an invalid people list.": "Contact sourcing returned an '
                       'unusable result. Retry to continue.",\n'
                       '        "Apollo enrichment failed after dispatch; billing is unknown and these person IDs will '
                       'not be revealed again in this run.": "Contact verification failed and may have incurred a '
                       'charge. These contacts will not be checked again in this run.",\n'
                       '        "Apollo connection failed; reveal billing is unknown.": "Contact verification could '
                       'not connect and may have incurred a charge.",\n'
                       '        "Apollo is in a provider-requested cooldown; retry later.": "Contact sourcing is '
                       'temporarily unavailable. Retry later.",\n'
                       '        "The database connection was interrupted and could not be restored. Your filters are '
                       'unchanged. Retry the search.": "The search connection was interrupted. Your filters are '
                       'unchanged. Retry the search.",\n'
                       '        "The database query exceeded its time limit. Your filters are unchanged. Retry, or '
                       'select fewer topics.": "The search took too long to finish. Your filters are unchanged. Retry, '
                       'or select fewer topics.",\n'
                       '        "The database request failed. Your filters are unchanged. Retry the search; the local '
                       'service log contains diagnostic details.": "The search could not load intent data. Your '
                       'filters are unchanged. Retry the search.",\n'
                       '        "OpenAI enrichment failed. Check the API key, quota, and connectivity, then retry.": '
                       '"Revenue research could not finish. Check that research access and credits are available, then '
                       'retry.",\n'
                       '        "Search could not finish. Check the local service and try again.": "Search could not '
                       'finish. Try again shortly.",\n'
                       '        "This search expired or the backend restarted. Start a new search.": "This report is '
                       'no longer available. Start a new search.",\n'
                       '        "This search expired or the backend restarted.": "This report is no longer available. '
                       'Start a new search.",\n'
                       '        "The database is still reconnecting. Please retry shortly.": "The search connection is '
                       'still reconnecting. Please retry shortly.",\n'
                       '        "Database request failed.": "The search could not load intent data. Please retry.",\n'
                       '        "Previous-week table unavailable.": "Last week\'s data is unavailable, so score '
                       'comparisons cannot be shown.",\n'
                       '        "The current table does not contain exactly one week. Retry after the data refresh.": '
                       '"The intent update contains mixed or missing reporting dates. Retry once the update is '
                       'complete.",\n'
                       '        "Score and detail tables are on different weeks. Retry after the data refresh.": '
                       '"Intent scores and company details are from different reporting weeks. Retry once the update '
                       'is complete.",\n'
                       '        "Validating current and helper reporting weeks": "Checking reporting dates",\n'
                       '        "The source is still on an older reporting week. This search read it directly; '
                       'old-week intent data is not being reused from cache.": "The latest available intent data is '
                       'still from an older reporting week. This report uses that week; try again after the next '
                       'update.",\n'
                       '        "More than 200,000 metro rows: Excel formatting may take several minutes and '
                       'substantial memory.": "This report has more than 200,000 metro rows. Preparing the Excel '
                       'download may take several minutes.",\n'
                       '        "Formatting the four-sheet workbook in memory": "Preparing your four-sheet report",\n'
                       '        "Reused this campaign version\'s completed reporting week.": "This campaign already '
                       'has completed results for this reporting week.",\n'
                       '        "Cancelling; in-flight provider requests may finish before stopping.": "Cancelling. '
                       'Work already underway may take a little time to stop.",\n'
                       '        "Campaign models or prompts changed. Start a new run so the saved run keeps its '
                       'original policy version.": "Campaign preparation has been updated. Start a new run to '
                       'continue; your earlier results remain available.",\n'
                       '        "The original intent workbook expired or the backend restarted. Saved campaign results '
                       'remain available; run a weekly review for a new full workbook.": "The full report download has '
                       'expired. Run a new account search to prepare a current report.",\n'
                       '        "The source reporting week changed. Start a new weekly review; this interrupted run '
                       'cannot mix reporting periods.": "The reporting week changed. Start a new account search to '
                       'continue with current data.",\n'
                       '        "The reporting week changed while reloading. Retry with a new weekly review.": "The '
                       'reporting week changed. Start a new account search to continue with current data.",\n'
                       '    }\n'
                       '    for original, replacement in replacements.items():\n'
                       '        message = message.replace(original, replacement)\n'
                       '    message = message.replace("The weekly account search ", "The account search ")\n'
                       '    message = re.sub(r"Required (opus|sol) provider request failed( \\(HTTP \\d+\\))?; no '
                       'model fallback was used\\.",\n'
                       '        lambda match: f"{\'Research\' if match[1] == \'opus\' else \'Writing\'} could not '
                       'finish{match[2] or \'\'}. Retry to continue.", message)\n'
                       '    message = re.sub(r"Configure ((?:Anthropic|OpenAI|Apollo)(?:, '
                       '(?:Anthropic|OpenAI|Apollo))*) credentials locally before starting the campaign\\.",\n'
                       '        lambda match: "Setup is needed for " + ", ".join({"Anthropic": "company research", '
                       '"OpenAI": "email drafting", "Apollo": "contact sourcing"}[name]\n'
                       '            for name in match[1].split(", ")) + " before building the campaign.", message)\n'
                       '    message = re.sub(r"\\bApollo (?=(?:API key|endpoint|is in a provider-requested '
                       'cooldown|connection failed|enrichment|rate limit|request failed|returned|retry limit|search '
                       'returned)\\b)",\n'
                       '                     "Contact service ", message)\n'
                       '    message = re.sub(r"(?:Invalid provider (?:result|list length|text length|numeric '
                       'range)|Provider (?:omitted required fields|added unsupported fields)) at [\\w.$\\[\\]-]+\\.",\n'
                       '                     "This step returned an unusable result. Retry to continue.", message)\n'
                       '    return message\n'
                       '\n'
                       '\n'
                       'def fingerprint(value):\n'
                       '    return hashlib.sha256(json.dumps(value, sort_keys=True, '
                       'default=str).encode()).hexdigest()[:16]\n'
                       '\n'
                       '\n'
                       'def _call(api, method, path, **kwargs):\n'
                       '    response = api(method, path, **kwargs)\n'
                       '    return response.json() if response is not None else None\n'
                       '\n'
                       '\n'
                       'def _split(value):\n'
                       '    return list(dict.fromkeys(part.strip() for part in str(value or "").split(";") if '
                       'part.strip()))\n'
                       '\n'
                       '\n'
                       'def brief_tables(brief, topics):\n'
                       '    """Editable projections keep source evidence and explicit mappings separate."""\n'
                       '    offerings, capabilities = [], []\n'
                       '    for item in brief.get("offerings") or []:\n'
                       '        offerings.append({"Offering": item.get("name", ""), "Description": '
                       'item.get("description", ""),\n'
                       '                          "Sub-offerings": "; ".join(sub.get("name", "") for sub in '
                       'item.get("sub_offerings") or [])})\n'
                       '        capabilities += [{"Offering": item.get("name", ""), "Capability": cap.get("text", '
                       '""),\n'
                       '                          "Source IDs": "; ".join(cap.get("source_ids") or [])} for cap in '
                       'item.get("capabilities") or []]\n'
                       '    classified = {item.get("topic"): item for item in brief.get("taxonomy") or []}\n'
                       '    taxonomy = [{"Topic": topic, "Classification": classified.get(topic, '
                       '{}).get("classification", "ambiguous"),\n'
                       '                 "Reason": classified.get(topic, {}).get("reason", "Review the role this topic '
                       'plays for your offering.")}\n'
                       '                for topic in dict.fromkeys(topics)]\n'
                       '    return offerings, capabilities, taxonomy\n'
                       '\n'
                       '\n'
                       'def assemble_brief(original, name, description, offerings, capabilities, taxonomy):\n'
                       '    brief = deepcopy(original)\n'
                       '    brief.update(customer_name=str(name).strip(), description=str(description).strip())\n'
                       '    previous = {item.get("name"): item for item in original.get("offerings") or []}\n'
                       '    assembled = []\n'
                       '    for row in offerings:\n'
                       '        label = str(row.get("Offering") or "").strip()\n'
                       '        if not label:\n'
                       '            continue\n'
                       '        item = deepcopy(previous.get(label, {}))\n'
                       '        item.update(id=item.get("id") or "off_" + fingerprint(label), name=label,\n'
                       '                    description=str(row.get("Description") or "").strip())\n'
                       '        existing_subs = {sub.get("name"): sub for sub in item.get("sub_offerings") or []}\n'
                       '        item["sub_offerings"] = [existing_subs.get(sub) or {"id": "sub_" + fingerprint([label, '
                       'sub]), "name": sub, "description": ""}\n'
                       '                                 for sub in _split(row.get("Sub-offerings"))]\n'
                       '        existing_caps = {cap.get("text"): cap for cap in item.get("capabilities") or []}\n'
                       '        item["capabilities"] = []\n'
                       '        for cap in capabilities:\n'
                       '            text = str(cap.get("Capability") or "").strip()\n'
                       '            if str(cap.get("Offering") or "").strip() != label or not text:\n'
                       '                continue\n'
                       '            value = deepcopy(existing_caps.get(text, {}))\n'
                       '            value.update(id=value.get("id") or "cap_" + fingerprint([label, text]), '
                       'text=text,\n'
                       '                         source_ids=_split(cap.get("Source IDs")))\n'
                       '            item["capabilities"].append(value)\n'
                       '        assembled.append(item)\n'
                       '    brief["offerings"] = assembled\n'
                       '    brief["taxonomy"] = [{"topic": str(row.get("Topic") or "").strip(),\n'
                       '                           "classification": row.get("Classification") if '
                       'row.get("Classification") in TAXONOMY else "ambiguous",\n'
                       '                           "reason": str(row.get("Reason") or "").strip()} for row in taxonomy '
                       'if row.get("Topic")]\n'
                       '    return brief\n'
                       '\n'
                       '\n'
                       'def _brief_editor(api, draft):\n'
                       '    record = st.session_state.get("campaign_brief_record") or {}\n'
                       '    brief_id = record.get("id") or record.get("brief_id")\n'
                       '    if not brief_id:\n'
                       '        return\n'
                       '    revision = st.session_state.get("campaign_brief_revision", 0)\n'
                       '    key = f"brief_{brief_id}_{revision}"\n'
                       '    candidate = st.session_state.get("campaign_brief_edit") or {}\n'
                       '    seed = st.session_state.get("campaign_brief_seed") or {}\n'
                       '    if seed.get("key") != key or key + "_name" not in st.session_state:\n'
                       '        # Keep an immutable data-editor seed while mounted, but restore unsaved\n'
                       '        # edits after another wizard screen removes its widget state.\n'
                       '        brief = candidate["brief"] if candidate.get("id") == brief_id else record.get("brief") '
                       'or {}\n'
                       '        seed = {"key": key, "brief": deepcopy(brief)}\n'
                       '        st.session_state.campaign_brief_seed = seed\n'
                       '    brief = seed["brief"]\n'
                       '    left, right = st.columns(2)\n'
                       '    name = left.text_input("Customer name", value=brief.get("customer_name", ""), key=key + '
                       '"_name")\n'
                       '    right.caption("Product details guide account research and email drafts. Topic-to-offering '
                       'links come only from your mapping.")\n'
                       '    description = st.text_area("What the customer offers", value=brief.get("description", ""), '
                       'height=90, key=key + "_description")\n'
                       '    offerings, capabilities, taxonomy = brief_tables(brief, record.get("topics") or '
                       'draft.get("topics") or [])\n'
                       '    tab_offerings, tab_taxonomy, tab_sources = st.tabs(["Offerings & capabilities", "Topic '
                       'meaning", "Research sources"])\n'
                       '    with tab_offerings:\n'
                       '        st.caption("Review the offering descriptions and capabilities. Separate sub-offerings '
                       'with semicolons.")\n'
                       '        offers = st.data_editor(pd.DataFrame(offerings, columns=["Offering", "Description", '
                       '"Sub-offerings"]),\n'
                       '            num_rows="dynamic", hide_index=True, width="stretch", height=190, key=key + '
                       '"_offerings")\n'
                       '        caps = st.data_editor(pd.DataFrame(capabilities, columns=["Offering", "Capability", '
                       '"Source IDs"]),\n'
                       '            num_rows="dynamic", hide_index=True, width="stretch", height=155, key=key + '
                       '"_capabilities")\n'
                       '    with tab_taxonomy:\n'
                       '        tax = st.data_editor(pd.DataFrame(taxonomy, columns=["Topic", "Classification", '
                       '"Reason"]), hide_index=True,\n'
                       '            width="stretch", height=240, disabled=["Topic"], key=key + "_taxonomy",\n'
                       '            column_config={"Classification": '
                       'st.column_config.SelectboxColumn(options=TAXONOMY, required=True)})\n'
                       '        st.caption("Diagnostic means specific to the workflow; supporting adds context. Broad '
                       'or ambiguous topics need caution. This does not create offering mappings.")\n'
                       '    with tab_sources:\n'
                       '        if brief.get("sources"):\n'
                       '            st.dataframe(pd.DataFrame(brief["sources"]), hide_index=True, width="stretch", '
                       'height=220)\n'
                       '        else:\n'
                       '            st.caption("No researched sources. Keep manually supplied claims within what you '
                       'can confirm.")\n'
                       '        for gap in brief.get("gaps") or []:\n'
                       '            st.caption(str(gap))\n'
                       '    edited = assemble_brief(brief, name, description, offers.fillna("").to_dict("records"),\n'
                       '                            caps.fillna("").to_dict("records"), '
                       'tax.fillna("").to_dict("records"))\n'
                       '    st.session_state.campaign_brief_edit = {"id": brief_id, "brief": edited}\n'
                       '    changed = fingerprint(edited) != fingerprint(record.get("brief") or {})\n'
                       '    st.session_state.campaign_brief_dirty = changed\n'
                       '    if changed:\n'
                       '        st.caption("Save these changes before building a campaign, or discard them to use the '
                       'researched brief.")\n'
                       '    if st.button("Save brief changes", disabled=not name.strip() or not description.strip(), '
                       'key=key + "_save"):\n'
                       '        response = _call(api, "PUT", f"/customer-briefs/{brief_id}", json={"brief": edited})\n'
                       '        if response:\n'
                       '            st.session_state.campaign_brief_record = {"id": brief_id, **response}\n'
                       '            st.session_state.campaign_brief_edit = {"id": brief_id, "brief": '
                       'response.get("brief") or edited}\n'
                       '            st.session_state.campaign_brief_dirty = False\n'
                       '            st.session_state.campaign_brief_revision = revision + 1\n'
                       '            st.rerun()\n'
                       '    if changed and st.button("Discard brief changes", key=key + "_discard"):\n'
                       '        st.session_state.pop("campaign_brief_edit", None)\n'
                       '        st.session_state.campaign_brief_dirty = False\n'
                       '        st.session_state.campaign_brief_revision = revision + 1\n'
                       '        st.rerun()\n'
                       '\n'
                       '\n'
                       'def _clear_sender_overrides():\n'
                       '    for key in ("campaign_sender", "campaign_sender_name", "campaign_sender_company",\n'
                       '                "campaign_sender_signature", "campaign_sender_cta"):\n'
                       '        st.session_state.pop(key, None)\n'
                       '\n'
                       '\n'
                       'def customer_context_enabled(options):\n'
                       '    capabilities = options.get("campaigns") or {}\n'
                       '    return bool(capabilities.get("enabled") and capabilities.get("customer_context_version", '
                       '0) >= 2)\n'
                       '\n'
                       '\n'
                       'def customer_website():\n'
                       '    record = st.session_state.get("campaign_brief_record") or {}\n'
                       '    return st.session_state.get("campaign_context_website", record.get("website") or '
                       '(record.get("brief") or {}).get("website", ""))\n'
                       '\n'
                       '\n'
                       'def customer_website_valid():\n'
                       '    try:\n'
                       '        normalize_customer_website(customer_website())\n'
                       '        return True\n'
                       '    except ValueError:\n'
                       '        return False\n'
                       '\n'
                       '\n'
                       'def brief_request(draft, website):\n'
                       '    """Order-independent identity for the website, topics and explicit mappings."""\n'
                       '    mappings = {json.dumps(row, sort_keys=True): row for row in draft.get("topic_mappings") or '
                       '[]}\n'
                       '    return {"website": normalize_customer_website(website),\n'
                       '            "topics": sorted(set(draft.get("topics") or [])),\n'
                       '            "mappings": [mappings[key] for key in sorted(mappings)]}\n'
                       '\n'
                       '\n'
                       'def _brief_context_is_stale(capabilities, draft):\n'
                       '    record = st.session_state.get("campaign_brief_record") or {}\n'
                       '    if not record:\n'
                       '        return False\n'
                       '    current = capabilities.get("customer_context_version", 2)\n'
                       '    previous = st.session_state.get("campaign_brief_context_version", 2)\n'
                       '    if previous == current or record.get("status") == "approved":\n'
                       '        return False\n'
                       '    if st.session_state.get("campaign_brief_saved_context"):\n'
                       '        brief = record.get("brief") or {}\n'
                       '        offerings = brief.get("offerings") or []\n'
                       '        mapped = {row.get("offering") for row in draft.get("topic_mappings") or []}\n'
                       '        supported = {item.get("name") for item in offerings if item.get("description") and\n'
                       '                     any(cap.get("text") and cap.get("source_ids") for cap in '
                       'item.get("capabilities") or [])}\n'
                       '        if brief.get("description") and supported and (not mapped or mapped <= supported):\n'
                       '            return False\n'
                       '    return True\n'
                       '\n'
                       '\n'
                       'def _sync_brief_input(draft):\n'
                       '    st.session_state.campaign_context_website = customer_website()\n'
                       '    try:\n'
                       '        payload = brief_request(draft, customer_website())\n'
                       '    except ValueError:\n'
                       '        payload = {"website": customer_website(), "topics": sorted(set(draft.get("topics") or '
                       '[])),\n'
                       '                   "mappings": draft.get("topic_mappings") or []}\n'
                       '    signature = fingerprint(payload)\n'
                       '    previous = st.session_state.get("campaign_brief_input_signature")\n'
                       '    if previous and previous != signature:\n'
                       '        old = st.session_state.get("campaign_brief_record") or {}\n'
                       '        if old.get("id") or old.get("brief_id"):\n'
                       '            st.session_state.campaign_brief_supersedes = old.get("id") or old.get("brief_id")\n'
                       '        for key in ("campaign_brief_record", "campaign_brief_edit", "campaign_brief_seed", '
                       '"campaign_brief_dirty",\n'
                       '                    "campaign_brief_attempt_signature", "campaign_brief_request_error", '
                       '"campaign_brief_status_error",\n'
                       '                    "campaign_brief_context_version", '
                       '"campaign_brief_attempt_context_version", "campaign_brief_saved_context",\n'
                       '                    "campaign_created_for_job", "campaign_download", '
                       '"campaign_download_signature",\n'
                       '                    "campaign_run_id", "campaign_run_base_job_id", "campaign_run_snapshot", '
                       '"campaign_active_id", "campaign_brief_review_panel"):\n'
                       '            st.session_state.pop(key, None)\n'
                       '        st.session_state.campaign_brief_revision = '
                       'st.session_state.get("campaign_brief_revision", 0) + 1\n'
                       '    st.session_state.campaign_brief_input_signature = signature\n'
                       '    return payload, signature\n'
                       '\n'
                       '\n'
                       'def start_customer_research(api, options, draft, retry=False):\n'
                       '    """Called on leaving Topics, or by an explicit retry; never by rendering."""\n'
                       '    if not customer_context_enabled(options):\n'
                       '        return True\n'
                       '    if not customer_website_valid():\n'
                       '        st.error("Enter a valid customer website to continue, such as https://customer.com.")\n'
                       '        return False\n'
                       '    payload, signature = _sync_brief_input(draft)\n'
                       '    capabilities = options.get("campaigns") or {}\n'
                       '    context_version = capabilities.get("customer_context_version", 2)\n'
                       '    record = st.session_state.get("campaign_brief_record") or {}\n'
                       '    old_attempt = not record and st.session_state.get("campaign_brief_attempt_signature") and '
                       'st.session_state.get("campaign_brief_attempt_context_version", 2) != context_version\n'
                       '    # Untagged generated briefs predate version 3. Renewal happens only on an\n'
                       '    # explicit forward/retry action; saved runs and their downloads stay intact.\n'
                       '    if _brief_context_is_stale(capabilities, draft) or old_attempt:\n'
                       '        if record.get("id") or record.get("brief_id"):\n'
                       '            st.session_state.campaign_brief_supersedes = record.get("id") or '
                       'record.get("brief_id")\n'
                       '        for key in ("campaign_brief_record", "campaign_brief_edit", "campaign_brief_seed", '
                       '"campaign_brief_dirty",\n'
                       '                    "campaign_brief_attempt_signature", "campaign_brief_request_error", '
                       '"campaign_brief_status_error",\n'
                       '                    "campaign_brief_context_version", '
                       '"campaign_brief_attempt_context_version", "campaign_brief_saved_context"):\n'
                       '            st.session_state.pop(key, None)\n'
                       '        st.session_state.campaign_brief_revision = '
                       'st.session_state.get("campaign_brief_revision", 0) + 1\n'
                       '    if not retry and (st.session_state.get("campaign_brief_record") or\n'
                       '                      st.session_state.get("campaign_brief_attempt_signature") == signature):\n'
                       '        return True\n'
                       '    st.session_state.campaign_brief_attempt_signature = signature\n'
                       '    st.session_state.campaign_brief_attempt_context_version = context_version\n'
                       '    payload["retry"] = retry\n'
                       '    if st.session_state.get("campaign_brief_supersedes"):\n'
                       '        payload["supersedes_id"] = st.session_state.campaign_brief_supersedes\n'
                       '    response = _call(api, "POST", "/customer-briefs", json=payload, '
                       'error_state="campaign_brief_request_error")\n'
                       '    if response:\n'
                       '        st.session_state.campaign_brief_record = {"id": response.get("brief_id") or '
                       'response.get("id"), **response}\n'
                       '        st.session_state.campaign_brief_context_version = context_version\n'
                       '        st.session_state.pop("campaign_brief_saved_context", None)\n'
                       '        st.session_state.campaign_brief_revision = '
                       'st.session_state.get("campaign_brief_revision", 0) + 1\n'
                       '        for key in ("campaign_brief_edit", "campaign_brief_seed", "campaign_brief_dirty", '
                       '"campaign_brief_status_error", "campaign_brief_supersedes"):\n'
                       '            st.session_state.pop(key, None)\n'
                       '    return True\n'
                       '\n'
                       '\n'
                       'def _product_summary(brief, ready=True):\n'
                       '    st.markdown(("**Product brief ready" if ready else "**Product brief") + (f" · '
                       '{brief[\'customer_name\']}**" if brief.get("customer_name") else "**"))\n'
                       '    if brief.get("description"):\n'
                       '        st.write(brief["description"])\n'
                       '    offerings = brief.get("offerings") or []\n'
                       '    for offering in offerings[:4]:\n'
                       '        st.markdown(f"**{offering.get(\'name\', \'Product\')}**" + (f" — '
                       '{offering[\'description\']}" if offering.get("description") else ""))\n'
                       '        capabilities = [str(item.get("text") or "") for item in offering.get("capabilities") '
                       'or [] if item.get("text")]\n'
                       '        if capabilities:\n'
                       '            st.caption(" · ".join(capabilities[:2]))\n'
                       '    if len(offerings) > 4:\n'
                       '        st.caption(f"{len(offerings) - 4} more offerings in the optional brief review.")\n'
                       '    if ready:\n'
                       '        st.caption("Ready to use automatically for campaign research and writing.")\n'
                       '\n'
                       '\n'
                       'def render_customer_progress(api, options, draft):\n'
                       '    if not customer_context_enabled(options):\n'
                       '        return\n'
                       '    _sync_brief_input(draft)\n'
                       '    record = st.session_state.get("campaign_brief_record") or {}\n'
                       '    brief_id = record.get("id") or record.get("brief_id")\n'
                       '    polling = bool(brief_id and record.get("status") in BRIEF_ACTIVE)\n'
                       '\n'
                       '    @st.fragment(run_every=2 if polling else None)\n'
                       '    def brief_status():\n'
                       '        access.require_session()\n'
                       '        current = st.session_state.get("campaign_brief_record") or {}\n'
                       '        if (current.get("id") or current.get("brief_id")) != brief_id:\n'
                       '            return\n'
                       '        if brief_id and (current.get("status") in BRIEF_ACTIVE or\n'
                       '                         (current.get("status") in BRIEF_READY and "brief" not in current)):\n'
                       '            updated = _call(api, "GET", f"/customer-briefs/{brief_id}", '
                       'error_state="campaign_brief_status_error")\n'
                       '            if updated:\n'
                       '                current = {"id": brief_id, **updated}\n'
                       '                st.session_state.campaign_brief_record = current\n'
                       '            elif (st.session_state.get("campaign_brief_status_error") or {}).get("status") == '
                       '404:\n'
                       '                current = {"id": brief_id, "status": "unavailable", "error": "This product '
                       'brief is no longer available. Retry customer research to prepare a new one.", "brief": {}}\n'
                       '                st.session_state.campaign_brief_record = current\n'
                       '            if polling and current.get("status") not in BRIEF_ACTIVE:\n'
                       '                # Rebuild the parent once so its ready/error layout and the\n'
                       '                # fragment timer both reflect the finished brief.\n'
                       '                st.rerun()\n'
                       '        status = current.get("status")\n'
                       '        error = st.session_state.get("campaign_brief_request_error") or {}\n'
                       '        if status in BRIEF_READY and current.get("brief"):\n'
                       '            _product_summary(current["brief"], ready=not '
                       '_brief_context_is_stale(options.get("campaigns") or {}, draft))\n'
                       '            review = st.expander("Review or edit product brief (optional)", expanded=False,\n'
                       '                                 key="campaign_brief_review_panel", on_change="rerun")\n'
                       '            if review.open:\n'
                       '                with review:\n'
                       '                    _brief_editor(api, draft)\n'
                       '            sources = st.expander("Product sources", expanded=False, '
                       'key="campaign_brief_sources_panel", on_change="rerun")\n'
                       '            if sources.open:\n'
                       '                with sources:\n'
                       '                    for source in current["brief"].get("sources") or []:\n'
                       '                        url = str(source.get("url") or "")\n'
                       '                        if url.startswith(("https://", "http://")):\n'
                       '                            st.link_button(source.get("title") or url, url)\n'
                       '                    for gap in current["brief"].get("gaps") or []:\n'
                       '                        st.caption(str(gap))\n'
                       '        elif status in BRIEF_ACTIVE:\n'
                       '            st.info("Preparing the product brief in the background. Continue setting geography '
                       'or finding accounts; campaign preparation will wait if needed.")\n'
                       '            st.caption("Researching products, capabilities and customer problems.")\n'
                       '        elif status in {"failed", "cancelled", "unavailable", "draft"} or error:\n'
                       '            st.error(public_service_message(current.get("error") or error.get("message") or '
                       '"Customer research did not finish. Retry to prepare the product brief."))\n'
                       '            if st.button("Retry customer research", disabled=not customer_website_valid() or '
                       'not draft.get("topics")):\n'
                       '                start_customer_research(api, options, draft, retry=True)\n'
                       '                st.rerun()\n'
                       '        elif st.session_state.get("step", 2) > 2:\n'
                       '            st.info("Add the required customer website on Choose topics and continue to start '
                       'the product brief.")\n'
                       '        failure = st.session_state.get("campaign_brief_status_error") or {}\n'
                       '        if failure and status in BRIEF_ACTIVE:\n'
                       '            st.warning("Customer research status is temporarily unavailable. The last '
                       'confirmed update is shown.")\n'
                       '\n'
                       '    brief_status()\n'
                       '\n'
                       '\n'
                       'def render_customer_context(api, options, draft):\n'
                       '    _clear_sender_overrides()\n'
                       '    if not (options.get("campaigns") or {}).get("enabled"):\n'
                       '        return\n'
                       '    if not customer_context_enabled(options):\n'
                       '        st.info("Product research is temporarily unavailable.")\n'
                       '        return\n'
                       '    website = st.text_input("Customer website (required)", value=customer_website(), '
                       'key="campaign_website",\n'
                       '                            placeholder="https://customer.com", help="The website of the '
                       'customer whose products you are selling.")\n'
                       '    st.session_state.campaign_context_website = website.strip()\n'
                       '    st.caption("Product research starts automatically when you continue to geography. You can '
                       'keep working while it runs.")\n'
                       '    render_customer_progress(api, options, draft)\n'
                       '\n'
                       '\n'
                       'def _campaign_list(api, refresh=False):\n'
                       '    cached = st.session_state.get("campaign_list_cache")\n'
                       '    if refresh or cached is None or time.monotonic() - cached["at"] > 30:\n'
                       '        response = _call(api, "GET", "/campaigns")\n'
                       '        if response is not None:\n'
                       '            cached = {"at": time.monotonic(), "items": response.get("campaigns", [])}\n'
                       '            st.session_state.campaign_list_cache = cached\n'
                       '    return cached["items"] if cached else []\n'
                       '\n'
                       '\n'
                       'def _activate_run(campaign_id, response):\n'
                       '    run_id = response.get("run_id") or response.get("id")\n'
                       '    if not run_id:\n'
                       '        return\n'
                       '    st.session_state.campaign_active_id = campaign_id\n'
                       '    st.session_state.campaign_run_id = run_id\n'
                       '    st.session_state.campaign_run_base_job_id = response.get("base_job_id")\n'
                       '    st.session_state.pop("campaign_run_snapshot", None)\n'
                       '    st.session_state.pop("campaign_download", None)\n'
                       '    st.session_state.pop("campaign_download_signature", None)\n'
                       '    st.session_state.pop("campaign_control_error", None)\n'
                       '    st.session_state.pop("campaign_status_error", None)\n'
                       '\n'
                       '\n'
                       'def _leave_build_workspace():\n'
                       '    st.query_params.pop("build", None)\n'
                       '    for key in ("campaign_build_id", "campaign_build_snapshot", '
                       '"campaign_build_selected_run"):\n'
                       '        st.session_state.pop(key, None)\n'
                       '\n'
                       '\n'
                       'def _saved_campaigns(api, capabilities, draft, job_id=None, job=None):\n'
                       '    panel = st.expander("Saved campaigns", expanded=False, key="saved_campaigns_panel", '
                       'on_change="rerun")\n'
                       '    if not panel.open:\n'
                       '        return\n'
                       '    with panel:\n'
                       '        items = _campaign_list(api)\n'
                       '        if not items:\n'
                       '            st.caption("Campaign history appears here after the first campaign is created.")\n'
                       '            return\n'
                       '        lookup = {item["id"]: item for item in items}\n'
                       '        selected = st.selectbox("Saved campaign", [""] + list(lookup), '
                       'key="campaign_saved_selection",\n'
                       '            format_func=lambda value: (lookup[value].get("name") or value) if value else '
                       '"Select a campaign")\n'
                       '        if not selected:\n'
                       '            return\n'
                       '        if st.button("Open campaign"):\n'
                       '            response = _call(api, "GET", f"/campaigns/{selected}")\n'
                       '            if response:\n'
                       '                st.session_state.campaign_active_id = selected\n'
                       '                st.session_state.campaign_saved_details = response\n'
                       '                runs = response.get("runs") or []\n'
                       '                if runs:\n'
                       '                    latest = max(runs, key=lambda item: str(item.get("created_at") or '
                       'item.get("started_at") or ""))\n'
                       '                    _leave_build_workspace()\n'
                       '                    _activate_run(selected, latest)\n'
                       '                st.rerun()\n'
                       '        details = st.session_state.get("campaign_saved_details") or {}\n'
                       '        if (details.get("campaign") or {}).get("id") == selected and details.get("runs"):\n'
                       '            runs = {item["id"]: item for item in details["runs"]}\n'
                       '            run_numbers = {run_id: index for index, run_id in enumerate(runs, 1)}\n'
                       '            chosen = st.selectbox("Past run", list(runs), '
                       'key=f"campaign_past_run_{selected}",\n'
                       '                format_func=lambda value: f"Run {run_numbers[value]} - '
                       "{runs[value].get('reporting_week') or runs[value].get('week') or 'Week unavailable'} - "
                       '{runs[value].get(\'status\', \'saved\').replace(\'_\', \' \')}")\n'
                       '            if st.button("View selected run"):\n'
                       '                _leave_build_workspace()\n'
                       '                _activate_run(selected, runs[chosen])\n'
                       '                st.rerun()\n'
                       '        with st.popover("Update campaign settings"):\n'
                       '            st.caption("Updated product details and filters apply to future runs. Earlier '
                       'results keep their original settings.")\n'
                       '            if st.button("Edit saved product brief"):\n'
                       '                stored = _call(api, "GET", f"/campaigns/{selected}")\n'
                       '                if stored:\n'
                       '                    campaign = stored.get("campaign") or {}\n'
                       '                    saved_brief = campaign.get("brief") or {}\n'
                       '                    created = _call(api, "POST", f"/campaigns/{selected}/customer-brief", '
                       'json={})\n'
                       '                    if created:\n'
                       '                        brief_id = created.get("id") or created.get("brief_id")\n'
                       '                        saved_brief = created.get("brief") or saved_brief\n'
                       '                        topics = created.get("topics", [item["topic"] for item in '
                       'saved_brief.get("taxonomy", [])])\n'
                       '                        mappings = created.get("mappings", (campaign.get("config") or '
                       '{}).get("topic_mappings", []))\n'
                       '                        changed_selection = set(topics) != set(draft.get("topics") or []) or '
                       '{\n'
                       '                            fingerprint(item) for item in mappings} != {fingerprint(item) for '
                       'item in draft.get("topic_mappings") or []}\n'
                       '                        draft.update(topics=list(topics), topic_mappings=deepcopy(mappings))\n'
                       '                        st.session_state.pending_widget_values = {"topic_selection": '
                       'list(topics)}\n'
                       '                        if changed_selection:\n'
                       '                            for key in ("job_id", "job_request", "download", '
                       '"download_signature", "job_progress_snapshot",\n'
                       '                                        "job_progress_id", "job_progress_status", '
                       '"campaign_created_for_job"):\n'
                       '                                st.session_state.pop(key, None)\n'
                       '                            st.session_state.notice = "Loaded this campaign\'s saved topics '
                       'and mapping for its product brief. Run a new account search to use these selections."\n'
                       '                        st.session_state.campaign_brief_record = {"id": brief_id, **created}\n'
                       '                        st.session_state.campaign_brief_edit = {"id": brief_id, "brief": '
                       'deepcopy(saved_brief)}\n'
                       '                        _clear_sender_overrides()\n'
                       '                        st.session_state.campaign_context_website = created.get("website") or '
                       'saved_brief.get("website", "")\n'
                       '                        st.session_state.campaign_brief_dirty = False\n'
                       '                        st.session_state.pop("campaign_brief_context_version", None)\n'
                       '                        st.session_state.pop("campaign_brief_attempt_context_version", None)\n'
                       '                        st.session_state.campaign_brief_saved_context = True\n'
                       '                        st.session_state.pop("campaign_brief_input_signature", None)\n'
                       '                        st.session_state.pop("campaign_brief_seed", None)\n'
                       '                        st.session_state.campaign_brief_revision = '
                       'st.session_state.get("campaign_brief_revision", 0) + 1\n'
                       '                        st.session_state.pop("campaign_website", None)\n'
                       '                        st.session_state.step = 2\n'
                       '                        st.session_state.campaign_brief_review_panel = True\n'
                       '                        st.rerun()\n'
                       '            record = st.session_state.get("campaign_brief_record") or {}\n'
                       '            reviewed = record.get("status") in BRIEF_READY and not '
                       'st.session_state.get("campaign_brief_dirty", False)\n'
                       '            if st.button("Use this product brief for the campaign", disabled=not reviewed):\n'
                       '                updated = _call(api, "PUT", f"/campaigns/{selected}/configuration", json={\n'
                       '                    "brief_id": record.get("id") or record.get("brief_id"), "sender": {}})\n'
                       '                if updated:\n'
                       '                    st.session_state.pop("campaign_list_cache", None)\n'
                       '                    st.success("Product details saved for future runs. Earlier results are '
                       'unchanged.")\n'
                       '            ready = job_id and job and job.get("status") == "complete"\n'
                       '            empty = ready and (job.get("result_counts") or {}).get("accounts", 0) == 0\n'
                       '            providers = empty or all(capabilities.get(key) for key in ("anthropic_configured", '
                       '"openai_configured", "apollo_configured"))\n'
                       '            if st.button("Build saved campaign from current search", disabled=not ready or not '
                       'providers):\n'
                       '                started = _call(api, "POST", f"/campaigns/{selected}/runs", json={"job_id": '
                       'job_id})\n'
                       '                if started:\n'
                       '                    _activate_run(selected, {"base_job_id": job_id, **started})\n'
                       '                    st.rerun()\n'
                       '            st.caption("Build combines this campaign\'s saved product details with the '
                       'accounts, filters and mapping from your completed search.")\n'
                       '        with st.popover("Delete saved campaign"):\n'
                       '            st.caption("Deletes this campaign\'s saved settings, summaries, contacts, drafts '
                       'and run history.")\n'
                       '            if st.button("Delete this campaign", key="campaign_delete_confirm"):\n'
                       '                response = _call(api, "DELETE", f"/campaigns/{selected}")\n'
                       '                if response is not None:\n'
                       '                    st.session_state.pop("campaign_list_cache", None)\n'
                       '                    if st.session_state.get("campaign_active_id") == selected:\n'
                       '                        for key in ("campaign_active_id", "campaign_run_id", '
                       '"campaign_run_base_job_id", "campaign_run_snapshot", "campaign_download", '
                       '"campaign_download_signature"):\n'
                       '                            st.session_state.pop(key, None)\n'
                       '                    st.session_state.pop("campaign_saved_selection", None)\n'
                       '                    st.rerun()\n'
                       '\n'
                       '\n'
                       'def contact_phase_label(snapshot):\n'
                       '    phases = snapshot.get("contact_phase_counts") or {}\n'
                       '    labels = {"exact": "Searching original locations", "nearby": "Checking nearby locations",\n'
                       '              "company": "Checking other locations at this company"}\n'
                       '    active = [phase for phase in labels if int(phases.get(phase) or 0) > 0]\n'
                       '    if not active:\n'
                       '        return "Finding and verifying contacts"\n'
                       '    return labels[max(active, key=lambda phase: int(phases[phase]))]\n'
                       '\n'
                       '\n'
                       'def _campaign_start(api, capabilities, job_id, job, draft):\n'
                       '    if not job_id or not job or job.get("status") != "complete":\n'
                       '        return\n'
                       '    accounts = (job.get("result_counts") or {}).get("accounts", 0)\n'
                       '    st.markdown("**Build the outreach package**")\n'
                       '    st.caption(f"{accounts:,} accounts · Up to {accounts * 5:,} contacts in total · Maximum 5 '
                       'per company")\n'
                       '    coverage = ("Search signal locations first, then nearby locations and elsewhere in the '
                       'same company when needed."\n'
                       '                if capabilities.get("contact_coverage") == "signal_nearby_company" else '
                       '"Contacts stay within surge metros.")\n'
                       '    if capabilities.get("delivery_mode") == "apollo_native":\n'
                       '        st.caption(f"{coverage} Review the finished emails and approve their schedule before '
                       'starting in Apollo. Test emails go only to {TEST_RECIPIENT}.")\n'
                       '    else:\n'
                       '        st.caption(f"{coverage} This step prepares email drafts.")\n'
                       '    record = st.session_state.get("campaign_brief_record") or {}\n'
                       '    stale = _brief_context_is_stale(capabilities, draft)\n'
                       '    dirty = st.session_state.get("campaign_brief_dirty", False)\n'
                       '    usable = record.get("status") in (BRIEF_READY | BRIEF_ACTIVE) and not dirty and not stale\n'
                       '    missing = [label for key, label in (("anthropic_configured", "company research"), '
                       '("openai_configured", "draft writing"),\n'
                       '                                      ("apollo_configured", "contact sourcing")) if not '
                       'capabilities.get(key)]\n'
                       '    if not accounts:\n'
                       '        missing = []\n'
                       '    if stale:\n'
                       '        st.info("Update the product brief before preparing new email drafts.")\n'
                       '        if dirty:\n'
                       '            st.caption("Save or discard your optional brief edits on Choose topics before '
                       'updating.")\n'
                       '        if st.button("Update product brief", disabled=dirty or not customer_website_valid()):\n'
                       '            start_customer_research(api, {"campaigns": capabilities}, draft, retry=True)\n'
                       '            st.rerun()\n'
                       '    if not usable and not stale:\n'
                       '        st.info("Continue from Choose topics with a customer website to prepare the product '
                       'brief. Save or discard any optional brief edits before building a campaign.")\n'
                       '    elif record.get("status") in BRIEF_ACTIVE:\n'
                       '        st.caption("You can build now. Campaign preparation will wait for the product brief to '
                       'finish.")\n'
                       '    if missing:\n'
                       '        st.warning("Setup is needed for " + ", ".join(missing) + " before building the '
                       'campaign.")\n'
                       '    snapshot = st.session_state.get("campaign_run_snapshot") or {}\n'
                       '    active = bool(st.session_state.get("campaign_run_id") and snapshot.get("status") not in '
                       'TERMINAL)\n'
                       '    name = st.text_input("Campaign name", value=(record.get("brief") or '
                       '{}).get("customer_name", "") or "Account campaign", key="campaign_new_name")\n'
                       '    can_build = usable and not missing and not active and bool(name.strip())\n'
                       '    if st.button("Build campaign", type="primary", disabled=not can_build) and can_build:\n'
                       '        identity = fingerprint([job_id, record.get("id") or record.get("brief_id"), {}, '
                       'name])\n'
                       '        created = st.session_state.get("campaign_created_for_job") or {}\n'
                       '        if created.get("signature") != identity:\n'
                       '            campaign = _call(api, "POST", "/campaigns", json={"name": name.strip(),\n'
                       '                "brief_id": record.get("id") or record.get("brief_id"), "sender": {}})\n'
                       '            if campaign is None:\n'
                       '                return\n'
                       '            created = {"signature": identity, "id": campaign["id"]}\n'
                       '            st.session_state.campaign_created_for_job = created\n'
                       '            st.session_state.pop("campaign_list_cache", None)\n'
                       '        response = _call(api, "POST", f"/campaigns/{created[\'id\']}/runs", json={"job_id": '
                       'job_id})\n'
                       '        if response:\n'
                       '            _activate_run(created["id"], {"base_job_id": job_id, **response})\n'
                       '            st.rerun()\n'
                       '\n'
                       '\n'
                       'def _control(api, run_id, action):\n'
                       '    if action not in {"retry", "cancel", "redraft"}:\n'
                       '        return\n'
                       '    response = _call(api, "POST", f"/campaign-runs/{run_id}/{action}", json={}, '
                       'error_state="campaign_control_error")\n'
                       '    if response is not None:\n'
                       '        if action in {"retry", "redraft"} and response.get("run_id"):\n'
                       '            _activate_run(st.session_state.get("campaign_active_id"),\n'
                       '                          {"base_job_id": st.session_state.get("campaign_run_base_job_id"), '
                       '**response})\n'
                       '        else:\n'
                       '            st.session_state.pop("campaign_run_snapshot", None)\n'
                       '            st.session_state.pop("campaign_download_signature", None)\n'
                       '        st.rerun()\n'
                       '\n'
                       '\n'
                       'def _revenue_continue(api, job_id):\n'
                       '    response = _call(api, "POST", f"/jobs/{job_id}/confirm-revenue", '
                       'error_state="campaign_control_error")\n'
                       '    if response is not None:\n'
                       '        st.session_state.pop("campaign_run_snapshot", None)\n'
                       '        st.rerun()\n'
                       '\n'
                       '\n'
                       'def _refresh_status():\n'
                       '    st.session_state.pop("campaign_run_snapshot", None)\n'
                       '    st.session_state.pop("campaign_status_error", None)\n'
                       '\n'
                       '\n'
                       'def _recovery_successor(api, run_id, snapshot):\n'
                       '    """Discover explicitly started recovery on ordinary renders, without a timer."""\n'
                       '    counts = snapshot.get("counts") or {}\n'
                       '    if snapshot.get("status") not in TERMINAL or counts.get("contacts", 0) <= '
                       'counts.get("drafts", counts.get("sequences", 0)):\n'
                       '        return None\n'
                       '    campaign_id = snapshot.get("campaign_id") or st.session_state.get("campaign_active_id")\n'
                       '    if not campaign_id:\n'
                       '        return None\n'
                       '    cached = st.session_state.get("campaign_recovery_discovery") or {}\n'
                       '    if cached.get("run_id") != run_id or time.monotonic() - cached.get("at", 0) >= 30:\n'
                       '        response = _call(api, "GET", f"/campaigns/{campaign_id}", '
                       'error_state="campaign_recovery_discovery_error")\n'
                       '        candidates = [item for item in (response or {}).get("runs", [])\n'
                       '                      if item.get("repair_of_run_id") == run_id and item.get("id") != run_id\n'
                       '                      and item.get("campaign_id", campaign_id) == campaign_id]\n'
                       '        successor = max(candidates, key=lambda item: str(item.get("created_at") or ""), '
                       'default=None)\n'
                       '        cached = {"run_id": run_id, "at": time.monotonic(), "successor": successor}\n'
                       '        st.session_state.campaign_recovery_discovery = cached\n'
                       '    return cached.get("successor")\n'
                       '\n'
                       '\n'
                       'def _open_recovery(campaign_id, successor):\n'
                       '    _activate_run(campaign_id, successor)\n'
                       '    st.rerun()\n'
                       '\n'
                       '\n'
                       'def _run_status(api, capabilities, *, continuous=False):\n'
                       '    run_id = st.session_state.get("campaign_run_id")\n'
                       '    if not run_id:\n'
                       '        return\n'
                       '    saved = st.session_state.get("campaign_run_snapshot") or {}\n'
                       '    polling = saved.get("status") not in TERMINAL or '
                       'bool(saved.get("cancellation_pending_requests"))\n'
                       '    successor = _recovery_successor(api, run_id, saved)\n'
                       '\n'
                       '    @st.fragment(run_every=2 if polling else None)\n'
                       '    def live():\n'
                       '        access.require_session()\n'
                       '        snapshot = st.session_state.get("campaign_run_snapshot") or {}\n'
                       '        if polling or not snapshot:\n'
                       '            response = _call(api, "GET", f"/campaign-runs/{run_id}", '
                       'error_state="campaign_status_error")\n'
                       '            if response:\n'
                       '                st.session_state.campaign_run_snapshot = response\n'
                       '                snapshot = response\n'
                       '                if response.get("base_job_id"):\n'
                       '                    st.session_state.campaign_run_base_job_id = response["base_job_id"]\n'
                       '                if polling and snapshot.get("status") in TERMINAL and not '
                       'snapshot.get("cancellation_pending_requests"):\n'
                       '                    st.rerun()\n'
                       '            elif not snapshot:\n'
                       '                failure = st.session_state.get("campaign_status_error") or {}\n'
                       '                st.error(public_service_message(failure.get("message") or "Campaign status is '
                       'temporarily unavailable."))\n'
                       '                st.button("Retry status update", on_click=_refresh_status)\n'
                       '                return\n'
                       '        status, counts = snapshot.get("status", "running"), snapshot.get("counts") or {}\n'
                       '        drafts = counts.get("drafts", counts.get("sequences", 0))\n'
                       '        total = counts.get("accounts_total", counts.get("accounts", 0))\n'
                       '        completed = counts.get("accounts_completed", counts.get("completed", 0) + '
                       'counts.get("failed", 0))\n'
                       '        left, right = st.columns([4, 1])\n'
                       '        stage = status if status in TERMINAL else snapshot.get("stage") or status\n'
                       '        stage_label = {"queued": "Waiting to start", "waiting_for_customer_context": '
                       '"Preparing the product brief",\n'
                       '                    "waiting_for_data": "Waiting for current intent data", "data_pending": '
                       '"Waiting for current intent data",\n'
                       '                    "intent_search": "Finding current accounts", "research": "Researching '
                       'companies",\n'
                       '                    "role_plan": "Identifying relevant contacts", "contact_refit": "Checking '
                       'contact relevance",\n'
                       '                    "analysis": "Assessing account fit", "contacts": "Finding and verifying '
                       'contacts",\n'
                       '                    "drafts": "Writing and checking email drafts", "partial": "Finished with '
                       'some accounts incomplete",\n'
                       '                    "complete": "Campaign results ready", "completed": "Campaign results '
                       'ready",\n'
                       '                    "reused": "Results already available for this week", "interrupted": '
                       '"Campaign interrupted",\n'
                       '                    "failed": "Campaign could not finish", "cancelled": "Campaign cancelled",\n'
                       '                    "cancelling": "Stopping campaign preparation"}\n'
                       '        if status == "awaiting_revenue_confirmation":\n'
                       '            stage = status\n'
                       '            stage_label[stage] = "Confirm revenue research to continue"\n'
                       '        label = stage_label.get(stage, str(stage).replace("_", " ").capitalize())\n'
                       '        if stage == "contacts":\n'
                       '            label = contact_phase_label(snapshot)\n'
                       '        if snapshot.get("cancellation_pending_requests"):\n'
                       '            label = "Cancelling — finishing the current request"\n'
                       '        if status in {"complete", "completed"} and not drafts and total:\n'
                       '            label = "Finished without email sequences"\n'
                       '        left.markdown(f"**{label}**")\n'
                       '        elapsed = max(0, int(snapshot.get("elapsed_seconds") or 0))\n'
                       '        minutes, seconds = divmod(elapsed, 60)\n'
                       '        left.caption(f"Elapsed {minutes:,}m {seconds:02d}s" +\n'
                       '                     (f" - reporting week {snapshot[\'reporting_week\']}" if '
                       'snapshot.get("reporting_week") else ""))\n'
                       '        settling = bool(snapshot.get("cancellation_pending_requests"))\n'
                       '        if status not in TERMINAL or settling:\n'
                       '            cancel_control(api, f"/campaign-runs/{run_id}/cancel", f"campaign_{run_id}", '
                       'label="Cancel campaign",\n'
                       '                           cancelling=status == "cancelling" or settling)\n'
                       '        else:\n'
                       '            cancel_control(api, "", f"campaign_{run_id}", terminal=True)\n'
                       '        ready_accounts = counts.get("ready_accounts")\n'
                       '        labels = ["Accounts ready", "Verified contacts", "Emails ready"] if ready_accounts is '
                       'not None else ["Accounts processed", "Contacts", "Email sequences ready"]\n'
                       '        values = [f"{ready_accounts:,}", f"{counts.get(\'contacts\', 0):,}", f"{drafts * '
                       '3:,}"] if ready_accounts is not None else [f"{completed:,} / {total:,}", '
                       'f"{counts.get(\'contacts\', 0):,}", f"{drafts:,}"]\n'
                       '        for column, metric_label, value in zip(st.columns(3), labels, values):\n'
                       '            column.metric(metric_label, value)\n'
                       '        if ready_accounts is not None:\n'
                       '            st.caption(f"{total:,} matched accounts · '
                       '{counts.get(\'contact_checked_accounts\', 0):,} checked for contacts · "\n'
                       '                       f"{counts.get(\'contactable_accounts\', 0):,} with usable contacts · '
                       '{counts.get(\'skipped_accounts\', 0):,} skipped")\n'
                       '        if status not in TERMINAL:\n'
                       '            if snapshot.get("mode") == "redraft":\n'
                       '                recovery_total = counts.get("draft_recovery_total", 0)\n'
                       '                recovery_completed = counts.get("draft_recovery_completed", 0)\n'
                       '                if recovery_total:\n'
                       '                    st.progress(min(1.0, recovery_completed / recovery_total),\n'
                       '                                text=f"{recovery_completed:,} of {recovery_total:,} contacts '
                       'checked for missing emails")\n'
                       '            elif total:\n'
                       '                st.progress(min(1.0, completed / total))\n'
                       '        if st.session_state.get("campaign_control_error"):\n'
                       '            '
                       'st.error(public_service_message(st.session_state.campaign_control_error["message"]))\n'
                       '        if st.session_state.get("campaign_status_error"):\n'
                       '            '
                       'st.warning(public_service_message(st.session_state.campaign_status_error["message"]) +\n'
                       '                       " Showing the last confirmed campaign update.")\n'
                       '            st.button("Retry status update", on_click=_refresh_status)\n'
                       '        if status == "awaiting_revenue_confirmation" and snapshot.get("base_job_id"):\n'
                       '            pending = snapshot.get("revenue_pending") or {}\n'
                       '            st.warning(f"Revenue research needs confirmation for '
                       "{pending.get('uncached_domains', 'many')} new company checks before proceeding. Research "
                       'charges apply.")\n'
                       '            st.button("Continue revenue research", key=f"revenue_{run_id}", '
                       'on_click=_revenue_continue,\n'
                       '                      args=(api, snapshot["base_job_id"]))\n'
                       '        reason = public_service_message(snapshot.get("error"))\n'
                       '        if not reason and status in {"failed", "cancelled", "interrupted", "data_pending"}:\n'
                       '            reason = public_service_message(snapshot.get("message"))\n'
                       '        if reason:\n'
                       '            st.error(reason)\n'
                       '        notes = []\n'
                       '        for warning in dict.fromkeys(public_service_message(item) for item in '
                       'snapshot.get("warnings") or []):\n'
                       '            if not warning or warning == reason:\n'
                       '                continue\n'
                       '            if '
                       're.search(r"\\b(retry|charge[sd]?|confirm(?:ation)?|failed|expired|interrupted)\\b|could '
                       'not|needs? setup", warning, re.I):\n'
                       '                st.warning(warning)\n'
                       '            else:\n'
                       '                notes.append(warning)\n'
                       '        if status in {"partial", "failed", "cancelled", "interrupted", "data_pending"} and not '
                       'settling and not continuous:\n'
                       '            st.button("Retry campaign", key=f"retry_{run_id}", on_click=_control, args=(api, '
                       'run_id, "retry"))\n'
                       '        if status not in TERMINAL or settling:\n'
                       '            if notes:\n'
                       '                with st.expander(f"Notes ({len(notes)})", expanded=False):\n'
                       '                    for note in notes:\n'
                       '                        st.write(note)\n'
                       '            return\n'
                       '        complete = status in {"complete", "completed"}\n'
                       '        if not drafts and total:\n'
                       '            st.warning("No email sequences were generated. The download contains the available '
                       'account and contact results, with reasons for missing drafts.")\n'
                       '        elif not complete:\n'
                       '            st.warning(f"This run did not finish every account. The download includes '
                       '{drafts:,} ready email sequences and the available results.")\n'
                       '        if successor:\n'
                       '            ready = successor.get("status") in TERMINAL and (successor.get("counts") or '
                       '{}).get("drafts", 0) > drafts\n'
                       '            st.button("Open recovered emails" if ready else "Open email recovery", '
                       'key=f"recovery_{run_id}",\n'
                       '                      on_click=_open_recovery, args=(snapshot.get("campaign_id") or '
                       'st.session_state.get("campaign_active_id"), successor))\n'
                       '        elif capabilities.get("draft_recovery") and snapshot.get("can_redraft") and '
                       'snapshot.get("source_available"):\n'
                       '            st.button("Generate missing emails", key=f"redraft_{run_id}", on_click=_control, '
                       'args=(api, run_id, "redraft"),\n'
                       '                      help="Prepare missing email drafts using the contacts already found. '
                       'Earlier results remain available.")\n'
                       '        if not continuous:\n'
                       '            st.caption("Email sequences for Day 1, Day 4 and Day 7. Schedule and delivery '
                       'status appear below."\n'
                       '                   if drafts and capabilities.get("delivery_mode") == "apollo_native" else\n'
                       '                   "Email drafts for Day 1, Day 4 and Day 7. Test sending is available '
                       'below."\n'
                       '                   if drafts and capabilities.get("sending_mode") == "test_only" else\n'
                       '                   "Email drafts for Day 1, Day 4 and Day 7. No emails are sent." if drafts '
                       'else "Email drafts only. No emails are sent.")\n'
                       '        if snapshot.get("source_available", False):\n'
                       '            signature = fingerprint([run_id, snapshot.get("export_version", 0)])\n'
                       '            full_package = complete and bool(drafts)\n'
                       '            build = st.session_state.get("campaign_build_snapshot") or {}\n'
                       '            if continuous and build.get("download_error"):\n'
                       '                st.warning("The campaign is saved, but its download could not be prepared. Try '
                       'Prepare download below.")\n'
                       '            if continuous and build.get("export_ready", True) and '
                       'st.session_state.get("campaign_download_signature") != signature and '
                       'st.session_state.get("campaign_download_attempt") != signature:\n'
                       '                st.session_state.campaign_download_attempt = signature\n'
                       '                with st.spinner("Preparing your campaign download…"):\n'
                       '                    response = api("GET", f"/campaign-runs/{run_id}/excel", timeout=60, '
                       'error_state="campaign_export_error")\n'
                       '                if response is not None:\n'
                       '                    st.session_state.campaign_download = response.content\n'
                       '                    st.session_state.campaign_download_signature = signature\n'
                       '                    st.session_state.pop("campaign_download_presentation", None)\n'
                       '            if st.session_state.get("campaign_download_signature") == signature:\n'
                       '                st.download_button("Download outreach package" if full_package else "Download '
                       'available results", st.session_state.campaign_download, '
                       'file_name="intent_to_outreach_campaign.xlsx",\n'
                       '                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", '
                       'on_click="ignore", key=f"download_{run_id}", type="primary",\n'
                       '                    help="Includes account research, priorities, buying roles, contacts, email '
                       'drafts and supporting evidence.")\n'
                       '            elif st.button("Prepare download" if full_package else "Prepare available '
                       'results", key=f"export_{run_id}", type="primary"):\n'
                       '                response = api("GET", f"/campaign-runs/{run_id}/excel", timeout=600)\n'
                       '                if response is not None:\n'
                       '                    st.session_state.campaign_download = response.content\n'
                       '                    st.session_state.campaign_download_signature = signature\n'
                       '                    st.session_state.pop("campaign_download_presentation", None)\n'
                       '                    st.rerun()\n'
                       '        else:\n'
                       '            st.caption("The full report download has expired. Run a new account search to '
                       'prepare a current report.")\n'
                       '        if notes:\n'
                       '            with st.expander(f"Notes ({len(notes)})", expanded=False):\n'
                       '                for note in notes:\n'
                       '                    st.write(note)\n'
                       '\n'
                       '    live()\n'
                       '\n'
                       '\n'
                       'def _review_rows(api, run_id, view, page, limit=20):\n'
                       '    snapshot = st.session_state.get("campaign_run_snapshot") or {}\n'
                       '    signature = fingerprint([run_id, snapshot.get("export_version", 0), view, page, limit])\n'
                       '    key = f"campaign_review_rows_{view}"\n'
                       '    cached = st.session_state.get(key) or {}\n'
                       '    if cached.get("signature") == signature:\n'
                       '        return cached["data"]\n'
                       '    data = _call(api, "GET", f"/campaign-runs/{run_id}/results",\n'
                       '                 params={"view": view, "offset": page * limit, "limit": limit},\n'
                       '                 error_state=f"email_review_error_{run_id}")\n'
                       '    if data is not None:\n'
                       '        st.session_state[key] = {"signature": signature, "data": data}\n'
                       '    return data\n'
                       '\n'
                       '\n'
                       'def _email_preview(api, run_id):\n'
                       '    page_key = f"email_review_page_{run_id}"\n'
                       '    page = int(st.session_state.get(page_key, 0))\n'
                       '    data = _review_rows(api, run_id, "sequences", page)\n'
                       '    if data is None:\n'
                       '        st.warning("Email previews are temporarily unavailable. Your drafts remain saved.")\n'
                       '        return\n'
                       '    rows = data.get("rows") or []\n'
                       '    total = int(data.get("total") or 0)\n'
                       '    if not rows:\n'
                       '        st.info("No ready email sequences are available for this selection.")\n'
                       '        return\n'
                       '    contact_column, day_column = st.columns([3, 1])\n'
                       '    index = contact_column.selectbox("Company and contact", list(range(len(rows))), '
                       'key=f"email_review_contact_{run_id}_{page}",\n'
                       '        format_func=lambda n: f"{rows[n].get(\'Company Name\') or rows[n].get(\'Domain\') or '
                       'rows[n].get(\'domain\') or \'Company\'} · {rows[n].get(\'name\') or \'Contact\'}")\n'
                       '    row = rows[index]\n'
                       '    location = row.get("location") or ", ".join(str(row.get(key) or "") for key in ("city", '
                       '"state", "country") if row.get(key))\n'
                       '    if location:\n'
                       '        st.caption("Contact location: " + str(location))\n'
                       '    tier = {"exact": "Signal area", "nearby": "Nearby area", "company": "Elsewhere in '
                       'company"}.get(row.get("match_tier"))\n'
                       '    signals = row.get("signal_metros") or ([row["metro"]] if row.get("metro") else [])\n'
                       '    if tier:\n'
                       '        st.caption("Found in: " + tier + (" · Signal metros: " + "; ".join(map(str, signals)) '
                       'if signals else ""))\n'
                       '    offering = row.get("offering") or row.get("Offering")\n'
                       '    sub = row.get("sub_offering") or row.get("Sub-offering")\n'
                       '    if offering:\n'
                       '        st.caption("Offering: " + str(offering) + (" · " + str(sub) if sub and sub != offering '
                       'else ""))\n'
                       '    day = day_column.segmented_control("Email", [1, 4, 7], default=1, format_func=lambda n: '
                       'f"Day {n}",\n'
                       '                                      key=f"email_review_day_{run_id}_{page}_{index}") or 1\n'
                       '    with st.container(border=True):\n'
                       '        st.caption("Subject")\n'
                       '        st.text(str(row.get(f"subject_day_{day}") or row.get(f"Subject Day {day}") or "Subject '
                       'unavailable"))\n'
                       '        st.text(str(row.get(f"email_day_{day}") or row.get(f"Email Day {day}") or "Email text '
                       'unavailable"))\n'
                       '    if total > 20:\n'
                       '        previous, middle, following = st.columns([1, 3, 1])\n'
                       '        if previous.button("Previous contacts", disabled=page == 0, '
                       'key=f"email_review_previous_{run_id}"):\n'
                       '            st.session_state[page_key] = page - 1\n'
                       '            st.rerun()\n'
                       '        middle.caption(f"Contacts {page * 20 + 1}–{min((page + 1) * 20, total)} of '
                       '{total:,}")\n'
                       '        if following.button("Next contacts", disabled=(page + 1) * 20 >= total, '
                       'key=f"email_review_next_{run_id}"):\n'
                       '            st.session_state[page_key] = page + 1\n'
                       '            st.rerun()\n'
                       '\n'
                       '\n'
                       'def _coverage_review(api, run_id, snapshot):\n'
                       '    page_key = f"coverage_review_page_{run_id}"\n'
                       '    page = int(st.session_state.get(page_key, 0))\n'
                       '    st.caption("All matched accounts remain in your report. Companies without usable contacts '
                       'or checked emails are excluded from the ready campaign.")\n'
                       '    rows = _review_rows(api, run_id, "summary", page)\n'
                       '    if not rows:\n'
                       '        return\n'
                       '    for row in rows.get("rows") or []:\n'
                       '        name = row.get("Company Name") or row.get("Domain") or "Company"\n'
                       '        sequences = int(row.get("Sequences") or 0)\n'
                       '        contacts = int(row.get("Contacts") or 0)\n'
                       '        label = f"{name} · {sequences * 3:,} emails ready" if sequences else f"{name} · No '
                       'ready emails"\n'
                       '        with st.expander(label, expanded=False):\n'
                       '            st.caption(f"{contacts:,} verified contacts · {sequences:,} ready sequences")\n'
                       '            reason = row.get("Skip Reason") or row.get("skip_reason") or row.get("Error")\n'
                       '            if reason:\n'
                       '                st.write(public_service_message(reason))\n'
                       '            elif not sequences:\n'
                       '                st.caption("See the campaign download for contact and email preparation '
                       'outcomes.")\n'
                       '    total = int(rows.get("total") or 0)\n'
                       '    if total > 20:\n'
                       '        previous, middle, following = st.columns([1, 3, 1])\n'
                       '        if previous.button("Previous accounts", disabled=page == 0, '
                       'key=f"coverage_previous_{run_id}"):\n'
                       '            st.session_state[page_key] = page - 1\n'
                       '            st.rerun()\n'
                       '        middle.caption(f"Accounts {page * 20 + 1}–{min((page + 1) * 20, total)} of '
                       '{total:,}")\n'
                       '        if following.button("Next accounts", disabled=(page + 1) * 20 >= total, '
                       'key=f"coverage_next_{run_id}"):\n'
                       '            st.session_state[page_key] = page + 1\n'
                       '            st.rerun()\n'
                       '\n'
                       '\n'
                       'def _final_review(api, run_id, snapshot, options):\n'
                       '    drafts = (snapshot.get("counts") or {}).get("drafts", (snapshot.get("counts") or '
                       '{}).get("sequences", 0))\n'
                       '    choices = ["Emails", "Schedule", "Coverage"] if drafts and options.get("delivery", '
                       '{}).get("enabled") else ["Emails", "Coverage"] if drafts else ["Coverage"]\n'
                       '    section_key = f"campaign_result_section_{run_id}"\n'
                       '    section = st.segmented_control("Review campaign", choices, default=choices[0], '
                       'key=section_key) or choices[0]\n'
                       '    if section == "Emails":\n'
                       '        _email_preview(api, run_id)\n'
                       '        if "Schedule" in choices:\n'
                       '            def show_schedule():\n'
                       '                st.session_state[section_key] = "Schedule"\n'
                       '            st.button("Review schedule & approve", key=f"review_schedule_{run_id}", '
                       'on_click=show_schedule)\n'
                       '    elif section == "Schedule":\n'
                       '        from frontend.delivery import render_delivery\n'
                       '        render_delivery(api, run_id, snapshot, options.get("delivery"))\n'
                       '    else:\n'
                       '        _coverage_review(api, run_id, snapshot)\n'
                       '\n'
                       '\n'
                       'def render_campaign_workspace(api, options, draft, job_id=None, job=None, *, '
                       'continuous=False):\n'
                       '    _clear_sender_overrides()\n'
                       '    capabilities = options.get("campaigns") or {}\n'
                       '    if options.get("delivery", {}).get("enabled"):\n'
                       '        capabilities = {**capabilities, "sending_mode": "test_only", "delivery_mode": '
                       'options["delivery"].get("mode")}\n'
                       '    if not capabilities.get("enabled"):\n'
                       '        return\n'
                       '    if st.session_state.get("campaign_run_id"):\n'
                       '        _run_status(api, capabilities, continuous=continuous)\n'
                       '        snapshot = st.session_state.get("campaign_run_snapshot") or {}\n'
                       '        if snapshot.get("status") in TERMINAL and not '
                       'snapshot.get("cancellation_pending_requests"):\n'
                       '            _final_review(api, st.session_state.campaign_run_id, snapshot, options)\n'
                       '        base_job_id = snapshot.get("base_job_id") or '
                       'st.session_state.get("campaign_run_base_job_id")\n'
                       '        if not continuous and job_id and job and job.get("status") == "complete" and job_id != '
                       'base_job_id:\n'
                       '            panel = st.expander("Prepare another campaign", expanded=False,\n'
                       '                                key="campaign_new_setup_panel", on_change="rerun")\n'
                       '            if panel.open:\n'
                       '                with panel:\n'
                       '                    _campaign_start(api, capabilities, job_id, job, draft)\n'
                       '    elif not continuous:\n'
                       '        _campaign_start(api, capabilities, job_id, job, draft)\n'
                       '    _saved_campaigns(api, capabilities, draft, job_id, job)\n',
 'frontend.delivery': '"""Compact, explicit controls for the fixed-recipient email test schedule."""\n'
                      '\n'
                      'from datetime import date, datetime, time, timedelta, timezone\n'
                      'from math import ceil\n'
                      'import csv\n'
                      'from io import StringIO\n'
                      'from zoneinfo import ZoneInfo, ZoneInfoNotFoundError\n'
                      '\n'
                      'import streamlit as st\n'
                      'from frontend import access\n'
                      'from frontend.presentation import TEST_SENDER, SENDERS, SENDER_NAMES, TEST_RECIPIENT\n'
                      'from frontend.controls import cancel_control\n'
                      '\n'
                      '\n'
                      'IST = ZoneInfo("Asia/Kolkata")\n'
                      'PAGE_SIZE = 20\n'
                      'STATUS_LABELS = {\n'
                      '    "pending": "Scheduled", "scheduled": "Scheduled", "waiting": "Waiting for the earlier '
                      'email",\n'
                      '    "creating": "Preparing email", "drafted": "Preparing to send",\n'
                      '    "blocked_timezone": "Choose a time zone", "drafting": "Preparing email", "preparing": '
                      '"Preparing email",\n'
                      '    "claimed": "Preparing to send", "submitting": "Submitting to Apollo", "sending": '
                      '"Submitting to Apollo",\n'
                      '    "queued": "Queued by Apollo", "accepted": "Queued by Apollo", "sent": "Sent", "delivered": '
                      '"Delivered",\n'
                      '    "opened": "Opened", "replied": "Replied", "bounced": "Bounced", "unsubscribed": '
                      '"Unsubscribed",\n'
                      '    "cancelled": "Cancelled", "canceled": "Cancelled", "stopped": "Stopped", "skipped": "Not '
                      'scheduled",\n'
                      '    "failed": "Needs attention", "blocked": "Needs attention", "uncertain": "Checking send '
                      'status",\n'
                      '    "ambiguous": "Checking send status", "attention": "Needs attention", "reconciling": '
                      '"Checking send status",\n'
                      '    "upload_pending": "Preparing schedule", "uploading": "Adding to Apollo", "needs_timezone": '
                      '"Choose a time zone",\n'
                      '    "paused": "Paused", "send_requested": "Send requested",\n'
                      '    "awaiting_approval": "Awaiting your approval",\n'
                      '}\n'
                      'ACTIVE_PLAN_STATES = {"active", "running", "started"}\n'
                      '\n'
                      '\n'
                      'def parse_time(value):\n'
                      '    if isinstance(value, datetime):\n'
                      '        return value if value.tzinfo else None\n'
                      '    try:\n'
                      '        result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))\n'
                      '        return result if result.tzinfo else None\n'
                      '    except (TypeError, ValueError):\n'
                      '        return None\n'
                      '\n'
                      '\n'
                      'def due_labels(item, native=False):\n'
                      '    """Never silently assign a zone to an ambiguous/missing timestamp."""\n'
                      '    confirmed = parse_time(item.get("confirmed_due_at"))\n'
                      '    due = confirmed or parse_time(item.get("due_at"))\n'
                      '    zone_name = item.get("timezone") or item.get("time_zone") or ""\n'
                      '    if not due:\n'
                      '        return "Time zone needed" if not zone_name else "Not scheduled", "", ""\n'
                      '    ist = due.astimezone(IST).strftime("%a %d %b, %I:%M %p IST")\n'
                      '    try:\n'
                      '        local = due.astimezone(ZoneInfo(zone_name))\n'
                      '    except (ValueError, ZoneInfoNotFoundError):\n'
                      '        return "Local time unavailable", ist, ""\n'
                      '    day = local.strftime("%a %d %b %Y")\n'
                      '    if native and not (confirmed or item.get("due_at_confirmed")):\n'
                      '        try:\n'
                      '            start = time.fromisoformat(item.get("delivery_window_start") or "10:00")\n'
                      '            end = time.fromisoformat(item.get("delivery_window_end") or "11:00")\n'
                      '        except (TypeError, ValueError):\n'
                      '            return "Delivery window unavailable", "", day\n'
                      '        first = datetime.combine(local.date(), start, tzinfo=local.tzinfo)\n'
                      '        last = datetime.combine(local.date(), end, tzinfo=local.tzinfo)\n'
                      '        if last <= first:\n'
                      '            last += timedelta(days=1)\n'
                      '        first_format = "%a %d %b, %I:%M" if first.strftime("%p") == last.strftime("%p") else '
                      '"%a %d %b, %I:%M %p"\n'
                      '        label = first.strftime(first_format) + "–" + last.strftime("%I:%M %p")\n'
                      '        ist = first.astimezone(IST).strftime("%a %d %b, %I:%M %p") + "–" + '
                      'last.astimezone(IST).strftime("%I:%M %p IST")\n'
                      '        return f"Planned {label} ({zone_name})", f"Planned {ist}", day\n'
                      '    prefix = "Apollo: " if native else ""\n'
                      '    return prefix + local.strftime("%a %d %b, %I:%M %p") + f" ({zone_name})", ist, day\n'
                      '\n'
                      '\n'
                      'def status_label(value):\n'
                      '    return STATUS_LABELS.get(value, "Status unavailable")\n'
                      '\n'
                      '\n'
                      'def local_send_at(day, clock, zone):\n'
                      '    value = datetime.combine(day, clock, tzinfo=zone)\n'
                      '    if value.astimezone(timezone.utc).astimezone(zone).replace(tzinfo=None) != '
                      'value.replace(tzinfo=None):\n'
                      '        raise ValueError("That local time is skipped when the clocks change. Choose another '
                      'send time.")\n'
                      '    if value.replace(fold=0).utcoffset() != value.replace(fold=1).utcoffset():\n'
                      '        raise ValueError("That local time occurs twice when the clocks change. Choose an '
                      'unambiguous send time.")\n'
                      '    return value.isoformat()\n'
                      '\n'
                      '\n'
                      'def _polling(plan):\n'
                      '    if plan.get("approval_required") and not int((plan.get("counts") or {}).get("accepted") or '
                      '0) and not plan.get("pending_operation"):\n'
                      '        return False\n'
                      '    if plan.get("pending_operation"):\n'
                      '        return True\n'
                      '    if _native(plan):\n'
                      '        counts = plan.get("counts") or {}\n'
                      '        if plan.get("active"):\n'
                      '            return True\n'
                      '        if _native_finished(plan):\n'
                      '            return False\n'
                      '        return bool(plan.get("status") != "paused" and _native_remaining(plan))\n'
                      '    if "active" in plan:\n'
                      '        return bool(plan["active"])\n'
                      '    return plan.get("status") in ACTIVE_PLAN_STATES or bool((plan.get("counts") or '
                      '{}).get("queued"))\n'
                      '\n'
                      '\n'
                      'def _native(plan):\n'
                      '    return plan.get("ownership") == "apollo"\n'
                      '\n'
                      '\n'
                      'def _native_finished(plan):\n'
                      '    counts = plan.get("counts") or {}\n'
                      '    total = int(counts.get("total") or 0)\n'
                      '    return bool(total and int(counts.get("sent") or 0) + int(counts.get("stopped") or 0) >= '
                      'total)\n'
                      '\n'
                      '\n'
                      'def _native_remaining(plan):\n'
                      '    counts = plan.get("counts") or {}\n'
                      '    if "scheduled" in counts or "queued" in counts:\n'
                      '        return int(counts.get("scheduled") or 0) + int(counts.get("queued") or 0)\n'
                      '    return max(0, int(counts.get("accepted") or 0) - sum(int(counts.get(key) or 0) for key in '
                      '("sent", "stopped", "attention")))\n'
                      '\n'
                      '\n'
                      'def _native_incomplete(value):\n'
                      '    return bool(value.get("partial") or value.get("status") in {"attention", "blocked", '
                      '"uncertain", "partial"}\n'
                      '                or any(_native_incomplete(group) for group in value.get("groups") or []))\n'
                      '\n'
                      '\n'
                      'def account_options(accounts):\n'
                      '    values = {}\n'
                      '    for item in accounts or []:\n'
                      '        if isinstance(item, str):\n'
                      '            values[item] = item\n'
                      '        elif isinstance(item, dict) and item.get("domain"):\n'
                      '            domain = item["domain"]\n'
                      '            company = item.get("company") or item.get("name") or domain\n'
                      '            values[domain] = f"{company} ({domain})" if company != domain else domain\n'
                      '    return dict(sorted(values.items(), key=lambda item: item[1].casefold()))\n'
                      '\n'
                      '\n'
                      'def _call(api, method, path, key, **kwargs):\n'
                      '    st.session_state.pop(key, None)\n'
                      '    response = api(method, path, error_state=key, **kwargs)\n'
                      '    if response is None:\n'
                      '        return None\n'
                      '    if getattr(response, "ok", True) is False:\n'
                      '        detail = response.json().get("detail")\n'
                      '        st.session_state[key] = {"message": detail if isinstance(detail, str) else "This action '
                      'could not finish. Try again."}\n'
                      '        return None\n'
                      '    return response.json()\n'
                      '\n'
                      '\n'
                      'def _error(key, fallback=None):\n'
                      '    value = st.session_state.get(key) or {}\n'
                      '    if value or fallback:\n'
                      '        st.error(str(value.get("message") or fallback))\n'
                      '\n'
                      '\n'
                      'def _notice(run_id):\n'
                      '    notice = st.session_state.pop(f"delivery_notice_{run_id}", None)\n'
                      '    if notice:\n'
                      '        st.info(notice)\n'
                      '\n'
                      '\n'
                      'def _action(api, run_id, path, payload=None, notice=None, method="POST", '
                      'invalidate_run=False):\n'
                      '    key = f"delivery_action_error_{run_id}"\n'
                      '    result = _call(api, method, path, key, json=payload or {})\n'
                      '    if result is not None:\n'
                      '        if invalidate_run:\n'
                      '            st.session_state.pop("campaign_run_snapshot", None)\n'
                      '        st.session_state[f"delivery_notice_{run_id}"] = notice or "Schedule updated."\n'
                      '        st.rerun()\n'
                      '    _error(key)\n'
                      '\n'
                      '\n'
                      'def _ready(options):\n'
                      '    # The server also enforces these values. A conflicting older response must\n'
                      '    # never expose an enabled send control in this client.\n'
                      '    locked = options.get("test_recipient", TEST_RECIPIENT) == TEST_RECIPIENT\n'
                      '    if options.get("mode") == "apollo_native":\n'
                      '        senders = options.get("senders") or []\n'
                      '        addresses = [item.get("email") if isinstance(item, dict) else item for item in '
                      'senders]\n'
                      '        locked = locked and bool(addresses) and all(email in SENDERS for email in addresses)\n'
                      '    else:\n'
                      '        locked = locked and options.get("sender", TEST_SENDER) == TEST_SENDER\n'
                      '    return bool(options.get("ready")) and locked\n'
                      '\n'
                      '\n'
                      'def _setup_notice(options):\n'
                      '    if not _ready(options):\n'
                      '        native = options.get("mode") == "apollo_native"\n'
                      '        fallback = ("Email sending needs setup. Check the approved sender mailboxes in Apollo." '
                      'if native else\n'
                      '                    "Email sending needs setup. Connect the authorized sender in Apollo before '
                      'starting.")\n'
                      '        reason = options.get("reason") or fallback\n'
                      '        if options.get("test_recipient", TEST_RECIPIENT) != TEST_RECIPIENT:\n'
                      '            reason = "Sending is blocked because the test recipient or sender does not match '
                      'the approved addresses."\n'
                      '        st.warning(reason)\n'
                      '        if native:\n'
                      '            st.caption("You can review the emails here. Emails not yet accepted by Apollo '
                      'remain unscheduled until setup is complete.")\n'
                      '        else:\n'
                      '            st.caption("You can still review and prepare the schedule. Sending begins only '
                      'after setup is ready and you explicitly start the schedule or choose Send now.")\n'
                      '\n'
                      '\n'
                      'def _native_controls(api, run_id, plan, options):\n'
                      '    counts = plan.get("counts") or {}\n'
                      '    total = int(counts.get("total") or 0)\n'
                      '    accepted = int(counts.get("accepted") or 0)\n'
                      '    sent = int(counts.get("sent") or 0)\n'
                      '    pending = int(counts.get("pending_handoff") or 0)\n'
                      '    attention = int(counts.get("attention") or 0)\n'
                      '    stopped = int(counts.get("stopped") or 0)\n'
                      '    operation = bool(plan.get("pending_operation"))\n'
                      '    incomplete = _native_incomplete(plan)\n'
                      '    if plan.get("approval_required"):\n'
                      '        st.markdown("**Proposed email schedule**")\n'
                      '        st.caption(f"{total:,} emails are ready for review. Nothing has been started in '
                      'Apollo." if not accepted else\n'
                      '                   f"{pending:,} unsubmitted emails await approval. The {accepted:,} already '
                      'accepted emails keep their current schedule.")\n'
                      '        summaries = plan.get("sender_summary") or []\n'
                      '        if summaries:\n'
                      '            for column, sender in zip(st.columns(len(summaries)), summaries):\n'
                      '                column.markdown(f"**{sender.get(\'name\') or '
                      'SENDER_NAMES.get(sender.get(\'email\')) or \'Sender\'}**")\n'
                      '                column.caption(f"{int(sender.get(\'accounts\') or 0):,} companies · '
                      '{int(sender.get(\'ready_contacts\') or 0):,} contacts")\n'
                      '        if plan.get("schedule_stale"):\n'
                      '            st.info("Some proposed dates have passed. Update them and review the new schedule '
                      'before approving.")\n'
                      '            if st.button("Update proposed dates", '
                      'key=f"delivery_refresh_dates_{plan[\'id\']}"):\n'
                      '                _action(api, run_id, f"/delivery/plans/{plan[\'id\']}/refresh-schedule", '
                      'notice="Proposed dates updated. Review them before approving.")\n'
                      '        elif not plan.get("can_start"):\n'
                      '            st.caption("Resolve the schedule details below before approving this campaign.")\n'
                      '        if st.button("Approve & start in Apollo", type="primary", '
                      'key=f"delivery_approve_{plan[\'id\']}",\n'
                      '                     disabled=not _ready(options) or not plan.get("can_start") or not '
                      'plan.get("approval_token") or bool(plan.get("schedule_stale"))):\n'
                      '            _action(api, run_id, f"/delivery/plans/{plan[\'id\']}/start", {"approval_token": '
                      'plan["approval_token"]},\n'
                      '                    notice="Campaign approved. Adding the reviewed emails and schedule to '
                      'Apollo; acceptance will appear here.")\n'
                      '        st.caption(f"Approval starts only the reviewed test campaign. Every email is addressed '
                      'to {TEST_RECIPIENT}.")\n'
                      '        return\n'
                      '    if operation:\n'
                      '        st.markdown("**Confirming schedule changes with Apollo**")\n'
                      '        st.caption("The existing schedule remains in effect until the change is confirmed.")\n'
                      '    elif incomplete:\n'
                      '        st.markdown("**Schedule needs attention**")\n'
                      '    elif plan.get("status") == "paused":\n'
                      '        st.markdown("**Schedule paused**")\n'
                      '    elif total and sent + stopped >= total:\n'
                      '        st.markdown("**Schedule finished**")\n'
                      '    elif pending:\n'
                      '        st.markdown("**Preparing the email schedule**")\n'
                      '    elif attention:\n'
                      '        st.markdown("**Schedule needs attention**")\n'
                      '    elif accepted:\n'
                      '        st.markdown("**Scheduled in Apollo**")\n'
                      '    else:\n'
                      '        st.markdown("**Preparing the email schedule**")\n'
                      '    if pending and total:\n'
                      '        st.progress(min(accepted / total, 1.0), text=f"{accepted:,} of {total:,} emails '
                      'accepted by Apollo")\n'
                      '    if incomplete:\n'
                      '        st.caption("Scheduling is incomplete or still needs confirmation. Review the sender '
                      'details below; accepted emails and confirmed delivery history remain available.")\n'
                      '    elif _native_finished(plan):\n'
                      '        st.caption("No emails remain scheduled. Confirmed outcomes are available in History.")\n'
                      '    elif accepted and plan.get("status") == "paused":\n'
                      '        st.caption("Accepted emails remain in Apollo. Sending is paused.")\n'
                      '    elif accepted and _native_remaining(plan):\n'
                      '        st.caption("Upcoming emails accepted by Apollo continue when this app is closed. '
                      'Accepted does not mean sent; delivery confirmation appears below.")\n'
                      '    elif accepted:\n'
                      '        st.caption("Accepted emails are recorded in History. Review any emails that need '
                      'attention before continuing.")\n'
                      '    elif total:\n'
                      '        st.caption("The approved emails are being added to Apollo. No emails have been '
                      'confirmed as scheduled yet.")\n'
                      '    summaries = plan.get("sender_summary") or []\n'
                      '    if summaries:\n'
                      '        with st.container(border=True):\n'
                      '            columns = st.columns(min(3, len(summaries)))\n'
                      '            for index, sender in enumerate(summaries):\n'
                      '                with columns[index % len(columns)]:\n'
                      '                    email = sender.get("email") or ""\n'
                      '                    st.markdown(f"**{sender.get(\'name\') or SENDER_NAMES.get(email) or '
                      '\'Sender\'}**")\n'
                      '                    st.caption(f"{int(sender.get(\'accounts\') or 0):,} companies · '
                      '{int(sender.get(\'ready_contacts\') or 0):,} ready contacts")\n'
                      '                    st.caption(f"{int(sender.get(\'accepted\') or 0):,} accepted · '
                      '{int(sender.get(\'sent\') or 0):,} sent")\n'
                      '                    if sender.get("error"):\n'
                      '                        st.warning(sender["error"])\n'
                      '    st.caption(f"{pending:,} preparing · {accepted:,} accepted in total · {sent:,} confirmed '
                      'sent · {stopped:,} stopped")\n'
                      '    if attention:\n'
                      '        st.warning(f"{attention:,} email(s) need attention. Open the email below to see the '
                      'reason.")\n'
                      '    if plan.get("error"):\n'
                      '        st.error(plan["error"])\n'
                      '    actions = [("can_pause", "Pause schedule", "pause", "Pause requested. The schedule changes '
                      'only after Apollo confirms it."),\n'
                      '               ("can_resume", "Resume schedule", "start", "Resume requested. Check the schedule '
                      'for Apollo\'s confirmation."),\n'
                      '               ("can_retry", "Retry scheduling", "retry", "Retry requested for emails that were '
                      'not accepted. Already scheduled emails are kept.")]\n'
                      '    for capability, label, endpoint, notice in actions:\n'
                      '        if plan.get(capability) and st.button(label, disabled=operation or (capability != '
                      '"can_pause" and not _ready(options)),\n'
                      '                                             '
                      'key=f"delivery_native_{endpoint}_{plan[\'id\']}"):\n'
                      '            _action(api, run_id, f"/delivery/plans/{plan[\'id\']}/{endpoint}", notice=notice)\n'
                      '\n'
                      '\n'
                      'def _plan_controls(api, run_id, plan, options):\n'
                      '    if _native(plan):\n'
                      '        _native_controls(api, run_id, plan, options)\n'
                      '        return\n'
                      '    status = plan.get("status", "paused")\n'
                      '    counts = plan.get("counts") or {}\n'
                      '    pending = int(counts.get("pending") or 0)\n'
                      '    if status in ACTIVE_PLAN_STATES and (pending or counts.get("queued")):\n'
                      '        st.markdown("**Test schedule is running**")\n'
                      '        st.caption("Emails will be submitted at their scheduled times while the service is '
                      'running. A reply, bounce or unsubscribe stops later emails for that contact.")\n'
                      '        if st.button("Pause schedule", key=f"delivery_pause_{plan[\'id\']}"):\n'
                      '            _action(api, run_id, f"/delivery/plans/{plan[\'id\']}/pause", notice="Schedule '
                      'paused. Emails already submitted to Apollo may still be sent.")\n'
                      '    elif not pending and counts.get("queued"):\n'
                      '        st.markdown("**Waiting for delivery confirmation**")\n'
                      '    elif status == "complete" or not pending and counts.get("total"):\n'
                      '        st.markdown("**Schedule finished**" if not counts.get("attention") else "**Schedule '
                      'needs attention**")\n'
                      '    else:\n'
                      '        st.markdown("**Schedule paused**")\n'
                      '        st.caption("Review the schedule, then start when you are ready. You can also send the '
                      'next eligible email now.")\n'
                      '        label = "Resume test schedule" if plan.get("started_at") else "Start test schedule"\n'
                      '        if st.button(label, disabled=not _ready(options) or not pending or '
                      'bool(plan.get("unresolved")), key=f"delivery_start_{plan[\'id\']}"):\n'
                      '            _action(api, run_id, f"/delivery/plans/{plan[\'id\']}/start", notice="Test schedule '
                      'started. Upcoming emails will go only to the test inbox.")\n'
                      '    if counts.get("attention"):\n'
                      '        st.warning(f"{int(counts[\'attention\']):,} email(s) need attention. Open History below '
                      'to see the reason before taking another action.")\n'
                      '    sent = int(counts.get("sent") or 0)\n'
                      '    queued = int(counts.get("queued") or 0)\n'
                      '    stopped = int(counts.get("stopped") or 0)\n'
                      '    st.caption(f"{pending:,} scheduled · {queued:,} awaiting confirmation · {sent:,} sent · '
                      '{stopped:,} stopped")\n'
                      '    if plan.get("error"):\n'
                      '        st.error(plan["error"])\n'
                      '\n'
                      '\n'
                      'def _timezone_choices(plan, options, unresolved):\n'
                      '    overrides = dict(plan.get("timezone_overrides") or {})\n'
                      '    zones = [value for value in options.get("timezones") or [] if isinstance(value, str)]\n'
                      '    locations = {str(item.get("timezone_key") or item.get("metro") or ""): item\n'
                      '                 for item in unresolved if isinstance(item, dict)}\n'
                      '    for key, item in sorted(locations.items()):\n'
                      '        label = item.get("location_label") or item.get("metro") or "unspecified location"\n'
                      '        if item.get("can_select_timezone") is False:\n'
                      '            st.caption(f"{item.get(\'contact_name\') or \'Contact\'}: {item.get(\'reason\') or '
                      '\'Location unavailable.\'}")\n'
                      '            continue\n'
                      '        current = overrides.get(key)\n'
                      '        selected = st.selectbox(f"Time zone for {label}", zones,\n'
                      '            index=zones.index(current) if current in zones else None, placeholder="Choose the '
                      'contact\'s local time zone",\n'
                      '            key=f"delivery_zone_{plan[\'id\']}_{key}")\n'
                      '        if selected:\n'
                      '            overrides[key] = selected\n'
                      '    return overrides\n'
                      '\n'
                      '\n'
                      'def _schedule_settings(api, run_id, plan, options):\n'
                      '    native = _native(plan)\n'
                      '    accounts = account_options(plan.get("accounts"))\n'
                      '    unresolved = plan.get("unresolved") or plan.get("unresolved_timezones") or []\n'
                      '    if unresolved:\n'
                      '        st.warning("Some contact locations need a time zone or a complete location before their '
                      'emails can be scheduled. Check Schedule settings.")\n'
                      '    panel = st.expander("Schedule settings", expanded=False, '
                      'key=f"delivery_settings_{plan[\'id\']}", on_change="rerun")\n'
                      '    if not panel.open:\n'
                      '        return\n'
                      '    with panel:\n'
                      '        counts = plan.get("counts") or {}\n'
                      '        can_edit = plan.get("can_edit", plan.get("status") == "paused" and\n'
                      '                            not any(counts.get(key) for key in ("sent", "queued", "stopped", '
                      '"attention")))\n'
                      '        if not can_edit:\n'
                      '            if native and plan.get("can_update_timezones") and unresolved:\n'
                      '                st.caption("Choose time zones for the remaining emails. Emails already accepted '
                      'keep their schedule.")\n'
                      '                with st.form(f"delivery_zones_form_{plan[\'id\']}"):\n'
                      '                    overrides = _timezone_choices(plan, options, unresolved)\n'
                      '                    if st.form_submit_button("Save time zones"):\n'
                      '                        _action(api, run_id, f"/delivery/plans/{plan[\'id\']}", '
                      '{"timezone_overrides": overrides}, method="PATCH",\n'
                      '                                notice="Time zones submitted. Scheduling continues for eligible '
                      'emails.")\n'
                      '                return\n'
                      '            st.caption("Emails already accepted by Apollo keep their schedule. Open an upcoming '
                      'email to see its available controls."\n'
                      '                       if native else "The schedule has started. Pause it to change individual '
                      'upcoming emails; emails already submitted remain in the history.")\n'
                      '            return\n'
                      '        current_domains = plan.get("selected_domains") or list(accounts)\n'
                      '        current_domains = [domain for domain in current_domains if domain in accounts]\n'
                      '        try:\n'
                      '            initial_date = date.fromisoformat(str(plan.get("local_start_date")))\n'
                      '        except (TypeError, ValueError):\n'
                      '            initial_date = datetime.now(IST).date()\n'
                      '        try:\n'
                      '            initial_time = time.fromisoformat(str(plan.get("local_send_time") or '
                      'options.get("local_send_time") or "10:00"))\n'
                      '        except (TypeError, ValueError):\n'
                      '            initial_time = time(10, 0)\n'
                      '        with st.form(f"delivery_settings_form_{plan[\'id\']}"):\n'
                      '            selected = st.multiselect("Companies in schedule", list(accounts), '
                      'default=current_domains,\n'
                      '                                      format_func=lambda value: accounts[value], '
                      'key=f"delivery_include_{plan[\'id\']}")\n'
                      '            st.caption("This selection controls which companies\' drafts are scheduled. The '
                      'Company filter below only changes what you see.")\n'
                      '            left, middle, right = st.columns([1, 1, 1])\n'
                      '            start = left.date_input("Start on or after", value=initial_date, '
                      'key=f"delivery_start_date_{plan[\'id\']}")\n'
                      '            if native:\n'
                      '                hour = middle.selectbox("Local delivery window", list(range(23)), '
                      'index=min(initial_time.hour, 22),\n'
                      '                    format_func=lambda value: f"{value:02d}:00–{value + 1:02d}:00", '
                      'key=f"delivery_local_hour_{plan[\'id\']}")\n'
                      '                local_time = time(hour, 0)\n'
                      '            else:\n'
                      '                local_time = middle.time_input("Local send time", value=initial_time, '
                      'key=f"delivery_local_time_{plan[\'id\']}")\n'
                      '            window = right.selectbox("Sending days", ["weekdays", "daily"],\n'
                      '                                     index=0 if plan.get("window", "weekdays") == "weekdays" '
                      'else 1,\n'
                      '                                     format_func=lambda value: "Weekdays" if value == '
                      '"weekdays" else "Every day",\n'
                      '                                     key=f"delivery_window_{plan[\'id\']}")\n'
                      '            st.caption("Day 1, Day 4 and Day 7, within the selected delivery window in each '
                      'contact\'s location. Apollo confirms the delivery dates; weekday schedules skip weekends."\n'
                      '                       if native else "Day 1, Day 4 and Day 7, at the selected local time in '
                      'each contact\'s location. Weekend dates move to the next weekday when Weekdays is selected.")\n'
                      '            overrides = _timezone_choices(plan, options, unresolved)\n'
                      '            if st.form_submit_button("Save schedule", disabled=not accounts):\n'
                      '                if not selected:\n'
                      '                    st.error("Select at least one company for the schedule.")\n'
                      '                else:\n'
                      '                    _action(api, run_id, f"/delivery/plans/{plan[\'id\']}",\n'
                      '                        {"selected_domains": selected, "local_start_date": start.isoformat(),\n'
                      '                         "local_send_time": local_time.strftime("%H:%M"), "window": window,\n'
                      '                         "timezone_overrides": overrides}, method="PATCH",\n'
                      '                        notice="Schedule changes requested. Check the times and acceptance '
                      'status below." if native else\n'
                      '                               "Schedule updated and paused. Review the confirmed times before '
                      'starting.")\n'
                      '\n'
                      '\n'
                      'def _message(api, run_id, item, ready, native=False):\n'
                      '    local, ist, _ = due_labels(item, native)\n'
                      '    company = item.get("company") or item.get("domain") or "Company"\n'
                      '    person = item.get("name") or "Contact"\n'
                      '    day = item.get("day", "?")\n'
                      '    state = "Send requested" if item.get("manual_requested") and item.get("status") == '
                      '"pending" else status_label(item.get("status"))\n'
                      '    if native and item.get("status") == "accepted":\n'
                      '        state = "Accepted by Apollo"\n'
                      '    if native and item.get("status") == "scheduled":\n'
                      '        state = "Accepted · schedule unconfirmed" if item.get("schedule_unconfirmed") else '
                      '"Scheduled in Apollo"\n'
                      '    label = f"{company} · {person} · Day {day} · {state}"\n'
                      '    panel = st.expander(label, expanded=False, key=f"delivery_email_{item[\'id\']}", '
                      'on_change="rerun")\n'
                      '    if not panel.open:\n'
                      '        return\n'
                      '    with panel:\n'
                      '        st.caption(f"{local}" + (f" · {ist}" if ist else ""))\n'
                      '        if item.get("schedule_delay_reason"):\n'
                      '            st.caption(str(item["schedule_delay_reason"]))\n'
                      '        st.write(str(item.get("subject") or "Subject unavailable"))\n'
                      '        sender = item.get("sender") or ("Sender to be confirmed" if native else TEST_SENDER)\n'
                      '        st.caption(f"To: {TEST_RECIPIENT} · From: {sender}")\n'
                      '        original = item.get("original_email")\n'
                      '        if original:\n'
                      '            st.caption(f"Draft prepared for {person} at {company} ({original}). This person '
                      'will not receive the test email.")\n'
                      '        if item.get("contact_location"):\n'
                      '            st.caption(f"Contact location: {item[\'contact_location\']}")\n'
                      '        signals = item.get("signal_metros") or ([item["metro"]] if item.get("metro") else [])\n'
                      '        if signals:\n'
                      '            tier = {"exact": "Exact metro", "nearby": "Nearby", "company": '
                      '"Company-wide"}.get(item.get("match_tier"))\n'
                      '            st.caption("Signal metros: " + "; ".join(signals) + (f" · Contact match: {tier}" if '
                      'tier else ""))\n'
                      '        st.text(str(item.get("body") or "Email text unavailable"))\n'
                      '        if item.get("error"):\n'
                      '            st.warning(item["error"])\n'
                      '        if item.get("pending_operation"):\n'
                      '            st.caption("A change has been requested. Waiting for Apollo to confirm the '
                      'result.")\n'
                      '        elif native and item.get("status") in {"accepted", "scheduled"}:\n'
                      '            st.caption("Apollo has received this email, but its schedule still needs '
                      'confirmation." if item.get("schedule_unconfirmed") else\n'
                      '                       "Apollo has accepted this email. It has not been confirmed as sent.")\n'
                      '        elif item.get("status") in {"uncertain", "ambiguous", "reconciling", "queued", '
                      '"accepted"}:\n'
                      '            st.caption("Waiting for Apollo to confirm what happened. This email will not be '
                      'submitted again automatically.")\n'
                      '        if item.get("can_send_now"):\n'
                      '            left, right = st.columns([1, 3])\n'
                      '            if left.button("Send now", disabled=not ready or '
                      'bool(item.get("pending_operation")), key=f"delivery_send_{item[\'id\']}",\n'
                      '                           help=f"Send this email only to {TEST_RECIPIENT}. Its scheduled send '
                      'is removed."):\n'
                      '                _action(api, run_id, f"/delivery/messages/{item[\'id\']}/send-now",\n'
                      '                        notice="Send requested for the test inbox. This email will not be sent '
                      'again at its scheduled time. Track the confirmed outcome in History.")\n'
                      '            right.caption("Sends this email once, instead of its scheduled time.")\n'
                      '        if native or item.get("status") in {"pending", "scheduled", "blocked_timezone"}:\n'
                      '            if item.get("can_reschedule", not native and not item.get("manual_requested")):\n'
                      '                _reschedule(api, run_id, item, native)\n'
                      '            if item.get("can_cancel", not native) and not item.get("pending_operation"):\n'
                      '                cancel_control(api, f"/delivery/messages/{item[\'id\']}/cancel", '
                      'f"email_{item[\'id\']}",\n'
                      '                    label="Cancel this and later emails", noun="this email and its later '
                      'follow-ups",\n'
                      '                    message="Requesting cancellation from Apollo." if native else "Removing '
                      'these emails from the schedule.",\n'
                      '                    confirm_note="Sent emails stay in the delivery history.",\n'
                      '                    pending_note="Upcoming emails stay scheduled until Apollo confirms the '
                      'cancellation." if native else\n'
                      '                                 "The schedule will update after cancellation is confirmed.")\n'
                      '\n'
                      '\n'
                      'def _reschedule(api, run_id, item, native=False):\n'
                      '    zone_name = item.get("timezone") or item.get("time_zone")\n'
                      '    try:\n'
                      '        zone = ZoneInfo(zone_name)\n'
                      '    except (TypeError, ValueError, ZoneInfoNotFoundError):\n'
                      '        st.caption("Choose this contact location\'s time zone in Schedule settings before '
                      'setting a send time.")\n'
                      '        return\n'
                      '    due = parse_time(item.get("confirmed_due_at")) or parse_time(item.get("due_at")) or '
                      'datetime.now(timezone.utc)\n'
                      '    due = due.astimezone(zone)\n'
                      '    with st.form(f"delivery_reschedule_{item[\'id\']}"):\n'
                      '        left, right = st.columns(2)\n'
                      '        selected_date = left.date_input("Send date", value=due.date(), '
                      'key=f"delivery_date_{item[\'id\']}")\n'
                      '        selected_time = right.time_input(f"Send time ({zone_name})", '
                      'value=due.time().replace(tzinfo=None),\n'
                      '                                         key=f"delivery_time_{item[\'id\']}")\n'
                      '        st.caption("Later follow-ups may move to preserve the gap between emails." +\n'
                      '                   (" The change takes effect only after Apollo confirms it." if native else '
                      '""))\n'
                      '        if st.form_submit_button("Change send time", '
                      'disabled=bool(item.get("pending_operation"))):\n'
                      '            try:\n'
                      '                value = local_send_at(selected_date, selected_time, zone)\n'
                      '            except ValueError as exc:\n'
                      '                st.error(str(exc))\n'
                      '            else:\n'
                      '                _action(api, run_id, f"/delivery/messages/{item[\'id\']}/reschedule", '
                      '{"due_at": value},\n'
                      '                        notice="Time change requested. Check the schedule for Apollo\'s '
                      'confirmed delivery time." if native else\n'
                      '                               "Send time updated. The confirmed local time and IST equivalent '
                      'appear in the schedule.")\n'
                      '\n'
                      '\n'
                      'def _agenda(api, run_id, plan, options):\n'
                      '    native = _native(plan)\n'
                      '    accounts = account_options(plan.get("accounts"))\n'
                      '    left, right = st.columns([2, 1])\n'
                      '    domain = left.selectbox("Company", [""] + list(accounts), format_func=lambda value: '
                      'accounts.get(value, "All companies"),\n'
                      '                            key=f"delivery_company_{plan[\'id\']}")\n'
                      '    view = right.segmented_control("Emails", ["Upcoming", "History"], default="Upcoming", '
                      'selection_mode="single",\n'
                      '                                   key=f"delivery_view_{plan[\'id\']}") or "Upcoming"\n'
                      '    scope = f"{plan[\'id\']}_{domain}_{view}"\n'
                      '    page_key = f"delivery_page_{scope}"\n'
                      '    page = int(st.session_state.get(page_key, 0))\n'
                      '    data = _call(api, "GET", f"/delivery/plans/{plan[\'id\']}", '
                      'f"delivery_agenda_error_{run_id}",\n'
                      '                 params={"domain": domain, "status": view.lower(), "offset": page * PAGE_SIZE, '
                      '"limit": PAGE_SIZE})\n'
                      '    if data is None:\n'
                      '        _error(f"delivery_agenda_error_{run_id}", "The schedule is temporarily unavailable.")\n'
                      '        return\n'
                      '    rows = data.get("items") or []\n'
                      '    total = int(data.get("total") or 0)\n'
                      '    pages = max(1, ceil(total / PAGE_SIZE))\n'
                      '    if page >= pages:\n'
                      '        st.session_state[page_key] = pages - 1\n'
                      '        st.rerun()\n'
                      '    if not rows:\n'
                      '        st.caption("No upcoming emails for this selection." if view == "Upcoming" else "No '
                      'delivery history for this selection yet.")\n'
                      '        return\n'
                      '    if native:\n'
                      '        first = plan.get("delivery_window_start") or plan.get("local_send_time") or "10:00"\n'
                      '        last = plan.get("delivery_window_end") or "11:00"\n'
                      '        st.caption(f"Planned dates use a {first}–{last} delivery window in each contact\'s '
                      'location, with IST alongside. Apollo-confirmed times replace estimates when available.")\n'
                      '    else:\n'
                      '        st.caption("Scheduled in each contact\'s local time zone. IST is shown alongside it. '
                      'Open an email to read it or change its send time.")\n'
                      '    with st.container(height=390, border=False):\n'
                      '        previous_day = None\n'
                      '        for item in rows:\n'
                      '            item = {**item}\n'
                      '            if native:\n'
                      '                group = next((group for group in plan.get("groups") or [] if group.get("id") == '
                      'item.get("group_id")), None)\n'
                      '                item["schedule_unconfirmed"] = _native_incomplete(group if group is not None '
                      'else plan)\n'
                      '            for key in ("delivery_window_start", "delivery_window_end"):\n'
                      '                if key not in item and plan.get(key):\n'
                      '                    item[key] = plan[key]\n'
                      '            local, ist, day = due_labels(item, native)\n'
                      '            heading = day or "Time to be confirmed"\n'
                      '            if heading != previous_day:\n'
                      '                st.markdown(f"**{heading}**")\n'
                      '                previous_day = heading\n'
                      '            # The time remains visible without requiring a preview click.\n'
                      '            st.caption(local + (f" · {ist}" if ist else ""))\n'
                      '            approved_item = item.get("status") in {"accepted", "scheduled", "queued", "sent", '
                      '"delivered"}\n'
                      '            _message(api, run_id, item, _ready(options) and (not plan.get("approval_required") '
                      'or approved_item), native)\n'
                      '    if pages > 1:\n'
                      '        previous, counter, following = st.columns([1, 3, 1])\n'
                      '        if previous.button("Previous", disabled=page == 0, key=f"delivery_previous_{scope}"):\n'
                      '            st.session_state[page_key] = page - 1\n'
                      '            st.rerun()\n'
                      '        counter.caption(f"Page {page + 1} of {pages} · {total:,} emails")\n'
                      '        if following.button("Next", disabled=page + 1 >= pages, key=f"delivery_next_{scope}"):\n'
                      '            st.session_state[page_key] = page + 1\n'
                      '            st.rerun()\n'
                      '\n'
                      '\n'
                      'def schedule_csv(items, plan):\n'
                      '    """Literal spreadsheet text, with every scheduled occurrence represented."""\n'
                      '    output = StringIO(newline="")\n'
                      '    writer = csv.writer(output)\n'
                      '    writer.writerow(["Company", "Domain", "Contact", "Contact location", "Signal metros", '
                      '"Location match", "Day", "Sender", "Subject", "Local schedule", "Time zone", "IST schedule", '
                      '"Status", "Test recipient"])\n'
                      '    def literal(value):\n'
                      '        text = str(value or "")\n'
                      '        return "\'" + text if text.lstrip().startswith(("=", "+", "-", "@")) or '
                      'text.startswith(("\\t", "\\r")) else text\n'
                      '    for item in items:\n'
                      '        local, ist, _ = due_labels({**{k: plan[k] for k in ("delivery_window_start", '
                      '"delivery_window_end") if k in plan}, **item}, _native(plan))\n'
                      '        writer.writerow([literal(value) for value in (item.get("company") or '
                      'item.get("domain"), item.get("domain"),\n'
                      '            item.get("name"), item.get("contact_location") or "",\n'
                      '            "; ".join(item.get("signal_metros") or ([item["metro"]] if item.get("metro") else '
                      '[])),\n'
                      '            {"exact": "Exact metro", "nearby": "Nearby", "company": '
                      '"Company-wide"}.get(item.get("match_tier"), ""),\n'
                      '            item.get("day"), item.get("sender"), item.get("subject"), local,\n'
                      '            item.get("timezone") or item.get("time_zone"), ist, '
                      'status_label(item.get("status")), TEST_RECIPIENT)])\n'
                      '    return output.getvalue().encode("utf-8-sig")\n'
                      '\n'
                      '\n'
                      'def _schedule_download(api, run_id, plan):\n'
                      '    key = f"schedule_export_{plan[\'id\']}"\n'
                      '    panel = st.expander("Download schedule", expanded=False, '
                      'key=f"schedule_download_panel_{plan[\'id\']}", on_change="rerun")\n'
                      '    if not panel.open:\n'
                      '        return\n'
                      '    with panel:\n'
                      '        st.caption("Includes every company and email in this schedule, with local times, IST, '
                      'senders and status.")\n'
                      '        if st.button("Prepare schedule download", '
                      'key=f"schedule_export_prepare_{plan[\'id\']}"):\n'
                      '            items, offset, expected = [], 0, None\n'
                      '            with st.spinner("Preparing the full schedule…"):\n'
                      '                while expected is None or offset < expected:\n'
                      '                    page = _call(api, "GET", f"/delivery/plans/{plan[\'id\']}", '
                      'f"schedule_export_error_{run_id}",\n'
                      '                                 params={"offset": offset, "limit": 200})\n'
                      '                    if page is None:\n'
                      '                        break\n'
                      '                    rows = page.get("items") or []\n'
                      '                    expected = int(page.get("total") or 0)\n'
                      '                    if not rows and offset < expected:\n'
                      '                        st.session_state[f"schedule_export_error_{run_id}"] = {"message": "The '
                      'schedule changed while preparing the download. Please try again."}\n'
                      '                        break\n'
                      '                    items.extend(rows)\n'
                      '                    offset += len(rows)\n'
                      '                    if offset >= expected:\n'
                      '                        if len({item.get("id") for item in items}) != len(items):\n'
                      '                            st.session_state[f"schedule_export_error_{run_id}"] = {"message": '
                      '"The schedule changed while preparing the download. Please try again."}\n'
                      '                            break\n'
                      '                        st.session_state[key] = {"bytes": schedule_csv(items, plan), "rows": '
                      'len(items),\n'
                      '                            "at": datetime.now(IST).strftime("%d %b, %I:%M %p IST")}\n'
                      '                        st.rerun()\n'
                      '            _error(f"schedule_export_error_{run_id}")\n'
                      '        saved = st.session_state.get(key)\n'
                      '        if saved:\n'
                      '            st.download_button("Download schedule CSV", saved["bytes"], '
                      'file_name="campaign_email_schedule.csv", mime="text/csv", on_click="ignore")\n'
                      '            st.caption(f"{saved[\'rows\']:,} emails · Prepared {saved[\'at\']}. Prepare again '
                      'to include later status changes.")\n'
                      '\n'
                      '\n'
                      'def render_delivery(api, run_id, snapshot=None, capabilities=None):\n'
                      '    """Render delivery independently of the source report\'s in-memory lifetime.\n'
                      '\n'
                      '    Rendering only reads. The user explicitly approves the current proposal;\n'
                      '    viewing a plan never starts it or recreates its emails.\n'
                      '    """\n'
                      '    if not run_id:\n'
                      '        return\n'
                      '    options = _call(api, "GET", "/delivery/options", f"delivery_setup_error_{run_id}")\n'
                      '    if options is None:\n'
                      '        _error(f"delivery_setup_error_{run_id}", "Email scheduling is temporarily '
                      'unavailable.")\n'
                      '        return\n'
                      '    st.markdown("**Email schedule**")\n'
                      '    st.info(f"Test mode · Every email goes only to {TEST_RECIPIENT}. No emails go to '
                      'prospects.")\n'
                      '    _setup_notice(options)\n'
                      '    data = _call(api, "GET", "/delivery/plans", f"delivery_plans_error_{run_id}", '
                      'params={"run_id": run_id})\n'
                      '    if data is None:\n'
                      '        _error(f"delivery_plans_error_{run_id}", "Your email schedule is temporarily '
                      'unavailable.")\n'
                      '        return\n'
                      '    plans = data.get("plans") or []\n'
                      '    plan = plans[0] if plans else None\n'
                      '    if not plan:\n'
                      '        _notice(run_id)\n'
                      '        if options.get("mode") == "apollo_native":\n'
                      '            if (snapshot or {}).get("delivery_preparing"):\n'
                      '                @st.fragment(run_every=5)\n'
                      '                def preparing():\n'
                      '                    access.require_session()\n'
                      '                    st.caption("Preparing the schedule for your ready emails…")\n'
                      '                    current = _call(api, "GET", f"/campaign-runs/{run_id}", '
                      'f"delivery_preparing_error_{run_id}")\n'
                      '                    if current is not None and not current.get("delivery_preparing"):\n'
                      '                        st.rerun()\n'
                      '                    if current is None:\n'
                      '                        _error(f"delivery_preparing_error_{run_id}", "Schedule updates are '
                      'temporarily unavailable.")\n'
                      '                preparing()\n'
                      '            elif (snapshot or {}).get("can_retry_delivery"):\n'
                      '                st.warning("The email schedule could not be prepared. Your ready drafts are '
                      'still available.")\n'
                      '                if st.button("Retry scheduling", key=f"delivery_retry_prepare_{run_id}"):\n'
                      '                    _action(api, run_id, "/delivery/plans", {"run_id": run_id}, '
                      'invalidate_run=True,\n'
                      '                            notice="Schedule preparation requested. Check its acceptance status '
                      'below.")\n'
                      '            else:\n'
                      '                st.caption("Prepare the proposed schedule, review the emails and times, then '
                      'approve starting in Apollo.")\n'
                      '                if st.button("Prepare proposed schedule", key=f"delivery_prepare_{run_id}"):\n'
                      '                    _action(api, run_id, "/delivery/plans", {"run_id": run_id}, '
                      'invalidate_run=True,\n'
                      '                            notice="Proposed schedule prepared. Review it before approving.")\n'
                      '            return\n'
                      '        st.caption("Prepare a schedule from ready email drafts. It will remain paused until you '
                      'start it.")\n'
                      '        if st.button("Prepare test schedule", key=f"delivery_prepare_{run_id}"):\n'
                      '            _action(api, run_id, "/delivery/plans", {"run_id": run_id}, notice="Schedule '
                      'prepared and paused. Review it before starting.")\n'
                      '        return\n'
                      '    linked_key = f"delivery_linked_plan_{run_id}"\n'
                      '    linked = st.session_state.get(linked_key)\n'
                      '    if linked:\n'
                      '        existing = _call(api, "GET", f"/delivery/plans/{linked}", '
                      'f"delivery_linked_error_{run_id}", params={"limit": 1})\n'
                      '        if st.button("Back to this run\'s schedule", key=f"delivery_back_{run_id}"):\n'
                      '            st.session_state.pop(linked_key, None)\n'
                      '            st.rerun()\n'
                      '        if existing is None:\n'
                      '            _error(f"delivery_linked_error_{run_id}", "The existing schedule could not be '
                      'loaded.")\n'
                      '            return\n'
                      '        st.caption("Showing the existing schedule for these emails. Each email remains '
                      'scheduled only once.")\n'
                      '        plan = existing.get("plan") or existing\n'
                      '    elif plan.get("already_planned"):\n'
                      '        st.caption(f"{int(plan[\'already_planned\']):,} emails already have a schedule and have '
                      'not been added again.")\n'
                      '        references = list(dict.fromkeys(plan.get("existing_plan_ids") or []))\n'
                      '        for index, identity in enumerate(references):\n'
                      '            label = "Open existing schedule" + (f" {index + 1}" if len(references) > 1 else '
                      '"")\n'
                      '            if st.button(label, key=f"delivery_existing_{run_id}_{identity}"):\n'
                      '                st.session_state[linked_key] = identity\n'
                      '                st.rerun()\n'
                      '        if not (plan.get("counts") or {}).get("total"):\n'
                      '            return\n'
                      '    polling = _polling(plan)\n'
                      '    if options.get("mode") == "apollo_native" and not _native(plan):\n'
                      '        st.caption("Earlier schedule · these emails retain their existing controls and have not '
                      'been added to a new schedule.")\n'
                      '\n'
                      '    @st.fragment(run_every=5 if polling else None)\n'
                      '    def live():\n'
                      '        access.require_session()\n'
                      '        current = _call(api, "GET", f"/delivery/plans/{plan[\'id\']}", '
                      'f"delivery_plan_error_{run_id}", params={"limit": 1})\n'
                      '        if current is None:\n'
                      '            _error(f"delivery_plan_error_{run_id}", "Schedule updates are temporarily '
                      'unavailable.")\n'
                      '            return\n'
                      '        current = current.get("plan") or current\n'
                      '        still_polling = _polling(current)\n'
                      '        if polling and not still_polling:\n'
                      '            st.rerun()\n'
                      '        _notice(run_id)\n'
                      '        _plan_controls(api, run_id, current, options)\n'
                      '        _schedule_settings(api, run_id, current, options)\n'
                      '        _agenda(api, run_id, current, options)\n'
                      '        _schedule_download(api, run_id, current)\n'
                      '\n'
                      '    live()\n',
 'frontend.builds': '"""Continuous account-to-campaign workspace; delivery needs final approval."""\n'
                    'from copy import deepcopy\n'
                    'from datetime import datetime, timezone\n'
                    'import time\n'
                    'import uuid\n'
                    '\n'
                    'import streamlit as st\n'
                    'from frontend import access\n'
                    '\n'
                    'from frontend.campaigns import (BRIEF_ACTIVE, BRIEF_READY, _brief_context_is_stale, '
                    '_clear_sender_overrides,\n'
                    '    _activate_run, public_service_message, render_campaign_workspace, customer_website_valid, '
                    'contact_phase_label)\n'
                    'from frontend.controls import cancel_control\n'
                    'from frontend.progress import duration, display_count, progress_view\n'
                    'from frontend.state import search_payload\n'
                    '\n'
                    'TERMINAL = {"complete", "partial", "failed", "cancelled", "interrupted"}\n'
                    'PREPARATION_APPROVAL = "awaiting_preparation_approval"\n'
                    'STAGES = {\n'
                    '    "queued": "Preparing your campaign", "searching": "Finding matching accounts",\n'
                    '    "preview": "Finding matching accounts", "week_alignment": "Checking the reporting week",\n'
                    '    "exclusions": "Checking account eligibility", "details": "Applying your company filters",\n'
                    '    "metros": "Checking location scores", "geography": "Checking surge locations",\n'
                    '    "revenue": "Checking company revenue", "previous_week": "Comparing last week\'s signals",\n'
                    '    "mapping": "Matching topics to your offerings", "excel": "Preparing account results",\n'
                    '    "waiting_for_customer_context": "Preparing the product brief", "role_plan": "Identifying '
                    'relevant contacts",\n'
                    '    "contacts": "Finding and verifying contacts", "research": "Researching reachable companies",\n'
                    '    "analysis": "Assessing account fit", "contact_refit": "Checking contact relevance",\n'
                    '    "drafts": "Writing and checking emails", "building": "Preparing your campaign",\n'
                    '    "packaging": "Preparing your campaign download",\n'
                    '    "waiting_for_confirmation": "Confirm revenue research to continue", "cancelling": "Cancelling '
                    'campaign preparation",\n'
                    '    PREPARATION_APPROVAL: "Ready to prepare your campaign",\n'
                    '    "complete": "Campaign ready to review", "partial": "Available campaign results are ready",\n'
                    '    "failed": "Campaign preparation needs attention", "cancelled": "Campaign preparation '
                    'cancelled",\n'
                    '    "interrupted": "Campaign preparation interrupted",\n'
                    '}\n'
                    '\n'
                    '\n'
                    'def enabled(options):\n'
                    '    return bool((options.get("campaign_builds") or {}).get("enabled"))\n'
                    '\n'
                    '\n'
                    'def _read(api, method, path, **kwargs):\n'
                    '    response = api(method, path, **kwargs)\n'
                    '    return response.json() if response is not None and getattr(response, "ok", True) else None\n'
                    '\n'
                    '\n'
                    'def _working(snapshot):\n'
                    '    return snapshot.get("status") not in TERMINAL | {PREPARATION_APPROVAL} or '
                    'bool(snapshot.get("cancellation_pending_requests"))\n'
                    '\n'
                    '\n'
                    'def _polling(snapshot, build_id):\n'
                    '    cancellation = st.session_state.get(f"cancel_state_build_{build_id}") or {}\n'
                    '    return _working(snapshot) or (snapshot.get("status") not in TERMINAL\n'
                    '                                 and cancellation.get("phase") in {"requesting", "sent"})\n'
                    '\n'
                    '\n'
                    'def render_build_action(api, options, draft):\n'
                    '    _clear_sender_overrides()\n'
                    '    record = st.session_state.get("campaign_brief_record") or {}\n'
                    '    caps = options.get("campaigns") or {}\n'
                    '    dirty = bool(st.session_state.get("campaign_brief_dirty"))\n'
                    '    stale = _brief_context_is_stale(caps, draft)\n'
                    '    usable = record.get("status") in BRIEF_READY | BRIEF_ACTIVE and not dirty and not stale\n'
                    '    configured = all(caps.get(key) for key in ("anthropic_configured", "openai_configured", '
                    '"apollo_configured"))\n'
                    '    name = st.text_input("Campaign name", value=(record.get("brief") or {}).get("customer_name") '
                    'or "Account campaign",\n'
                    '                         key="campaign_new_name")\n'
                    '    if (options.get("campaign_builds") or {}).get("preparation_approval_required"):\n'
                    '        st.caption("Find matching accounts, then review the account count and estimated time '
                    'before approving campaign preparation. Review the finished campaign before starting it in '
                    'Apollo.")\n'
                    '    else:\n'
                    '        st.caption("Find matching accounts, verify relevant contacts and prepare their emails. '
                    'Review the finished campaign before starting it in Apollo.")\n'
                    '    if caps.get("contact_coverage") == "signal_nearby_company":\n'
                    '        st.caption("Find up to five contacts per company, starting in signal locations and '
                    'expanding nearby, then elsewhere in the company when needed.")\n'
                    '    if not usable:\n'
                    '        st.info("Prepare the customer product brief on Choose topics before building. Save or '
                    'discard any optional edits first.")\n'
                    '    elif record.get("status") in BRIEF_ACTIVE:\n'
                    '        st.caption("Product research is underway. You can build now; the campaign will use it '
                    'when ready.")\n'
                    '    if not configured:\n'
                    '        st.warning("Campaign research and contact sourcing need setup before you can build.")\n'
                    '    can_start = usable and configured and bool(name.strip()) and bool(draft.get("topics")) and '
                    'customer_website_valid()\n'
                    '    if st.button("Build campaign", type="primary", disabled=not can_start, '
                    'key="continuous_build_start"):\n'
                    '        pending = st.session_state.get("campaign_build_submission") or {}\n'
                    '        body = {"name": name.strip(), "brief_id": record.get("id") or record.get("brief_id"), '
                    '"search": search_payload(draft)}\n'
                    '        if pending.get("body") != body:\n'
                    '            pending = {"request_id": uuid.uuid4().hex, "body": deepcopy(body)}\n'
                    '            st.session_state.campaign_build_submission = pending\n'
                    '        result = _read(api, "POST", "/campaign-builds", json={"request_id": '
                    'pending["request_id"], **body},\n'
                    '                       error_state="campaign_build_start_error")\n'
                    '        if result:\n'
                    '            st.session_state.campaign_build_id = result.get("id") or result.get("build_id")\n'
                    '            st.query_params["build"] = st.session_state.campaign_build_id\n'
                    '            st.session_state.campaign_build_snapshot = result\n'
                    '            st.session_state.campaign_build_request = deepcopy(body)\n'
                    '            for key in ("campaign_run_id", "campaign_run_snapshot", "campaign_download", '
                    '"campaign_download_signature",\n'
                    '                        "job_id", "job_progress_snapshot", "download", "download_signature"):\n'
                    '                st.session_state.pop(key, None)\n'
                    '            st.rerun()\n'
                    '    error = st.session_state.get("campaign_build_start_error") or {}\n'
                    '    if error:\n'
                    '        st.error(public_service_message(error.get("message")))\n'
                    '        st.caption("Your selections are kept. Try Build campaign again to recover the same '
                    'request.")\n'
                    '\n'
                    '\n'
                    'def stage_label(snapshot, request):\n'
                    '    status = snapshot.get("status") or "queued"\n'
                    '    if status in TERMINAL or status in {"cancelling", "waiting_for_confirmation", '
                    'PREPARATION_APPROVAL}:\n'
                    '        return STAGES[status]\n'
                    '    stage = snapshot.get("stage") or status\n'
                    '    if stage == "contacts":\n'
                    '        return contact_phase_label(snapshot.get("campaign") or snapshot)\n'
                    '    if stage == "exclusions":\n'
                    '        data = (request or {}).get("search") or {}\n'
                    '        domain = bool(data.get("suppressed_domains") or data.get("suppression_list_ids"))\n'
                    '        edu = bool(data.get("exclude_edu"))\n'
                    '        if domain and edu:\n'
                    '            return "Applying domain and education exclusions"\n'
                    '        if domain:\n'
                    '            return "Applying your domain exclusions"\n'
                    '        if edu:\n'
                    '            return "Excluding .edu domains"\n'
                    '        return "Checking account eligibility"\n'
                    '    return STAGES.get(stage, "Preparing your campaign")\n'
                    '\n'
                    '\n'
                    'def _elapsed(snapshot):\n'
                    '    if isinstance(snapshot.get("elapsed_seconds"), (float, int)):\n'
                    '        return snapshot["elapsed_seconds"]\n'
                    '    try:\n'
                    '        start = datetime.fromisoformat(str(snapshot.get("created_at")).replace("Z", "+00:00"))\n'
                    '        return max(0, (datetime.now(timezone.utc) - start).total_seconds()) if start.tzinfo else '
                    'None\n'
                    '    except (TypeError, ValueError):\n'
                    '        return None\n'
                    '\n'
                    '\n'
                    'def _last_update(snapshot):\n'
                    '    try:\n'
                    '        value = snapshot.get("last_progress_at") or snapshot.get("updated_at")\n'
                    '        if isinstance(value, (int, float)):\n'
                    '            updated = datetime.fromtimestamp(value, timezone.utc)\n'
                    '        else:\n'
                    '            updated = datetime.fromisoformat(str(value).replace("Z", "+00:00"))\n'
                    '        return max(0, (datetime.now(timezone.utc) - updated).total_seconds()) if updated.tzinfo '
                    'else None\n'
                    '    except (TypeError, ValueError, OverflowError, OSError):\n'
                    '        return None\n'
                    '\n'
                    '\n'
                    'def _progress(snapshot, request, *, preparation_approval_required=False):\n'
                    '    search = snapshot.get("search") or {}\n'
                    '    campaign = snapshot.get("campaign") or {}\n'
                    '    counts = campaign.get("counts") or snapshot.get("counts") or {}\n'
                    '    if _working(snapshot):\n'
                    '        st.status(stage_label(snapshot, request), state="running", expanded=False)\n'
                    '    else:\n'
                    '        st.markdown(f"**{stage_label(snapshot, request)}**")\n'
                    '    st.caption(f"Elapsed {duration(_elapsed(snapshot))}" +\n'
                    '               (f" · Reporting week {campaign[\'reporting_week\']}" if '
                    'campaign.get("reporting_week") else "") +\n'
                    '               (f" · Last progress update {duration(_last_update(snapshot))} ago" if '
                    '_last_update(snapshot) is not None else ""))\n'
                    '    if snapshot.get("run_id") or campaign:\n'
                    '        matched = counts.get("accounts_total", counts.get("accounts"))\n'
                    '        contacts = counts.get("contacts", 0)\n'
                    '        sequences = counts.get("drafts", counts.get("sequences", 0))\n'
                    '        checked = counts.get("contact_checked_accounts")\n'
                    '        contactable = counts.get("contactable_accounts")\n'
                    '        ready = counts.get("ready_accounts")\n'
                    '        for col, label, value in zip(st.columns(3), ("Accounts with contacts", "Verified '
                    'contacts", "Emails ready"),\n'
                    '                                    (contactable, contacts, sequences * 3)):\n'
                    '            col.metric(label, display_count(value))\n'
                    '        summary = [f"{display_count(matched)} matched accounts"]\n'
                    '        if checked is not None:\n'
                    '            summary.append(f"{display_count(checked)} checked for contacts")\n'
                    '        if ready is not None:\n'
                    '            summary.append(f"{display_count(ready)} ready for outreach")\n'
                    '        skipped = counts.get("skipped_accounts")\n'
                    '        if skipped:\n'
                    '            summary.append(f"{display_count(skipped)} skipped")\n'
                    '        st.caption(" · ".join(summary))\n'
                    '        completed = counts.get("accounts_completed", counts.get("completed", 0) + '
                    'counts.get("failed", 0))\n'
                    '        if matched:\n'
                    '            st.progress(min(1.0, completed / matched), text=f"{completed:,} of {matched:,} '
                    'accounts finished")\n'
                    '        activity = campaign.get("activity_counts") or snapshot.get("activity_counts") or {}\n'
                    '        active = []\n'
                    '        for stages, label in (((\'role_plan\', \'contacts\', \'contact_refit\'), "checking '
                    'contacts"),\n'
                    '                              ((\'research\', \'analysis\'), "researching companies"), '
                    '((\'drafts\',), "preparing emails")):\n'
                    '            count = sum(int(activity.get(stage) or 0) for stage in stages)\n'
                    '            if count:\n'
                    '                active.append(f"{count:,} {label}")\n'
                    '        if active:\n'
                    '            st.caption("In progress: " + " · ".join(active))\n'
                    '        elif snapshot.get("status") not in TERMINAL | {"cancelling"}:\n'
                    '            st.caption("The current step is still running. Counts update when a check '
                    'finishes.")\n'
                    '    else:\n'
                    '        view = progress_view(search, now=time.time())\n'
                    '        for col, label, value in zip(st.columns(3), ("Accounts remaining", "Verified contacts", '
                    '"Emails ready"),\n'
                    '                                    (view["current"]["accounts"], None, None)):\n'
                    '            col.metric(label, display_count(value))\n'
                    '        revenue = view.get("revenue")\n'
                    '        if revenue and revenue.get("total"):\n'
                    '            done, total = revenue.get("completed") or 0, revenue["total"]\n'
                    '            st.progress(min(1.0, done / total), text=f"Revenue checked for {done:,} of {total:,} '
                    'companies")\n'
                    '        elif search.get("telemetry"):\n'
                    '            finished = [stage for stage in search["telemetry"].get("stages", []) if '
                    'stage.get("status") == "complete"]\n'
                    '            if finished:\n'
                    '                st.caption("Latest completed step: " + STAGES.get(finished[-1]["id"], "Account '
                    'checks"))\n'
                    '        if search.get("status") not in TERMINAL and snapshot.get("status") != "cancelling":\n'
                    '            st.caption("The account search is running. You\'ll review the account count and '
                    'estimated time before preparation begins."\n'
                    '                       if preparation_approval_required else\n'
                    '                       "The account search is running. Contact checks and email preparation will '
                    'follow automatically.")\n'
                    '\n'
                    '\n'
                    'def _preparation_review(api, build_id, snapshot):\n'
                    '    """A paused, read-only checkpoint until the displayed proposal is approved."""\n'
                    '    approval = snapshot.get("preparation_approval") or {}\n'
                    '    approval_id = approval.get("id")\n'
                    '    error_key = f"campaign_build_preparation_error_{build_id}"\n'
                    '    cancellation = st.session_state.get(f"cancel_state_build_{build_id}") or {}\n'
                    '    cancelling = bool(snapshot.get("cancellation_pending_requests"))\n'
                    '    can_approve = bool(approval_id and snapshot.get("can_approve_preparation")\n'
                    '                       and not cancelling and not cancellation.get("phase"))\n'
                    '    with st.container(border=True):\n'
                    '        st.markdown("**Ready to prepare your campaign**")\n'
                    '        st.write(f"Up to {display_count(approval.get(\'account_count\'))} accounts")\n'
                    '        minimum, maximum = approval.get("estimate_min_minutes"), '
                    'approval.get("estimate_max_minutes")\n'
                    '        estimate = display_count(minimum) if minimum == maximum else '
                    'f"{display_count(minimum)}–{display_count(maximum)}"\n'
                    '        st.write(f"Rough time estimate: {estimate} minutes")\n'
                    '        st.caption("Estimate includes finding contacts, account research and email preparation. '
                    'Accounts without suitable contacts will be skipped for outreach.")\n'
                    '        st.caption("Waiting for your approval. Preparation has not started.")\n'
                    '        # The proposal identity is part of the widget identity. If a status read\n'
                    '        # replaces a stale proposal, a click on the old button cannot approve it.\n'
                    '        if st.button("Approve & start preparation", type="primary", disabled=not can_approve,\n'
                    '                     key=f"build_preparation_approve_{build_id}_{approval_id}") and can_approve:\n'
                    '            result = _read(api, "POST", f"/campaign-builds/{build_id}/approve-preparation",\n'
                    '                           json={"approval_id": approval_id}, error_state=error_key)\n'
                    '            if result:\n'
                    '                st.session_state.campaign_build_snapshot = result\n'
                    '                st.rerun()\n'
                    '            # A lost response can follow an accepted request. Reconcile with a\n'
                    '            # read; never repeat an approval automatically after an error.\n'
                    '            latest = _read(api, "GET", f"/campaign-builds/{build_id}", '
                    'error_state="campaign_build_status_error")\n'
                    '            if latest:\n'
                    '                st.session_state.campaign_build_snapshot = latest\n'
                    '                if latest.get("status") != PREPARATION_APPROVAL:\n'
                    '                    st.session_state.pop(error_key, None)\n'
                    '            st.rerun()\n'
                    '        error = st.session_state.get(error_key) or {}\n'
                    '        if error:\n'
                    '            st.error(public_service_message(error.get("message")))\n'
                    '            st.caption("Approval was not confirmed. Review the current account count and estimate '
                    'before trying again.")\n'
                    '        if not snapshot.get("can_approve_preparation"):\n'
                    '            st.warning("The account selection needs to be checked before approval.")\n'
                    '            if st.button("Check account selection", key=f"build_preparation_check_{build_id}"):\n'
                    '                latest = _read(api, "GET", f"/campaign-builds/{build_id}", '
                    'error_state="campaign_build_status_error")\n'
                    '                if latest:\n'
                    '                    st.session_state.campaign_build_snapshot = latest\n'
                    '                    st.rerun()\n'
                    '        cancel_control(api, f"/campaign-builds/{build_id}/cancel", f"build_{build_id}", '
                    'cancelling=cancelling,\n'
                    '                       confirm_note="The account report stays available. Contact sourcing and '
                    'campaign preparation will not start.")\n'
                    '\n'
                    '\n'
                    'def _account_download(api, snapshot):\n'
                    '    job_id = snapshot.get("job_id")\n'
                    '    search = snapshot.get("search") or {}\n'
                    '    if not job_id or search.get("status") != "complete":\n'
                    '        return\n'
                    '    with st.expander("Account report and skipped accounts", expanded=False):\n'
                    '        st.caption("The account report keeps all companies that passed your filters. The campaign '
                    'download includes contact outcomes and reasons for skipped outreach.")\n'
                    '        key = f"build_account_download_{job_id}"\n'
                    '        if key in st.session_state:\n'
                    '            st.download_button("Download account report", st.session_state[key], '
                    'file_name="intent_accounts.xlsx",\n'
                    '                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", '
                    'on_click="ignore")\n'
                    '        elif st.button("Prepare account download", key=f"build_account_export_{job_id}"):\n'
                    '            response = api("GET", f"/jobs/{job_id}/excel", timeout=600)\n'
                    '            if response is not None:\n'
                    '                st.session_state[key] = response.content\n'
                    '                st.rerun()\n'
                    '\n'
                    '\n'
                    'def render_build_workspace(api, options, draft):\n'
                    '    build_id = st.session_state.get("campaign_build_id")\n'
                    '    saved = st.session_state.get("campaign_build_snapshot") or {}\n'
                    '    polling = _polling(saved, build_id)\n'
                    '    requires_approval = bool((options.get("campaign_builds") or '
                    '{}).get("preparation_approval_required"))\n'
                    '\n'
                    '    @st.fragment(run_every=2 if polling else None)\n'
                    '    def live():\n'
                    '        access.require_session()\n'
                    '        snapshot = st.session_state.get("campaign_build_snapshot") or {}\n'
                    '        if polling or not snapshot or snapshot.get("status") == PREPARATION_APPROVAL:\n'
                    '            result = _read(api, "GET", f"/campaign-builds/{build_id}", '
                    'error_state="campaign_build_status_error")\n'
                    '            if result:\n'
                    '                st.session_state.campaign_build_snapshot = snapshot = result\n'
                    '                if polling != _polling(result, build_id):\n'
                    '                    st.rerun()\n'
                    '            elif not snapshot:\n'
                    '                st.error("Campaign progress is temporarily unavailable. Your build has not been '
                    'started again.")\n'
                    '                return\n'
                    '        if not _working(snapshot):\n'
                    '            return\n'
                    '        cancel_state = st.session_state.get(f"cancel_state_build_{build_id}") or {}\n'
                    '        visible = {**snapshot, "status": "cancelling"} if cancel_state.get("phase") in '
                    '{"requesting", "sent"} else snapshot\n'
                    '        _progress(visible, st.session_state.get("campaign_build_request") or {}, '
                    'preparation_approval_required=requires_approval)\n'
                    '        if st.session_state.get("campaign_build_status_error"):\n'
                    '            st.warning("Live status could not refresh. Showing the last confirmed update.")\n'
                    '        cancelling = snapshot.get("status") == "cancelling" or '
                    'bool(snapshot.get("cancellation_pending_requests"))\n'
                    '        cancel_control(api, f"/campaign-builds/{build_id}/cancel", f"build_{build_id}", '
                    'cancelling=cancelling)\n'
                    '        if snapshot.get("status") == "waiting_for_confirmation" and not cancelling:\n'
                    '            pending = (snapshot.get("search") or {}).get("revenue_pending") or {}\n'
                    '            st.warning(f"Revenue research needs confirmation for '
                    '{pending.get(\'uncached_domains\', \'many\')} company checks. Research charges apply.")\n'
                    '            if st.button("Continue revenue research", key=f"build_revenue_{build_id}"):\n'
                    '                result = _read(api, "POST", f"/campaign-builds/{build_id}/confirm-revenue", '
                    'json={}, error_state="campaign_build_action_error")\n'
                    '                if result:\n'
                    '                    st.session_state.campaign_build_snapshot = result\n'
                    '                    st.rerun()\n'
                    '        error = st.session_state.get("campaign_build_action_error") or {}\n'
                    '        if error:\n'
                    '            st.error(public_service_message(error.get("message")))\n'
                    '\n'
                    '    live()\n'
                    '    snapshot = st.session_state.get("campaign_build_snapshot") or {}\n'
                    '    if _working(snapshot):\n'
                    '        return\n'
                    '    if snapshot.get("status") == PREPARATION_APPROVAL:\n'
                    '        _preparation_review(api, build_id, snapshot)\n'
                    '        if st.session_state.get("campaign_build_status_error"):\n'
                    '            st.warning("Build status could not refresh. Approval will be checked against the '
                    'latest account selection.")\n'
                    '        _account_download(api, snapshot)\n'
                    '        return\n'
                    '    cancel_control(api, "", f"build_{build_id}", terminal=True)\n'
                    '    search = snapshot.get("search") or {}\n'
                    '    if snapshot.get("job_id"):\n'
                    '        st.session_state.job_id = snapshot["job_id"]\n'
                    '        st.session_state.job_progress_snapshot = search\n'
                    '    if snapshot.get("run_id") and snapshot.get("campaign"):\n'
                    '        selected = st.session_state.get("campaign_build_selected_run")\n'
                    '        if selected != snapshot["run_id"]:\n'
                    '            _activate_run(snapshot.get("campaign_id"), {"base_job_id": snapshot.get("job_id"), '
                    '**snapshot["campaign"]})\n'
                    '            st.session_state.campaign_build_selected_run = snapshot["run_id"]\n'
                    '        render_campaign_workspace(api, options, draft, job_id=snapshot.get("job_id"), job=search, '
                    'continuous=True)\n'
                    '    else:\n'
                    '        _progress(snapshot, st.session_state.get("campaign_build_request") or {}, '
                    'preparation_approval_required=requires_approval)\n'
                    '        if snapshot.get("status") == "complete":\n'
                    '            st.info("No accounts passed your filters. No contact sourcing or campaign research '
                    'was needed.")\n'
                    '        elif snapshot.get("error"):\n'
                    '            st.error(public_service_message(snapshot["error"]))\n'
                    '    _account_download(api, snapshot)\n'
                    '    if snapshot.get("status") in {"failed", "cancelled", "interrupted", "partial"}:\n'
                    '        if st.button("Continue unfinished build", key=f"build_retry_{build_id}"):\n'
                    '            result = _read(api, "POST", f"/campaign-builds/{build_id}/retry", json={}, '
                    'error_state="campaign_build_retry_error")\n'
                    '            if result:\n'
                    '                st.session_state.campaign_build_id = result.get("id", build_id)\n'
                    '                st.query_params["build"] = st.session_state.campaign_build_id\n'
                    '                st.session_state.campaign_build_snapshot = result\n'
                    '                st.session_state.pop("campaign_run_snapshot", None)\n'
                    '                st.rerun()\n'
                    '        error = st.session_state.get("campaign_build_retry_error") or {}\n'
                    '        if error:\n'
                    '            st.error(public_service_message(error.get("message")))\n'
                    '    with st.expander("Start another campaign", expanded=False):\n'
                    '        st.caption("Your current results stay available in saved campaigns.")\n'
                    '        if st.button("Return to filters", key="build_new_filters"):\n'
                    '            st.query_params.pop("build", None)\n'
                    '            for key in ("campaign_build_id", "campaign_build_snapshot", '
                    '"campaign_build_submission", "campaign_build_selected_run",\n'
                    '                        "campaign_run_id", "campaign_run_snapshot", "job_id", '
                    '"job_progress_snapshot"):\n'
                    '                st.session_state.pop(key, None)\n'
                    '            st.session_state.step = 1\n'
                    '            st.rerun()\n'}

import importlib.abc as _abc
import importlib.util as _util
import linecache as _linecache
import sys as _sys

class _FrontendBundle(_abc.MetaPathFinder, _abc.Loader):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "frontend" or fullname in _FRONTEND_SOURCES:
            return _util.spec_from_loader(fullname, self, is_package=fullname == "frontend")
        return None

    def create_module(self, spec):
        return None

    def exec_module(self, module):
        if module.__name__ == "frontend":
            module.__path__ = []
            return
        source = _FRONTEND_SOURCES[module.__name__]
        filename = "<bundled " + module.__name__ + ">"
        module.__file__ = filename
        _linecache.cache[filename] = (len(source), None, source.splitlines(True), filename)
        exec(compile(source, filename, "exec"), module.__dict__)

if getattr(_sys, "_intent_frontend_bundle", None) != _BUNDLE_VERSION:
    for _name in list(_sys.modules):
        if _name == "frontend" or _name.startswith("frontend."):
            del _sys.modules[_name]
    _sys.meta_path[:] = [f for f in _sys.meta_path if not getattr(f, "_intent_bundle", False)]
    _finder = _FrontendBundle()
    _finder._intent_bundle = True
    _sys.meta_path.insert(0, _finder)
    _sys._intent_frontend_bundle = _BUNDLE_VERSION

import hashlib
import json
import os
import time
from copy import deepcopy

import pandas as pd
import requests
import streamlit as st
from frontend.presentation import INTERNAL_REPORT_FIELDS
from frontend import transport
from frontend.access import require_access, require_session

try:
    from frontend.state import migrate_draft, regional_countries, search_payload, update_country_overrides
    from frontend.progress import STAGE_LABELS, TERMINAL, display_count, duration, journey_rows, progress_view
    from frontend.campaigns import (public_service_message, customer_context_enabled, customer_website_valid, render_customer_context,
                                    render_customer_progress, render_campaign_workspace, start_customer_research)
except ModuleNotFoundError:
    from state import migrate_draft, regional_countries, search_payload, update_country_overrides
    from progress import STAGE_LABELS, TERMINAL, display_count, duration, journey_rows, progress_view
    from campaigns import (public_service_message, customer_context_enabled, customer_website_valid, render_customer_context,
                           render_customer_progress, render_campaign_workspace, start_customer_research)

# Customer research is started by forward navigation, never by status rendering.
INTERNAL_REPORT_COLUMNS = list(INTERNAL_REPORT_FIELDS)
st.set_page_config(page_title="Intent to Outreach", page_icon="◉", layout="wide")
require_access()
st.markdown("""<style>
.block-container {max-width:1280px;padding-top:3.75rem;padding-bottom:1.5rem;}
[data-testid="stVerticalBlock"] {gap:.65rem;}
[data-testid="stMultiSelectTagsContainer"] {max-height:7rem;overflow-y:auto;}
[data-testid="stMetric"] {background:#f3f6fa;border-radius:10px;padding:12px;}
[data-testid="stHeadingWithActionElements"] h3 {padding-top:.1rem;padding-bottom:.2rem;}
hr {margin:.4rem 0;}
div.stButton > button[kind="primary"] {background:#174e67;border:0;}
</style>""", unsafe_allow_html=True)


def api(method, path, **kwargs):
    require_session()
    error_state = kwargs.pop("error_state", None)

    def show_error(message, status=None):
        message = public_service_message(message)
        if error_state:
            st.session_state[error_state] = {"message": message, "status": status}
        else:
            st.error(message)

    try:
        response = transport.request(method, path, timeout=kwargs.pop("timeout", 20), **kwargs)
        if not response.ok:
            try:
                detail = response.json().get("detail", "The request failed.")
            except ValueError:
                detail = "The request failed."
            show_error(detail if isinstance(detail, str) else "Check the selected filters and try again.", getattr(response, "status_code", None))
            return None
        if error_state:
            st.session_state.pop(error_state, None)
        return response
    except requests.RequestException:
        show_error("The app is temporarily unavailable. Please try again shortly.")
        return None


def control_job(job_id, action):
    api("POST", f"/jobs/{job_id}/{action}", error_state="job_control_error")


def refresh_job_status():
    st.session_state.pop("job_control_error", None)


def render_progress(job, job_id):
    view = progress_view(job, now=st.session_state.get("job_terminal_seen_at", time.time()),
                         observed_at=st.session_state.get("job_observed_at"), request=st.session_state.get("job_request") or st.session_state.get("draft"))
    title, elapsed, actions = st.columns([3, 1, 1])
    title.markdown(f"**{view['stage_label']}**")
    elapsed.caption(f"{view['elapsed_label']} {duration(view['elapsed_seconds'])}")
    if view["stage_elapsed_seconds"] is not None and job["status"] not in TERMINAL:
        title.caption(f"This step: {duration(view['stage_elapsed_seconds'])}")
    elif job["status"] not in TERMINAL:
        title.caption("Progress updates automatically as each step finishes.")
    if job["status"] not in TERMINAL or job.get("cancellation_pending_requests"):
        from frontend.controls import cancel_control
        cancel_control(api, f"/jobs/{job_id}/cancel", f"search_{job_id}", label="Cancel search", noun="this search",
                       cancelling=job.get("status") == "cancelling" or bool(job.get("cancellation_pending_requests")))
    if job["status"] == "awaiting_revenue_confirmation":
        pending = job["revenue_pending"]
        st.warning(f"Revenue research covers {pending['uncached_domains']:,} companies, estimated at {pending['estimated_minutes']} minutes. Research charges apply; timing and cost vary.")
        st.button("Continue revenue research", type="primary", on_click=control_job, args=(job_id, "confirm-revenue"))
    if job["status"] not in TERMINAL:
        control_error = st.session_state.get("job_control_error")
        if control_error:
            st.error(public_service_message(control_error["message"]))
            st.caption("The action did not complete. Retry it or refresh the search status to resume tracking.")
        if control_error or st.session_state.get("job_status_error"):
            st.button("Refresh search status", on_click=refresh_job_status)
    progress_message = public_service_message(job.get("message", "Search in progress"))
    if view["stage"] == "exclusions":
        progress_message = view["stage_label"]
    if (view["stage"] == "revenue" and view["revenue"]) or job["status"] in TERMINAL or progress_message == view["stage_label"]:
        progress_message = None
    st.progress(min(1.0, max(0.0, job.get("progress", 0))), text=progress_message)
    for column, key, label in zip(st.columns(3), ("accounts", "topic_rows", "metro_rows"),
                                  ("Accounts after filters", "Account–topic rows", "Metro observations")):
        column.metric(label, display_count(view["current"][key]))
        column.caption(view["sources"][key])
    baseline = next((item for item in view["checkpoints"] if item["id"] == "preview"), None)
    if baseline:
        st.caption(f"Started with {display_count(baseline['counts']['accounts'])} accounts and "
                   f"{display_count(baseline['counts']['topic_rows'])} topic rows matching your topics and company score range.")
    reporting_week = (job.get("counts") or {}).get("week")
    if reporting_week:
        st.caption(f"Reporting week: {reporting_week}")
    revenue = view["revenue"]
    if revenue:
        completed, total = revenue["completed"], revenue["total"]
        label = f"{display_count(completed)} / {display_count(total)} revenue checks completed"
        if completed is not None and total is not None and total > 0:
            st.progress(min(1.0, completed / total), text=label)
        else:
            st.write(label)
        st.caption(f"{display_count(revenue['cached'])} previously checked · {display_count(revenue['research_completed'])} newly checked"
                   " · completed checks may include Unknown revenue")
    rows = journey_rows(view)
    if len(rows) > 1:
        journey = st.expander("Filter journey", expanded=False, key=f"filter_journey_{job_id}", on_change="rerun")
        if journey.open:
            with journey:
                st.caption("— means this count is not available yet.")
                st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch", height=min(270, 35 * (len(rows) + 1) + 3))
                if view["exclusions"]:
                    st.caption("Excluded: " + " · ".join(view["exclusions"]))


widget_updates = set()


def set_widget_value(key, value):
    """Mark explicit updates so the widget does not receive a second default."""
    st.session_state[key] = deepcopy(value)
    widget_updates.add(key)


def widget_default(key, fallback):
    return None if key in widget_updates else st.session_state.get(key, fallback)


def submit_search(payload):
    payload = {**payload, "fill_revenue": True, "include_unknown_revenue": True}
    response = api("POST", "/search", json=payload)
    if response is None:
        return False
    st.session_state.job_id = response.json()["job_id"]
    st.session_state.job_request = deepcopy(payload)
    for key in ("download", "download_signature", "job_progress_id", "job_progress_snapshot", "job_progress_status",
                "job_observed_at", "job_terminal_seen_at", "job_status_error", "job_control_error"):
        st.session_state.pop(key, None)
    return True


def session_cache(name, ttl, fetch):
    cached = st.session_state.get(name)
    if cached and time.monotonic() < cached["expires"]:
        return deepcopy(cached["data"])
    value = fetch()
    st.session_state[name] = {"data": value, "expires": time.monotonic() + ttl}
    return deepcopy(value)


def fetch_json(path):
    response = transport.get(path, timeout=15)
    response.raise_for_status()
    return response.json()


def load_options():
    return session_cache("_options_cache", 60, lambda: fetch_json("/options"))


def load_topics():
    cached = st.session_state.get("topic_catalog_cache")
    if cached and time.monotonic() < cached["expires"]:
        return cached["data"]
    response = transport.get("/topics", timeout=15)
    response.raise_for_status()
    data = response.json()
    st.session_state.topic_catalog_cache = {"data": data, "expires": time.monotonic() + (300 if data["status"] == "ready" else 15)}
    return data


def clear_topics():
    st.session_state.pop("topic_catalog_cache", None)


def short_selection(values, empty, limit=3):
    if not values:
        return empty
    preview = ", ".join(str(value) for value in values[:limit])
    if len(preview) > 145:
        preview = preview[:142] + "…"
    return preview + (f" · +{len(values) - limit:,} more" if len(values) > limit else "")


def load_suppression_lists():
    return session_cache("_suppression_cache", 15, lambda: fetch_json("/suppression-lists")["lists"])


def upload_identity(upload):
    return hashlib.sha256(upload.name.encode() + upload.getvalue()).hexdigest()[:16]


def structured_settings(upload, prefix, fields):
    """Read actual content once and let the user choose a sheet and columns."""
    identity = upload_identity(upload)
    cache = st.session_state.setdefault("upload_inspections", {})
    selections = st.session_state.setdefault("upload_selections", {}).setdefault((prefix, identity), {"columns": {}})

    def inspect(sheet=None):
        key = (identity, sheet)
        if key not in cache:
            response = api("POST", "/imports/inspect", files={"file": (upload.name, upload.getvalue())},
                           data={"sheet": sheet} if sheet else {})
            if response is None:
                return None
            cache[key] = response.json()
        return cache[key]

    info = inspect()
    if info is None:
        return None
    sheets = info.get("sheets") or [info.get("sheet") or "CSV"]
    sheet_key = f"{prefix}_sheet_{identity}"
    saved_sheet = selections.get("sheet") if selections.get("sheet") in sheets else sheets[0]
    sheet = st.selectbox("Worksheet", sheets, index=sheets.index(st.session_state.get(sheet_key, saved_sheet)), key=sheet_key)
    selections["sheet"] = sheet
    if sheet != info.get("sheet") and sheet != "CSV":
        info = inspect(sheet)
        if info is None:
            return None
    columns = {column["index"]: column["label"] for column in info["columns"]}
    if not columns:
        st.warning("This sheet has no populated columns. Choose another sheet or file.")
        return None
    selected = {}
    remembered_columns = selections["columns"].setdefault(sheet, {})
    for field, label, optional in fields:
        choices = ([-1] if optional else []) + list(columns)
        default = remembered_columns.get(field, info.get("suggested_columns", {}).get(field))
        if default not in choices:
            default = -1 if optional else choices[0]
        column_key = f"{prefix}_{field}_{identity}_{sheet}"
        selected[field] = st.selectbox(label, choices, index=choices.index(st.session_state.get(column_key, default)),
                                      format_func=lambda value: "Unspecified" if value == -1 else f"{columns[value]} (column {value + 1})",
                                      key=column_key)
        remembered_columns[field] = selected[field]
    st.caption(f"{info.get('row_count', 0):,} populated rows detected.")
    return {"sheet": info.get("sheet") or sheet, **selected}


def show_invalid(entries):
    if entries:
        st.warning(f"{len(entries):,} invalid entries need correction. They will not be applied.")
        st.dataframe(pd.DataFrame(entries), width="stretch", hide_index=True)


def go(step):
    if step > max(2, st.session_state.step) and customer_context_enabled(options):
        if not draft.get("topics"):
            st.error("Select at least one topic to continue.")
            return
        if not customer_website_valid():
            st.error("Enter a valid customer website on Choose topics to continue.")
            return
        if st.session_state.step == 2 and not start_customer_research(api, options, draft):
            return
    st.session_state.step = step
    st.rerun()


first_visit = "step" not in st.session_state
if first_visit:
    st.session_state.step = 1
try:
    options = load_options()
except requests.RequestException:
    st.title("Intent to Outreach")
    st.error("The app is temporarily unavailable. Please try reconnecting shortly.")
    if st.button("Reconnect"):
        st.session_state.pop("_options_cache", None)
        st.rerun()
    st.stop()

if first_visit and (options.get("campaign_builds") or {}).get("enabled") and st.query_params.get("build"):
    st.session_state.step = 4

draft, migration_notices = migrate_draft(st.session_state.get("draft", {}), options)
st.session_state.draft = draft
st.session_state.pop("result_personas", None)
st.session_state.pop("personas", None)
st.session_state.pop("icp_fill_revenue", None)
st.session_state.pop("icp_include_unknown_revenue", None)
for key, value in st.session_state.pop("pending_widget_values", {}).items():
    set_widget_value(key, value)
tier_labels = {tier["id"]: tier["label"] for tier in options["revenue_tiers"]}
score_options = options["score_ranges"]

st.markdown("**Intent to Outreach** · Find accounts. Prepare outreach.")
step_names = ["Define ICP", "Choose topics", "Set geography", "Review & export"]
build_focus = st.session_state.step == 4 and (options.get("campaign_builds") or {}).get("enabled") and bool(
    st.session_state.get("campaign_build_id") or st.query_params.get("build"))
if not build_focus:
    for index, column in enumerate(st.columns(4), start=1):
        bold = "**" if st.session_state.step == index else ""
        column.markdown(f"{bold}{index:02d}  {step_names[index - 1]}{bold}")
    st.divider()
for notice in migration_notices:
    st.info(notice)
if st.session_state.get("notice"):
    st.success(st.session_state.pop("notice"))


if st.session_state.step == 1:
    st.subheader("Define your ideal customer")
    industry_column, left, right = st.columns(3)
    draft["industries"] = industry_column.multiselect("Industry", options["industries"], default=draft["industries"], key="icp_industries",
        on_change="ignore", wrap=True, help="Optional. Selecting a parent includes its sub-industries.")
    draft["sizes"] = left.multiselect("Company size · employees", options["size_bands"], default=draft["sizes"], key="icp_sizes", on_change="ignore", wrap=True)
    draft["revenue_tiers"] = right.multiselect("Estimated annual revenue · USD", list(tier_labels),
                                               default=draft["revenue_tiers"], key="icp_revenue_tiers", format_func=tier_labels.get, on_change="ignore", wrap=True,
                                               help="Revenue tiers are estimated automatically for public and private companies. Companies with unknown revenue stay included when filtering. Lower bounds are included; upper bounds are excluded.")
    with st.expander("Domain Suppression List", expanded=False):
        st.caption("Exclude domains and their subdomains.")
        lists_available = True
        try:
            saved_lists = load_suppression_lists()
        except requests.RequestException:
            saved_lists = []
            lists_available = False
            st.error("Saved suppression lists are unavailable. Refresh the lists before continuing.")
        saved_by_id = {item["id"]: item for item in saved_lists}
        known_names = st.session_state.setdefault("suppression_list_names", {})
        known_names.update({item["id"]: item["name"] for item in saved_lists})
        selected_lists = st.session_state.get("selected_suppression_lists", draft["suppression_list_ids"])
        list_choices = list(dict.fromkeys([*saved_by_id, *selected_lists]))
        draft["suppression_list_ids"] = st.multiselect("Saved suppression lists", list_choices, default=widget_default("selected_suppression_lists", selected_lists), key="selected_suppression_lists",
            format_func=lambda value: (f"{saved_by_id[value]['name']} ({len(saved_by_id[value]['domains']):,} domains)" if value in saved_by_id
                                       else f"Unavailable saved list: {known_names.get(value, value)}"))
        missing_lists = [value for value in draft["suppression_list_ids"] if value not in saved_by_id]
        if missing_lists:
            st.error("A selected suppression list is unavailable. Refresh the lists or remove that selection before continuing.")
        if st.button("Refresh saved lists"):
            st.session_state.pop("_suppression_cache", None)
            st.rerun()
        saved_domain_text = st.session_state.get("additional_domains_text", "\n".join(draft["suppressed_domains"]))
        if "additional_domains_text" not in st.session_state:
            st.session_state.applied_domain_signature = (saved_domain_text, None, "null")
        manual = st.text_area("Additional domains · comma or newline separated", value=saved_domain_text, key="additional_domains_text",
                              placeholder="example.com\nhttps://shop.example.org/customers", height=110)
        suppression_file = st.file_uploader("Upload domains", type=["txt", "csv", "xlsx"], key="suppression_upload")
        domain_settings = None
        if suppression_file and not suppression_file.name.lower().endswith(".txt"):
            domain_settings = structured_settings(suppression_file, "domains", [("domain", "Domain column", False)])
        domain_signature = (manual, upload_identity(suppression_file) if suppression_file else None,
                            json.dumps(domain_settings, sort_keys=True))
        domains_changed = domain_signature != st.session_state.get("applied_domain_signature")
        if st.button("Preview domains", disabled=bool(suppression_file and not suppression_file.name.lower().endswith(".txt") and not domain_settings)):
            if suppression_file:
                data = {"text": manual}
                if domain_settings:
                    data.update(sheet=domain_settings["sheet"], column=domain_settings["domain"])
                response = api("POST", "/imports/domains", files={"file": (suppression_file.name, suppression_file.getvalue())}, data=data)
            else:
                response = api("POST", "/imports/domains", json={"text": manual})
            if response is not None:
                st.session_state.domain_preview = response.json()
                st.session_state.domain_preview_signature = domain_signature
        if st.session_state.get("domain_preview_signature") == domain_signature:
            preview = st.session_state.domain_preview
            st.caption(f"{len(preview['domains']):,} unique valid domains. Excluding a subdomain does not exclude its parent domain.")
            if preview["domains"]:
                st.dataframe(pd.DataFrame({"Domain": preview["domains"]}), width="stretch", hide_index=True)
            show_invalid(preview.get("invalid", []))
            if st.button("Apply valid domains"):
                draft["suppressed_domains"] = preview["domains"]
                st.session_state.applied_domain_signature = domain_signature
                st.session_state.notice = f"Applied {len(preview['domains']):,} additional domain exclusions."
                st.rerun()
        if domains_changed:
            st.info("Preview and apply your domain changes before continuing. Invalid entries are never applied.")
        effective_domains = set(draft["suppressed_domains"])
        for list_id in draft["suppression_list_ids"]:
            if list_id in saved_by_id:
                effective_domains.update(saved_by_id[list_id]["domains"])
        st.caption(f"{len(effective_domains):,} unique excluded domains from selected lists and applied additional entries.")
        draft["exclude_edu"] = st.checkbox("Exclude .edu domains", value=draft["exclude_edu"], key="icp_exclude_edu", on_change="ignore",
                                           help="Excludes example.edu and its subdomains. Does not include .edu.au or .ac.uk.")
        with st.popover("Save or manage reusable suppression lists"):
            new_name = st.text_input("Name for a new suppression list")
            st.caption("Save the effective domains shown above, including selected lists and applied additional domains.")
            if st.button("Save new list", disabled=not new_name.strip() or not effective_domains or domains_changed or not lists_available or bool(missing_lists)):
                response = api("POST", "/suppression-lists", json={"name": new_name.strip(), "domains": sorted(effective_domains)})
                if response is not None:
                    st.session_state.pop("_suppression_cache", None)
                    st.session_state.notice = "Suppression list saved. Select it above to reuse it."
                    st.rerun()
            if saved_by_id:
                edit_id = st.selectbox("List to manage", list(saved_by_id), format_func=lambda value: saved_by_id[value]["name"])
                existing = saved_by_id[edit_id]
                version = hashlib.sha256(json.dumps(existing, sort_keys=True).encode()).hexdigest()[:10]
                edited_name = st.text_input("Saved list name", value=existing["name"], key=f"list_name_{version}")
                edited_domains = st.text_area("Saved list domains", value="\n".join(existing["domains"]), key=f"list_domains_{version}")
                update_column, delete_column = st.columns(2)
                if update_column.button("Validate & update saved list", disabled=not edited_name.strip()):
                    checked = api("POST", "/imports/domains", json={"text": edited_domains})
                    if checked is not None:
                        parsed = checked.json()
                        if parsed.get("invalid"):
                            show_invalid(parsed["invalid"])
                            st.error("Correct the invalid entries before updating this saved list.")
                        else:
                            response = api("PUT", f"/suppression-lists/{edit_id}", json={"name": edited_name.strip(), "domains": parsed["domains"]})
                            if response is not None:
                                st.session_state.pop("_suppression_cache", None)
                                st.session_state.notice = "Suppression list updated. Existing searches keep their original exclusions."
                                st.rerun()
                if delete_column.button("Delete saved list"):
                    response = api("DELETE", f"/suppression-lists/{edit_id}")
                    if response is not None:
                        draft["suppression_list_ids"] = [value for value in draft["suppression_list_ids"] if value != edit_id]
                        st.session_state.pending_widget_values = {"selected_suppression_lists": draft["suppression_list_ids"]}
                        st.session_state.pop("_suppression_cache", None)
                        st.session_state.notice = "Suppression list deleted. Existing searches keep their original exclusions."
                        st.rerun()
    if st.button("Continue to topics →", type="primary", disabled=domains_changed or not lists_available or bool(missing_lists)):
        go(2)

elif st.session_state.step == 2:
    st.subheader("Choose intent topics")
    try:
        catalog = load_topics()
    except requests.RequestException:
        st.error("The topic catalog is temporarily unavailable.")
        st.stop()
    if catalog["status"] != "ready":
        st.info("More topics are loading. You can use available topics now.")
    topic_column, score_column = st.columns([3, 2])
    all_topics = sorted(set(catalog["topics"]) | set(st.session_state.get("topic_selection", draft["topics"])))
    selected = topic_column.multiselect("Search topics", all_topics, default=widget_default("topic_selection", draft["topics"]), key="topic_selection",
                             on_change="ignore", wrap=True, filter_mode="contains")
    draft["topics"] = selected
    score_range = score_column.slider("Company/topic score", min_value=score_options["min"], max_value=score_options["max"],
                            value=(draft["company_score_min"], draft["company_score_max"]), key="company_score_range", step=1, on_change="ignore",
                            help="Minimum and maximum are included. Lowering the minimum only includes scores present in the source report.")
    draft["company_score_min"], draft["company_score_max"] = score_range
    catalog_column, refresh_column = st.columns([4, 1])
    catalog_column.caption(f"{len(catalog['topics']):,} available topics. Search by name, or import a list below.")
    if refresh_column.button("Refresh topic catalog"):
        clear_topics()
        st.rerun()
    render_customer_context(api, options, draft)
    with st.expander("Import customer topic mapping", expanded=False):
        st.caption("Map Intent Topic → Offering → Sub-offering. Applying a customer file replaces the previous mapping and selected topics.")
        mapping_file = st.file_uploader("Customer topic mapping", type=["csv", "xlsx"], key="mapping_upload")
        if mapping_file:
            settings = structured_settings(mapping_file, "mapping", [("topic", "Intent topic column", False),
                                            ("offering", "Offering column", False), ("sub_offering", "Sub-offering column", True)])
            if settings:
                signature = (upload_identity(mapping_file), json.dumps(settings, sort_keys=True))

                def parse_mapping(resolutions=None):
                    data = {"sheet": settings["sheet"], "topic_column": settings["topic"], "offering_column": settings["offering"]}
                    # -1 explicitly disables this column; omission means auto-detect.
                    data["sub_offering_column"] = settings["sub_offering"]
                    if resolutions:
                        data["resolutions"] = json.dumps(resolutions)
                    response = api("POST", "/imports/topic-mapping", files={"file": (mapping_file.name, mapping_file.getvalue())}, data=data)
                    if response is not None:
                        st.session_state.mapping_preview = response.json()
                        st.session_state.mapping_preview_signature = signature
                        st.session_state.mapping_preview_resolutions = dict(resolutions or {})
                        return True
                    return False

                if st.button("Preview topic mapping"):
                    parse_mapping()
                if st.session_state.get("mapping_preview_signature") == signature:
                    preview = st.session_state.mapping_preview
                    st.caption(f"{len(preview['mappings']):,} relationships across {len(preview['matched_topics']):,} matched topics.")
                    if preview["mappings"]:
                        frame = pd.DataFrame(preview["mappings"]).rename(columns={"topic": "Intent Topic", "offering": "Offering", "sub_offering": "Sub-offering"})
                        frame["Sub-offering"] = frame["Sub-offering"].fillna("").replace("", "Unspecified")
                        st.dataframe(frame, width="stretch", hide_index=True)
                    show_invalid(preview.get("invalid", []))
                    unresolved = {entry["input"]: entry for entry in preview.get("unmatched", [])}
                    checked_resolutions = dict(st.session_state.get("mapping_preview_resolutions", {}))
                    resolutions = dict(checked_resolutions)
                    if unresolved:
                        st.warning(f"{len(unresolved):,} topic names need review. Unresolved relationships will not be applied.")
                    for raw_topic, entry in unresolved.items():
                        match = st.selectbox(f"Match topic: {raw_topic}", [""] + entry.get("suggestions", []),
                                             format_func=lambda value: value or "Leave unresolved",
                                             key="mapping_match_" + hashlib.sha256(repr((signature, raw_topic)).encode()).hexdigest()[:16])
                        if match:
                            resolutions[raw_topic] = match
                        else:
                            resolutions.pop(raw_topic, None)
                    review_pending = resolutions != checked_resolutions
                    if review_pending:
                        st.info("Recheck selected topic matches to update the preview before applying your mapping.")
                    if unresolved and st.button("Recheck selected topic matches"):
                        if parse_mapping(resolutions):
                            st.rerun()
                    if st.button("Apply reviewed mappings", disabled=not preview["mappings"] or review_pending):
                        draft["topic_mappings"] = preview["mappings"]
                        draft["topics"] = preview["matched_topics"]
                        st.session_state.pending_widget_values = {"topic_selection": preview["matched_topics"]}
                        st.session_state.topic_unmatched = []
                        st.session_state.notice = f"Applied {len(preview['mappings']):,} mappings. Matched topics are selected below."
                        st.rerun()
        if draft["topic_mappings"]:
            st.caption(f"{len(draft['topic_mappings']):,} topic-to-offering relationships applied. Changes affect future searches; existing reports stay the same.")
            if st.button("Clear customer mapping"):
                draft["topic_mappings"] = []
                st.rerun()
    with st.expander("Paste or upload a topic list", expanded=False):
        text = st.text_area("Paste topics separated by commas or newlines", height=100)
        upload = st.file_uploader("Or upload a topic list", type=["xlsx", "csv"], help="Put only your topic names on the first sheet; all populated cells are included.")
        if st.button("Match & select topics", disabled=not (text.strip() or upload)):
            response = (api("POST", "/topics/match", files={"file": (upload.name, upload.getvalue())}) if upload else
                        api("POST", "/topics/match", json={"text": text}))
            if response is not None:
                matched = response.json()
                st.session_state.pending_widget_values = {"topic_selection": sorted(set(st.session_state.get("topic_selection", draft["topics"]) + matched["matched"]))}
                st.session_state.topic_unmatched = matched["unmatched"]
                st.session_state.notice = f"Selected {len(matched['matched']):,} matching topics."
                st.rerun()
        for entry in st.session_state.get("topic_unmatched", []):
            st.warning(f"Unmatched: {entry['input']}")
            if entry["suggestions"]:
                suggestion = st.selectbox("Suggested match", [""] + entry["suggestions"], format_func=lambda value: value or "Choose a topic…",
                                          key="suggest_" + entry["input"])
                if suggestion and st.button("Add suggestion", key="add_" + entry["input"]):
                    st.session_state.pending_widget_values = {"topic_selection": sorted(set(st.session_state.get("topic_selection", draft["topics"]) + [suggestion]))}
                    st.session_state.topic_unmatched = [value for value in st.session_state.topic_unmatched if value["input"] != entry["input"]]
                    st.rerun()
    topic_preview = st.expander("Selected topics and offerings", expanded=False, key="selected_topic_preview", on_change="rerun")
    if topic_preview.open:
        with topic_preview:
            mapped_topics = {mapping["topic"] for mapping in draft["topic_mappings"]}
            unmapped = [topic for topic in selected if topic not in mapped_topics]
            st.caption(f"{len(selected):,} selected · {len(unmapped):,} Unmapped topics")
            mappings = [dict(mapping, sub_offering=mapping.get("sub_offering") or "Unspecified") for mapping in draft["topic_mappings"] if mapping["topic"] in selected]
            mappings.extend({"topic": topic, "offering": "Unmapped", "sub_offering": "Unspecified"} for topic in unmapped)
            if mappings:
                st.dataframe(pd.DataFrame(mappings[:200]).rename(columns={"topic": "Intent Topic", "offering": "Offering", "sub_offering": "Sub-offering"}), width="stretch", hide_index=True, height=260)
                if len(mappings) > 200:
                    st.caption("Showing the first 200 relationships. All relationships are kept for the report.")
            else:
                st.caption("Select topics above to review their mappings.")
    left, right = st.columns([1, 3])
    if left.button("← ICP"):
        go(1)
    if right.button("Continue to geography →", type="primary"):
        if selected:
            go(3)
        else:
            st.error("Select at least one topic to continue.")

elif st.session_state.step == 3:
    st.subheader("Where is intent surging?")
    st.caption("Choose regions or individual countries. Leave blank for all surge locations.")
    render_customer_progress(api, options, draft)
    st.session_state.regions_saved = [region for region in st.session_state.get("regions_saved", []) if region in options["regions"]]
    if "geo_regions" in st.session_state:
        valid_regions = [region for region in st.session_state.geo_regions if region in options["regions"]]
        if valid_regions != st.session_state.geo_regions:
            set_widget_value("geo_regions", valid_regions)
    base = set(regional_countries(options["regions"], st.session_state.regions_saved))
    if "geo_manual_additions" not in st.session_state:
        current_countries = set(draft["countries"])
        st.session_state.geo_manual_additions = sorted(current_countries - base)
        st.session_state.geo_manual_removals = sorted(base - current_countries)

    # Country edits and a region change can arrive in the same browser request.
    # Capture the latest value of the existing widget before replacing its key.
    previous_country_key = f"geo_countries_{st.session_state.get('geo_country_revision', 0)}"
    incoming_countries = st.session_state.get(previous_country_key, draft["countries"])
    additions, removals = update_country_overrides(
        st.session_state.get("geo_previous_countries", incoming_countries), incoming_countries,
        st.session_state.geo_manual_additions, st.session_state.geo_manual_removals)
    st.session_state.geo_manual_additions = additions
    st.session_state.geo_manual_removals = removals

    region_column, metro_column = st.columns([3, 2])
    selected_regions = region_column.pills("Regions", list(options["regions"]), selection_mode="multi",
                                          default=widget_default("geo_regions", st.session_state.regions_saved), key="geo_regions")
    regions_changed = selected_regions != st.session_state.regions_saved
    if regions_changed:
        draft["countries"] = regional_countries(options["regions"], selected_regions,
                                               st.session_state.geo_manual_additions, st.session_state.geo_manual_removals)
        st.session_state.regions_saved = list(selected_regions)
        # A fresh widget identity prevents an old browser value from overwriting
        # the new union. Manual overrides stay in their own persistent fields.
        st.session_state.geo_country_revision = st.session_state.get("geo_country_revision", 0) + 1
    score_range = metro_column.slider("Metro Composite Score", min_value=score_options["min"], max_value=score_options["max"],
                            value=(draft["metro_score_min"], draft["metro_score_max"]), key="metro_score_range", step=1, on_change="ignore",
                            help="Minimum and maximum are included. Locations without a valid score are excluded, even at 0–100.")
    draft["metro_score_min"], draft["metro_score_max"] = score_range
    country_editor = st.expander("Edit countries", expanded=False, key="country_editor", on_change="rerun")
    with country_editor:
        with st.container(height=190, border=False):
            country_key = f"geo_countries_{st.session_state.get('geo_country_revision', 0)}"
            countries = st.multiselect("Countries · edit the regional selection", options["countries"], default=draft["countries"], key=country_key, wrap=True, on_change="ignore")
            if not regions_changed:
                additions, removals = update_country_overrides(st.session_state.get("geo_previous_countries", countries), countries,
                                                               st.session_state.geo_manual_additions, st.session_state.geo_manual_removals)
                st.session_state.geo_manual_additions = additions
                st.session_state.geo_manual_removals = removals
            st.session_state.geo_previous_countries = list(countries)
            draft["countries"] = countries
            st.caption("Manual country additions and removals are kept when regions change.")
        if st.button("Reset countries to selected regions", help="Clear manual additions and removals, then select every country in the chosen regions."):
            reset_countries = regional_countries(options["regions"], selected_regions)
            st.session_state.geo_manual_additions = []
            st.session_state.geo_manual_removals = []
            st.session_state.geo_previous_countries = list(reset_countries)
            draft["countries"] = reset_countries
            st.session_state.geo_country_revision = st.session_state.get("geo_country_revision", 0) + 1
            st.rerun()
    if not country_editor.open:
        st.caption(f"{len(countries):,} countries selected" if countries else "All surge locations")
    left, right = st.columns([1, 3])
    if left.button("← Topics"):
        go(2)
    if right.button("Review search →", type="primary"):
        go(4)

else:
    st.subheader("Your campaign" if build_focus else "Review & export")
    from frontend.builds import enabled as continuous_build_enabled, render_build_action, render_build_workspace
    continuous_build = continuous_build_enabled(options)
    shared_build = str(st.query_params.get("build", ""))
    if continuous_build and not st.session_state.get("campaign_build_id") and shared_build and all(
            char.isalnum() or char in "_-" for char in shared_build):
        st.session_state.campaign_build_id = shared_build
    if continuous_build and st.session_state.get("campaign_build_id"):
        render_build_workspace(api, options, draft)
        st.stop()
    campaign_focus = bool(st.session_state.get("campaign_run_id"))
    if campaign_focus:
        render_campaign_workspace(api, options, draft, job_id=st.session_state.get("job_id"),
                                  job=st.session_state.get("job_progress_snapshot"))
        brief_record = st.session_state.get("campaign_brief_record") or {}
        brief_needs_attention = brief_record.get("status") not in {"complete", "approved"} or bool(
            st.session_state.get("campaign_brief_request_error") or st.session_state.get("campaign_brief_status_error"))
        brief_panel = st.expander("Product brief", expanded=brief_needs_attention,
                                  key=f"review_brief_{st.session_state.campaign_run_id}_{brief_needs_attention}", on_change="rerun")
        if brief_panel.open:
            with brief_panel:
                render_customer_progress(api, options, draft)
    else:
        render_customer_progress(api, options, draft)
    with st.expander("Your search", expanded=not st.session_state.get("job_id") and not campaign_focus):
        left, right = st.columns(2)
        left.write("**Topics:** " + short_selection(draft["topics"], "None selected"))
        left.write("**Industry:** " + short_selection(draft["industries"], "All industries"))
        left.write("**Size:** " + short_selection(draft["sizes"], "All company sizes"))
        revenue_description = short_selection([tier_labels[tier] for tier in draft["revenue_tiers"]], "All revenue tiers · estimates included")
        left.write("**Revenue:** " + revenue_description.replace("$", r"\$"))
        right.write(f"**Scores:** company/topic {draft['company_score_min']}–{draft['company_score_max']} · metro {draft['metro_score_min']}–{draft['metro_score_max']}")
        geography = f"{len(draft['countries']):,} countries · " + short_selection(draft["countries"], "All countries", limit=2) if draft["countries"] else "All countries"
        right.write("**Surge geography:** " + geography)
        right.write(f"**Exclusions:** {len(draft['suppression_list_ids']):,} saved lists + {len(draft['suppressed_domains']):,} domains · .edu {'excluded' if draft['exclude_edu'] else 'included'}")
        unmapped_count = len(set(draft["topics"]) - {mapping["topic"] for mapping in draft["topic_mappings"]})
        right.write(f"**Mapping:** {len(draft['topic_mappings']):,} relationships · {unmapped_count:,} Unmapped topics")
    details = st.expander("All search details", expanded=False, key="search_details", on_change="rerun")
    if details.open:
        with details:
            selections = [("Topic", value) for value in draft["topics"]]
            selections += [("Industry", value) for value in draft["industries"]]
            selections += [("Employee category", value) for value in draft["sizes"]]
            selections += [("Revenue tier", tier_labels[value]) for value in draft["revenue_tiers"]]
            selections += [("Country", value) for value in draft["countries"]]
            if selections:
                st.dataframe(pd.DataFrame(selections, columns=["Filter", "Selection"]), hide_index=True, width="stretch", height=280)
            st.caption(f"Company/topic score {draft['company_score_min']}–{draft['company_score_max']}; metro score {draft['metro_score_min']}–{draft['metro_score_max']}. Endpoints included.")
    if not st.session_state.get("job_id"):
        if not campaign_focus and not continuous_build:
            render_campaign_workspace(api, options, draft)
        left, right = st.columns([1, 3])
        if left.button("← Geography"):
            go(3)
        if continuous_build and not campaign_focus:
            render_build_action(api, options, draft)
        elif not continuous_build and right.button("Find accounts", type="primary", disabled=not draft["topics"] or
                                                   (customer_context_enabled(options) and not customer_website_valid())):
            if submit_search(search_payload(draft)):
                st.rerun()
        st.stop()
    job_id = st.session_state.job_id
    if st.session_state.get("job_progress_id") != job_id:
        for key in ("job_progress_snapshot", "job_progress_status", "job_terminal_seen_at", "job_status_error", "job_control_error"):
            st.session_state.pop(key, None)
        st.session_state.job_progress_id = job_id
        st.session_state.job_observed_at = time.time()
    polling = st.session_state.get("job_progress_status") not in TERMINAL or bool(
        (st.session_state.get("job_progress_snapshot") or {}).get("cancellation_pending_requests"))

    @st.fragment(run_every=2 if polling else None)
    def search_status():
        require_session()
        if st.session_state.get("job_id") != job_id:
            return
        saved = st.session_state.get("job_progress_snapshot")
        if polling or saved is None:
            response = api("GET", f"/jobs/{job_id}", error_state="job_status_error")
            if response is None:
                failure = st.session_state.job_status_error
                if failure.get("status") == 404 or saved is None:
                    st.error(public_service_message(failure["message"]))
                    st.caption("Your filters are kept. Return to review before deciding whether to submit another search.")
                    if st.button("Return to search review"):
                        for key in ("job_id", "job_request", "download", "download_signature"):
                            st.session_state.pop(key, None)
                        go(4)
                    return
                st.warning("Live status could not refresh. Showing the last confirmed update.")
                st.caption(public_service_message(failure["message"]))
                job = saved
            else:
                job = response.json()
                st.session_state.job_progress_snapshot = job
                st.session_state.job_progress_status = job["status"]
                if polling and job["status"] in TERMINAL and not job.get("cancellation_pending_requests"):
                    st.session_state.job_terminal_seen_at = time.time()
                    st.rerun()
        else:
            job = saved
        if campaign_focus and job["status"] == "complete":
            account_count = (job.get("result_counts") or {}).get("accounts")
            label = "Account results" + (f" · {account_count:,} accounts" if account_count is not None else "")
            account_panel = st.expander(label, expanded=False, key=f"account_results_{job_id}", on_change="rerun")
            if not account_panel.open:
                return
        else:
            account_panel = st.container()
        with account_panel:
            counts, early = job.get("result_counts") or {}, job.get("counts") or {}
            render_progress(job, job_id)
            for warning in job.get("warnings", []):
                st.warning(public_service_message(warning))
            if job["status"] not in TERMINAL:
                return
            if job["status"] == "complete":
                summary_tab, details_tab = st.tabs(["Account Summary", "Detailed Results"])
                with summary_tab:
                    if job.get("summary_preview"):
                        st.dataframe(pd.DataFrame(job["summary_preview"]).drop(columns=INTERNAL_REPORT_COLUMNS, errors="ignore"), width="stretch", hide_index=True)
                        st.caption("First 200 account summaries. Each topic has equal weight in Average Topic Metro Score.")
                    elif not job.get("preview"):
                        st.info("No accounts match these filters. You can still download the empty four-sheet report.")
                with details_tab:
                    if job.get("preview"):
                        st.dataframe(pd.DataFrame(job["preview"]).drop(columns=INTERNAL_REPORT_COLUMNS, errors="ignore"), width="stretch", hide_index=True)
                        st.caption("First 200 detailed rows. The Excel download contains all matching observations.")
                    else:
                        st.info("No detailed observations match these filters.")
                st.caption(f"{job.get('unmapped_topic_count', counts.get('unmapped_topics', early.get('unmapped_topics', 0))):,} Unmapped topics in this report. NEW means not reported last week; unavailable comparisons have blank scores and deltas.")
                fmt = job.get("formatter", {})
                st.write(f"Excel: **{fmt.get('total', 0):,} detailed rows** · **4 sheets**: Detailed Results, Topic Mapping, Raw Data, Account Summary")
                if st.session_state.get("download_signature") != job_id:
                    with st.spinner("Preparing download…"):
                        download = api("GET", f"/jobs/{job_id}/excel", timeout=600)
                    if download is not None:
                        st.session_state.download = download.content
                        st.session_state.download_signature = job_id
                if st.session_state.get("download_signature") == job_id:
                    st.download_button("Download account report", st.session_state.download,
                                       file_name="intent_to_outreach_accounts.xlsx",
                                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", on_click="ignore",
                                       help="Account results only. Build the outreach package below for contacts and email sequences.")
                st.caption("Download your report to keep a copy. Report downloads are temporary and may expire after one hour.")
            elif job["status"] == "failed":
                st.error(public_service_message(job["message"]))
                if st.button("Retry search", type="primary"):
                    if submit_search(st.session_state.get("job_request") or search_payload(draft)):
                        st.rerun()
            else:
                st.info("Search cancelled.")
            timings = [{"Step": STAGE_LABELS[key], "Time": duration(seconds)}
                       for key, seconds in job.get("timings", {}).items() if key in STAGE_LABELS]
            if timings:
                with st.expander("Time by step"):
                    st.dataframe(pd.DataFrame(timings), hide_index=True, width="stretch")
            if not campaign_focus and st.button("Edit filters & start a new search"):
                for key in ("job_id", "job_request", "download", "download_signature"):
                    st.session_state.pop(key, None)
                go(1)

    search_status()
    if not campaign_focus:
        render_campaign_workspace(api, options, draft, job_id=job_id,
                                  job=st.session_state.get("job_progress_snapshot"))
    elif st.button("Start a new search", key="campaign_new_search"):
        for key in ("job_id", "job_request", "download", "download_signature"):
            st.session_state.pop(key, None)
        go(1)
