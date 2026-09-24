#!/bin/bash

# ~/.agents skills
SHARED_DIR="$HOME/dotfiles/agents/_shared"
TARGET_DIR="$HOME/.agents"

ln -sfn $SHARED_DIR/evals $TARGET_DIR/evals
ln -sfn $SHARED_DIR/rules $TARGET_DIR/rules
ln -sfn $SHARED_DIR/agents $TARGET_DIR/agents

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