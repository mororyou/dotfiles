---
title: React Server Components と Client Components の使い分け
created: 2026-09-19
updated: 2026-09-19
type: tech-note
status: evergreen
tags:
  - react
  - react-server-components
  - nextjs
  - frontend
  - architecture
aliases:
  - RSC と Client Components
  - use client の判断基準
---

# React Server Components と Client Components の使い分け

> [!summary] 要点
> - **デフォルトは Server Component**。`'use client'` は「ブラウザでしか出来ないこと」が必要になった箇所に、できるだけ**末端（葉）に近い位置**で付ける。
> - `'use client'` は「クライアントでのみ動く」宣言ではなく、**サーバー/クライアント境界の宣言**。その先の import はすべてクライアントバンドルに入る。
> - データ取得は**サーバー側で、必要なコンポーネントの中で直接**行い、結果を props で下に流す。クライアント側の取得は「ユーザー操作起点・リアルタイム・ブラウザ固有」に限定する。
> - Server Component は Client Component の **children / props として渡せる**（合成パターン）。これを知っていると境界を上に押し上げずに済む。

---

## 1. 前提：2 種類のコンポーネントは何が違うのか

| 観点 | Server Component (RSC) | Client Component |
| --- | --- | --- |
| 実行場所 | サーバー（ビルド時 or リクエスト時）のみ | サーバー（SSR/プリレンダー）**と**ブラウザの両方 |
| JS バンドル | クライアントに**送られない** | クライアントに送られ、ハイドレーションされる |
| state / effect | 使えない（`useState` / `useEffect` 不可） | 使える |
| イベントハンドラ | 付けられない（`onClick` 等は不可） | 付けられる |
| ブラウザ API | 使えない（`window`, `localStorage`…） | 使える（`useEffect` 内など） |
| データ取得 | `async/await` で直接 fetch、DB アクセス可 | fetch はできるが DB 直アクセスは不可 |
| 秘匿情報 | 環境変数・API キーを安全に扱える | 送られたものは全てユーザーに見える |
| 再レンダリング | クライアント state 変化では再実行されない（再取得はナビゲーションや `router.refresh`） | state / props 変化で再レンダリング |
| Context | Provider を置くことはできない（消費も不可） | Provider / `useContext` が使える |

> [!note] 「Server Component」と「SSR」は別物
> SSR は「Client Component の初期 HTML をサーバーで生成する」仕組み。Client Component も SSR される。
> RSC は「そのコンポーネントの JS 自体をクライアントに送らない」仕組み。両者は組み合わせて使われる。

---

## 2. 境界の置き方（Boundary Design）

### 2.1 基本原則：「葉に向かって」境界を押し下げる

```
❌ 悪い例: ページ全体を 'use client' にする
app/products/page.tsx  ('use client')
  └─ ProductList
       └─ ProductCard
            └─ AddToCartButton   ← 本当に interactivity が必要なのはここだけ

✅ 良い例: 末端だけ Client にする
app/products/page.tsx  (Server: DB から products を取得)
  └─ ProductList        (Server)
       └─ ProductCard   (Server)
            └─ AddToCartButton  ('use client')
```

- `'use client'` を付けたファイルから import されるモジュールは、**すべてクライアントバンドルに含まれる**（推移的）。上に置くほど巻き込みが増える。
- 判断基準は「**そのサブツリーの中で、ブラウザでしか出来ないことをしている最上位のノードはどこか**」。そこが境界。

### 2.2 合成パターン：Server Component を Client Component に渡す

Client Component の**中に** Server Component を置きたいとき、import はできないが **props（特に `children`）経由なら渡せる**。

```tsx
// components/Tabs.tsx  ← Client
'use client';
import { useState } from 'react';

export function Tabs({ tabs }: { tabs: { label: string; content: React.ReactNode }[] }) {
  const [active, setActive] = useState(0);
  return (
    <div>
      {tabs.map((t, i) => (
        <button key={t.label} onClick={() => setActive(i)}>{t.label}</button>
      ))}
      {tabs[active].content}   {/* ← ここに Server Component がそのまま入る */}
    </div>
  );
}
```

