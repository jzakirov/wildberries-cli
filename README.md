# wildberries-cli

Wildberries seller platform CLI built on top of [`wildberries-sdk`](https://github.com/eslazarev/wildberries-sdk).

The executable name is `wb`.

```bash
wb general seller-info
wb tariffs commission --locale en
wb reports sales --date-from 2026-01-01T00:00:00+03:00
wb communications feedbacks list --unanswered --take 100 --skip 0
wb orders-fbs orders new --pretty
wb raw methods reports
```

## Installation

```bash
pip install wildberries-cli
```

Or with uv:

```bash
uv tool install wildberries-cli
```

## Configuration

Run the interactive setup wizard:

```bash
wb config init
```

Config is stored in `~/.config/wildberries-cli/config.toml`.

Example:

```toml
[core]
api_token = "your_wb_api_token"
timeout_seconds = 30.0
retries = 3

[defaults]
locale = "ru" # optional (ru|en|zh)
```

### Environment Variables

| Environment variable | Config key |
|---|---|
| `WB_API_TOKEN` | `core.api_token` |
| `WB_TIMEOUT` | `core.timeout_seconds` |
| `WB_RETRIES` | `core.retries` |
| `WB_LOCALE` | `defaults.locale` |

CLI flags override both config and env values.

## Command Overview

### `config`

```bash
wb config init
wb config show
wb config show --reveal
wb config set core.retries 5
```

### `general`

```bash
wb general ping
wb general seller-info
wb general users --limit 50 --offset 0
wb general users --invited-only
```

### `tariffs`

```bash
wb tariffs commission [--locale ru|en|zh]
wb tariffs box --date YYYY-MM-DD
wb tariffs pallet --date YYYY-MM-DD
wb tariffs return --date YYYY-MM-DD
wb tariffs acceptance-coefficients [--warehouse-ids "1,2,3"]
```

### `reports`

```bash
wb reports orders   --date-from 2026-01-01T00:00:00+03:00 [--flag 0|1]
wb reports sales    --date-from 2026-01-01T00:00:00+03:00 [--flag 0|1]
wb reports stocks   --date-from 2026-01-01T00:00:00+03:00
wb reports incomes  --date-from 2026-01-01T00:00:00+03:00
```

### `communications`

```bash
wb communications feedbacks list --unanswered --take 100 --skip 0
wb communications feedbacks get <feedback-id>
wb communications feedbacks answer <feedback-id> --text "Thanks for your feedback"
wb communications feedbacks answer <feedback-id> --text -

wb communications questions list --unanswered --take 100 --skip 0
wb communications questions get <question-id>
wb communications questions answer <question-id> --text "Yes, this fits..." [--state wbRu]
```

### `products`

```bash
wb products cards limits
wb products cards list --body-file cards-query.json [--locale ru|en|zh]
wb products objects list [--name socks] [--parent-id 123]
wb products directories colors [--locale en]
wb products tags list
```

`wb products cards list` expects the WB SDK request JSON for `content_v2_get_cards_list_post`.

### `orders-fbs`

```bash
wb orders-fbs orders new
wb orders-fbs orders list --limit 100 --next 0
wb orders-fbs orders status --order 123 --order 456
wb orders-fbs orders stickers --order 123 --type zplv --width 58 --height 40

wb orders-fbs supplies list --limit 100 --next 0
wb orders-fbs supplies create --name "Batch 2026-02-23"
```

### `raw` (direct SDK fallback)

Use `raw` for any `wildberries-sdk` `DefaultApi` method that does not yet have a curated command.

```bash
wb raw modules
wb raw methods reports
wb raw signature reports api_v1_supplier_sales_get
wb raw call general api_v1_seller_info_get
wb raw call tariffs api_v1_tariffs_commission_get --arg locale=ru
wb raw call reports api_v1_supplier_sales_get --arg-json date_from='"2026-01-01T00:00:00+03:00"'
```

Notes:
- `--arg` passes values as strings.
- `--arg-json` passes parsed JSON values (numbers, booleans, arrays, objects, quoted strings).
- `--kwargs-json` accepts a full JSON object for method kwargs.

## Output

- Default output is JSON to stdout.
- Errors are structured JSON to stderr.
- `--pretty` renders Rich tables for selected list endpoints (and pretty JSON otherwise).

Example error shape:

```json
{"error":{"type":"auth_error","message":"Authentication failed. Check WB_API_TOKEN.","status_code":401}}
```

## Publishing to PyPI

This repository includes GitHub Actions trusted publishing (`.github/workflows/publish.yml`):

- Push a tag like `v0.1.0`
- Workflow runs `uv build`
- Workflow runs `uv publish` with OIDC (PyPI trusted publisher)

## Scope (v1)

The curated command surface is intentionally narrow. Wildberries SDK exposes many modules and hundreds of methods, so `wb raw` is included to provide immediate access to the full SDK while curated commands are expanded over time.

## License

MIT (see `LICENSE`).
