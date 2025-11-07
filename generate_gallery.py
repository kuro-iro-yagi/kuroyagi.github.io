# -*- coding: utf-8 -*-
"""
VRChatギャラリー用 生成スクリプト（Windows 11 / Python 3.x）
- 入力: gallery/original/*.png, *.jpg, *.jpeg
  - 不足分は gallery/dummy.jpg を使用（無ければ自動生成）
- 出力:
  - gallery/full_pc/     : 長辺 2048px JPEG（右下に日時※）
  - gallery/full_mobile/ : 長辺 1024px JPEG（右下に日時※）
  - thumbs_page_XXXX.jpg : JPEGアトラス（サムネには日時は描かない）
- ※日時はファイル名が VRChat_YYYY-MM-DD_HH-MM-SS(.mmm)_WxH.ext の形式に一致した場合のみ
  （例: VRChat_2023-10-16_21-54-52.027_3840x2160.png → 2023/10/16 21:54）
- 最大 208 枚（13ページ×16）。JSON は生成しない。

使い方:
    py generate_gallery.py [--pc-max 2048] [--mobile-max 1024]
                           [--cell 256x144] [--grid 4x4]
"""
from __future__ import annotations
import argparse
import re
from pathlib import Path
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ImageOps

# ---------------------------- 既定値 ----------------------------
DEFAULT_PC_MAX = 2048
DEFAULT_MOBILE_MAX = 1024
DEFAULT_CELL_W = 256
DEFAULT_CELL_H = 144
DEFAULT_GRID_COLS = 4
DEFAULT_GRID_ROWS = 4
MAX_ITEMS = 208
MAX_PAGES = 13
DUMMY_SIZE = (2048, 1152)
DUMMY_COLOR = (128, 128, 128)
ATLAS_BG = (0, 0, 0)
TEXT_FILL = (255, 255, 255)
TEXT_STROKE = (0, 0, 0)
TEXT_MARGIN = 10
TEXT_OPACITY_BG = 160
# --------------------------------------------------------------

# 例: VRChat_2023-10-16_21-54-52.027_3840x2160.png
# 小数点以下は3〜5桁を許容、拡張子は png/jpg/jpeg
FNAME_RE = re.compile(
    r'^VRChat_(?P<Y>\d{4})-(?P<M>\d{2})-(?P<D>\d{2})_'
    r'(?P<h>\d{2})-(?P<m>\d{2})-(?P<s>\d{2})(?:\.(?P<frac>\d{3,5}))?_'
    r'(?P<w>\d+)x(?P<hh>\d+)\.(?P<ext>png|jpg|jpeg)$',
    re.IGNORECASE
)

def parse_args():
    p = argparse.ArgumentParser(description="Generate gallery JPEGs and JPEG atlas from original images.")
    p.add_argument("--pc-max", type=int, default=DEFAULT_PC_MAX,
                   help="full_pc の長辺上限 px（既定 2048）")
    p.add_argument("--mobile-max", type=int, default=DEFAULT_MOBILE_MAX,
                   help="full_mobile の長辺上限 px（既定 1024）")
    p.add_argument("--cell", default=f"{DEFAULT_CELL_W}x{DEFAULT_CELL_H}",
                   help="サムネセルのサイズ（例: 256x144 / 256x256）")
    p.add_argument("--grid", default=f"{DEFAULT_GRID_COLS}x{DEFAULT_GRID_ROWS}",
                   help="アトラスのグリッド（例: 4x4）")
    return p.parse_args()

def ensure_dirs(gallery_dir: Path):
    (gallery_dir / "full_pc").mkdir(parents=True, exist_ok=True)
    (gallery_dir / "full_mobile").mkdir(parents=True, exist_ok=True)

def list_original_images(original_dir: Path) -> list[Path]:
    exts = {".png", ".jpg", ".jpeg"}
    files = [p for p in sorted(original_dir.iterdir())
             if p.is_file() and p.suffix.lower() in exts]
    return files

