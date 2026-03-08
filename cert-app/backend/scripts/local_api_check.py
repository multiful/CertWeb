"""
로컬 API 전부 호출해서 200/정상 응답인지 확인.
실행: cert-app/backend 에서 uv run python scripts/local_api_check.py [--base http://127.0.0.1:8001]
"""
import argparse
import json
import sys
from urllib.parse import urlencode, quote

try:
    import urllib.request
    import urllib.error
except ImportError:
    pass

BASE = "http://127.0.0.1:8001"


def request(method: str, url: str, timeout: int = 60) -> tuple[int, bytes, str | None]:
    try:
        req = urllib.request.Request(url, method=method)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read(), None
    except urllib.error.HTTPError as e:
        return e.code, getattr(e, "read", lambda: b"")() or b"", str(e)
    except Exception as e:
        return -1, b"", str(e)


def main():
    global BASE
    p = argparse.ArgumentParser()
    p.add_argument("--base", default=BASE, help="Base URL e.g. http://127.0.0.1:8001")
    args = p.parse_args()
    BASE = args.base.rstrip("/")

    prefix = f"{BASE}/api/v1"
    ok = 0
    fail = 0
    # 한글 등 비ASCII는 quote로 인코딩
    major_q = quote("컴퓨터", safe="")
    cases = [
        ("GET", f"{BASE}/health", "health"),
        ("GET", f"{BASE}/", "root"),
        ("GET", f"{prefix}/certs?page=1&page_size=5&sort=name&sort_desc=true", "certs list"),
        ("GET", f"{prefix}/certs/filter-options", "certs filter-options"),
        ("GET", f"{prefix}/certs/trending/now?limit=5", "certs trending/now"),
        ("GET", f"{prefix}/recommendations/majors", "recommendations/majors"),
        ("GET", f"{prefix}/recommendations?major={major_q}&limit=5", "recommendations by major"),
        ("GET", f"{prefix}/recommendations/ai/hybrid-recommendation?major={major_q}&limit=5", "hybrid-recommendation"),
        ("GET", f"{prefix}/majors", "majors list"),
        ("GET", f"{prefix}/certs/1", "certs detail (qual_id=1)"),
        ("GET", f"{prefix}/certs/1/stats", "certs stats (qual_id=1)"),
    ]

    for method, url, name in cases:
        code, body, err = request(method, url)
        if code == 200:
            ok += 1
            try:
                j = json.loads(body.decode("utf-8"))
                if name == "hybrid-recommendation":
                    print(f"  OK  {name} (results={len(j.get('results', []))} items)")
                elif name == "certs list":
                    items = j.get("items") or j.get("data") or []
                    print(f"  OK  {name} (items={len(items)})")
                else:
                    print(f"  OK  {name}")
            except Exception:
                print(f"  OK  {name} (body len={len(body)})")
        elif code == 404 and ("certs detail" in name or "certs stats" in name):
            ok += 1
            print(f"  OK  {name} (404 no data)")
        else:
            fail += 1
            print(f"  FAIL {name} -> {code} {err or body[:200]!r}")

    # 인증 필요한 경로는 401 예상
    query_q = quote("정보처리", safe="")
    auth_cases = [
        (f"{prefix}/recommendations/ai/semantic-search?query={query_q}&limit=5", "semantic-search (expect 401)"),
    ]
    for url, name in auth_cases:
        code, _, _ = request("GET", url)
        if code in (200, 401):
            ok += 1
            print(f"  OK  {name} -> {code}")
        else:
            fail += 1
            print(f"  FAIL {name} -> {code}")

    print()
    print(f"Result: {ok} passed, {fail} failed")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
