# MCP Video Gen Provider Model Catalog - 2026-06-27

## Repository

- GitHub: `kevinten-ai/mcp-video-gen`
- Runtime: MCP server for video, speech, music, and transcription providers
- Ark path: Volcengine Ark Seedance video provider

## Actions Taken

- Synced local `main` to the remote Ark Seedance provider migration.
- Added provider model catalogs and default model metadata for configured video providers.
- Added optional `model` support to `generate_video` so one request can override the provider default model.
- Added MCP resources under `providers://models/<provider>` for model catalog discovery.
- Updated README docs for the new `model` parameter and current Veo default model.

## Validation

- Passed: `python3 -m compileall src`
- Passed: provider registry smoke without creating video tasks. The smoke confirmed Ark registration, `providers://models/ark`, `generate_video.model`, and `list_providers` default model output.
- Passed: non-generating Ark video API query smoke against a fake task id returned `status=404`, `resourceNotFound=True`, and `authRejected=False`.
- Passed: `git diff --check`
- Passed: staged additions secret/provider check
- `scan_project.sh .` still reports the documented CogVideoX legacy optional provider, while the default Ark path and newly added staged lines do not introduce legacy provider runtime dependencies.

## Notes

- Do not create real video tasks during routine migration validation unless explicitly requested, because video generation can incur billing.
- Ark video generation uses `/contents/generations/tasks` and must not reuse the CodingPlan chat completions endpoint.
