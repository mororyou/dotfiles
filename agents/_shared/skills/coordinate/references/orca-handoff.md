# Orca での Agent Handoff

`orchestrator.md` §7 は**何を渡し、何を守るか**（サブエージェントへの委譲・Memory Context・読む Artifact・
`worker_done` に書くこと・起動時の決め）を持つ。この文書はその実行手順で、**どう起動し、どう待ち、
どう後始末するか**を Orca のコマンド単位で書く。方針が食い違ったら §7 を正とする。

コマンドのフラグはこの文書ではなく `orca skills get orchestration --full` を正とする。Orca は版ごとに
コマンドが変わり、ここに写したものは古くなる。以下は「何をどの順で呼ぶか」の骨格。

## 方針

| 論点 | v0.1 での決め |
|---|---|
| Worktree | 全 worker を `--worktree current`。Implementer の未 commit 差分を Reviewer が同じ場所で見るため。並列実装はしない（`orchestrator.md` §11） |
| 監督モード | supervised（`task-create` → `worker-start` → `check --wait`）。差し戻しループがあるので full handoff にしない |
| Run | 1 タスク（`task_id`）につき 1 Run。Run の objective に `task_id` を入れる |
| Orca Task と `task.md` | `task.md` が人間向けの正。Orca の Task / Dispatch はランタイム状態。Run ID と各 Dispatch ID は `task.md` の Log に残す |
| Worker の後始末 | `worker_done` を処理したら `worker-release`。同じ役割に即座に次の Task があるときだけ `--terminal` で再利用 |

## 役割ごとの起動

全役割を Claude Code で起動する（`--agent claude`）。モデルと effort は `~/.agents/agents/{role}.md` の
Role セクション「Model」行を読んで `--model` / `--effort` に渡す。ここに書かない（役割定義が正本で、
モデルの入れ替えはそちらと wrapper の `model:` で行う）。

| Role | 起動の仕方 | read-only ガード |
|---|---|---|
| Researcher | Task spec で「`researcher` サブエージェントに委譲」と指示し、`~/.claude/agents/researcher.md` を経由させる | サブエージェントの `disallowedTools: Write, Edit` |
| Architect | 「`architect` サブエージェントに委譲」（`~/.claude/agents/architect.md`） | 同上 |
| Implementer | 「`implementer` サブエージェントに委譲」（`~/.claude/agents/implementer.md`） | なし（書く役） |
| Reviewer | 「`reviewer` サブエージェントに委譲」（`~/.claude/agents/reviewer.md`） | サブエージェントの `disallowedTools: Write, Edit` |

Orca は Claude を `--dangerously-skip-permissions` 付きで起動する（Settings → Agents → Agent Permissions の既定）。
トップレベルの Claude に直接役割を演じさせると上のガードが効かないので、**wrapper（サブエージェント）を必ず経由させる。**

`--effort` はトップレベルの Claude に効く。サブエージェントに継承されるかは未確認なので、最初の 1 タスクで
`worker-start` の receipt（`launch.effective`）と worker の挙動を見て確かめ、継承されなければ Task spec に
「effort {level} で」と一言足す。

### Codex を second opinion に使うとき

Codex（`~/.codex/agents/reviewer` 相当のカスタムエージェント）は常設の経路には入れない。Implementer と Reviewer が
同じ Claude 系列になったので、**盲点の相関が特に怖いとき**だけ Coordinator が追加で起こす。

- 使う条件の目安: Architecture Change 経路、Reviewer が `Critical` を出した後の再レビュー、Human が「別の目で見てほしい」と言ったとき
- 起動: `task-create` で Reviewer と同じ spec（`read: implementation.md, review.md`）を作り、`worker-start --agent codex --model gpt-6-sol` で
  「`reviewer` エージェントとして」と名指しする。Codex は `--dangerously-bypass-approvals-and-sandbox` 付きで起動されるので、
  完了後の `git status --porcelain` 比較を必ず行う
