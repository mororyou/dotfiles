# artifact-copy ベンチマーク (iteration-1)

> **注意: `without_skill` アームは汚染されており、比較には使えない。**
> スキルはグローバル登録済みでベースライン側のスキル一覧にも載り、さらに期待値ファイルが
> エージェントから読める場所にあった。信頼できるのは `with_skill` の合否のみ。
> 詳細と対策はワークスペースの README.md に記載。

## サマリ

| 指標 | with_skill | without_skill (汚染) |
|---|---|---|
| 合格率 | 100.0% (14/14) | 100.0% (14/14) |
| 所要時間 | 82.3s ± 8.4 | 107.0s ± 18.1 |
| トークン | 45342 ± 2430 | 43968 ± 1708 |

## eval 別

| eval | with_skill | without_skill (汚染) |
|---|---|---|
| eval-0-slogan-title-to-searchable-filename | 5/5 (70s) | 5/5 (130s) |
| eval-1-multi-file-artifact | 5/5 (88s) | 5/5 (104s) |
| eval-2-update-preserves-user-filename | 4/4 (89s) | 4/4 (86s) |
