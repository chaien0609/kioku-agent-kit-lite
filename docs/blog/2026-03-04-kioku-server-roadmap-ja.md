# SQLiteからクラウドへ：Kiokuのアーキテクチャとkioku-serverへのロードマップ

*公開日: 2026-03-04 · v0.1.28*

こんにちは、ビルダーの皆さん！

数日前に [Kioku Lite](https://phuc-nt.github.io/kioku-lite-landing/) を紹介しました — AIエージェント向けのゼロDocker・SQLite完結型パーソナルメモリエンジンです。その後、2つの質問をよくいただきます：

1. *「グラフ検索の内部はどう動いているの？」*
2. *「エンタープライズ/クラウド版はどんな形になるの？」*

この記事では両方に答えます — さらに、Anthropic公式のMCP Memory Serverとの詳細な比較も含めます。多くの人がそれをベースラインとして参照しているためです。

---

## パート1 — kioku-lite：アーキテクチャの詳細

### コアの考え方：SQLiteで十分（個人規模では）

kioku-liteの哲学は *「少ないリソースでより多くを実現する」* です。ChromaDB、FalkorDB、Ollamaサーバーを立ち上げる代わりに、すべてが **単一の`.db`ファイル** に収まります：

```
~/.kioku-lite/users/<profile>/
├── data/kioku.db          ← SQLite: FTS5 + sqlite-vec + Knowledge Graph
└── memory/YYYY-MM/        ← Markdownバックアップ（人間が読める、git追跡可能）
    └── <content_hash>.md
```

3つのストレージエンジン、1つのファイル：

| エンジン | SQLite拡張 | 目的 |
|---|---|---|
| FTS5 | 組み込み | BM25全文キーワード検索 |
| sqlite-vec | ロード可能拡張 | 1024次元ベクターANN検索 |
| GraphStore | 通常のSQLテーブル | エンティティ-関係BFSトラバーサル |

### インターフェース：CLI + SKILL.md

インターフェース層は **Typer CLI**（`kioku-lite`）と、任意のエージェントに使い方を教える`SKILL.md`ファイルです。SDKは不要 — シェルコマンドを実行できるエージェントならkioku-liteを使えます。

```
エージェント (Claude Code / Cursor / Windsurf / OpenClaw)
    │
    ├─ kioku-lite save "..."            → メモリを保存
    ├─ kioku-lite kg-index <hash>       → エンティティをKGにインデックス
    ├─ kioku-lite search "..." --entities "A,B"
    ├─ kioku-lite recall "Entity"
    └─ kioku-lite connect "A" "B"
```

このCLIファーストの設計により、kioku-liteは **エージェント非依存** になります。Claude、GPT、Gemini、ローカルモデル — SKILL.mdを読んでシェルコマンドを呼べるエージェントなら何でも動作します。

### アーキテクチャ概観

```
┌──────────────────────────────────────────────────────────────┐
│                     インターフェース層                        │
│   cli.py (Typer) — 12コマンド: save, search, kg-index,      │
│   recall, connect, entities, timeline, users, init, ...      │
└──────────────────────────┬───────────────────────────────────┘
                           ▼
┌──────────────────────────────────────────────────────────────┐
│             KiokuLiteService  (service.py)                   │
│   save_memory() │ search() │ kg_index() │ recall()           │
└──────┬───────────────────┬─────────────────────┬─────────────┘
       │                   │                     │
       ▼                   ▼                     ▼
 MarkdownStore         Embedder              KiokuDB
 ~/memory/*.md        FastEmbed             (single .db)
 (人間用バックアップ)  ONNX local    ┌────────────────────────┐
                                    │  SQLiteStore           │
                                    │  ├── memories (FTS5)   │
                                    │  └── memory_vec        │
                                    │      (sqlite-vec)      │
                                    │                        │
                                    │  GraphStore            │
                                    │  ├── kg_nodes          │
                                    │  ├── kg_edges          │
                                    │  └── kg_aliases        │
                                    └────────────────────────┘
```

### 書き込みパイプライン：save → kg-index

すべてのメモリは2ステップの書き込みプロトコルに従います — どちらもエージェントが呼び出します：

```
ステップ1: kioku-lite save "text" --mood MOOD --event-time YYYY-MM-DD
        │
        ├─ SHA256(text) → content_hash  (ユニバーサル重複排除キー)
        ├─ FastEmbed.embed("passage: " + text) → 1024次元ベクター
        ├─ MarkdownStore → ~/memory/YYYY-MM/<hash>.md
        ├─ SQLiteStore.upsert_memory() → FTS5 (BM25インデックス)
        └─ SQLiteStore.upsert_vector() → sqlite-vec

ステップ2: kioku-lite kg-index <hash> --entities '[...]' --relationships '[...]'
        │
        ├─ エージェントがコンテキストからエンティティを抽出（追加LLM呼び出しなし！）
        ├─ GraphStore.upsert_node() → kg_nodes (mention_count++)
        └─ GraphStore.upsert_edge() → kg_edges (source_hash + event_time付き)
```

**重要な設計判断**：kioku-liteは内部でLLMを呼びません。kioku-liteを呼んでいるエージェント *自身が* LLMです — 自分の推論ステップでエンティティを抽出し、それを`kg-index`に渡します。追加コストなし。追加レイテンシなし。ベンダーロックインなし。

### 検索パイプライン：トライハイブリッド → RRF

```
kioku-lite search "query" --entities "お母さん,Sato"
         │
         ▼
1. FastEmbed.embed("query: " + text) → 1024次元クエリベクター
         │
         ├─────────────────────────────────────┐
         ▼                   ▼                 ▼
  BM25検索            セマンティック検索    グラフ検索
  (FTS5 MATCH)        (sqlite-vec ANN)    (BFSトラバーサル)
  BM25による上位K      コサイン類似度による  エンティティ連結
  キーワードヒット      上位K              メモリ
         │                   │                 │
         └─────────────────────────────────────┘
                             ▼
              Reciprocal Rank Fusion (RRF)
              定数k=60、融合スコア
                             │
                             ▼
              重複排除された上位N件
              (content_hashでキー付け)
```

3つのシグナル、ランカーを訓練せずに融合：

| シグナル | 発見できるもの |
|---|---|
| BM25 | 正確な名前、日付、キーワード（日本語/多言語対応） |
| ベクター | 意味的類似性 — 「ストレス」が「不安」にマッチ |
| グラフ | エンティティ連結メモリ — 「お母さん」に接続する全エッジ |

### グラフ検索：ハブノード問題（v0.1.27–0.1.28で解決）

パーソナルKGでは、ユーザー自身のエンティティ（例：「Phúc」）がほぼすべてのメモリに登場します。30以上のエッジがあると、そこからトラバースすると全メモリの90%以上が返ってきます — シグナルゼロ。

3つの層でこれを解決しました：

**タスク1A — セルフエンティティの除外（v0.1.27）**
```python
# ハブを検出：mention_countが最も高いエンティティ
self_entity = store.get_top_entity()  # → "Phúc"（33回言及）

# 他のシードが存在する場合、ハブをトラバーサルから除外
if self_entity and 他のシードが存在:
    seeds = [e for e in seeds if e.name.lower() != self_entity.lower()]
```

**タスク1C — 適応ホップ制限（v0.1.27）**
```python
degree = store.get_degree(entity_name)
effective_hops = 1 if degree > 15 else max_hops  # ハブ→1ホップ、通常→2
```

**タスク2E — マルチエンティティ交差（v0.1.28）**
```
2つ以上のシードがある場合：すべてのシードから到達可能なメモリを返す（交差）
交差が空の場合はユニオンにフォールバック
```

結果：`--entities "お母さん,Sato"` の検索が、お母さん *と* Sato両方に関するメモリを返すようになりました — 全メモリの92%ではなく。

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
