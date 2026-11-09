"""Removes the background of product photos waiting for review.

Runs on GitHub Actions (see .github/workflows/clean-photos.yml). For every photo in
`product_images` with status 'pending' that hasn't been processed yet:
  1. download the (server-cropped) photo,
  2. remove the background (rembg, model isnet-general-use),
  3. trim to the product with a small margin, max 800 px, save as WebP with transparency,
  4. upload it next to the original and store clean_url / clean_ok on the row.
The admin then picks the clean or the original version on besinradar.app/admin.
"""

import io
import os
import sys
from datetime import datetime, timezone

import requests
from PIL import Image
from rembg import new_session, remove

URL = os.environ["SUPABASE_URL"].rstrip("/")
KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
BUCKET = "product-images"
# New Supabase secret keys (sb_secret_…) go in the apikey header only;
# legacy service_role keys are JWTs and are also sent as a Bearer token.
H = {"apikey": KEY, **({"Authorization": f"Bearer {KEY}"} if KEY.startswith("eyJ") else {})}
MAX_SIDE = 800
BATCH = 200


def pending():
    r = requests.get(
        f"{URL}/rest/v1/product_images",
        params={
            "select": "id,barcode,url",
            "status": "eq.pending",
            "processed_at": "is.null",
            "url": "not.is.null",
            "order": "created_at.asc",
            "limit": str(BATCH),
        },
        headers=H,
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def patch(row_id, data):
    r = requests.patch(
        f"{URL}/rest/v1/product_images",
        params={"id": f"eq.{row_id}"},
        headers={**H, "Content-Type": "application/json", "Prefer": "return=minimal"},
        json=data,
        timeout=30,
    )
    r.raise_for_status()


def upload(path, data, content_type):
    r = requests.post(
        f"{URL}/storage/v1/object/{BUCKET}/{path}",
        headers={**H, "Content-Type": content_type, "x-upsert": "true", "cache-control": "31536000"},
        data=data,
        timeout=60,
    )
    r.raise_for_status()
    return f"{URL}/storage/v1/object/public/{BUCKET}/{path}"


def clean(img, session):
    """Returns (webp bytes, coverage) or (None, coverage) when nothing was found."""
    cut = remove(img, session=session)  # RGBA
    alpha = cut.getchannel("A")
    mask = alpha.point(lambda a: 255 if a > 40 else 0)
    box = mask.getbbox()
    hist = mask.histogram()
    coverage = hist[255] / float(cut.width * cut.height)
    if not box:
        return None, coverage
    x0, y0, x1, y1 = box
    pad = int(max(x1 - x0, y1 - y0) * 0.04)
    cut = cut.crop((max(0, x0 - pad), max(0, y0 - pad), min(cut.width, x1 + pad), min(cut.height, y1 + pad)))
    cut.thumbnail((MAX_SIDE, MAX_SIDE), Image.LANCZOS)
    buf = io.BytesIO()
    cut.save(buf, "WEBP", quality=90, method=6)
    return buf.getvalue(), coverage


def main():
    rows = pending()
    print(f"{len(rows)} fotograf bekliyor")
    if not rows:
        return 0
    session = new_session("isnet-general-use")
    done = 0
    for row in rows:
        now = datetime.now(timezone.utc).isoformat()
        try:
            res = requests.get(row["url"], timeout=60)
            res.raise_for_status()
            img = Image.open(io.BytesIO(res.content)).convert("RGB")
            data, coverage = clean(img, session)
            if data is None:
                patch(row["id"], {"processed_at": now, "clean_ok": False, "clean_error": "nothing_found"})
                continue
            path = f"{row['barcode']}/{row['id']}-clean.webp"
            url = upload(path, data, "image/webp")
            # Very small or almost full-frame results usually mean the model missed the product.
            ok = 0.05 < coverage < 0.97
            patch(row["id"], {
                "processed_at": now, "clean_path": path, "clean_url": url, "clean_ok": ok,
                "clean_error": None if ok else f"coverage:{coverage:.2f}",
            })
            done += 1
            print(f"#{row['id']} {row['barcode']} temizlendi (kaplama {coverage:.2f})")
        except Exception as e:  # keep going with the next photo
            print(f"#{row['id']} hata: {e}", file=sys.stderr)
            try:
                patch(row["id"], {"processed_at": now, "clean_ok": False, "clean_error": str(e)[:300]})
            except Exception:
                pass
    print(f"{done} fotograf temizlendi")
    return 0


if __name__ == "__main__":
    sys.exit(main())
