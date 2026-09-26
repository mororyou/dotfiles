#!/bin/bash

# ~/.agents skills
SHARED_DIR="$HOME/dotfiles/agents/_shared"
TARGET_DIR="$HOME/.agents"

# link_dir <src> <dst>
# dst が実ディレクトリ（symlink でない）なら上書きしない。
# ln -sfn は dst が実ディレクトリだとその中に link を作ってしまうため。
link_dir() {
  if [ -d "$2" ] && [ ! -L "$2" ]; then
    echo "skip: $2 is a real directory. Move its contents into $1 and remove it, then rerun."
    return
  fi
  ln -sfn "$1" "$2"
  echo "linked: $2"
}

mkdir -p "$TARGET_DIR"

link_dir "$SHARED_DIR/rules"  "$TARGET_DIR/rules"
link_dir "$SHARED_DIR/agents" "$TARGET_DIR/agents"

mkdir -p "$TARGET_DIR/skills"

echo "Symlinking agents skills..."

for skill in "$SHARED_DIR"/skills/*; do
  [ -d "$skill" ] || continue

  name="$(basename "$skill")"

  ln -sfn "$skill" "$TARGET_DIR/skills/$name"
  echo "linked: $name"
done

echo "Symlinking claude skills..."

# ~/.claude skills
CLAUDE_SKILLS="$HOME/.claude/skills"

mkdir -p "$CLAUDE_SKILLS"

for skill in "$TARGET_DIR/skills"/*; do
  [ -d "$skill" ] || continue

  name="$(basename "$skill")"

  ln -sfn "$skill" "$CLAUDE_SKILLS/$name"
  echo "linked (claude): $name"
done

# ~/.codex skills
echo "Symlinking codex skills..."

CODEX_SKILLS="$HOME/.codex/skills"

mkdir -p "$CODEX_SKILLS"

for skill in "$TARGET_DIR/skills"/*; do
  [ -d "$skill" ] || continue

  name="$(basename "$skill")"

  ln -sfn "$skill" "$CODEX_SKILLS/$name"
  echo "linked (codex): $name"
done

# ~/.claude agents / ~/.codex agents
# どちらもディレクトリごと symlink する（Codex はディレクトリ内のファイル symlink を辿らず
# "agent type is currently not available" になる。Claude も揃えて同じ作りにする）。
# Cursor は ~/.claude/agents と ~/.codex/agents を User-level subagents の互換パスとして読む（Cursor docs）ので、
# ~/.cursor/agents へのリンクは不要
echo "Symlinking claude agents..."

link_dir "$HOME/dotfiles/agents/claude/agents" "$HOME/.claude/agents"

echo "Symlinking codex agents..."

link_dir "$HOME/dotfiles/agents/codex/agents" "$HOME/.codex/agents"

# ~/.cursor skills
echo "Symlinking cursor skills..."

CURSOR_SKILLS="$HOME/.cursor/skills"

mkdir -p "$CURSOR_SKILLS"

for skill in "$TARGET_DIR/skills"/*; do
  [ -d "$skill" ] || continue

  name="$(basename "$skill")"

  ln -sfn "$skill" "$CURSOR_SKILLS/$name"
  echo "linked (cursor): $name"
done

echo "Done"