- 出力は `review.md` に `## Round {n} (second opinion: Codex)` として追記させ、Verdict は Claude Reviewer のものを正とする。
  Codex の Findings は Coordinator が読んで、Claude Reviewer の次ラウンドに「確認してほしい点」として渡す
- Orca に Codex 用の hook（`~/.orca/agent-hooks/codex-hook.sh`）は入っているので、追加設定なしで `worker_done` は届く

### 決定論的な追加ガード

read-only の役割（Researcher / Architect / Reviewer）の `worker_done` を受けたら、次へ進む前に

```bash
git status --porcelain
```

を Implementer 起動前の状態と比べる。差分が増えていたら worker が書き換えたということなので、
Artifact を信用する前に何が変わったかを確認し、`task.md` の Log に残す。安いチェックで、
「Reviewer が実装を直してしまい Verdict が自己承認になる」事故を防げる。

## Task spec のテンプレート

Orca は Task spec の前に自分の preamble（`worker_done` / `ask` / `heartbeat` の指示）を注入する。
spec 側は役割と Memory Context に絞り、Orca の指示と競合する「Orchestrator に報告せよ」とは書かない。
`worker_done` の body に何を入れてほしいかだけ書く。

```text
この作業は `{role}` サブエージェントに委譲してください。サブエージェントはまず ~/.agents/agents/{role}.md を読み、{Role} として振る舞います。

product_memory_root: Works/{product}
task_id: {task_id}
route: {Simple | Bug | Feature | Architecture Change}
read: {task.md, requirements.md, ...}

サブエージェントの最終メッセージを受け取ったら、その内容を worker_done の body に転記してください:
- {artifact}.md の Vault パス
- {Researcher: Summary / Architect: Proposed Design の要約と Human 確認の要否 / Implementer: Verification の結果と Plan Deviations の有無 / Reviewer: Verdict と戻し先}
サブエージェントが「MCP unavailable」「Plan に問題がある」「Human 確認が必要」などブロッキングな報告を返したら、worker_done ではなく ask で伝えてください。
Implementer が検証失敗を報告したら worker_done は --outcome failed にしてください。Reviewer の CHANGES_REQUESTED は成功です。
```

`worker_done` / `ask` を送るのはトップレベルの Claude（Orca の preamble を受けた worker 本体）で、サブエージェントは最終メッセージで返すだけ。
役割定義の Shared Memory Protocol にもその旨を書いてあるので、spec 側はトップレベル向けの転記指示だけでよい。

差し戻しのときは `read:` に `review.md`（Implementer へ）または `review.md, implementation.md`（Architect へ）を足し、
「Round {n} を末尾に追記する」ことを一言添える（上書き禁止は役割定義にあるが、念押しが安い）。

### fallback 版（worker から obsidian MCP が通らないとき）

最初の worker が「MCP unavailable」を `ask` で返してきたら、その Run の残りは全役割をこの形にする。
途中で混ぜない（Reviewer だけ MCP、のような状態は `task.md` の Artifact links が嘘になる）。

```text
この作業は `{role}` サブエージェントに委譲してください。サブエージェントはまず ~/.agents/agents/{role}.md を読み、{Role} として振る舞います。

Shared Memory Protocol の差し替え: obsidian MCP は使わない。読む Artifact は下に貼ってある。`{artifact}.md` は Output Format 通りの本文を最終メッセージで返す（Vault への保存は Orchestrator が行う）。

product_memory_root: Works/{product}
task_id: {task_id}
route: {...}

--- task.md ---
{Orchestrator が vault_read した本文}
--- {前の artifact}.md ---
{同上}

サブエージェントの最終メッセージ（{artifact}.md の本文全体）を、そのまま worker_done の body に入れてください。要約しないでください。
Implementer が検証失敗を報告したら --outcome failed にしてください。
```

`worker_done` を受けたら Orchestrator が `vault_write` し、`task.md` の Log に「fallback: Orchestrator が保存」と残す。
本文が長くて `worker_done` の body に収まらないときは、worker に `{task_id}-{artifact}.md` を Repository 外（`/tmp`）に書かせてパスを返させる。
Repository に置かない（Reviewer の `git status` 比較に混ざる）。

