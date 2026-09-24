SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Installing skills..."
"$SCRIPT_DIR/install-skills.sh"

echo "Symlinking..."
"$SCRIPT_DIR/symlink.sh"