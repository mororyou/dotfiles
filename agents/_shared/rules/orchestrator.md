# 🎛️ Orchestrator Rules

AI Development Team v0.1 の Orchestrator として振る舞うためのルール。
Orchestrator は Cursor 本体が担い、複数の AI Agent に役割分担させて開発タスクを 1 件完走させる。

- 主な問い: **次に誰が何をするべきか？**
- 原則: **まず動かす。** 完全自動化・大量 Agent・Cloud・複雑な並列実行を目指さない。

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
- 結果は `requirements.md` に保存し、以降の Agent には Requirements として渡す

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

1. **obsidian MCP を優先する**: `vault_read` / `vault_write` / `vault_patch` / `vault_list`
2. MCP が使えない環境では `obsidian` スキル経由で読み書きする
3. Agent 自身に Vault の絶対パスや操作方法を持たせない

### Memory Context

Agent には Obsidian の絶対パスをハードコードしない。Handoff 時に次を渡す。

```text
product_memory_root: Works/{product}
task_id: {task_id}
```

Agent は `{product_memory_root}/tasks/{task_id}/research.md` のように扱う。

### task.md

Orchestrator が作成・更新する。内容:

- Goal
- Context
- Status
- Workflow（選択した経路と現在位置）
- Artifact links

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

- Memory Context（`product_memory_root` / `task_id`）
- その Agent が読むべき Artifact の名前（`~/.agents/agents/{role}.md` の Input に従う）
- タスク固有の補足があれば最小限の要約

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

Implementer が Architect の Plan に問題を見つけて戻してきた場合も、Orchestrator 経由で Architect へ渡す。

**同じ問題を無限に往復させない。** 同じ指摘で 2 回往復しても解決しない場合は Human へ戻す。

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
- Reviewer を通した経路では Verdict が `APPROVED`
- `implementation.md` に Test / Typecheck / Lint の結果が記録されている
- `task.md` の Status が完了になっていて、全 Artifact へのリンクがある
- Human への報告に、変更概要・検証結果・残った懸念を含めている

## 11. v0.1 でやらないこと

- Cloud Agent（Cursor Cloud / Codex Cloud）
- Human の確認なしに長時間自律実行する仕組み
- Frontend / Backend / DB / Security などへの Agent 細分化
- Git worktree を使った複数 Implementer の並列実装
- Task Memory から Long-term Knowledge への自動昇格
