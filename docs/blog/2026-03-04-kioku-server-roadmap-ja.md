# CLIからサーバーへ：Kiokuのアーキテクチャとkioku-serverへのロードマップ

*公開日: 2026-03-04 · v0.1.28*

こんにちは、ビルダーの皆さん！

この記事は[kioku-lite紹介記事](https://phuc-nt.github.io/kioku-lite-landing/blog.html#kioku-intro-ja)の後によくいただく2つの質問に答えます：アーキテクチャが実際にどう動くか、そしてkioku-serverでプロジェクトがどこへ向かっているか。さらにAnthropicのMCP Memory Serverとの比較も含めます。

---

## パート1 — kioku-liteの概要

kioku-liteはすべてを **単一のSQLiteファイル** に保存します — Dockerなし、外部サーバーなし。インターフェースは **CLI + SKILL.md**：シェルコマンドを実行できるエージェントならskillファイルを読み込んですぐにメモリ機能を使えます。

コアは **トライハイブリッド検索** — 3つのシグナルをRRF（Reciprocal Rank Fusion）で融合します：

| シグナル | 技術 | 発見できるもの |
|---|---|---|
| BM25 | SQLite FTS5 | 正確なキーワード、名前、日付 |
| Vector | sqlite-vec + FastEmbed ONNX | 意味的に類似したメモリ |
| Knowledge Graph | SQLite BFS | エンティティ連結メモリ、因果チェーン |

書き込みはエージェントが自ら呼び出す2ステッププロトコル：`save`（テキスト → SHA256ハッシュ + 埋め込み + FTS5）→ `kg-index`（エージェントがエンティティを抽出 → GraphStore）。**内蔵LLMなし** — 呼び出しているエージェント自身がLLMです。

v0.1.27–0.1.28のグラフ検索改善：セルフエンティティ除外（BFSシードからハブノードを除外）、適応ホップ制限（degree > 15 → 1ホップ）、マルチエンティティ交差（*すべての*シードエンティティから到達可能なメモリのみ返す）。

*→ 詳細ドキュメント: [System Architecture](https://phuc-nt.github.io/kioku-lite-landing/blog.html#system-architecture) · [Write Pipeline](https://phuc-nt.github.io/kioku-lite-landing/blog.html#write-save-kg-index) · [Search Architecture](https://phuc-nt.github.io/kioku-lite-landing/blog.html#search-architecture)*

---

## パート2 — kioku-server：ロードマップ

### 同じコアロジック、異なるインフラ

kioku-liteでアルゴリズムが機能することを証明しました。kioku-serverは同じコア — トライハイブリッド検索、RRF融合、エージェント駆動KG、オープンスキーマ — を取り、エンタープライズデプロイのためのインフラに置き換えます：

```
kioku-lite                        kioku-server（計画中）
─────────────────────────         ────────────────────────────────
インターフェース: CLI + SKILL.md  →  インターフェース: MCPサーバー
埋め込み: FastEmbed ONNX      →    埋め込み: Ollama / クラウドAPI
ベクターDB: sqlite-vec         →    ベクターDB: ChromaDB（専用）
グラフDB: SQLiteテーブル       →    グラフDB: FalkorDB（Cypher）
スケール: 1ユーザー、ローカル   →    スケール: マルチテナント、クラウド
```

サービス層（`KiokuService`）はそのまま。アルゴリズムはそのまま。I/Oアダプターだけが変わります。

### アーキテクチャ：kioku-server

```
┌───────────────────────────────────────────────────────────────┐
│                   MCPサーバー層                               │
│   MCPツール: memory/save, memory/search, memory/kg-index,    │
│              memory/recall, memory/connect, memory/entities   │
└──────────────────────────┬────────────────────────────────────┘
                           ▼
┌──────────────────────────────────────────────────────────────┐
│              KiokuService（共有コアロジック）                 │
│   save_memory() │ search() │ kg_index() │ recall()           │
└──────┬───────────────────┬─────────────────────┬─────────────┘
       │                   │                     │
       ▼                   ▼                     ▼
  PostgreSQL /         Embedder              専用DB
  オブジェクトストレージ Ollama / API  ┌──────────────────────────┐
  (メモリレコード,      (またはローカル │  ChromaDB                │
  Markdownエクスポート) ONNX)         │  (ベクターストア)         │
                                     │                          │
                                     │  FalkorDB                │
                                     │  (プロパティグラフ,       │
                                     │   Cypherクエリ)          │
                                     └──────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│              マルチテナント分離                               │
│  APIキー → ネームスペース → テナントごとのデータ分離          │
│  (kioku-liteのマルチユーザープロファイルと同じパターン)       │
└──────────────────────────────────────────────────────────────┘
```

### kioku-liteとの違い

| 次元 | kioku-lite | kioku-server |
|---|---|---|
| **インターフェース** | CLI + SKILL.md | MCPサーバー（JSON-RPC） |
| **埋め込み** | FastEmbed ONNX（ローカル） | Ollama / クラウドAPI（設定可能） |
| **ベクターストア** | sqlite-vec（インプロセス） | ChromaDB（専用コンテナ） |
| **グラフストア** | SQLiteテーブル + BFS | FalkorDB（プロパティグラフ、Cypher） |
| **スケール** | 1ユーザー、個人マシン | マルチテナント、クラウドデプロイ可能 |
| **認証** | プロファイル切り替え | APIキー（テナント別） |
| **デプロイ** | `pipx install` | Docker Compose / Kubernetes |

### 変わらないもの

- **コアアルゴリズム**：トライハイブリッド検索、RRF融合、セルフエンティティ除外、適応ホップ、マルチエンティティ交差
- **ナレッジグラフスキーマ**：オープンスキーマのエンティティタイプ、関係タイプ、エビデンスフィールド
- **エージェント駆動KG**：内蔵LLM抽出なし — エージェントが引き続き担当
- **コンテンツハッシュ**：すべてのストレージ層でメモリを連結するSHA256重複排除キー

---

## パート3 — AnthropicのMCP Memory Serverとの比較

AnthropicはMCP serversリポジトリの[公式MCP Memory Server](https://github.com/modelcontextprotocol/servers/tree/main/src/memory)をリファレンス実装として提供しています。kioku-serverとMCP Memory Serverの両方がMCPツール経由でメモリを提供するため、直接比較する価値があります。

### MCP Memory Serverとは？

MCP Memory Serverは、エージェントにJSONLフラットファイルに保存されたシンプルなナレッジグラフを提供する **TypeScriptのリファレンス実装** です。6つのMCPツールを公開しています：

- `create_entities` — エンティティノードを追加
- `create_relations` — エンティティ間のタイプ付き関係を追加
- `add_observations` — エンティティにファクトを添付
- `delete_entities` / `delete_relations` / `delete_observations`
- `search_nodes` — 名前でエンティティを検索（文字列マッチ）
- `read_graph` — グラフ全体を返す

ストレージは各行がエンティティまたは関係を表すJSONオブジェクトの`.jsonl`ファイルです。`search_nodes`は文字列マッチでそのリストをフィルタリングします。

### 機能比較

| 機能 | MCP Memory Server | kioku-lite | kioku-server（計画中） |
|---|---|---|---|
| **ストレージ** | JOSNLフラットファイル | 単一SQLiteファイル | ChromaDB + FalkorDB + PostgreSQL |
| **BM25キーワード検索** | ❌ | ✅ (SQLite FTS5) | ✅ |
| **セマンティック/ベクター検索** | ❌ | ✅ (FastEmbed ONNX) | ✅ (クラウドスケール) |
| **ナレッジグラフトラバーサル** | ❌ (フラットリスト、BFSなし) | ✅ (BFS、適応ホップ) | ✅ (FalkorDB Cypher) |
| **融合ランキング（RRF）** | ❌ | ✅ | ✅ |
| **エンティティリコール** | 部分的（リストフィルター） | ✅ `recall "entity"` | ✅ |
| **因果チェーン/パス** | ❌ | ✅ `connect "A" "B"` | ✅ |
| **タイムライン/時間クエリ** | ❌ | ✅ `--from --to` | ✅ |
| **マルチエンティティ交差** | ❌ | ✅ (v0.1.28) | ✅ |
| **ハブノード除外** | ❌ | ✅ (v0.1.27) | ✅ |
| **マルチテナント** | ❌ | ❌ (プロファイルベース) | ✅ |
| **多言語対応** | ❌ | ✅ (100以上の言語) | ✅ |
| **オフライン対応** | ✅ | ✅ | 設定可能 |
| **人間が読めるバックアップ** | ❌ | ✅ Markdown | ✅ Markdownエクスポート |
| **本番環境対応** | ❌ (リファレンス実装) | 個人規模 | はい |
| **言語** | TypeScript | Python | Python |

### 哲学：リファレンスvs本番

MCP Memory Serverは **意図的にシンプル** です。開発者がMCPでメモリツールを構築する方法を理解するためのリファレンス実装 — 終点ではなく出発点。Anthropicはフォークしてカスタマイズするためのテンプレートとしてこれを提供しています。

kioku-liteとkioku-serverは、実際のエージェントが実際の作業をするために構築された本番グレードのツールです：

> **MCP Memory Server**：「メモリツールがどのように機能するか、ここで示します。これを拡張してください。」
>
> **kioku-lite**：「本物のセマンティック検索、グラフトラバーサル、時間クエリを備えたSQLiteでメモリを保存。今すぐ使える、個人規模。」
>
> **kioku-server**：「同じアルゴリズム、エンタープライズインフラ。チームメモリ、マルチテナントクラウド。」

---

## まとめ

```
kioku-lite（現在）     kioku-server（計画中）    MCP Memory Server
────────────────────   ──────────────────────    ─────────────────
個人規模               エンタープライズ/クラウド  リファレンス実装
CLIインターフェース    MCPインターフェース         MCPインターフェース
SQLite完結            独立DB群                  JOSNLフラットファイル
トライハイブリッド検索  トライハイブリッド + 専用DB 文字列マッチのみ
エージェント駆動KG     エージェント駆動KG          エージェント駆動KG
0 Docker              Docker Compose / K8s       0インフラ
v0.1.28 · 利用可能     開発中                     利用可能（TypeScript）
```

**kioku-liteを使う場合：** コーディング/ジャーナリングエージェントのパーソナル長期メモリが今すぐほしい、インフラなし、オフライン対応。

**kioku-serverを使う場合：** 複数ユーザーがメモリバックエンドを共有するマルチエージェントシステムまたはエンタープライズデプロイを構築している場合。（まだ利用不可 — 開発中。）

**MCP Memory Serverを使う場合：** MCPメモリツールの動作を理解するシンプルな出発点がほしい、またはカスタムメモリレイヤーを自分で構築したい場合。

---

- GitHub: [github.com/phuc-nt/kioku-agent-kit-lite](https://github.com/phuc-nt/kioku-agent-kit-lite)
- ホームページ: [phuc-nt.github.io/kioku-lite-landing](https://phuc-nt.github.io/kioku-lite-landing/)
- Changelog: [CHANGELOG.md](https://github.com/phuc-nt/kioku-agent-kit-lite/blob/main/CHANGELOG.md)

読んでいただきありがとうございます！アーキテクチャの理解に役立ったなら、GitHubの⭐が大きな励みになります。
