SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Installing skills..."
"$SCRIPT_DIR/agents/install-skills.sh"

echo "Symlinking..."
"$SCRIPT_DIR/agents/symlink-skills.sh"