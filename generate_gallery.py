# -*- coding: utf-8 -*-
"""
VRChatギャラリー用 生成スクリプト（Windows 11 / Python 3.x）
- gallery/full_pc/*.png を入力に
  - gallery/full_mobile/ に縮小コピーを生成（既定: 長辺 1280 px）
  - 4x4=16枚のサムネセルからアトラス thumbs_page_XXXX.jpg を生成
  - list.json を生成（atlas と items[ full_pc / full_mobile / caption ]）
- サムネセルはアスペクト比を保持し、余白でレターボックス（崩れない）

使い方:
    py generate_gallery.py --user <github_username> [--cell 256x144] [--grid 4x4]
                           [--mobile-max 1280] [--ext png] [--base-url <url>]
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from PIL import Image

# ---------------------------- 設定の既定値 ----------------------------
DEFAULT_CELL_W = 256        # サムネセルの幅（アトラス内の1マス）
DEFAULT_CELL_H = 144        # サムネセルの高さ（16:9を想定。正方形なら 256 に）
DEFAULT_GRID_COLS = 4       # アトラス列数
DEFAULT_GRID_ROWS = 4       # アトラス行数
DEFAULT_MOBILE_MAX = 1280   # モバイル向け縮小の長辺 px
DEFAULT_EXT = "png"         # 出力拡張子（full_pc は入力のまま。full_mobile は既定 png）
# ---------------------------------------------------------------------

def parse_args():
    p = argparse.ArgumentParser(description="Generate atlas thumbnails and list.json for VRChat gallery.")
    p.add_argument("--user", required=False, help="GitHubユーザー名（例: kuroyagi）。指定がなければ相対URLにする。")
    p.add_argument("--base-url", default=None,
                   help="ベースURLを直接指定（例: https://<user>.github.io/gallery/）。指定があれば優先。")
    p.add_argument("--cell", default=f"{DEFAULT_CELL_W}x{DEFAULT_CELL_H}",
                   help="サムネセルのサイズ（例: 256x144 または 256x256）")
    p.add_argument("--grid", default=f"{DEFAULT_GRID_COLS}x{DEFAULT_GRID_ROWS}",
                   help="アトラスのグリッド（例: 4x4）")
    p.add_argument("--mobile-max", type=int, default=DEFAULT_MOBILE_MAX,
                   help="full_mobile の長辺上限 px（既定 1280）")
    p.add_argument("--ext", default=DEFAULT_EXT, choices=["png", "jpg", "jpeg"],
                   help="full_mobile の出力拡張子（既定 png）")
    p.add_argument("--caption", default="filename",
                   choices=["filename", "none"],
                   help="caption の埋め方: filename=ファイル名(拡張子除く) / none=空文字")
    return p.parse_args()

def ensure_dirs(gallery_dir: Path):
    (gallery_dir / "full_mobile").mkdir(parents=True, exist_ok=True)

def list_full_pc_images(full_pc_dir: Path) -> list[Path]:
    files = []
    for ext in ("*.png", "*.PNG"):
        files.extend(sorted(full_pc_dir.glob(ext)))
    return files

def resize_with_aspect(im: Image.Image, max_w: int, max_h: int) -> Image.Image:
    w, h = im.size
    scale = min(max_w / w, max_h / h)
    new_w, new_h = max(1, int(w * scale)), max(1, int(h * scale))
    return im.resize((new_w, new_h), Image.LANCZOS)

def make_letterboxed_thumb(src: Image.Image, cell_w: int, cell_h: int, bg=(0, 0, 0)) -> Image.Image:
    # アスペクト保持でセルに収め、足りない側は余白（レターボックス）
    thumb = Image.new("RGB", (cell_w, cell_h), bg)
    fit = resize_with_aspect(src, cell_w, cell_h)
    x = (cell_w - fit.width) // 2
    y = (cell_h - fit.height) // 2
    thumb.paste(fit, (x, y))
    return thumb

def save_image(im: Image.Image, path: Path, ext: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    if ext.lower() in ("jpg", "jpeg"):
        im = im.convert("RGB")
        im.save(path, quality=90, optimize=True)
    else:
        im.save(path, optimize=True)

def build_atlas(thumbs: list[Image.Image], cols: int, rows: int, cell_w: int, cell_h: int) -> Image.Image:
    atlas = Image.new("RGB", (cols * cell_w, rows * cell_h), (0, 0, 0))
    for i, t in enumerate(thumbs):
        r = i // cols
        c = i % cols
        if r >= rows:
            break
        atlas.paste(t, (c * cell_w, r * cell_h))
    return atlas

def main():
    args = parse_args()
    cell_w, cell_h = map(int, args.cell.lower().split("x"))
    cols, rows = map(int, args.grid.lower().split("x"))

    repo_root = Path(__file__).resolve().parent
    gallery_dir = repo_root / "gallery"
    full_pc_dir = gallery_dir / "full_pc"
    full_mobile_dir = gallery_dir / "full_mobile"

    ensure_dirs(gallery_dir)

    # ベースURL（完全URL推奨）。--base-url が最優先。--user があれば https://<user>.github.io/gallery/
    if args.base_url:
        base_url = args.base_url.rstrip("/") + "/"
    elif args.user:
        base_url = f"https://{args.user}.github.io/gallery/"
    else:
        # 相対URLも動くけれど、VRChatでは完全URL推奨。必要なら --user か --base-url を指定してね。
        base_url = "./gallery/"

    # 対象ファイルを収集
    inputs = list_full_pc_images(full_pc_dir)
    if not inputs:
        print(f"[!] 入力が見つからないわ: {full_pc_dir}\\*.png を用意してね")
        return

    items = []          # list.json用の全アイテム
    atlas_pages = []    # 生成したアトラスのファイル名（URL）

    # 1) full_mobile 生成 + サムネセル生成
    thumbs_cells: list[Image.Image] = []
    for idx, src_path in enumerate(inputs, start=1):
        stem = src_path.stem  # 例: 0001
        # full_mobile
        with Image.open(src_path) as im:
            im = im.convert("RGBA") if im.mode in ("LA", "RGBA", "P") else im.convert("RGB")
            # 長辺 args.mobile_max で縮小（拡大はしない）
            w, h = im.size
            if max(w, h) > args.mobile_max:
                if w >= h:
                    resized = resize_with_aspect(im, args.mobile_max, 10**8)
                else:
                    resized = resize_with_aspect(im, 10**8, args.mobile_max)
            else:
                resized = im

            mobile_name = f"{stem}.{args.ext}"
            mobile_path = full_mobile_dir / mobile_name
            save_image(resized, mobile_path, args.ext)

            # サムネセル（レターボックス）
            cell = make_letterboxed_thumb(im, cell_w, cell_h, bg=(0, 0, 0))
            thumbs_cells.append(cell)

        # list.json の1件（caption はファイル名 or 空）
        if args.caption == "filename":
            caption = stem
        else:
            caption = ""

        items.append({
            "id": idx,
            "caption": caption,
            "full_pc":     f"{base_url}full_pc/{stem}.png",
            "full_mobile": f"{base_url}full_mobile/{mobile_name}"
        })

    # 2) アトラス生成（16枚/ページ）
    per_page = cols * rows
    for page_idx in range(0, len(thumbs_cells), per_page):
        page_cells = thumbs_cells[page_idx:page_idx + per_page]
        atlas = build_atlas(page_cells, cols, rows, cell_w, cell_h)
        atlas_name = f"thumbs_page_{(page_idx // per_page + 1):04d}.jpg"
        atlas_path = gallery_dir / atlas_name
        save_image(atlas, atlas_path, "jpg")
        atlas_pages.append(atlas_name)

    # 3) list.json を組み立て（pages[]）
    pages = []
    for p, atlas_name in enumerate(atlas_pages, start=1):
        start = (p - 1) * per_page
        end = min(p * per_page, len(items))
        page_items = items[start:end]
        pages.append({
            "atlas": f"{base_url}{atlas_name}",
            "items": page_items
        })

    manifest = {"pages": pages}
    out_path = gallery_dir / "list.json"
    out_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] list.json を出力: {out_path}")
    print(f"[OK] アトラス {len(atlas_pages)} 枚、full_mobile {len(items)} 枚 生成したわ。")

if __name__ == "__main__":
    main()
