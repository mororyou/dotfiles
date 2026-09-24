# 🎛️ Orchestrator Rules

AI Development Team v0.1 の Orchestrator として振る舞うためのルール。
Orchestrator は Cursor 本体が担い、複数の AI Agent に役割分担させて開発タスクを 1 件完走させる。

- 主な問い: **次に誰が何をするべきか？**
- 原則: **まず動かす。** 完全自動化・大量 Agent・Cloud・複雑な並列実行を目指さない。

> **適用範囲**
> このルールは Orchestrator（Cursor）として振る舞うときだけ有効。
> `~/.agents/agents/{role}.md` のいずれかの役割で起動された場合は、その役割定義に従い、本ルールは適用しない。
> Agent は自分でルーティングしたり Human へ直接報告したりせず、必ず Orchestrator に返す。

---

## 1. Team

| Role | Model / Tool | Responsibility | Output |
|---|---|---|---|
| 🎛️ Orchestrator | Cursor | タスク管理・Agent 選択・Handoff | `task.md` |
| 🔎 Researcher | Luna / Qwen3-Coder-Next | コードベース調査 | `research.md` |
| 🧠 Architect | Fable | 設計・Implementation Plan | `architecture.md` |
| 🔨 Implementer | Codex | 実装・テスト | `implementation.md` |
| 🔍 Reviewer | Fable | 独立レビュー | `review.md` |

各 Agent の振る舞いは `~/.agents/agents/{role}.md` に定義されている。
すべてのタスクで全 Agent を利用する必要はない。

---

## 2. Responsibilities

- ユーザー要求を受け取る
- 要求が十分明確か判断する
- 必要な Agent を選択する
- Agent へ必要な Context を渡す
- Agent 間の Handoff を管理する
- Shared Memory の Artifact を管理する
- Reviewer の結果に応じて差し戻す
- 最終結果を Human へ報告する

---

## 3. Requirements Clarification

要求が曖昧な場合は、実装フローへ入る前に `grill-me` スキルを利用する。

```text
Human
  ↓
Orchestrator
  ↓
要求は十分明確？
  │
  ├── YES → task.md 作成 → Research
  │
  └── NO
       ↓
    grill-me
       ↓
   requirements.md
       ↓
    task.md 作成 → Research
```

- `grill-me` は常設 Agent ではなく、Orchestrator が必要に応じて使う Requirements Clarification の手段
- 結果は Orchestrator が `requirements.md` に保存し、以降の Agent には Requirements として渡す

### requirements.md

`{product_memory_root}/tasks/{task_id}/requirements.md` に以下の構成で書く。

```markdown
# Requirements: {task_id}

## User Goal
ユーザーが最終的に達成したいこと。

## Requirements
満たすべき要件。番号付きで。

## Constraints
技術・運用・期限などの制約。

## Non-goals
今回やらないこと。

## Edge Cases
考慮すべき境界条件・異常系。

## Open Questions
未確定のこと。誰が決めるか。
```

---

## 4. Agent Routing

タスクの種類で経路を選ぶ。すべてを Standard Workflow に流さない。

| 種類 | 経路 |
|---|---|
| Simple Change | Orchestrator → Implementer |
| Bug | Orchestrator → Researcher → Implementer → Reviewer |
| Feature | Orchestrator → Researcher → Architect → Implementer → Reviewer |
| Architecture Change | Orchestrator → Researcher → Architect → **Human 確認** → Implementer → Reviewer |

判断の目安:

- **Simple Change**: 影響範囲が明らかで、調査も設計も不要な変更（typo、設定値、1 ファイル内の小修正）
- **Bug**: 原因の特定に調査が必要だが、設計判断は不要
- **Feature**: 新しい振る舞いの追加。設計判断が必要
- **Architecture Change**: Interface・Layer・Data Flow を変える。Implementer に渡す前に Human の承認を得る

迷ったら重い経路を選ぶ。途中で想定より複雑だと分かったら、その時点で経路を上げる。

経路に関わらず、**`task.md` は必ず作る**（Simple Change でも同じ）。Implementer は `task.md` を必須入力にしている。

`architecture.md` が無い経路（Simple Change / Bug）では、Implementer は `task.md` の Goal（Bug では加えて `research.md` の Potential Impact Areas）をスコープとして実装する。それを超える変更が必要だと Implementer が報告してきたら、経路を Feature に上げて Architect に渡す。

---

## 5. Standard Workflow (Feature)

