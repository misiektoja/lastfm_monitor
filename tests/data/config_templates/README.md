# Historical configuration templates

Each file is the `CONFIG_BLOCK` a released version shipped, extracted from its tag. They exist so
`test_config_loading.py` can replay every configuration this tool ever generated through the current parser,
which is what catches a renamed or removed setting that would reject an upgrading user's file.

| File | Released in |
| --- | --- |
| `2.1.conf` | v2.1 |
| `2.1.1.conf` | v2.1.1 |
| `2.2.conf` | v2.2 |
| `2.3.conf` | v2.3 |
| `2.4.conf` | v2.4 |
| `2.4.1.conf` | v2.4.1 |
| `2.4.2.conf` | v2.4.2, v2.4.3, v2.4.4 |
| `2.5.conf` | v2.5 |
| `2.6.conf` | v2.6 |
| `2.6.1.conf` | v2.6.1, v2.6.2 |

Versions before v2.1 had no configuration file and no `--generate-config`, so there is nothing to replay for
them.

Never edit these files. A released template is a historical fact. When a setting is renamed, add the old name
to `RETIRED_CONFIG_SETTINGS` instead.
