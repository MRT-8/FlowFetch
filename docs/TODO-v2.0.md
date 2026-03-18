# FlowFetch v2.0 Developer TODO

This file is for maintainers and contributors. It describes a planned v2.0
improvement and is not intended as end-user documentation.

## Resumable Downloads From `.part` Files

### Goal

Support resuming interrupted downloads from an existing `.part` file instead of
always restarting from byte `0`.

### Current Behavior

- FlowFetch writes downloads to a `.part` file first.
- On failure, the partial file may be kept or deleted depending on CLI options.
- A later retry starts the download from the beginning.

### v2.0 Target Behavior

1. Detect an existing `.part` file before starting a new download attempt.
2. Read the current partial size and validate that it is non-negative and not
   larger than the expected remote size when metadata is available.
3. Probe whether the server supports byte range requests.
4. If range requests are supported, continue downloading from the last byte
   already written.
5. If range requests are not supported, choose a clear fallback path:
   - restart from zero automatically, or
   - ask the user whether to restart, keep, or delete the stale partial file
6. After completion, keep the existing validation and rename flow:
   - verify final size
   - keep using the `.part` to final rename handoff
   - preserve current archive detection and extraction behavior

### Suggested Implementation Plan

1. Extend metadata probing to capture resumability hints such as
   `Accept-Ranges` and normalized content length.
2. Add a helper that inspects an existing `.part` file and decides whether the
   state is resumable, stale, or invalid.
3. Add HTTP range support to the `httpx` downloader path:
   - send `Range: bytes=<offset>-`
   - require a `206 Partial Content` response for a true resume
   - append to the existing `.part` instead of truncating it
4. Define fallback semantics for mismatched responses:
   - if the server returns `200 OK` to a ranged request, restart cleanly
   - if the remote size shrank or changed unexpectedly, discard or rename the
     stale partial file before retrying
5. Decide whether system downloader resume should be supported in v2.0:
   - `curl -C -`
   - `wget -c`
   - or postpone system-tool resume support to a later milestone
6. Add explicit user messaging so resume decisions are visible in logs.

### Edge Cases To Cover

- The partial file is larger than the remote object.
- The remote object changed since the partial file was created.
- The server advertises range support incorrectly.
- The resumed download succeeds but the final size still mismatches.
- Non-interactive mode needs deterministic behavior without prompts.
- Resume logic must still cooperate with fallback downloaders and retry loops.

### Acceptance Criteria

- Re-running FlowFetch after an interrupted download can continue from the
  existing `.part` file when the server supports it.
- Resume failures do not silently corrupt the final output.
- Final validation remains mandatory before renaming the file into place.
- Existing `--keep-partial`, `--delete-partial`, retry, fallback, and
  non-interactive behaviors remain understandable and testable.
