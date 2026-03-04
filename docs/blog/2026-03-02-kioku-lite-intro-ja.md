# Kioku: なぜ私はAIエージェントのためにKnowledge Graphメモリエンジンを自作したのか

ビルダーとオープンソースコミュニティの皆さん、こんにちは！

今日は、とても個人的な課題を解決するために開発したサイドプロジェクトを紹介したいと思います。きっと多くの方が同じ悩みを抱えているはずです：**AIに感情や因果関係を理解する「長期記憶」を持たせるにはどうすればいいのか？**

そこで生まれたのが **Kioku**（記憶）です。「記」は記録する、「憶」は思い出す — まさにこのプロジェクトの本質を表す名前です。完全にローカルで動作する超軽量なPersonal Memory Engineで、AIエージェント専用に設計されています。

![kioku-lite homepage](img/image.png)
*ホームページ: [phuc-nt.github.io/kioku-lite-landing](https://phuc-nt.github.io/kioku-lite-landing/)*

## 原点：日記好きの悩み

私は毎日日記を書く習慣があります。自己省察（self-reflect）を通して過去の出来事を振り返るのが好きです。AI時代の到来で多くのツールやチャットボットを試しましたが、結果はいつも期待外れでした。

最大の問題は：**感情の保存・分析、そして行動間の因果関係の理解を適切にこなすツールが存在しないこと。**

現在の主要なエージェント（有名どころを含め）には「長期記憶」機能がありますが、実質的にはフラットテキストやベクトルをコンテキストウィンドウに詰め込んでいるだけです。*「先月、プロジェクトXでなぜストレスを感じていたの？」*と聞いても、イベントA（上司との口論）が感情B（ストレス）を引き起こし、決断C（プロジェクト変更）に繋がったという**つながり**を追跡できないためうまく答えられません。

## 解決策：あらゆるエージェントのためのオープンメモリエンジン

AIツール、特にコーディングエージェント（Claude Code、Windsurf、Cursor）を日常的に使う中で気づきました：新しいボットをゼロから作るより、お気に入りのエージェントに「接続」できる独立した*記憶器官*を作ればいいのでは？

目標は**できるだけ多くのエージェントと互換性を持つ**こと。そのためlite版（kioku-lite）では **CLI** と **SKILLSファイル**（CLIエージェントで広く使われている `AGENTS.md` & `SKILL.md` 形式）ベースのアーキテクチャを選びました。数コマンドで、どのエージェントも記憶の読み書きを学習できます。

## アーキテクチャ概要：Write、Search、比較

Kioku Liteは **Tri-hybrid**（3つのハイブリッド）検索メカニズムを使用し、100% SQLite上で動作します：
1. **BM25 (FTS5):** キーワード完全一致検索。
2. **Vector (sqlite-vec + FastEmbed ONNX):** セマンティック検索（ローカル実行、API不要）。
3. **Knowledge Graph (GraphStore):** エンティティグラフと因果関係。

システム概要：

```
┌──────────────────────────────────────────────────────────────┐
│                     INTERFACE LAYER                          │
│                                                              │
│   ┌───────────────────────────────────────────────────────┐  │
│   │  cli.py  (Typer CLI)                                  │  │
│   │  • save       • kg-index    • kg-alias               │  │
│   │  • search     • recall      • connect                │  │
│   │  • entities   • timeline    • users    • setup       │  │
│   │  • init       • install-profile                      │  │
│   └──────────────────────────┬────────────────────────────┘  │
│                              │                               │
└──────────────────────────────┼───────────────────────────────┘
                               ▼
┌──────────────────────────────────────────────────────────────┐
│               KiokuLiteService  (service.py)                 │
│   save_memory() │ search() │ kg_index() │ delete_memory()   │
└────────┬─────────────────┬─────────────────────┬─────────────┘
         │                 │                     │
         ▼                 ▼                     ▼
  MarkdownStore        Embedder              KiokuDB
  ~/memory/*.md       FastEmbed             (single .db)
  (human backup)      ONNX local    ┌────────────────────────┐
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

プロトコルはエージェントが自律的に調整する2つの主要フェーズで構成されます：

### 1. Writeフェーズ
新しいイベント発生時：エージェントがテキストを保存（`save`）し、自律的にエンティティ/関係を抽出してグラフにインデックス（`kg-index`）。すべてローカルで実行、隠れたLLM呼び出しなし。

### 2. Searchフェーズ
コンテキストが必要な時：エージェントが `search` を呼び出し。結果は3つの個別パイプラインを通り、RRF（Reciprocal Rank Fusion）で統合：

```
┌──────────────────────────────────────────────────────────────┐
│                  kioku-lite search "query"                   │
└──────────────────────────────┬───────────────────────────────┘
                               ▼
┌──────────────────────────────────────────────────────────────┐
│           1. Embed Query (FastEmbed 1024-dim ONNX)           │
└──────────────────────────────┬───────────────────────────────┘
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                 2. Tri-hybrid Search Engines                 │
│                                                              │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐  │
│  │   BM25 Search  │  │ Semantic Search│  │  Graph Search  │  │
│  │ (SQLite FTS5)  │  │  (sqlite-vec)  │  │  (SQLite BFS)  │  │
│  └───────┬────────┘  └───────┬────────┘  └───────┬────────┘  │
└──────────┼───────────────────┼───────────────────┼───────────┘
           │                   │                   │
           ▼                   ▼                   ▼
┌──────────────────────────────────────────────────────────────┐
│    3. Reciprocal Rank Fusion (RRF) & Deduplication           │
└──────────────────────────────┬───────────────────────────────┘
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                    Final Merged Results                      │
└──────────────────────────────────────────────────────────────┘
```

### メモリモデル比較

主要システムとの比較：

| システム | インフラ | LLM必須 | 検索 | Knowledge Graph |
|---|---|---|---|---|
| **Mem0** | クラウド管理 | あり — 書き込みごと | Vector + Graph | あり（マネージド） |
| **Claude Code** | フラットMarkdownファイル | なし | コンテキストウィンドウのみ | なし |
| **OpenClaw** | エージェント別SQLite | なし | セマンティック（embedding） | なし |
| ✦ **Kioku Lite** | **SQLiteファイル1つ** | **エージェント駆動、追加なし** | **Tri-hybrid (BM25 + vector + KG)** | **あり（エージェント駆動）** |

**Mem0**について：本番アプリ向けのマネージドメモリプラットフォームとして知られており、書き込みのたびにLLMを呼び出してメモリを自動抽出・圧縮し、クラウド管理のベクターストアに保存します。エンタープライズ用途では強力ですが、データはデバイスを離れ、保存のたびにLLM呼び出しコストが発生します。Kioku Liteは逆の発想を取ります：kioku-liteを呼び出すエージェント*自体がすでにLLM*なので、追加のLLM呼び出しは不要。セットアップ後はすべてオンデバイス、オフライン、無料で動作します。

*(詳細: [System Architecture](https://phuc-nt.github.io/kioku-lite-landing/blog.html#system-architecture) | [Write Pipeline](https://phuc-nt.github.io/kioku-lite-landing/blog.html#write-save-kg-index) | [Search Architecture](https://phuc-nt.github.io/kioku-lite-landing/blog.html#search-architecture) | [Memory Comparison](https://phuc-nt.github.io/kioku-lite-landing/blog.html#memory-comparison))*

## Knowledge Graph (KG)：柔軟性の鍵

Kioku Liteのもう一つの強みは、Knowledge Graphの**オープンスキーマ**です。エンティティタイプ（`entity_type`）と関係タイプ（`rel_type`）は柔軟な文字列であり、固定のenumに縛られません。

kioku-liteには**2つのビルトインペルソナ**が付属：
- **Companion**: `EMOTION`、`LIFE_EVENT`ノードを `TRIGGERED_BY` で接続。日記や感情追跡に最適。
- **Mentor**: `DECISION`、`LESSON`ノードを `LED_TO` で接続。自己省察や経験からの学びに最適。

さらに、人事管理、プロダクトマネジメントなど、どんな分野でもエージェントに新しいペルソナを設定させることができます。

*(スキーマ詳細: [KG Open Schema](https://phuc-nt.github.io/kioku-lite-landing/blog.html#kg-open-schema))*

## コピペ一発でセットアップ

日常的に使っている2種類のエージェント用セットアップガイドを用意しました：

1. **[General Agent Setup (Claude Code, Cursor, Windsurf)](https://phuc-nt.github.io/kioku-lite-landing/agent-setup.html)**
2. **[OpenClaw Agent Setup](https://phuc-nt.github.io/kioku-lite-landing/openclaw-setup.html)**

対応するガイドをコピーしてエージェントに渡すだけ。エージェントが自動でセットアップを実行し、IDを設定し、お使いのマシン上のメモリエンジンに接続します。

詳細は [Kioku Lite Homepage](https://phuc-nt.github.io/kioku-lite-landing/) をご覧ください。

## kioku-lite vs kioku-server

**kioku-lite** はまず個人ユーザー向けに公開。`pipx` で素早いセットアップ、Docker不要、APIキー不要、ChromaDB/FalkorDBなどの外部データベース不要。パーソナルマシンのバックグラウンドでスムーズに動作します。

一方、専用のグラフ/ベクトルデータベースとマルチテナントエンタープライズサポートを備えた **kioku-server** は現在開発中です。インフラ規模という点では、kioku-serverはMem0が提供するものに近づきますが、エージェント駆動（内蔵LLM抽出なし）とtri-hybridサーチという核心的な差別化要素は維持し続けます。

## おわりに

ビルダーの皆さん、オープンソース愛好家の皆さん、そして特にAIに感情と因果関係を本当の友人のように理解させる「長期記憶」ソリューションを探している方、ぜひ **Kioku Lite** を試してみてください。

- ホームページ: **[phuc-nt.github.io/kioku-lite-landing](https://phuc-nt.github.io/kioku-lite-landing/)**
- GitHub: **[github.com/phuc-nt/kioku-agent-kit-lite](https://github.com/phuc-nt/kioku-agent-kit-lite)**

フィードバックと応援がプロジェクトを前に進める力です。試してみて、必要な方にシェアして、あるいはリポジトリにStarをつけていただけると嬉しいです！

読んでいただきありがとうございます！Happy codingで、コミュニティからのフィードバックをお待ちしています！