## 1 タスクの流れ

`--model` / `--effort` の値は例（2026-09 時点の役割定義）。実際は各 `~/.agents/agents/{role}.md` の Model 行を読んで埋める。

```text
run-create --objective "{task_id}: {Goal 1 行}"
  │
  ├─ task-create --spec "{Researcher の spec}"
  │  worker-start --task <t1> --worktree current --agent claude --model claude-sonnet-5 --effort high
  │  check --wait --types worker_done,escalation,question
  │    → research.md を vault_read で確認、task.md 更新、worker-release
  │
  ├─ task-create --spec "{Architect の spec}"      （Feature / Architecture Change）
  │  worker-start --task <t2> --worktree current --agent claude --model claude-fable-5-1 --effort high
  │  check --wait ...
  │    → architecture.md 確認。Architecture Change なら Human 確認（task.md Status: Awaiting Human）
  │
  ├─ task-create --spec "{Implementer の spec}"
  │  worker-start --task <t3> --worktree current --agent claude --model claude-opus-5-5
  │  check --wait ...
  │    → implementation.md 確認（Test / Typecheck / Lint / Build が記録されているか）
  │
  └─ task-create --spec "{Reviewer の spec}"
     worker-start --task <t4> --worktree current --agent claude --model claude-fable-5-1 --effort high
     check --wait ...
       → review.md の Verdict で分岐（orchestrator.md §8）
```

`task-create --deps` で DAG にすることもできるが、v0.1 では Coordinator が Artifact を確認してから
次を作る**逐次**にする。前の Artifact を読まずに次の worker が走り出すのを避けるため。

## 待ち方

- `check --wait --timeout-ms 900000` を回す。タイムアウトや `{count:0}` は**チェックポイント**で、失敗ではない。
  Implementer は 15〜60 分かかるのが普通
- `question` が来たら `reply` で答える。Human の判断が要る内容なら `task.md` を `Awaiting Human` にしてユーザーに聞き、
  答えを得てから `reply` する
- `escalation` が来たら worker を止めず、内容を読んでから判断する（役割定義の「Orchestrator に戻す」に相当）
- worker が生きているのに完了しない、を理由に `worker-stop` しない。`worker-show` / `worker-read` で状況を見る

## worker_done を受けたら

1. Artifact を `vault_read` して、Output Format どおりか・最新ラウンドが追記されているかを自分の目で確認する。
   `worker_done` の body だけで判断しない（`orchestrator.md` §6 Source of Truth: Repository > ... > Task Memory）
2. `--outcome failed` なら理由を読み、再実行か経路変更か Human かを決める。同じ Task を無条件にリトライしない
3. `task.md` の Status / Workflow / Artifact links / Log を `vault_write`（または `vault_append`）で更新する
4. `worker-release --dispatch <id>`（即座に同じ役割へ次を渡すときだけ `--terminal` で再利用）
5. `check --ack <delivery_id>` で Delivery を確定してから次の Task を作る

## 差し戻しの実装

`orchestrator.md` §8 の表に従い、戻し先の役割で**新しい Task を作って** `worker-start` する。
前の Dispatch を蘇生させない（Orca の Task は 1 attempt = 1 Dispatch の単位で、Round の概念は Vault 側にある）。

- Finding ID の往復回数は `review.md` の Round ごとの Findings 表で数える。Orca 側では数えない
- 3 ラウンド目にも同じ ID が残ったら、次の worker を作らず `task.md` を `Blocked` にして Human へ
- Architecture Change に上がったら、Implementer を起動する前に `task.md` を `Awaiting Human` にして止まる。
  Orca の `gate-create` は使っても使わなくてもよいが、Human への実際の問いかけはこのセッションで行う

## 終わったら

- 残っている worker を `worker-release` する（`task-list --json` で `dispatched` が無いことを確認）
- `task.md` を `Done`、Run ID と全 Dispatch ID を Log に残す
- Human に報告（`orchestrator.md` §10）。JIRA への書き戻しは聞いてから
