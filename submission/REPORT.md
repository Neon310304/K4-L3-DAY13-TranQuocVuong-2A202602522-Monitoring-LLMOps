# Báo cáo cá nhân — K4-L3B Day 13 Monitoring & LLMOps

> Mỗi học viên hoàn thiện một file duy nhất này. Khi dẫn evidence, dùng đường dẫn tương đối, ví dụ `evidence/07-trace-waterfall.png`.

## 1. Thông tin học viên

- **Họ và tên:** Trần Quốc Vương (theo tên repository; cần xác nhận trước khi nộp)
- **MSSV:** 2A202602522 (theo tên repository; cần xác nhận trước khi nộp)
- **Lớp:** K4-L3B
- **Repository URL:** https://github.com/Neon310304/K4-L3-DAY13-TranQuocVuong-2A202602522-Monitoring-LLMOps
- **Commit SHA cuối:** Ghi SHA từ `git log -1` khi nộp trên LMS/Codelabs.
- **Challenge ID:** `day13-k4-l3b-monitoring-llmops-v1` có trong file local; chờ xác nhận link/thông báo release của Lab Coach.
- **Tên project Langfuse cá nhân:** dự kiến `day13-k4-l3b-2A202602522`; chưa xác minh project/key.

## 2. Evidence index

Điền đúng đường dẫn tới evidence thực tế. Có thể đổi tên hoặc dùng nhiều ảnh nếu cần.

| Evidence | Đường dẫn |
|---|---|
| Pytest cuối | `evidence/01-pytest.txt` |
| Log validator | `evidence/02-log-validator.txt` |
| Dashboard validator | `evidence/03-dashboard-validator.txt` |
| Structured log | `evidence/04-structured-log.txt` |
| PII redaction | `evidence/05-pii-redaction.txt` |
| Trace list | Chưa có — chờ project Langfuse cá nhân |
| Trace waterfall | Chưa có — chờ project Langfuse cá nhân |
| Trace metadata | Chưa có — chờ project Langfuse cá nhân |
| Prompt versions | Chưa có — chờ project Langfuse cá nhân |
| Prompt rollback | Chưa có — chờ project Langfuse cá nhân |
| Dashboard runtime | [`evidence/11-dashboard-overview.png`](evidence/11-dashboard-overview.png); [JSON snapshot](evidence/11-dashboard-runtime.txt) |
| Incident metric | Chưa có — chờ link challenge chính thức |
| Incident log | Chưa có — chờ link challenge chính thức |
| Incident trace | Chưa có — chờ challenge và Langfuse key |

## 3. Kết quả kỹ thuật

| Nội dung | Baseline | Kết quả cuối | Nhận xét |
|---|---|---|---|
| `validate_logs.py` | 30/100 | 100/100 tại CP1 | Starter thiếu correlation ID và context. |
| `validate_dashboard.py` | 6/6 | 6/6 | Chỉ xác nhận contract YAML. |
| `pytest` | 22 passed | 25 passed tại CP4 | [Output](evidence/01-pytest.txt); cần đối chiếu SHA commit nộp. |
| Số traces hợp lệ | 0 | Chưa có | Chưa cấu hình Langfuse cá nhân. |
| Số PII leak | 0 | 0 | CP4: 21 log records, 10 correlation IDs, [validator 100/100](evidence/02-log-validator.txt). |
| Latency P95 / TTFT P95 | Chưa ghi | 152 ms / 50 ms | Từ 10 request CP0 hiện tại. |
| Retrieval success rate | Chưa ghi | 100% trên 19 request trong cửa sổ 60 phút | Dashboard runtime local, chưa có incident. |

### Ghi nhận CP0 hiện tại

Vì working copy đã có thay đổi CP1/CP2 trước khi chạy CP0, baseline được **tái hiện từ commit starter `2073168` trong worktree tạm**, không phải ảnh chụp tại thời điểm trước khi sửa: log validator 30/100, dashboard 6/6, pytest 22 passed. Output và phương pháp: [evidence/00-cp0-starter-baseline.txt](evidence/00-cp0-starter-baseline.txt). Lần chạy working copy hiện tại dùng API tại `127.0.0.1:8013` (cổng 8000 đang bận), 10/10 request HTTP 200; log validator 100/100, dashboard validator 6/6, PII leak 0, P95 152 ms và TTFT P95 50 ms. Chi tiết output: [evidence/00-cp0-runtime.txt](evidence/00-cp0-runtime.txt).

Langfuse chưa được cấu hình nên `/health` báo `tracing_enabled=false`; chưa có trace nào được tính vào số traces hợp lệ. Đây là kết quả runtime sau thay đổi, không phải evidence Langfuse hoặc baseline trước khi làm bài.

## 4. Logging và PII

