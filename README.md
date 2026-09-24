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
    │   ├── evals
    │   └── skills
    │       └── README.md
    ├── claude Claude 固有設定
    │   ├── agents
    │   └── skills
    │       ├── README.md
    │       └── shared -> ../../_shared/skills
    ├── codex
    │   ├── agents
    │   └── skills
    │       └── README.md
    └── cursor
        ├── agents
        └── skills
            └── README.md
```