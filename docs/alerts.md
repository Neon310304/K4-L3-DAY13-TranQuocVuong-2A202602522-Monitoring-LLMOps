# Alert runbooks

All alerts notify Slack `#k4-l3b-alerts`; owner is `student-2A202602522`. Follow **Metrics → Logs → Traces** and use sanitized logs only.

## Alert 1

- **Name:** `HighLatencyP95`.
- **Trigger:** `p95(response_sent.latency_ms) > 3000` for 5 minutes.
- **Impact:** users wait too long for an answer; this violates the primary latency SLI.
- **Check:** (1) confirm P95/P99 and TTFT on the latency panel; (2) find a slow `response_sent` JSONL event and note its `correlation_id`; (3) open that trace and compare retrieval and generation spans.
- **Mitigation:** if generation is the slow span, roll `production` prompt back to the last known good version; if retrieval is slow, disable the active practice incident and investigate retrieval latency.

## Alert 2

- **Name:** `ElevatedErrorRate`.
- **Trigger:** failed requests exceed 2% of received requests for 5 minutes.
- **Impact:** users receive failed requests instead of answers and the SLO error budget burns faster.
- **Check:** (1) confirm error rate and traffic volume; (2) group `request_failed` events by `error_type` and record a `correlation_id`; (3) open its trace and identify the failed observation.
- **Mitigation:** disable the failing practice scenario or roll back the last prompt/config change; verify successful requests recover before closing the incident.

## Alert 3

- **Name:** `LowRetrievalSuccess`.
- **Trigger:** retrieval tool success below 90% for 10 minutes.
- **Impact:** answers may lack relevant context or fail entirely, reducing answer quality.
- **Check:** (1) inspect the errors panel's retrieval success and quality proxy; (2) find events with `tool_name=retrieval` and `tool_success=false`; (3) open a matching trace and inspect the retrieval span and document count.
- **Mitigation:** disable the active retrieval practice incident, restore the last known good retrieval configuration, then confirm retrieval success and quality recover.
