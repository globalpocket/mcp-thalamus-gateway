# mcp-thalamus-gateway

Thalamusのイベント駆動プロトコルに準拠し、MCPクライアント側の要求を使い捨てSubagentへ中継するGateway実装です。

## 実装済みの最小構成

- [gateway/nats_gateway.py](gateway/nats_gateway.py): `runtime.task.assign` 発行、`runtime.llm.request` 中継、`runtime.task.result` 回収、`runtime.agent.exit` で破棄
- [gateway/supervisor.py](gateway/supervisor.py): Dockerコンテナ起動・停止、`/workspace` マウント
- [subagent/worker.py](subagent/worker.py): task受信→`runtime.llm.request`→`runtime.task.result`/`runtime.agent.exit`
- [schemas/events.py](schemas/events.py): canonical event envelope（`id/type/timestamp/source/scope/refs/payload`）
- [infra/docker-compose.yml](infra/docker-compose.yml): NATS + Gatewayのローカル起動

## ディレクトリ

- [gateway/](gateway)
- [subagent/](subagent)
- [schemas/](schemas)
- [infra/](infra)
- [tests/](tests)

## セットアップ

> 重要: `thalamus` 依存は Python `>=3.10` を要求します。ローカルが `3.9` 系の場合は、以下の Docker 手順を正系として利用してください。

1. 依存インストール

```bash
# Python 3.10+ のローカル環境がある場合のみ
pip install -e .
```

2. Subagentイメージ作成

```bash
docker build -f infra/subagent.Dockerfile -t thalamus-subagent:dev .
```

3. NATS + Gateway起動

```bash
docker compose -f infra/docker-compose.yml up --build
```

## Runtime実体利用への移行状況

- `thalamus` 依存は [`pyproject.toml`](pyproject.toml) に追加済み
- Docker イメージ内では [`infra/gateway.Dockerfile`](infra/gateway.Dockerfile) と [`infra/subagent.Dockerfile`](infra/subagent.Dockerfile) で `pip install git+https://github.com/globalpocket/thalamus.git` を実行
- runtime API 置換の調査メモは [`docs/runtime-api-notes.md`](docs/runtime-api-notes.md) を参照

## テスト

```bash
pytest -q
```

## 10ステップ実行フローとの対応

1. 親要求受領（Gateway API層で受理想定）
2. SupervisorがSubagentコンテナ起動し、workspaceを`/workspace`へマウント
3. Gatewayが`runtime.task.assign`発行
4. Subagentが`runtime.llm.request`発行
5. GatewayがLLMへ中継し`runtime.llm.response`返却
6. Subagentが`/workspace`上で処理
7. Subagentが`runtime.task.result`発行
8. Subagentが`runtime.agent.exit`発行
9. Gatewayが`runtime.task.result`回収し親へ返却
10. Gatewayが`runtime.agent.exit`受信でコンテナ破棄