def ensure_dummy(gallery_dir: Path) -> Path:
    dummy = gallery_dir / "dummy.jpg"
    if not dummy.exists():
        im = Image.new("RGB", DUMMY_SIZE, DUMMY_COLOR)
        im.save(dummy, format="JPEG", quality=90, optimize=True)
    return dummy

def resize_with_aspect(im: Image.Image, max_long: int) -> Image.Image:
    w, h = im.size
    long_side = max(w, h)
    if long_side <= max_long:
        return im
    if w >= h:
        new_w = max_long
        new_h = int(h * (max_long / w))
    else:
        new_h = max_long
        new_w = int(w * (max_long / h))
    return im.resize((max(1, new_w), max(1, new_h)), Image.LANCZOS)

def draw_timestamp(im: Image.Image, when: datetime) -> Image.Image:
    """右下に 'YYYY/MM/DD HH:MM' を描画。サムネには使わない。"""
    txt = when.strftime("%Y/%m/%d %H:%M")
    draw = ImageDraw.Draw(im, "RGBA")
    short_side = min(im.size)
    font_size = max(14, int(short_side * 0.035))  # 約3.5%
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except Exception:
        font = ImageFont.load_default()

    # textbbox は (l,t,r,b) を返す
    l, t, r, b = draw.textbbox((0, 0), txt, font=font)
    tw, th = r - l, b - t
    pad = 6
    box_w = tw + pad * 2
    box_h = th + pad * 2
    x1 = im.width - TEXT_MARGIN - box_w
    y1 = im.height - TEXT_MARGIN - box_h
    x2 = x1 + box_w
    y2 = y1 + box_h
    draw.rectangle([x1, y1, x2, y2], fill=(0, 0, 0, TEXT_OPACITY_BG))
    draw.text((x1 + pad, y1 + pad - 1), txt, font=font,
              fill=TEXT_FILL, stroke_width=2, stroke_fill=TEXT_STROKE)
    return im

def make_letterboxed_thumb(src: Image.Image, cell_w: int, cell_h: int, bg=ATLAS_BG) -> Image.Image:
    base = Image.new("RGB", (cell_w, cell_h), bg)
    w, h = src.size
    scale = min(cell_w / w, cell_h / h)
    new_w, new_h = max(1, int(w * scale)), max(1, int(h * scale))
    fit = src.resize((new_w, new_h), Image.LANCZOS)
    x = (cell_w - new_w) // 2
    y = (cell_h - new_h) // 2
    base.paste(fit, (x, y))
    return base

