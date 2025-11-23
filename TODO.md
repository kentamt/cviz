# TODO

## Configurable ZMQ Endpoint
1. Introduce a single configuration entry (env var `CVIZ_ZMQ_ENDPOINT` with default `tcp://127.0.0.1:5555`).
2. Update `Publisher` to accept the endpoint at init (lazily create/bind sockets so multiple publishers can coexist).
3. Read the endpoint in `CvizServerManager` and pass it to each `Subscriber`, bubbling the value through CLI arguments where appropriate.
4. Propagate the same setting to helper tools (`recorder`, `topic_*`, `playback`) so every component can target the same broker without code edits.

## Simulation Timestamp Recording
1. Add a recorder CLI flag (e.g. `--timestamp-field sim_time`) that names the payload key containing simulation time.
2. While recording, prefer the configured field when present, storing both `wall_time` and `sim_time` (or leaving `sim_time` null if absent).
3. Update metadata/comments to explain the new option and how downstream tooling can consume the two timestamps.