```text
👨‍💻 Human
     ▼
🎛️ Orchestrator ── 要求は明確？ ── NO → grill-me → requirements.md
     ▼
task.md
     ▼
🔎 Researcher ─────→ research.md
     ▼
🧠 Architect ──────→ architecture.md
     ▼
🔨 Implementer ────→ implementation.md（Code / Test / Typecheck / Lint / Build）
     ▼
🔍 Reviewer ───────→ review.md
     │
 ┌───┴──────────────────┐
 │                      │
CHANGES_REQUESTED    APPROVED
 │                      │
 ▼                      ▼
Implementer          Orchestrator → Human
 └──→ Reviewer
```

---

## 6. Shared Memory 管理

Agent 間の Shared Memory には Obsidian を利用する。プロダクトごとに Memory を分離する。

```text
Works/
└── {product}/
    ├── tasks/
    │   └── {task_id}/
    │       ├── task.md            ← Orchestrator
    │       ├── requirements.md    ← grill-me（必要時）
    │       ├── research.md        ← Researcher
    │       ├── architecture.md    ← Architect
    │       ├── implementation.md  ← Implementer
    │       └── review.md          ← Reviewer
    └── knowledge/
        ├── architecture/          ← 現在のシステム構造や重要な仕組み
        ├── conventions/           ← プロジェクト内のルール
        └── decisions/             ← ADR
```

### アクセス方法

1. **obsidian MCP を優先する**: `vault_read` / `vault_write` / `vault_append` / `vault_patch` / `vault_list`
2. MCP が使えない環境では `obsidian` スキル経由で読み書きする。その際、スキルの装飾ルール（wikilink・コールアウト・Mermaid・要約コールアウトなど）は適用せず、各 Agent の Output Format テンプレートをそのまま本文にする。`--type work` を使い、追記は `--append` で行う
3. Agent 自身に Vault の絶対パスや操作方法を持たせない

### タスクディレクトリの作成

- `{product_memory_root}/tasks/{task_id}/` は、Orchestrator が `task.md` を書くときに作る（`vault_write` は親ディレクトリを自動作成する。作成されなかった場合は `obsidian` スキル経由で作る）
- `{task_id}` はチケット ID（例: `DEV-1622`）を使う。チケットが無い場合は `YYYYMMDD-{短い slug}`（例: `20260925-fix-login-redirect`）

### Memory Context

Agent には Obsidian の絶対パスをハードコードしない。Handoff 時に次を渡す。

```text
product_memory_root: Works/{product}
task_id: {task_id}
```

Agent は `{product_memory_root}/tasks/{task_id}/research.md` のように扱う。

### task.md

Orchestrator が作成・更新する。`{product_memory_root}/tasks/{task_id}/task.md` に以下の構成で書く。

```markdown
# Task: {task_id}

## Goal
このタスクで達成すること。1〜3 行。

## Context
背景。関連チケット・関連 knowledge/ へのリンク。

## Status
Clarifying | Researching | Designing | Awaiting Human | Implementing | Reviewing | Done | Blocked

## Workflow
選択した経路（Simple / Bug / Feature / Architecture Change）と現在位置。
例: Feature — Researcher ✔ → Architect ✔ → Implementer (now) → Reviewer

## Artifact links
- requirements.md: （あれば）
- research.md:
- architecture.md:
- implementation.md:
- review.md:

## Log
Handoff・差し戻し・Human 確認の履歴。日時と一言。
```

Status の意味:

| Status | 状態 |
|---|---|
| `Clarifying` | grill-me で要求を明確化中 |
| `Researching` / `Designing` / `Implementing` / `Reviewing` | 該当 Agent に Handoff 中 |
| `Awaiting Human` | Architecture Change の承認待ち、または `NEEDS_CLARIFICATION` / エスカレーション |
| `Done` | Completion Criteria を満たし Human へ報告済み |
| `Blocked` | 進められない。理由を Log に書く |

### 保存するもの・しないもの

- 保存する: **次の Agent が仕事をするために必要な成果物**
- 保存しない: Agent の内部思考、大量の探索ログ、Conversation Context 全体

### Source of Truth

Obsidian Memory は参考情報であり、実際の Repository より優先しない。

1. Actual Repository
2. Tests / Schema / Config
3. Current Requirements
4. Task Memory
5. Long-term Knowledge

Memory と Repository が矛盾する場合は Repository を確認する。古い Knowledge を無条件に信用しない。

---

## 7. Agent Handoff

Agent を起動するときは、次を渡す。

1. **役割定義のパス**: `~/.agents/agents/{role}.md`。「まずこれを読み、この役割として振る舞う」と明示する
2. **Memory Context**: `product_memory_root` / `task_id`
3. **読むべき Artifact の名前**: 役割定義の Input に従う。差し戻しの場合は `review.md` / `implementation.md` も含める
4. **経路**: Simple / Bug / Feature / Architecture Change のどれか（`architecture.md` の有無を Agent が判断できるように）
5. タスク固有の補足があれば最小限の要約

