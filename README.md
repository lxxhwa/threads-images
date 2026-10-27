# threads-images

스레드·인스타 글에 쓰는 이미지와 프로필 링크 모음 페이지(`shop/`)를 담는 저장소.

- `shop/index.html`: 상품번호로 검색해서 쿠팡 파트너스 링크로 이동하는 링크 모음 페이지
- `shop/products.json`: 링크 모음 데이터 (번호, 상품명, 이미지, 쿠팡 링크, 날짜, 원글)
- `threads/`: 글에 쓰는 이미지

## 글 올리기 전 점검

글에 상품번호를 쓰기 전에 그 번호가 링크 모음에 먼저 등록돼 있어야 한다.

```sh
# 데이터 전체 점검 (중복 번호, 빈 링크, 쿠팡 파트너스 고지 문구)
python3 scripts/check_products.py

# 올릴 번호와 상품명이 맞는지 확인
python3 scripts/check_products.py --require "139=냉동 볶음밥"

# 글 본문에서 No.139, 139번 같은 번호를 찾아 확인
python3 scripts/check_products.py --post post.txt

# push 후 실제 배포 데이터에 반영됐는지 확인
python3 scripts/check_products.py \
  --source https://raw.githubusercontent.com/lxxhwa/threads-images/main/shop/products.json \
  --require 139
```

문제가 있으면 이유를 출력하고 종료 코드 1로 끝나므로, 자동 게시 스크립트에서는
이 명령이 실패하면 게시를 멈추면 된다. `shop/` 이 바뀔 때마다 GitHub Actions에서도
같은 점검을 돌린다.
