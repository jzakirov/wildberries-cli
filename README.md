# wildberries-cli

Wildberries seller platform CLI built on top of [`wildberries-sdk`](https://github.com/eslazarev/wildberries-sdk).

```bash
wildberries general seller-info
wildberries tariffs commission --locale en
wildberries reports sales --date-from 2026-01-01T00:00:00+03:00
wildberries communications feedbacks list --unanswered --take 100 --skip 0
wildberries orders-fbs orders new --pretty
wildberries raw methods reports
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
wildberries config init
```

Config is stored in `~/.config/wildberries-cli/config.toml`.

Example:

```toml
[core]
api_token = "your_wb_api_token"
timeout_seconds = 30.0
retries = 3

[defaults]
locale = "ru"   # optional (ru|en|zh)
pretty = true   # optional — always render Rich tables
```

### Environment Variables

| Environment variable | Config key         |
|----------------------|--------------------|
| `WB_API_TOKEN`       | `core.api_token`   |
| `WB_TIMEOUT`         | `core.timeout_seconds` |
| `WB_RETRIES`         | `core.retries`     |
| `WB_LOCALE`          | `defaults.locale`  |
| `WB_PRETTY`          | `defaults.pretty`  |

CLI flags override both config and env values.

## Command Overview

### `config`

```bash
wildberries config init
wildberries config init --skip-validation   # skip token check (useful offline)
wildberries config show
wildberries config show --reveal
wildberries config set core.retries 5
wildberries config set defaults.pretty true
```

### `general`

```bash
wildberries general ping
wildberries general seller-info
wildberries general users --limit 50 --offset 0
wildberries general users --invited-only
```

### `tariffs`

```bash
wildberries tariffs commission [--locale ru|en|zh]
wildberries tariffs box --date YYYY-MM-DD
wildberries tariffs pallet --date YYYY-MM-DD
wildberries tariffs return --date YYYY-MM-DD
wildberries tariffs acceptance-coefficients [--warehouse-ids "1,2,3"]
```

### `reports`

```bash
wildberries reports orders   --date-from 2026-01-01T00:00:00+03:00 [--flag 0|1]
wildberries reports sales    --date-from 2026-01-01T00:00:00+03:00 [--flag 0|1]
wildberries reports stocks   --date-from 2026-01-01T00:00:00+03:00
wildberries reports incomes  --date-from 2026-01-01T00:00:00+03:00
```

### `communications`

```bash
wildberries communications feedbacks list --unanswered --take 100 --skip 0
wildberries communications feedbacks get <feedback-id>
wildberries communications feedbacks answer <feedback-id> --text "Thanks for your feedback"
wildberries communications feedbacks answer <feedback-id> --text -

wildberries communications questions list --unanswered --take 100 --skip 0
wildberries communications questions get <question-id>
wildberries communications questions answer <question-id> --text "Yes, this fits..." [--state wbRu]
```

### `products`

```bash
wildberries products cards limits
wildberries products cards list --body-file cards-query.json [--locale ru|en|zh]
wildberries products objects list [--name socks] [--parent-id 123]
wildberries products directories colors [--locale en]
wildberries products tags list
```

`wildberries products cards list` expects the WB SDK request JSON for `content_v2_get_cards_list_post`.

### `orders-fbs`

```bash
wildberries orders-fbs orders new
wildberries orders-fbs orders list --limit 100 --next 0
wildberries orders-fbs orders status --order 123 --order 456
wildberries orders-fbs orders stickers --order 123 --type zplv --width 58 --height 40

wildberries orders-fbs supplies list --limit 100 --next 0
wildberries orders-fbs supplies create --name "Batch 2026-02-23"
```

### `raw` (direct SDK fallback)

Use `raw` for any `wildberries-sdk` `DefaultApi` method that does not yet have a curated command.

```bash
wildberries raw modules
wildberries raw methods reports
wildberries raw signature reports api_v1_supplier_sales_get
wildberries raw call general api_v1_seller_info_get
wildberries raw call tariffs api_v1_tariffs_commission_get --arg locale=ru
wildberries raw call reports api_v1_supplier_sales_get --arg-json date_from='"2026-01-01T00:00:00+03:00"'
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


## Scope (v1)

The curated command surface is intentionally narrow. Wildberries SDK exposes many modules and hundreds of methods, so `wildberries raw` is included to provide immediate access to the full SDK while curated commands are expanded over time.

## License

MIT (see `LICENSE`).