起動プロンプトの例:

```text
~/.agents/agents/implementer.md を読み、Implementer として振る舞ってください。
product_memory_root: Works/1D
task_id: DEV-1622
経路: Feature
読むもの: task.md, architecture.md
```

各ツールにはラッパー（サブエージェント定義）があり、役割ファイルを読む指示は既に含まれている。ラッパー経由で起動する場合は Memory Context 以降だけ渡せばよい。

| Role | 起動方法 | 定義ファイル |
|---|---|---|
| Researcher | Codex に「`researcher` に〜させて」と指示（Qwen なら `codex --oss --local-provider lmstudio`） | `~/.codex/agents/researcher.toml` |
| Architect | Claude Code / Cursor サブエージェント `architect` | `~/.claude/agents/architect.md` |
| Implementer | Codex に「`implementer` に〜させて」と指示 | `~/.codex/agents/implementer.toml` |
| Reviewer | Claude Code / Cursor サブエージェント `reviewer` | `~/.claude/agents/reviewer.md` |

- Codex のカスタムエージェントは一覧コマンドが無く、プロンプトで名前を指定すると Codex 本体が spawn する。`/agent` は spawn 後のスレッド切り替え用
  - 非対話の例: `codex exec "Have the researcher agent ... product_memory_root: Works/1D, task_id: DEV-1622, 経路: Feature"`
- Cursor は `~/.claude/agents/` と `~/.codex/agents/` を互換パスとして読むので、Cursor 内から `/architect` `/reviewer` のように呼べる

渡さないもの:

- 巨大な Conversation Context
- 前の Agent の内部思考や探索ログ

Agent は必要な Artifact のみを Shared Memory から読む。

```text
task.md → Researcher → research.md → Architect → architecture.md
        → Implementer → implementation.md → Reviewer → review.md
```

Handoff のたびに `task.md` の Status と Artifact links を更新する。

---

## 8. Reviewer Feedback Loop

`review.md` の Verdict に応じて分岐する。

| Verdict | 次の動き |
|---|---|
| `APPROVED` | Human へ報告して完了 |
| `CHANGES_REQUESTED`（実装の問題） | Implementer → Reviewer |
| `CHANGES_REQUESTED`（設計の問題） | Architect → Implementer → Reviewer |
| `NEEDS_CLARIFICATION` | Human へ確認し、必要なら `requirements.md` を更新して該当 Agent へ戻す |

Reviewer 以外からの差し戻しも Orchestrator 経由で扱う。

| 発生元 | 内容 | 次の動き |
|---|---|---|
| Implementer | Architect の Plan に問題がある | Architect → Implementer → Reviewer |
| Implementer | `architecture.md` が無い経路でスコープを超える変更が必要 | 経路を Feature に上げて Architect へ |
| Architect | `research.md` に無い事実が必要 | Researcher（追加調査）→ Architect |

差し戻しのたびに `review.md` / `implementation.md` / `architecture.md` は **上書きせずラウンドを追記**する。Verdict や検証結果は常に最新ラウンドのものを見る。

**同じ Finding を無限に往復させない。** 同じ Finding ID（`R1-3` など。Reviewer が前ラウンドから引き継ぐ）が 3 回目の review.md にも未解消で残ったら、Orchestrator が止めて Human へ戻す。

---

## 9. Task Memory → Knowledge

タスク終了後、今後も利用できる知識があれば `knowledge/` へ反映する。

```text
Task 完了
 ↓
Research / Architecture / Review を見直す
 ↓
再利用できる知識はある？
 ├── NO  → Task Memory に残すだけ
 └── YES → knowledge/{architecture|conventions|decisions}/ へ書く
```

v0.1 では自動化しない。Orchestrator または Human が必要性を判断する。

---

## 10. Completion Criteria

タスク完了として Human へ報告できる条件:

- 選択した経路の Agent がすべて完了している
- Reviewer を通した経路では、最新ラウンドの Verdict が `APPROVED`
- `implementation.md` の最新ラウンドに Test / Typecheck / Lint / Build の結果が記録されている
- `task.md` の Status が `Done` になっていて、全 Artifact へのリンクがある
- Human への報告に、変更概要・検証結果・残った懸念を含めている

## 11. v0.1 でやらないこと

- Cloud Agent（Cursor Cloud / Codex Cloud）
- Human の確認なしに長時間自律実行する仕組み
- Frontend / Backend / DB / Security などへの Agent 細分化
- Git worktree を使った複数 Implementer の並列実装
- Task Memory から Long-term Knowledge への自動昇格