- **Cách tạo/nhận và truyền correlation ID:** `CorrelationIdMiddleware` xóa context cũ, nhận header `x-request-id` hợp lệ hoặc sinh `req-<8 hex>`, bind vào structlog context, lưu ở `request.state` và trả cùng ID qua response header. Header `x-response-time-ms` đo thời gian xử lý.
- **Các metadata được ghi vào structured log:** `user_id_hash`, `session_id` đã hash, `feature`, `model`, `env`, `correlation_id`, latency, TTFT, token, cost, quality proxy và trạng thái tool.
- **Cách bảo đảm PII được scrub trước khi ghi:** `scrub_event` đi qua mọi string lồng nhau trước `JsonlFileProcessor` và JSON renderer; `summarize_text` cũng scrub trước khi tạo preview. Pattern gồm email, điện thoại VN, CCCD, thẻ, hộ chiếu và địa chỉ có nhãn.
- **Cách kiểm chứng kết quả:** Chuyển log cũ ra ngoài repo, restart API, chạy lại workload và sáu request chứa PII giả. Kiểm tra header tự sinh `req-c932973a`, header được truyền `req-abcdef12`, cả hai khớp với body và có response time. `pytest -q tests/test_pii.py`: 4 passed.

CP1 runtime trên log mới: 37 record, thiếu field bắt buộc 0, thiếu context 0, 18 correlation ID, PII leak 0, điểm ước tính 100/100. Output log đã scrub ở [evidence/05-pii-redaction.txt](evidence/05-pii-redaction.txt), cặp JSON request/response ở [evidence/04-structured-log.txt](evidence/04-structured-log.txt).

## 5. Tracing và prompt versioning

- **Cách xác nhận traces do chính tôi tạo trong project cá nhân:** Chưa thể xác nhận: `.env` chưa có Langfuse key. Sau khi cấu hình, lọc project cá nhân, kiểm tra ≥10 trace của workload mới cùng thời gian và `correlation_id` trong log.
- **Cấu trúc root/retrieval/generation observations:** `lab-agent-run` dùng `@observe(as_type="agent")`; `retrieve` là child `retriever`; `FakeLLM.generate` là child `generation`. Cả ba tắt capture input/output thô. Generation ghi model, usage, cost và truyền prompt object Langfuse bằng `prompt=`.
- **Cách nối trace với log:** `correlation_id` trong response/log được truyền vào trace metadata qua `propagate_attributes`; `user_id` và `session_id` được hash.
- **Prompt name:** `day13-chat`.
- **Version/label baseline:** Đã chuẩn bị nội dung ở [`prompts/day13-chat-v1.txt`](../prompts/day13-chat-v1.txt); chưa tạo trên Langfuse.
- **Version/label candidate:** Đã chuẩn bị nội dung ở [`prompts/day13-chat-v2.txt`](../prompts/day13-chat-v2.txt); chưa tạo trên Langfuse.
- **Trace ID của mỗi version:** Chưa có.
- **Cách promote và rollback `production`:** Chưa thực hiện. Sau khi tạo v1/v2, dời `production` v1 → v2, restart API và gửi request; sau đó dời về v1, restart và gửi request xác nhận. Cần lưu trace ID và ảnh hai trạng thái.

## 6. Dashboard, SLO và alerts

- **Dashboard và sáu panel:** Dashboard local tại `/dashboard` đọc `data/logs.jsonl`, dùng 60 phút gần nhất và refresh 30 giây. Sáu panel là latency (P50/P95/P99/TTFT P95), traffic, errors/retrieval success, cost, tokens và quality; mỗi panel có đơn vị và threshold từ `config/dashboard.yaml`. [Ảnh dashboard](evidence/11-dashboard-overview.png) được chụp từ API thật sau 10 request mới: 20 request trong cửa sổ 60 phút, P95 154 ms, error 0%, retrieval success 100%; [JSON snapshot trước đó](evidence/11-dashboard-runtime.txt) có 19 request.
- **SLO và lý do chọn:** [config/slo.yaml](../config/slo.yaml) đặt 99.5% request thành công trong 28 ngày với latency ≤3000 ms. CP0 local P95 152 ms, TTFT P95 50 ms; ngưỡng 3000 ms khớp dashboard và alert.
- **Cách tính error budget:** 100% − 99.5% = 0.5%. Với 10,000 request trong cửa sổ 28 ngày, cho phép tối đa 50 request lỗi hoặc chậm hơn 3000 ms.
- **Ba alert và runbook tương ứng:** [HighLatencyP95, ElevatedErrorRate, LowRetrievalSuccess](../config/alert_rules.yaml) có duration 5/5/10 phút, severity, owner `student-2A202602522`, Slack `#k4-l3b-alerts`; [runbook](../docs/alerts.md) theo Metrics → Logs → Traces và nêu mitigation cho từng alert.

> Ví dụ cách viết error budget: "SLO 99.5% trong 28 ngày nghĩa là error budget 0.5%. Nếu workload có 10,000 request thì tối đa 50 request được phép lỗi hoặc chậm hơn ngưỡng SLO."

## 7. Điều tra challenge

