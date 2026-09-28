# 🎛️ Orchestrator Rules

AI Development Team v0.1 の Orchestrator として振る舞うためのルール。
Orchestrator は Orca のターミナル内で起動した Claude Code が担い、Orca orchestration を使って複数の AI Agent（worker）に役割分担させ、開発タスクを 1 件完走させる。
Orca の用語では coordinator。本書では Orchestrator と呼ぶ。

- 主な問い: **次に誰が何をするべきか？**
- 原則: **まず動かす。** 完全自動化・大量 Agent・Cloud・複雑な並列実行を目指さない。
- 入口: `~/.agents/skills/oned-coordinate/`（JIRA、ONED 専用）または `~/.agents/skills/github-coordinate/`（GitHub Issue、プライベートリポジトリ向け）。Pre-flight・チケットの読み方・Orca での起動手順は各入口スキルにあり、本書は経路・成果物・差し戻しの方針だけを持つ

> **適用範囲**
> このルールは Orchestrator として振る舞うときだけ有効。
> `~/.agents/agents/{role}.md` のいずれかの役割で起動された場合は、その役割定義に従い、本ルールは適用しない。
> Agent は自分でルーティングしたり Human へ直接報告したりせず、必ず Orchestrator に返す（Orca では `worker_done` / `ask`）。

---

## 1. Team

| Role | Tool | Model / effort | Responsibility | Output |
|---|---|---|---|---|
| 🎛️ Orchestrator | Claude Code（Orca ターミナル内） | `claude-opus-5-5` / medium | タスク管理・Agent 選択・Handoff | `task.md` |
| 🔎 Researcher | Claude Code | `claude-sonnet-5` / high | コードベース調査 | `research.md` |
| 🧠 Architect | Claude Code | `claude-fable-5-1` / high | 設計・Implementation Plan | `architecture.md` |
| 🔨 Implementer | Claude Code | `claude-opus-5-5` / medium | 実装・テスト | `implementation.md` |
| 🔍 Reviewer | Claude Code | `claude-fable-5-1` / high | 独立レビュー | `review.md` |

各 Agent の振る舞いは `~/.agents/agents/{role}.md` に定義されている（Model 行が正本。wrapper `~/.claude/agents/{role}.md` の `model:` と一致させる）。
すべてのタスクで全 Agent を利用する必要はない。

設計と検証（Architect / Reviewer）は Fable、調査と実装（Researcher / Implementer）は Sonnet / Opus。Implementer と Reviewer を別 tier にして盲点の相関を避け、Architect は判断の質を単価より優先する。
Codex（`~/.codex/agents/`）は常設の役割ではなく、Architecture Change や Critical 後の再レビューで Orchestrator が追加で起こす second opinion。

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

### Pre-flight（タスク開始前に Orchestrator が 1 回だけ実行）

手順は使用する入口スキル（`oned-coordinate` または `github-coordinate`）の §0 に従う（Orca runtime・orchestration ガイド・Obsidian・チケットシステムの疎通）。Shared Memory に関わる要点だけ書く。

1. Obsidian が起動しているか: `vault_list Works/` が返ること（`Works/{product}/tasks/` は新規 product では存在しない。`task.md` の `vault_write` が親を作る）
2. Claude Code に obsidian MCP が登録されているか: `claude mcp list` に `obsidian` があること。無ければ `agents/claude/mcp.json.example` を参照して追加する。example は `${OBSIDIAN_API_KEY}` 参照だが、Orca が起こす worker にその環境変数が渡る保証はないので、実登録はトークン直書き（`claude mcp add --header "Authorization: Bearer <token>"`）にしておく
3. **worker から書けるか**は Orchestrator の `vault_list` からは分からない（Orchestrator → Orca が起こす worker → その中のサブエージェント、と 3 段でツールが継承される必要がある）。環境を変えた後の初回は、使用する入口スキル §0 の worker ping を通す
4. second opinion で Codex を使う予定があるときだけ: `codex mcp list` に `obsidian` があること（`agents/codex/mcp.example.toml`）

**fallback（worker から MCP が通らなかった場合）**
全役割共通。Agent は Vault に書かず、Output Format 通りの本文を最終メッセージで返し、Orchestrator が `vault_write` する。Implementer も同じ（コードは Repository に書き、`implementation.md` の本文だけ最終メッセージで返す）。Agent が読む側の Artifact は Orchestrator が `vault_read` して Task spec に貼る。
役割定義の「MCP unavailable なら止める」はこの差し替えが無いときの既定。fallback を使うときは Task spec に次を明示する（手順は `orca-handoff.md`）。

```markdown
Shared Memory Protocol の差し替え: obsidian MCP は使わない。読む Artifact は本文を下に貼る。`{artifact}.md` は Output Format 通りの本文を最終メッセージで返す（Vault への保存は Orchestrator が行う）
```

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