```tsx
// app/dashboard/page.tsx  ← Server
import { Tabs } from '@/components/Tabs';
import { SalesReport } from './SalesReport';     // async Server Component
import { InventoryReport } from './InventoryReport';

export default function Page() {
  return (
    <Tabs
      tabs={[
        { label: '売上', content: <SalesReport /> },
        { label: '在庫', content: <InventoryReport /> },
      ]}
    />
  );
}
```

> [!tip] 「穴を開ける」イメージ
> Client Component は「サーバーが描いたものを差し込むスロット」を持てる。Client Component の中で Server Component を **import して使う**ことはできないが、**上（Server）から作って渡す**ことはできる。この違いを覚えると境界設計が楽になる。

### 2.3 Provider の置き方

Context Provider は Client Component でしか作れないが、`children` を受け取る薄いラッパーにすれば、その下のツリーは Server のままにできる。

```tsx
// app/providers.tsx
'use client';
import { ThemeProvider } from 'next-themes';

export function Providers({ children }: { children: React.ReactNode }) {
  return <ThemeProvider>{children}</ThemeProvider>;
}
```

```tsx
// app/layout.tsx  ← Server のまま
import { Providers } from './providers';

export default function RootLayout({ children }) {
  return (
    <html><body>
      <Providers>{children}</Providers>   {/* children は Server Component */}
    </body></html>
  );
}
```

### 2.4 サードパーティライブラリの扱い

- `useState` 等を使っているのに `'use client'` を宣言していないライブラリ（RSC 対応前のもの）は、Server Component から直接 import するとエラーになる。
- 対処：**自分のプロジェクト側で Client Component としてラップして再 export** する。

```tsx
// components/Carousel.tsx
'use client';
export { Carousel } from 'some-carousel-lib';
```

### 2.5 サーバー専用コードを守る

「サーバーで動くことを前提にしたモジュール」が誤って Client 側に import されると、シークレット漏洩やビルドエラーになる。

- `server-only` パッケージを import しておくと、Client 側から import された時点で**ビルドエラー**になる（逆は `client-only`）。

```ts
// lib/db.ts
import 'server-only';
export async function getUser(id: string) { /* DB アクセス */ }
```

---

## 3. データ取得

### 3.1 原則：「使う場所で、サーバーで取る」

```tsx
// app/users/[id]/page.tsx  ← Server Component
export default async function UserPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const user = await db.user.findUnique({ where: { id } });   // 直接 DB でも fetch でも OK
  return <UserProfile user={user} />;
}
```

- **Prop drilling を避けるために親でまとめて取る必要はない**。各 Server Component が自分の必要なデータを取ればいい。
- 同じ URL への `fetch` は React が**リクエスト単位でメモ化**するので、複数箇所で同じデータを取っても実際のリクエストは 1 回になる（DB 直アクセスなら `React.cache` でメモ化）。
- waterfall を避けたい場合は `Promise.all` で並列化するか、コンポーネントを分けて `<Suspense>` で囲む（**ストリーミング**）。

```tsx
// 並列取得 + Suspense で段階的に表示
export default function Page() {
  return (
    <>
      <Header />                              {/* すぐ表示 */}
      <Suspense fallback={<Skeleton />}>
        <SlowRecommendations />               {/* 遅い部分は後から流れてくる */}
      </Suspense>
    </>
  );
}
```

### 3.2 Server → Client へのデータの渡し方

- Server Component から Client Component に渡す props は**シリアライズ可能**でなければならない（関数・クラスインスタンス・`Date` 以外の複雑なオブジェクトは不可。`Date`, `Map`, `Set`, `Promise` などは RSC 側でサポート）。
- **Promise を渡して Client 側で `use()` する**パターンも使える。サーバーで await せずストリーミングできる。

```tsx
// Server
export default function Page() {
  const commentsPromise = fetchComments();   // await しない
  return (
    <Suspense fallback={<Spinner />}>
      <Comments commentsPromise={commentsPromise} />
    </Suspense>
  );
}

// Client
'use client';
import { use } from 'react';
export function Comments({ commentsPromise }) {
  const comments = use(commentsPromise);   // 解決するまで Suspense
  return <ul>{comments.map(c => <li key={c.id}>{c.body}</li>)}</ul>;
}
```

### 3.3 クライアント側でデータを取るべきケース