- **Challenge ID:** File local ghi `day13-k4-l3b-monitoring-llmops-v1`, nhưng chưa có link/thông báo release để xác nhận nguồn; chưa chạy challenge chính thức.
- **Khoảng thời gian điều tra:** Chưa có incident. Baseline sạch được ghi lúc `2026-09-30T16:50:45Z` trên dashboard 60 phút; [output baseline](evidence/cp3-baseline.txt).
- **Triệu chứng từ metrics:** Chưa có incident để so sánh. Baseline server-side: latency P95 154 ms, TTFT P95 50 ms, error rate 0%, retrieval success 100%, 10 request.
- **Log line và correlation ID liên quan:** Chưa chọn request bất thường.
- **Trace ID và span gây ảnh hưởng:** Chưa có Langfuse key cá nhân; chưa có trace hợp lệ.
- **Root cause:** Chưa kết luận trước chuỗi bằng chứng Metrics → Logs → Traces.
- **Fix action:** Chờ challenge chính thức rồi xác định theo trace.
- **Preventive measure:** Chưa xác định từ incident chính thức.

Trước baseline, log cũ được chuyển ra ngoài repo, mọi practice incident đều `false`, và API chạy không có `--reload`. File `config/challenge.json` đã có sẵn trong lịch sử Git của fork; working copy hiện đã bỏ theo dõi file trong index nhưng giữ file local, để commit tiếp theo không chứa nội dung challenge.

> Gợi ý cách viết ngắn, không thay cho evidence thực tế: "Metric cho thấy `[latency/error/cost/quality]` bất thường trong `[khoảng thời gian]`. Log line `[event]` có `correlation_id=[...]` đại diện cho request bị ảnh hưởng. Trace cùng `correlation_id` cho thấy span `[retrieval/generation/prompt/tool]` có dấu hiệu `[chậm/lỗi/token tăng]`. Root cause là `[nguyên nhân suy ra từ evidence]`. Fix action là `[hành động khôi phục]`; preventive measure là `[alert/runbook/test/guardrail để ngăn tái diễn]`."

## 8. Giải thích và tự đánh giá

- **Một quyết định kỹ thuật quan trọng và lý do:** Dùng một `correlation_id` xuyên middleware, log và trace metadata; nhờ đó có thể chọn request từ log rồi mở đúng trace. Scrubber chạy sau format exception và trước ghi JSON để che cả thông báo lỗi.
- **Một lỗi/blocker đã gặp:** Cổng 8000 đang được ứng dụng khác dùng; fork còn theo dõi `config/challenge.json` từ lịch sử Git dù file nằm trong `.gitignore`. Langfuse key và link release chính thức chưa có.
- **Cách tìm nguyên nhân và xử lý:** Kiểm tra tiến trình giữ cổng 8000, chuyển API sang 8013 và thêm `--base-url` cho scripts. Dùng `git ls-files` phát hiện challenge đang tracked; bỏ theo dõi trong index, giữ file local. Không chạy challenge khi chưa xác nhận link.
- **Cách hiểu luồng Metrics → Logs → Traces:** Dashboard khoanh thời điểm và triệu chứng; JSON log chọn `correlation_id` của request bất thường; trace cùng ID chỉ ra observation retrieval hay generation chậm/lỗi. Root cause phải dựa trên cả ba tín hiệu.
- **Vai trò của prompt version, token/cost, SLO hoặc rollback trong vận hành LLM:** Prompt version gắn với từng trace để so sánh trước/sau thay đổi; token/cost phát hiện tăng chi phí dù HTTP 200; SLO 99.5% có error budget 50/10,000 request; rollback đưa label `production` về version ổn định khi có regression.
- **Điều quan trọng nhất đã học:** HTTP 200 riêng lẻ không cho thấy tail latency, token/cost hoặc chất lượng; cần dashboard và correlation ID để điều tra một request cụ thể.
- **Hạn chế hoặc phần chưa hoàn thành, nếu có:** Chưa có key/project Langfuse cá nhân nên chưa có ≥10 trace, prompt v1/v2 trên Cloud, promote/rollback hoặc ảnh 06–10/14. Chưa có link release challenge được xác nhận nên chưa chạy incident chính thức hoặc có ảnh 12–14. Dashboard 11 đã có ảnh PNG từ API thật. Evidence 04/05 là JSON text từ log thật, cần ảnh nếu giảng viên yêu cầu đúng định dạng.

## 9. Checklist trước khi nộp

- [ ] Kết quả và evidence thuộc commit SHA cuối.
- [ ] Tất cả ảnh/output mở được bằng đường dẫn tương đối.
- [ ] Incident evidence nối đúng metric → log → trace.
- [ ] Trace/prompt evidence thuộc project Langfuse cá nhân và ảnh không lộ key/secret.
- [ ] Repository chạy lại được theo README.
- [ ] Không có secret, API key, PII thô hoặc evidence của người khác/lớp khác.
- [ ] URL repo và commit SHA cuối đã được nộp trên LMS/Codelabs.
