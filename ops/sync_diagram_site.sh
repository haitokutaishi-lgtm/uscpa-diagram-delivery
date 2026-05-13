#!/usr/bin/env bash
# publish-html の完成ファイルを diagram-site の topics/<slug>/index.html にコピーする。
# 使い方: sync_diagram_site.sh <FARリポジトリのルート> <diagram-site クローンのパス>
set -euo pipefail

FAR_ROOT="${1:?FAR repo root}"
SITE_ROOT="${2:?diagram-site clone path}"
MANIFEST="$FAR_ROOT/ops/diagram-publish-manifest.json"

if [[ ! -f "$MANIFEST" ]]; then
  echo "::error::manifest not found: $MANIFEST"
  exit 1
fi

synced=0
skipped=0

while IFS= read -r row; do
  slug=$(echo "$row" | jq -r '.slug')
  src=$(echo "$row" | jq -r '.source')
  abs="$FAR_ROOT/$src"
  if [[ ! -f "$abs" ]]; then
    echo "::notice::skip slug=$slug (source missing: $src)"
    skipped=$((skipped + 1))
    continue
  fi
  dest="$SITE_ROOT/topics/$slug/index.html"
  mkdir -p "$(dirname "$dest")"
  cp "$abs" "$dest"
  echo "synced $slug <- $src"
  synced=$((synced + 1))
done < <(jq -c '.[]' "$MANIFEST")

# publish-html/avatars を各 topics/<slug>/avatars/ に複製（HTML は avatars/ 相対で参照可能）
AV_DIR="$FAR_ROOT/publish-html/avatars"
if [[ -d "$AV_DIR" ]]; then
  shopt -s nullglob
  av_files=("$AV_DIR"/*)
  shopt -u nullglob
  if ((${#av_files[@]} > 0)); then
    while IFS= read -r row; do
      slug=$(echo "$row" | jq -r '.slug')
      dest_dir="$SITE_ROOT/topics/$slug/avatars"
      mkdir -p "$dest_dir"
      cp -f "${av_files[@]}" "$dest_dir/"
      echo "synced avatars/ -> topics/$slug/avatars/"
    done < <(jq -c '.[]' "$MANIFEST")
  fi
fi

echo "diagram-site sync done: synced=$synced skipped=$skipped"