| ケース | 理由 | 手段の例 |
| --- | --- | --- |
| ユーザー操作起点の取得（検索入力、無限スクロール、フィルタ） | 操作するたびにサーバーラウンドトリップを起こしたくない / 部分更新したい | SWR, TanStack Query, Server Action + `useTransition` |
| リアルタイム・ポーリング | サーバーレンダリングは「その瞬間」の断面しか描けない | WebSocket, SWR の `refreshInterval` |
| ブラウザ固有情報に依存（位置情報、`localStorage` の設定値） | サーバーからは読めない | `useEffect` で取得 |
| 認可がクライアント側の状態に依存する（ログイン後にだけ表示） | Server で扱えない場合のみ。可能なら cookie を見て Server で判定する | |

> [!warning] Client Component で「初期表示のためのデータ」を `useEffect` + `fetch` するのは基本アンチパターン
> ローディングスピナー → 取得 → 表示 という **クライアントサイド waterfall** を招く。初期表示に必要なデータは Server Component で取り、props（or Promise）で渡す。

### 3.4 ミューテーション（更新系）

- フォーム送信・更新は **Server Actions（`'use server'`）** を第一候補にする。Client Component からも呼べる。
- 更新後は `revalidatePath` / `revalidateTag`（Next.js）などで Server Component 側のキャッシュを無効化し、再レンダリングさせる。
- 楽観的更新が必要なら `useOptimistic`、送信中の状態は `useFormStatus` / `useActionState`。

---

## 4. `'use client'` を付ける判断基準

### 4.1 チェックリスト

次のうち **1 つでも該当すれば** そのコンポーネント（またはその末端）は Client Component。

- [ ] `useState`, `useReducer`, `useEffect`, `useLayoutEffect`, `useRef`（DOM 参照）を使う
- [ ] `onClick`, `onChange`, `onSubmit` などのイベントハンドラを **自分で** JSX に書く
- [ ] `window`, `document`, `localStorage`, `navigator`, `IntersectionObserver` などのブラウザ API を使う
- [ ] Context を **消費する**（`useContext`）または **Provider を置く**
- [ ] `'use client'` が必要なカスタムフック / ライブラリ（framer-motion, react-hook-form, zustand の store 購読など）を使う
- [ ] `useRouter`, `usePathname`, `useSearchParams` 等のクライアント側ルーティングフックを使う

### 4.2 どれにも該当しないなら Server のまま

- 単に props を受け取って JSX を返すだけ
- データを取って表示するだけ
- 条件分岐・ループ・フォーマット処理だけ
- `Link` を置くだけ（`Link` 自体は Client だが、使う側は Server でよい）
- 「フォームを表示する」だけなら、`<form action={serverAction}>` にすれば Server のままで送信まで実現できる

### 4.3 判断フロー

```
そのコンポーネント自身が
  ブラウザ API / state / effect / イベントハンドラ / Context を使う？
    ├─ No  → Server Component のまま（宣言不要）
    └─ Yes → その処理は子コンポーネントに切り出せる？
               ├─ Yes → 切り出して、そこだけ 'use client'
               └─ No  → このファイルに 'use client'
                        （import 先が全部クライアントに乗ることを確認する）
```

### 4.4 迷いやすい境界例

| やりたいこと | 結論 | 補足 |
| --- | --- | --- |
| 日付を `toLocaleDateString` でフォーマット | Server で OK だが**ロケール/タイムゾーンはサーバーのもの**になる。ユーザーの TZ が必要なら Client か、TZ を cookie で渡す | hydration mismatch の典型原因 |
| 「もっと見る」で開閉するアコーディオン | 開閉ボタン部分だけ Client。中身のリストは Server から `children` で渡す | 合成パターン |
| テーブルのソート・フィルタ（データ量が小さい） | テーブル全体を Client にしてデータを props で渡す | データ取得は Server のまま |
| テーブルのソート・フィルタ（データ量が大きい / ページング） | 状態を **URL の searchParams** に持たせ、Server Component で取得し直す | Client state 不要。共有可能な URL になる |
| モーダル | 開閉トリガーとダイアログ枠は Client、中身は `children` で Server から | |
| ログイン状態で表示切り替え | cookie を Server で読んで分岐する | Client で `useSession` して切り替えるのは初期表示がチラつく |

---

