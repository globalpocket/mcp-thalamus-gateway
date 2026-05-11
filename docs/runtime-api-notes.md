# Thalamus Runtime API 調査メモ

このドキュメントは、[`mcp-thalamus-gateway`](../README.md) を **spec互換実装** から **runtime実体利用実装** へ移行するための調査メモです。

## 前提

- `thalamus` は [`git+https://github.com/globalpocket/thalamus.git`](../pyproject.toml) から導入する。
- `thalamus` は Python `>=3.10` を要求するため、ローカル実行ではなく Docker ベースで検証する。

## 調査対象

- Gateway置換対象: [`gateway/nats_gateway.py`](../gateway/nats_gateway.py)
- Subagent置換対象: [`subagent/worker.py`](../subagent/worker.py)
- イベント封筒縮小対象: [`schemas/events.py`](../schemas/events.py)

## 期待する確認項目

1. runtime / sdk の import 可能モジュール
2. task assign / result / llm request / exit に対応する公開API
3. supervisor / worker lifecycle に対応する制御API

## 次ステップ

1. Docker内で `thalamus` import を確認
2. 利用可能APIをこのファイルに追記
3. 置換実装（Gateway → Subagent）を段階適用

## 調査結果（2026-05-11）

- [`docker compose -f infra/docker-compose.yml build`](../infra/docker-compose.yml) は成功。
- `thalamus` というトップレベルモジュール名では import できない。
- コンテナ内で確認できたトップレベルは `runtime`, `schemas`。

確認コマンド例:

```bash
docker run --rm infra-gateway python -c "import pkgutil; print([m.name for m in pkgutil.iter_modules() if m.name in ('runtime','schemas','thalamus')])"
```

出力:

```text
['schemas', 'runtime']
```

示唆:

- 置換実装時は `import thalamus` 前提を捨て、`runtime.*` / `schemas.*` の実モジュールを起点にAPI探索する。
