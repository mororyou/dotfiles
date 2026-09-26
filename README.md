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
    │   ├── rules   常時適用するルール
    │   │   └── orchestrator.md
    │   ├── evals   スキルの評価ワークスペース（配下は省略）
    │   └── skills
    │       └── README.md
    ├── claude Claude 固有設定
    │   ├── agents  サブエージェント定義（_shared/agents の本体を参照する薄いラッパー）
    │   │   ├── architect.md   model: fable
    │   │   └── reviewer.md    model: fable
    │   ├── mcp.json.example  obsidian MCP（Shared Memory）の設定例
    │   └── skills
    │       ├── README.md
    │       └── shared -> ../../_shared/skills
    ├── codex
    │   ├── agents  カスタムエージェント定義（同上）
    │   │   ├── researcher.toml   gpt-6-luna / Qwen は --oss
    │   │   └── implementer.toml  gpt-6-sol
    │   ├── mcp.example.toml  obsidian MCP の設定例（~/.codex/config.toml に追記）
    │   └── skills
    │       └── README.md
    └── cursor
        ├── mcp.json.example  obsidian MCP の設定例（~/.cursor/mcp.json）
        └── skills
            └── README.md
```