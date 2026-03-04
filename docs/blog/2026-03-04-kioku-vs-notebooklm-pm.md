# Kioku vs NotebookLM: Công cụ nào phù hợp hơn cho PM cần hỏi đáp về daily notes?

*Xuất bản: 2026-03-04 · Chủ đề: So sánh công cụ*

---

Giả sử bạn là một PM. Bạn viết daily notes mỗi ngày — ai làm gì, issue nào mới phát sinh, quyết định nào được đưa ra, ai là người gây tắc nghẽn. Sau 4 tháng, bạn có một kho tư liệu khổng lồ và cần trả lời những câu hỏi như:

- *"Issue nổi bật nhất Q4 là gì và nguyên nhân từ đâu?"*
- *"Stakeholder nào cần chú ý nhất trong dự án Phoenix?"*
- *"Bài học rút ra từ lần deploy thất bại tháng 11?"*
- *"Alice và team Backend có liên quan thế nào đến deadline trượt?"*

Hai công cụ phổ biến nhất hiện nay cho bài toán này: **NotebookLM** của Google và **Kioku**. Cả hai đều dùng AI để hỏi đáp trên dữ liệu của bạn — nhưng theo cách hoàn toàn khác nhau.

---

## NotebookLM: "Trợ lý đọc tài liệu"

NotebookLM hoạt động theo mô hình RAG đơn giản: bạn upload notes (PDF, Google Docs, text), rồi chat với Gemini về nội dung đó. Thế mạnh là giao diện conversational rất tự nhiên, không cần setup.

**Những gì NotebookLM làm tốt với PM notes:**

Upload 4 tháng daily notes rồi hỏi *"Tóm tắt các rủi ro lớn nhất trong Q4"* — bạn sẽ nhận được một bản tóm tắt khá tốt, viết theo ngôn ngữ báo cáo, có thể copy thẳng vào email stakeholder. Tương tự với *"Viết executive summary cho Q1"* hay *"Những điểm nổi bật tháng 12"* — đây là điểm mạnh rõ ràng của NotebookLM.

**Nhưng có một số bài toán NotebookLM không xử lý tốt:**

Hỏi *"Alice bị block bởi bao nhiêu issue từ team Backend trong suốt 4 tháng?"* — NotebookLM sẽ tổng hợp text, nhưng không có cơ chế đếm chính xác cross-entry. Kết quả phụ thuộc vào cách Gemini interpret câu hỏi, không nhất quán giữa các lần hỏi.

Tệ hơn, hỏi *"Nguyên nhân sâu xa của Bug #47 là gì?"* khi nguyên nhân nằm ở note ngày thứ 3, hệ quả xuất hiện ở note ngày thứ 17, và link nhân quả không được viết rõ ràng trong text — NotebookLM không có cách nào trace được. Nó chỉ đọc văn bản, không build graph.

Một vấn đề thực tế nữa: khi có notes mới, bạn phải re-upload. Không có incremental update.

---

## Kioku: "Trí nhớ có cấu trúc tích lũy theo thời gian"

Kioku không phải RAG trên file tĩnh. Kioku là một **memory engine có Knowledge Graph** — mỗi entry được lưu kèm entities và relationships, tạo thành một mạng lưới có thể traverse được.

Với PM workflow, agent sẽ:
1. `save` — lưu text của daily note vào SQLite (BM25 + vector)
2. `kg-index` — extract entities (`PERSON`, `PROJECT`, `ISSUE`, `DECISION`) và relationships (`CAUSED_BY`, `BLOCKED_BY`, `LED_TO`) → lưu vào Knowledge Graph

Sau 4 tháng, bạn có một graph với ~200 entities và ~600 relationships, tất cả linked qua `source_hash` về entry gốc với timestamp chính xác.

**Những gì Kioku làm tốt hơn:**

```
kioku-lite entities --sort mention_count --limit 20
```
→ Ngay lập tức biết Alice xuất hiện 47 lần, team Backend 31 lần, Bug #47 xuất hiện 12 lần. Đây là **stakeholder ranking khách quan**, không phụ thuộc vào cách AI interpret câu hỏi.

