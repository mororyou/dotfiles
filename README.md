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
    │       ├── README.md
    │       ├── coordinate  JIRA チケット起点で Coordinator として振る舞い、Orca で各役割を回す入口
    │       ├── obsidian
    │       └── artifact-copy
    ├── claude Claude 固有設定（常設の全役割はここ）
    │   ├── agents  サブエージェント定義（_shared/agents の本体を参照する薄いラッパー）
    │   │   ├── researcher.md   claude-sonnet-5   / read-only
    │   │   ├── architect.md    claude-fable-5-1  / read-only
    │   │   ├── implementer.md  claude-opus-5-5
    │   │   └── reviewer.md     claude-fable-5-1  / read-only（Implementer と別 tier）
    │   ├── mcp.json.example  obsidian MCP（Shared Memory）の設定例
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
    └── cursor
        ├── mcp.json.example  obsidian MCP の設定例（~/.cursor/mcp.json）
        └── skills
            └── README.md
```