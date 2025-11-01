# -*- coding: utf-8 -*-
"""
VRChatギャラリー用 生成スクリプト（Windows 11 / Python 3.x）
- gallery/full_pc/*.png を入力に
  - 先に full_pc 内のファイルを 3桁連番（001.png, 002.png, ...）へリネーム
  - gallery/full_mobile/ に縮小コピーを生成（既定: 長辺 1024 px）
  - 4x4=16枚のサムネセルからアトラス thumbs_page_XXXX.jpg を生成
- サムネセルはアスペクト比を保持し、余白でレターボックス（崩れない）

使い方:
    py generate_gallery.py [--cell 256x144] [--grid 4x4]
                           [--mobile-max 1024] [--ext png]
"""
from __future__ import annotations
import argparse
from pathlib import Path
from PIL import Image

# ---------------------------- 設定の既定値 ----------------------------
DEFAULT_CELL_W = 256        # サムネセルの幅（アトラス内の1マス）
DEFAULT_CELL_H = 144        # サムネセルの高さ（16:9を想定。正方形なら 256 に）
DEFAULT_GRID_COLS = 4       # アトラス列数
DEFAULT_GRID_ROWS = 4       # アトラス行数
DEFAULT_MOBILE_MAX = 1024   # モバイル向け縮小の長辺 px
DEFAULT_EXT = "png"         # full_mobile の出力拡張子
# ---------------------------------------------------------------------

def parse_args():
    p = argparse.ArgumentParser(description="Generate atlas thumbnails for VRChat gallery (no json).")
    p.add_argument("--cell", default=f"{DEFAULT_CELL_W}x{DEFAULT_CELL_H}",
                   help="サムネセルのサイズ（例: 256x144 または 256x256）")
    p.add_argument("--grid", default=f"{DEFAULT_GRID_COLS}x{DEFAULT_GRID_ROWS}",
                   help="アトラスのグリッド（例: 4x4）")
    p.add_argument("--mobile-max", type=int, default=DEFAULT_MOBILE_MAX,
                   help="full_mobile の長辺上限 px（既定 1024）")
    p.add_argument("--ext", default=DEFAULT_EXT, choices=["png", "jpg", "jpeg"],
                   help="full_mobile の出力拡張子（既定 png）")
    return p.parse_args()

def ensure_dirs(gallery_dir: Path):
    (gallery_dir / "full_mobile").mkdir(parents=True, exist_ok=True)

def list_full_pc_images(full_pc_dir: Path) -> list[Path]:
    files = sorted(full_pc_dir.glob("*.png"))
    seen = set()
    unique = []
    for p in files:
        key = p.name.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(p)
    return unique

def rename_full_pc_sequential(full_pc_dir: Path, digits: int = 3) -> list[Path]:
    """
    full_pc 内の *.png を 3桁連番に統一（001.png, 002.png, ...）
    衝突回避のため一時名へ退避→最終名へ確定の二段階。
    戻り値は最終ファイルパスの昇順リスト。
    """
    files = list_full_pc_images(full_pc_dir)
    if not files:
        return []

    # 一時退避名へ
    temp_paths = []
    for i, src in enumerate(files, start=1):
        tmp = src.with_name(f"__tmp_renaming_{i:06d}.png")
        src.rename(tmp)
        temp_paths.append(tmp)

    # 最終名へ
    final_paths = []
    for i, tmp in enumerate(sorted(temp_paths), start=1):
        dst = full_pc_dir / f"{i:0{digits}d}.png"
        if dst.exists():
            dst.unlink()
        tmp.rename(dst)
        final_paths.append(dst)

    return final_paths

def resize_with_aspect(im: Image.Image, max_w: int, max_h: int) -> Image.Image:
    w, h = im.size
    scale = min(max_w / w, max_h / h)
    new_w, new_h = max(1, int(w * scale)), max(1, int(h * scale))
    return im.resize((new_w, new_h), Image.LANCZOS)

def make_letterboxed_thumb(src: Image.Image, cell_w: int, cell_h: int, bg=(0, 0, 0)) -> Image.Image:
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

    # 0) 連番リネーム（3桁）
    renamed = rename_full_pc_sequential(full_pc_dir, digits=3)
    if not renamed:
        print(f"[!] 入力が見つからないわ: {full_pc_dir}\\*.png を用意してね")
        return

    # 1) full_mobile 生成 + サムネセル生成
    thumbs_cells: list[Image.Image] = []
    for src_path in renamed:
        stem = src_path.stem  # 例: 001
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

    # 2) アトラス生成（16枚/ページ）
    per_page = cols * rows
    atlas_count = 0
    for page_idx in range(0, len(thumbs_cells), per_page):
        page_cells = thumbs_cells[page_idx:page_idx + per_page]
        atlas = build_atlas(page_cells, cols, rows, cell_w, cell_h)
        atlas_name = f"thumbs_page_{(page_idx // per_page + 1):04d}.jpg"
        atlas_path = gallery_dir / atlas_name
        save_image(atlas, atlas_path, "jpg")
        atlas_count += 1

    print(f"[OK] 連番リネーム: {len(renamed)} 枚（001.png〜）完了したわ。")
    print(f"[OK] アトラス {atlas_count} 枚、full_mobile {len(renamed)} 枚を生成したの。")
#    print(f"[NOTE] list.json の生成は行っていないわ。必要なら別途スクリプトで作ってね。")

if __name__ == "__main__":
    main()
