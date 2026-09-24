#!/bin/bash

# ~/.agents shared files
SHARED_DIR="$HOME/dotfiles/agents/_shared"
TARGET_DIR="$HOME/.agents"

ln -sfn $SHARED_DIR/evals $TARGET_DIR/evals
ln -sfn $SHARED_DIR/rules $TARGET_DIR/rules

mkdir -p "$TARGET_DIR/skills"

for skill in "$SHARED_DIR"/skills/*; do
  [ -d "$skill" ] || continue

  name="$(basename "$skill")"

  ln -sfn "$skill" "$TARGET_DIR/skills/$name"
  echo "linked: $name"
done

# ~/.claude skills（~/.agents/skills を参照）
CLAUDE_SKILLS="$HOME/.claude/skills"

mkdir -p "$CLAUDE_SKILLS"

for skill in "$TARGET_DIR/skills"/*; do
  [ -d "$skill" ] || continue

  name="$(basename "$skill")"

  ln -sfn "$skill" "$CLAUDE_SKILLS/$name"
  echo "linked (claude): $name"
done