def save_jpeg(im: Image.Image, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    if im.mode not in ("RGB", "L"):
        im = im.convert("RGB")
    im.save(path, format="JPEG", quality=90, optimize=True, progressive=True)

def build_atlas(thumbs: list[Image.Image], cols: int, rows: int, cell_w: int, cell_h: int) -> Image.Image:
    atlas = Image.new("RGB", (cols * cell_w, rows * cell_h), ATLAS_BG)
    for i, t in enumerate(thumbs):
        r = i // cols
        c = i % cols
        if r >= rows:
            break
        atlas.paste(t, (c * cell_w, r * cell_h))
    return atlas

def parse_dt_from_filename(p: Path) -> datetime | None:
    """ファイル名が規定フォーマットなら日時を返す。合致しなければ None。"""
    m = FNAME_RE.match(p.name)
    if not m:
        return None
    try:
        Y = int(m.group("Y")); M = int(m.group("M")); D = int(m.group("D"))
        h = int(m.group("h")); m_ = int(m.group("m")); s = int(m.group("s"))
        # 小数点以下は無視（表示は分まで）
        return datetime(Y, M, D, h, m_, s)
    except Exception:
        return None

def main():
    args = parse_args()
    cell_w, cell_h = map(int, args.cell.lower().split("x"))
    cols, rows = map(int, args.grid.lower().split("x"))
    per_page = cols * rows

    if per_page * MAX_PAGES < MAX_ITEMS:
        print(f"[!] グリッド {cols}x{rows} だと {MAX_PAGES} ページで {per_page*MAX_PAGES} 枚まで。"
              f" MAX_ITEMS={MAX_ITEMS} に届かないのよ。")
        return

    repo_root = Path(__file__).resolve().parent
    gallery_dir = repo_root / "gallery"
    original_dir = gallery_dir / "original"
    full_pc_dir = gallery_dir / "full_pc"
    full_mobile_dir = gallery_dir / "full_mobile"

    ensure_dirs(gallery_dir)
    dummy_path = ensure_dummy(gallery_dir)

    sources = list_original_images(original_dir)
    if not sources:
        print(f"[WARN] original が空ね。全 {MAX_ITEMS} 枚を dummy.jpg で補完するわ。")

    # 001..MAX_ITEMS を用意（足りない分は dummy）
    inputs: list[Path] = []
    dts:    list[datetime | None] = []
    for i in range(MAX_ITEMS):
        if i < len(sources):
            src = sources[i]
            inputs.append(src)
            dts.append(parse_dt_from_filename(src))  # 形式不一致なら None
        else:
            inputs.append(dummy_path)
            dts.append(None)  # dummy は日時描かない

    thumbs_cells: list[Image.Image] = []
    for idx, (src, dt) in enumerate(zip(inputs, dts), start=1):
        stem3 = f"{idx:03d}"
        is_dummy = (src == dummy_path)

        # 読み込み（EXIF回転補正）
        im = Image.open(src)
        im = ImageOps.exif_transpose(im)
        if im.mode not in ("RGB", "L"):
            im = im.convert("RGB")

        # full_pc：基準リサイズ →（条件付）日時描画 → 保存
        pc_base = resize_with_aspect(im, args.pc_max)
        pc_img = pc_base.copy()
        if (not is_dummy) and (dt is not None):
            pc_img = draw_timestamp(pc_img, dt)
        save_jpeg(pc_img, full_pc_dir / f"{stem3}.jpg")

        # full_mobile：基準リサイズ →（条件付）日時描画 → 保存
        mobile_base = resize_with_aspect(im, args.mobile_max)
        mobile_img = mobile_base.copy()
        if (not is_dummy) and (dt is not None):
            mobile_img = draw_timestamp(mobile_img, dt)
        save_jpeg(mobile_img, full_mobile_dir / f"{stem3}.jpg")

        # サムネ（※日時は描かない）：mobile_base をそのままレタボ化
        cell = make_letterboxed_thumb(mobile_base, cell_w, cell_h, bg=ATLAS_BG)
        thumbs_cells.append(cell)

    # アトラス生成（JPEG, 最大13ページ）
    atlas_count = 0
    for page_idx in range(0, min(len(thumbs_cells), per_page * MAX_PAGES), per_page):
        page_cells = thumbs_cells[page_idx:page_idx + per_page]
        atlas = build_atlas(page_cells, cols, rows, cell_w, cell_h)
        atlas_name = f"thumbs_page_{(page_idx // per_page + 1):04d}.jpg"
        save_jpeg(atlas, gallery_dir / atlas_name)
        atlas_count += 1

    print(f"[OK] full_pc JPEG: {MAX_ITEMS} 枚生成（001.jpg〜{MAX_ITEMS:03d}.jpg）。")
    print(f"[OK] full_mobile JPEG: {MAX_ITEMS} 枚生成。")
    print(f"[OK] サムネイル JPEG アトラス: {atlas_count} 枚（最大 {MAX_PAGES} ページ）。")
    print("[NOTE] 日付はファイル名が規定フォーマットのときのみ描画、サムネには描かないわ。")

if __name__ == "__main__":
    main()
