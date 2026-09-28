# dotfiles

### ファイル構成
```
├── README.md
└── agents
    ├── _shared Agent共通設定
    │   ├── agents  各 Agent の役割定義（ツール非依存）
    │   │   ├── architect.md
    │   │   ├── implementer.md
    │   │   ├── researcher.md
    │   │   └── reviewer.md
    │   ├── rules
    │   │   └── orchestrator.md  Orchestrator（Orca 上の Claude Code）の方針。oned-coordinate スキルから読む。worker には適用しない
    │   ├── evals   スキルの評価ワークスペース（配下は省略）
    │   └── skills
    │       ├── README.md
    │       ├── oned-coordinate  ONED の JIRA チケット起点で Coordinator として振る舞い、Orca で各役割を回す入口
    │       ├── obsidian
    │       └── artifact-copy
    ├── claude Claude 固有設定（常設の全役割はここ）
    │   ├── agents  サブエージェント定義（_shared/agents の本体を参照する薄いラッパー）
    │   │   ├── researcher.md   claude-sonnet-5   / read-only
    │   │   ├── architect.md    claude-fable-5-1  / read-only
    │   │   ├── implementer.md  claude-opus-5-5
    │   │   └── reviewer.md     claude-fable-5-1  / read-only（Implementer と別 tier）
    │   ├── mcp.json.example  obsidian MCP（Shared Memory）の設定例。実登録はトークン直書き（Orca 経由の worker に env が渡らない可能性）
    │   └── skills
    │       ├── README.md
    │       └── shared -> ../../_shared/skills
    ├── codex  second opinion / 代替用（常設経路には入らない）
    │   ├── agents  カスタムエージェント定義（同上）
    │   │   ├── reviewer.toml     gpt-6-sol  別系列レビュー。Orchestrator が明示的に追加起動
    │   │   ├── researcher.toml   gpt-6-luna / Qwen は --oss（Claude 版の代替）
    │   │   └── implementer.toml  gpt-6-sol（Claude 版の代替）
    │   ├── mcp.example.toml  obsidian MCP の設定例（~/.codex/config.toml に追記）
    │   └── skills
    │       └── README.md
    └── cursor  Cursor を単体で使うときの設定（AI Development Team の経路には入らない）
        ├── mcp.json.example  obsidian MCP の設定例（~/.cursor/mcp.json）
        └── skills
            └── README.md
```

### AI Development Team の動かし方

1. Orca のターミナルで Claude Code を起動し、`oned-coordinate` スキルに ONED の JIRA チケット ID か要求を渡す（例: `DEV-1622 を着手して`）
2. スキルが `~/.agents/rules/orchestrator.md` を読み、`task.md` を Obsidian に作り、Orca orchestration で各役割を worker として順に起こす
3. 各 worker は Claude Code。Task spec で `~/.claude/agents/{role}.md` のサブエージェントに委譲し、成果物を Obsidian（`Works/{product}/tasks/{task_id}/`）に書く

セットアップは `scripts/agent-setup.sh`（skills のインストールと symlink）。Orca 側は `orca skills install --skill orca-cli --skill orchestration --agent claude-code` と Settings → Experimental の orchestration 有効化が別途必要。