```
kioku-lite connect "Bug47" "DeploymentDecision"
```
→ BFS trong graph trả về path: `Bug47 → CAUSED_BY → MissingValidation → INTRODUCED_IN → Sprint23Commit → APPROVED_BY → DeploymentDecision`. Trace được chuỗi nhân quả ngay cả khi không entry nào viết rõ mối liên hệ này.

```
kioku-lite search "deadline trượt" --entities "Alice,BackendTeam" --from 2025-10-01 --to 2026-01-31
```
→ Multi-entity intersection: chỉ trả về memories liên quan đến cả Alice *và* BackendTeam trong khoảng thời gian đó — không phải mọi entry về deadline trượt.

**Những gì Kioku không làm được:**

Kioku không viết báo cáo. Không có conversational interface tự nhiên. Bạn cần agent (Claude Code, Cursor, OpenClaw...) để interpret kết quả và tổng hợp thành văn bản.

Và quan trọng hơn: **Kioku yêu cầu agent chạy `kg-index` cho từng note**. Nếu bạn đã có 4 tháng notes cũ chưa được index, phải batch-import thủ công — không upload được như NotebookLM.

---

## So sánh trực tiếp theo từng câu hỏi PM

| Câu hỏi | NotebookLM | Kioku |
|---|---|---|
| "Tóm tắt issue Q4" | ✅ Tốt | ✅ Tốt |
| "Viết executive summary" | ✅✅ Xuất sắc | ❌ Không phải mục tiêu |
| "Nguyên nhân sâu của Bug #47" | ⚠️ Chỉ nếu text viết rõ | ✅✅ Graph traversal |
| "Stakeholder nào cần chú ý nhất" | ⚠️ Không nhất quán | ✅✅ `mention_count` định lượng |
| "Alice liên quan thế nào đến Phoenix" | ⚠️ Tổng hợp text | ✅✅ `connect` trả về path |
| "Lesson learned từ deploy tháng 11" | ✅ Tốt | ✅ Tốt (nếu dùng LESSON entity) |
| Thêm notes mới mỗi ngày | ❌ Re-upload | ✅✅ Incremental |
| Data ở trên device | ❌ Google cloud | ✅ 100% local |
| Share với stakeholder khác | ✅✅ Dễ dàng | ❌ Không có |

---

## Vậy dùng cái nào?

**Dùng NotebookLM nếu:**
- Bạn đã có 4 tháng notes và muốn phân tích ngay hôm nay, không setup gì thêm
- Mục tiêu chính là viết báo cáo, summary, executive brief cho stakeholder
- Bạn cần share kết quả với người khác trong team
- Bạn chấp nhận data lên Google

**Dùng Kioku nếu:**
- Bạn đang xây PM workflow từ đầu và muốn agent tự index notes hàng ngày
- Câu hỏi quan trọng nhất là về relationship, causal chain, stakeholder ranking
- Data nhạy cảm, cần giữ offline
- Bạn đã có agent (Claude Code, OpenClaw...) trong workflow

**Kết hợp cả hai (approach thực tế nhất):**

Dùng Kioku làm *operational memory* — agent index notes mỗi ngày, query khi cần tra cứu relationship hoặc stakeholder. Dùng NotebookLM theo định kỳ (cuối sprint, cuối tháng) — upload notes của giai đoạn đó để viết báo cáo tổng hợp gửi stakeholder.

Hai công cụ không cạnh tranh nhau. Chúng giải quyết hai vấn đề khác nhau: Kioku cho **trí nhớ có cấu trúc tích lũy**, NotebookLM cho **tổng hợp tài liệu tĩnh**.

---

*Kioku hiện tại là personal memory engine cho AI agents — không phải tool PM chuyên dụng. Use case PM ở trên là một trong nhiều domain mà tri-hybrid search + Knowledge Graph có thể áp dụng. Nếu bạn đang thử nghiệm Kioku cho PM workflow, rất muốn nghe feedback!*

- GitHub: [github.com/phuc-nt/kioku-agent-kit-lite](https://github.com/phuc-nt/kioku-agent-kit-lite)
- Homepage: [phuc-nt.github.io/kioku-lite-landing](https://phuc-nt.github.io/kioku-lite-landing/)