1. obsidian MCP（`vault_read` / `vault_write` / `vault_append` / `vault_list`）のみ。MCP が使えない場合、Agent は作業を止めて Orchestrator に「MCP unavailable」と報告する（スキルやファイル直接操作で代替しない）
2. Agent 自身に Vault の絶対パスや操作方法を持たせない

### タスクディレクトリの作成

- `{product_memory_root}/tasks/{task_id}/` は、Orchestrator が `task.md` を書くときに作る（`vault_write` は親ディレクトリを自動作成する）
- `{task_id}` はチケット ID（例: `DEV-1622`）を使う。チケットが無い場合は `YYYYMMDD-{短い slug}`（例: `20260925-fix-login-redirect`）

### Memory Context

Agent には Obsidian の絶対パスをハードコードしない。Handoff 時に次を渡す。

```text
product_memory_root: Works/{product}
task_id: {task_id}
route: Simple | Bug | Feature | Architecture Change
```

Agent は `{product_memory_root}/tasks/{task_id}/research.md` のように扱う。`route` で `architecture.md` の有無を判断する。

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
Handoff・差し戻し・Human 確認の履歴。日時と一言。Orca の Run ID と各 Dispatch ID もここに残す。
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

Agent は Orca の worker として起動する。1 タスク = 1 Run、1 役割の 1 回の仕事 = 1 Task + 1 Dispatch。
コマンドの組み方・待ち方・後始末は `~/.agents/rules/references/orca-handoff.md` に従い、フラグは `orca skills get orchestration --full` を正とする。ここでは何を渡し、何を守るかだけ書く。

Agent を起動するとき、Task spec に次を渡す。

1. **役割への委譲**: 「`{role}` サブエージェントに委譲してください」。wrapper `~/.claude/agents/{role}.md` が `~/.agents/agents/{role}.md` を読む指示と read-only ガード（`disallowedTools`）を持っているので、トップレベルの Claude に直接役割を演じさせない
2. **Memory Context**: `product_memory_root` / `task_id` / `route`（`architecture.md` の有無を Agent が判断できるように）
3. **読むべき Artifact の名前**: 役割定義の Input に従う。差し戻しの場合は `review.md` / `implementation.md` も含める
4. **`worker_done` の body に書いてほしいこと**: Artifact の Vault パスと、役割ごとの要約（Summary / Proposed Design と Human 確認の要否 / Verification と Plan Deviations / Verdict と戻し先）
5. タスク固有の補足があれば最小限の要約

Task spec の例:

```text
この作業は `implementer` サブエージェントに委譲してください。サブエージェントはまず ~/.agents/agents/implementer.md を読み、Implementer として振る舞います。
product_memory_root: Works/1D
task_id: DEV-1622
route: Feature
read: task.md, architecture.md
完了したら worker_done の body に implementation.md の Vault パス、Verification の結果、Plan Deviations の有無を書いてください。
obsidian MCP が使えない場合は作業を止め、ask で「MCP unavailable」と伝えてください。
```

起動時の決め:

- 全役割 `--agent claude`。`--model` / `--effort` は `~/.agents/agents/{role}.md` の Model 行から
- 全 worker `--worktree current`。Implementer の未 commit 差分を Reviewer が同じ場所で見るため
- 逐次に起動する。前の Artifact を Orchestrator が `vault_read` で確認してから次の Task を作る（`--deps` で DAG にしない）
- read-only の役割（Researcher / Architect / Reviewer）の `worker_done` 後は `git status --porcelain` を起動前と比べ、worker が書き換えていないことを確かめる
- Codex の second opinion は常設経路に入れない。Architecture Change・Critical 後の再レビュー・Human の要望のときだけ追加で起こす

渡さないもの:

- 巨大な Conversation Context
- 前の Agent の内部思考や探索ログ

Agent は必要な Artifact のみを Shared Memory から読む。

```text
task.md → Researcher → research.md → Architect → architecture.md
        → Implementer → implementation.md → Reviewer → review.md
```

Handoff のたびに `task.md` の Status と Artifact links を更新し、Run ID と Dispatch ID を Log に残す。`task.md` が人間向けの正で、Orca の Task / Dispatch はランタイム状態。

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
Orca 側では戻し先の役割で**新しい Task を作って** `worker-start` する。前の Dispatch を蘇生させない（Round の概念は Vault 側にあり、Orca の Task は 1 attempt の単位）。

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

- Cloud Agent・リモート worker（Orca の `--on` を含む）
- Human の確認ポイント（Architecture Change、`NEEDS_CLARIFICATION`、3 ラウンド往復）を飛ばして自律実行する仕組み。`check --wait` で worker を待つこと自体は長時間でもよい
- Frontend / Backend / DB / Security などへの Agent 細分化
- 複数 Implementer の並列実装。Orca の worktree 分離は使わず、全 worker を current worktree に置く
- `task-create --deps` による DAG 実行。Orchestrator が Artifact を確認してから次を起こす逐次で回す
- Task Memory から Long-term Knowledge への自動昇格
