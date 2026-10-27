#!/usr/bin/env python3
"""링크 모음(shop/products.json) 점검 스크립트.

글을 올리기 전에 실행해서, 글에 적은 상품번호가 링크 모음에 먼저 등록돼 있고
번호와 상품이 맞는지 확인한다. 외부 패키지 없이 파이썬 3만 있으면 된다.

  # 데이터 전체 점검 (중복 번호, 빈 링크, 쿠팡 파트너스 고지 문구 등)
  python3 scripts/check_products.py

  # 올릴 번호 확인 (번호만, 또는 번호=상품명)
  python3 scripts/check_products.py --require 139
  python3 scripts/check_products.py --require "139=냉동 볶음밥"

  # 글 본문에서 번호(No.139, 139번)를 뽑아 확인
  python3 scripts/check_products.py --post post.txt
  echo "No.139 냉동 볶음밥" | python3 scripts/check_products.py --post -

  # 실제 배포된 페이지 데이터로 확인 (push 후 반영됐는지)
  python3 scripts/check_products.py --source https://raw.githubusercontent.com/lxxhwa/threads-images/main/shop/products.json --require 139

문제가 있으면 이유를 출력하고 종료 코드 1로 끝난다.
"""
import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PRODUCTS = ROOT / "shop" / "products.json"
PAGE = ROOT / "shop" / "index.html"
REPO_RAW = "https://raw.githubusercontent.com/lxxhwa/threads-images/main/"
DISCLOSURE = "이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다."
LINK_RE = re.compile(r"^https://link\.coupang\.com/\S+$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# 글 본문 속 번호 표기: "No.139", "No 139", "139번"
POST_NO_RE = re.compile(r"(?i)\bno\.?\s*(\d+)|(\d+)\s*번(?![가-힣])")


def norm(no):
    """페이지 검색과 같은 규칙: 숫자만 남기고 앞의 0 제거 ("007" == "7")."""
    return re.sub(r"\D", "", str(no)).lstrip("0")


def squash(s):
    return re.sub(r"\s+", "", str(s)).lower()


def load(source):
    if source.startswith(("http://", "https://")):
        with urllib.request.urlopen(source, timeout=20) as r:
            return json.load(r)
    return json.loads(Path(source).read_text(encoding="utf-8"))


def validate(items, local):
    errors = []
    if not isinstance(items, list):
        return ["products.json 최상위가 목록([])이 아니에요"]
    seen = {}
    for idx, item in enumerate(items):
        where = f"{idx + 1}번째 항목"
        if not isinstance(item, dict):
            errors.append(f"{where}: 객체가 아니에요")
            continue
        no = norm(item.get("no", ""))
        if not no:
            errors.append(f"{where}: 상품번호(no)가 비었어요")
        else:
            where = f"No.{item['no']}"
            if no in seen:
                errors.append(f"{where}: 번호가 No.{seen[no]}와 겹쳐요")
            seen.setdefault(no, item["no"])
        if not str(item.get("name", "")).strip():
            errors.append(f"{where}: 상품명(name)이 비었어요")
        links = item.get("links")
        if not isinstance(links, list) or not links:
            errors.append(f"{where}: 쿠팡 링크(links)가 없어요")
        else:
            for l in links:
                url = l.get("url", "") if isinstance(l, dict) else ""
                if not LINK_RE.match(url):
                    errors.append(f"{where}: 쿠팡 파트너스 링크 형식이 아니에요 ({url or '빈 값'})")
        date = item.get("date")
        if date and not DATE_RE.match(str(date)):
            errors.append(f"{where}: 날짜 형식이 YYYY-MM-DD가 아니에요 ({date})")
        image = str(item.get("image", ""))
        if local and image.startswith(REPO_RAW) and not (ROOT / image[len(REPO_RAW):]).is_file():
            errors.append(f"{where}: 이미지 파일이 저장소에 없어요 ({image[len(REPO_RAW):]})")
    return errors


def check_page():
    try:
        html = PAGE.read_text(encoding="utf-8")
    except OSError:
        return [f"{PAGE.relative_to(ROOT)} 파일을 찾을 수 없어요"]
    if DISCLOSURE not in html:
        return ["링크 모음 페이지에 쿠팡 파트너스 고지 문구가 없어요: " + DISCLOSURE]
    return []


def parse_require(value):
    no, _, name = value.partition("=")
    return norm(no), name.strip()


def post_numbers(text):
    return [norm(a or b) for a, b in POST_NO_RE.findall(text) if norm(a or b)]


def check_required(items, wanted):
    by_no = {norm(i.get("no", "")): i for i in items if isinstance(i, dict)}
    errors, ok = [], []
    for no, name in wanted:
        item = by_no.get(no)
        if not item:
            errors.append(f"No.{no}: 링크 모음에 아직 등록되지 않았어요. 글보다 먼저 등록해 주세요")
            continue
        if name and squash(name) not in squash(item.get("name", "")) and squash(item.get("name", "")) not in squash(name):
            errors.append(f"No.{no}: 링크 모음에는 '{item.get('name')}'로 등록돼 있는데 글에는 '{name}'(으)로 적혀 있어요")
            continue
        ok.append(f"No.{no} {item.get('name')} 확인")
    return errors, ok


def main():
    ap = argparse.ArgumentParser(description="링크 모음 상품번호 점검")
    ap.add_argument("--source", default=str(PRODUCTS), help="products.json 경로 또는 URL")
    ap.add_argument("--require", action="append", default=[], metavar="번호[=상품명]",
                    help="링크 모음에 있어야 하는 번호 (여러 번 지정 가능)")
    ap.add_argument("--post", metavar="파일", help="글 본문 파일 ('-'는 표준입력)에서 번호를 찾아 확인")
    args = ap.parse_args()

    local = not args.source.startswith(("http://", "https://"))
    try:
        items = load(args.source)
    except (OSError, ValueError) as e:
        print(f"✗ 상품 데이터를 읽지 못했어요: {e}")
        return 1

    errors = validate(items, local)
    if local and Path(args.source).resolve() == PRODUCTS:
        errors += check_page()

    wanted = [parse_require(v) for v in args.require]
    if args.post:
        text = sys.stdin.read() if args.post == "-" else Path(args.post).read_text(encoding="utf-8")
        found = post_numbers(text)
        if not found:
            errors.append("글 본문에서 상품번호(No.123 또는 123번)를 찾지 못했어요")
        wanted += [(n, "") for n in dict.fromkeys(found) if n not in {w[0] for w in wanted}]
    missing, ok = check_required(items if isinstance(items, list) else [], wanted)
    errors += missing

    for line in ok:
        print("✓ " + line)
    for line in errors:
        print("✗ " + line)
    if errors:
        return 1
    print(f"✓ 상품 {len(items)}개 점검 완료")
    return 0


if __name__ == "__main__":
    sys.exit(main())
