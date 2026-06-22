# YARA rules

Bundled starter pack. Drop additional `.yar` / `.yara` files in this folder and
restart the worker — they're compiled on demand.

Recommended public packs to add for production:

- **Florian Roth's signature-base**: https://github.com/Neo23x0/signature-base
- **YARA-Rules organisation**: https://github.com/Yara-Rules/rules
- **Elastic Security's**: https://github.com/elastic/protections-artifacts

Clone any of them into a subfolder here:

```bash
cd backend/rules
git clone --depth 1 https://github.com/Neo23x0/signature-base
```

The compiler walks the tree recursively, so subdirectories are fine.