## 5. よくある誤解

> [!failure] 誤解 1：「`'use client'` を付けたらサーバーでは実行されない」
> Client Component も **SSR / プリレンダーではサーバーで一度実行される**。だから `window` をトップレベルで参照するとサーバーで落ちる。ブラウザ専用処理は `useEffect` 内に置く。

> [!failure] 誤解 2：「`'use client'` は全ファイルに書く必要がある」
> 境界となる**入口ファイルに 1 回**でよい。そこから import されるモジュールは自動的にクライアントモジュールとして扱われる。逆に言うと、境界より下で `'use client'` を書いても意味は変わらない（明示のために書いても害はない）。

> [!failure] 誤解 3：「Client Component の中では Server Component が使えない」
> **import はできないが、props / children として受け取ることはできる**（§2.2）。「Client の下は全部 Client」ではない。

> [!failure] 誤解 4：「Server Component はデータ取得のためだけのもの」
> 「JS をクライアントに送らない」ことが本質。重いライブラリ（マークダウンパーサー、シンタックスハイライター、日付ライブラリ等）を Server に閉じ込めればバンドルサイズが劇的に減る。データ取得しないコンポーネントでも Server で持つ価値がある。

> [!failure] 誤解 5：「Server Component にすれば全部速くなる」
> Server で待つ時間は TTFB に乗る。遅い取得を `<Suspense>` で切らずに await すると、ページ全体が遅い取得に引っ張られる。**ストリーミング前提で Suspense 境界を設計する**ことが必要。

> [!failure] 誤解 6：「Server Component は state を持てないから、インタラクティブな画面には向かない」
> state を持てないのは「そのコンポーネントが」であって、画面全体ではない。インタラクティブな部分を末端の Client Component に切り出せば、大半は Server のまま保てる。実際のアプリは「Server の骨格に Client の島が点在する」構造になる。

> [!failure] 誤解 7：「Server Component 内の関数は秘匿される」
> Server Component 内のコードはクライアントに送られないが、**Client Component に渡した props は全部シリアライズされて HTML / RSC payload に含まれる**。ユーザーオブジェクトをそのまま渡すと `passwordHash` も送ってしまう。必要なフィールドだけ選んで渡す。

> [!failure] 誤解 8：「`useEffect` で fetch する従来パターンを Client Component に移せば OK」
> それは RSC を使わない SPA と同じ挙動になり、RSC の利点が消える。初期データは Server で取る。Client 側の取得はユーザー操作起点などに限定する（§3.3）。

> [!failure] 誤解 9：「Server Component は Context / Provider が使えないので、グローバル state 管理と相性が悪い」
> Provider は Client にして `children` を受け取る形にすればよい（§2.3）。ただし **Server Component から Context の値は読めない**。Server 側で必要な「グローバル値」（ログインユーザーなど）は cookie / headers / 関数呼び出し（`React.cache` でメモ化）で取る。

---

## 6. 実務での進め方（チェックリスト）

1. **ページ / レイアウトは Server で書き始める**。`'use client'` は書かない。
2. エラーが出た箇所（hook・イベントハンドラ・ブラウザ API）を **最小のコンポーネントに切り出し**、そこに `'use client'` を付ける。
3. Client Component の中に「サーバーで描けるもの」が入り込んでいたら、`children` / props で外から渡す形にリファクタする。
4. Client Component に渡す props を見直し、**不要なフィールドや秘匿情報を落とす**。
5. 遅いデータ取得は `<Suspense>` で囲み、ストリーミングさせる。
6. サーバー専用モジュールには `import 'server-only'` を付けて誤 import を防ぐ。
7. バンドルアナライザで Client バンドルを確認し、意図せず乗っているライブラリがないか見る。

---

## 関連

- Next.js App Router のキャッシュ戦略（`fetch` の `cache` / `revalidate`、`revalidateTag`）
- Server Actions とフォーム設計（`useActionState`, `useOptimistic`）
- Suspense とストリーミング SSR
- Hydration mismatch のデバッグ

## 参考

- React 公式: Server Components / `'use client'` / `'use server'` ディレクティブ
- Next.js 公式: Server and Client Components, Data Fetching, Composition Patterns
- Dan Abramov, "The Two Reacts" / "RSC From Scratch"
