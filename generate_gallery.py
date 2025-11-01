# -*- coding: utf-8 -*-
"""
VRChatギャラリー用 生成スクリプト（Windows 11 / Python 3.x）
- gallery/full_pc/*.png を入力に
  - 先に full_pc 内のファイルを 3桁連番（001.png, 002.png, ...）へリネーム
  - 最大 208 枚に満たない場合、2048x1152 の灰色PNGで補完（208 枚ちょうどに揃える）
  - gallery/full_mobile/ に縮小コピー（長辺既定: 1024 px, 常に PNG ）
  - 4x4=16枚のサムネからサムネイルアトラス thumbs_page_XXXX.png を生成（最大 13 枚）
- 生成される画像はすべて PNG

使い方:
    py generate_gallery.py [--cell 256x144] [--grid 4x4] [--mobile-max 1024]
"""
from __future__ import annotations
import argparse
from pathlib import Path
from PIL import Image

# ---------------------------- 定数 ----------------------------
DEFAULT_CELL_W = 256
DEFAULT_CELL_H = 144
DEFAULT_GRID_COLS = 4
DEFAULT_GRID_ROWS = 4
DEFAULT_MOBILE_MAX = 1024

MAX_ITEMS = 208            # full_pc / full_mobile の最大枚数
MAX_ATLAS_PAGES = 13       # サムネイルアトラスの最大枚数（13 * 16 = 208）
PLACEHOLDER_SIZE = (2048, 1152)
PLACEHOLDER_COLOR = (128, 128, 128)  # 灰色
# -------------------------------------------------------------

def parse_args():
    p = argparse.ArgumentParser(description="Generate PNG atlas thumbnails for VRChat gallery (no json).")
    p.add_argument("--cell", default=f"{DEFAULT_CELL_W}x{DEFAULT_CELL_H}",
                   help="サムネセルのサイズ（例: 256x144 または 256x256）")
    p.add_argument("--grid", default=f"{DEFAULT_GRID_COLS}x{DEFAULT_GRID_ROWS}",
                   help="アトラスのグリッド（例: 4x4）")
    p.add_argument("--mobile-max", type=int, default=DEFAULT_MOBILE_MAX,
                   help="full_mobile の長辺上限 px（既定 1024）")
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
    full_pc 内の *.png を 3桁連番に統一（001.png, 002.png, ...）。
    衝突回避のため一時名に退避→最終名へ確定の二段階。
    返り値は最終ファイルパスの昇順。
    """
    files = list_full_pc_images(full_pc_dir)
    if not files:
        return []

    # 一時退避
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

def pad_with_placeholders(full_pc_dir: Path, current_count: int, target: int = MAX_ITEMS,
                          digits: int = 3):
    """
    現在枚数 < target の場合、連番の末尾から target まで灰色プレースホルダPNGを生成。
    """
    for i in range(current_count + 1, target + 1):
        dst = full_pc_dir / f"{i:0{digits}d}.png"
        # うっかり存在してたら上書きするのよ
        if dst.exists():
            dst.unlink()
        im = Image.new("RGB", PLACEHOLDER_SIZE, PLACEHOLDER_COLOR)
        im.save(dst, optimize=True)

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

def save_png(im: Image.Image, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    # RGBA でもそのまま PNG で保存するわ
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

    # 入力なしでもOK。足りなければプレースホルダで埋める前提よ
    count_after_rename = len(renamed)

    # 1) プレースホルダで 208 枚に揃える
    if count_after_rename < MAX_ITEMS:
        pad_with_placeholders(full_pc_dir, count_after_rename, MAX_ITEMS, digits=3)
        print(f"[INFO] {count_after_rename} 枚しかなかったから、{MAX_ITEMS} 枚まで灰色PNGで補完したわ。")
    else:
        if count_after_rename > MAX_ITEMS:
            print(f"[WARN] {count_after_rename} 枚あったけど、先頭 {MAX_ITEMS} 枚だけ処理するのよ。")
        else:
            print(f"[OK] ちょうど {MAX_ITEMS} 枚揃っているわ。")

    # 2) 処理対象の 208 枚を読み直し
    targets = [full_pc_dir / f"{i:03d}.png" for i in range(1, MAX_ITEMS + 1)]

    # 3) full_mobile 生成 + サムネセル生成（PNG固定）
    thumbs_cells: list[Image.Image] = []
    for src_path in targets:
        stem = src_path.stem  # 例: 001
        with Image.open(src_path) as im:
            # 透過があっても PNG のまま扱うのよ
            if im.mode in ("LA", "RGBA", "P"):
                im = im.convert("RGBA")
            else:
                im = im.convert("RGB")

            # 長辺 args.mobile_max で縮小（拡大はしない）
            w, h = im.size
            if max(w, h) > args.mobile_max:
                if w >= h:
                    resized = resize_with_aspect(im, args.mobile_max, 10**8)
                else:
                    resized = resize_with_aspect(im, 10**8, args.mobile_max)
            else:
                resized = im

            mobile_path = full_mobile_dir / f"{stem}.png"
            save_png(resized, mobile_path)

            # サムネセル（レターボックス）
            cell = make_letterboxed_thumb(im, cell_w, cell_h, bg=(0, 0, 0))
            thumbs_cells.append(cell)

    # 4) アトラス生成（最大 13 枚、PNG固定）
    per_page = cols * rows
    max_cells = min(len(thumbs_cells), MAX_ITEMS)                    # 念のため安全側
    max_pages = min(MAX_ATLAS_PAGES, (max_cells + per_page - 1) // per_page)

    atlas_count = 0
    for page in range(max_pages):
        start = page * per_page
        end = min(start + per_page, max_cells)
        page_cells = thumbs_cells[start:end]
        if not page_cells:
            break
        atlas = build_atlas(page_cells, cols, rows, cell_w, cell_h)
        atlas_name = f"thumbs_page_{(page + 1):04d}.png"
        atlas_path = gallery_dir / atlas_name
        save_png(atlas, atlas_path)
        atlas_count += 1

    print(f"[OK] 連番リネーム完了（001.png〜）。")
    print(f"[OK] full_mobile を {len(targets)} 枚（PNG）生成したわ。")
    print(f"[OK] サムネイルアトラスを {atlas_count} 枚（PNG）作成したの。最大 {MAX_ATLAS_PAGES} 枚までに抑えてあるわ。")
    print(f"[NOTE] list.json の生成は行っていないのよ。")

if __name__ == "__main__":
    main()
