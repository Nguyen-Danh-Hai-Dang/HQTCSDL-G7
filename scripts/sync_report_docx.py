from pathlib import Path
from docx import Document
from docx.text.paragraph import Paragraph
from docx.oxml import OxmlElement
from docx.shared import Pt

ROOT = Path(__file__).resolve().parents[1]
DOCX = ROOT / "report" / "bao_cao_HQTCSDL_G7.docx"

BENCHMARK_ROWS = [
    ("100k","MySQL","Q1","0.441","0.437","0.9%"),
    ("100k","MySQL","Q2","0.223","0.181","18.8%"),
    ("100k","MySQL","Q3","9.375","0.386","95.9%"),
    ("100k","MySQL","Q4","183.546","187.660","-2.2%"),
    ("100k","MySQL","Q5","22.922","16.497","28.0%"),
    ("100k","MySQL","Q6","27.562","21.407","22.3%"),
    ("100k","MySQL","Q7","0.213","0.244","-14.7%"),
    ("100k","MySQL","Q8","19.922","12.838","35.6%"),
    ("100k","MongoDB","Q1","0.157","0.152","3.1%"),
    ("100k","MongoDB","Q2","31.187","0.243","99.2%"),
    ("100k","MongoDB","Q3","35.723","0.409","98.9%"),
    ("100k","MongoDB","Q4","295.364","327.647","-10.9%"),
    ("100k","MongoDB","Q5","55.405","14.307","74.2%"),
    ("100k","MongoDB","Q6","80.595","40.301","50.0%"),
    ("100k","MongoDB","Q7","0.531","0.530","0.3%"),
    ("100k","MongoDB","Q8","51.788","14.463","72.1%"),
    ("1M","MySQL","Q1","1.060","0.987","6.8%"),
    ("1M","MySQL","Q2","0.490","0.447","8.7%"),
    ("1M","MySQL","Q3","160.858","0.959","99.4%"),
    ("1M","MySQL","Q4","3049.647","3160.366","-3.6%"),
    ("1M","MySQL","Q5","412.866","286.763","30.5%"),
    ("1M","MySQL","Q6","472.748","351.112","25.7%"),
    ("1M","MySQL","Q7","0.496","0.498","-0.4%"),
    ("1M","MySQL","Q8","377.022","238.862","36.6%"),
    ("1M","MongoDB","Q1","0.387","0.408","-5.5%"),
    ("1M","MongoDB","Q2","584.627","0.524","99.9%"),
    ("1M","MongoDB","Q3","559.381","0.745","99.9%"),
    ("1M","MongoDB","Q4","4548.580","4884.114","-7.4%"),
    ("1M","MongoDB","Q5","813.981","227.972","72.0%"),
    ("1M","MongoDB","Q6","1220.147","632.492","48.2%"),
    ("1M","MongoDB","Q7","0.796","0.805","-1.2%"),
    ("1M","MongoDB","Q8","831.448","243.674","70.7%"),
]

def insert_paragraph_before(target, text, style=None):
    element = OxmlElement("w:p")
    target._p.addprevious(element)
    paragraph = Paragraph(element, target._parent)
    if style:
        paragraph.style = style
    paragraph.add_run(text)
    return paragraph

def replace_first(paragraphs, fragment, replacement):
    for p in paragraphs:
        if fragment in p.text:
            style = p.style
            p.clear()
            p.style = style
            p.add_run(replacement)
            return True
    print("Paragraph not found:", fragment)
    return False

def insert_benchmark_table(doc, target):
    title = insert_paragraph_before(
        target,
        "12. KẾT QUẢ BENCHMARK VÀ TRẢ LỜI RQ5–RQ6",
        "Heading 1"
    )
    insert_paragraph_before(
        target,
        "Benchmark GitHub Actions run #7 (commit d3e52159) sử dụng hai quy mô: "
        "100.000 và 1.000.000 đơn. Mỗi truy vấn có 5 lượt warm-up và 30 lượt đo, "
        "một client tuần tự. Runner Ubuntu có 4 logical CPU và khoảng 16 GB RAM; "
        "MySQL 8.4.13 và MongoDB 8.0.38 được cấu hình cache 1 GiB mỗi hệ. "
        "CPU model lần lượt là AMD EPYC 9V45 và AMD EPYC 7763."
    )
    insert_paragraph_before(
        target,
        "Baseline giữ các index bắt buộc của schema/constraint nhưng chưa có "
        "workload secondary index; Indexed bổ sung bộ secondary index phục vụ Q1–Q8. "
        "Cardinality Q1–Q8 khớp giữa hai DBMS ở cả hai chế độ. Bảng dùng median "
        "latency (ms); số âm ở cột cuối nghĩa là latency tăng sau khi thêm index."
    )
    insert_paragraph_before(target, "Median latency baseline/indexed (ms)", "Heading 2")
    table = doc.add_table(rows=1, cols=6)
    table.style = "Table Grid"
    headers = ["Quy mô", "DBMS", "Query", "Baseline (ms)", "Indexed (ms)", "Giảm latency"]
    for cell, value in zip(table.rows[0].cells, headers):
        cell.text = value
    for row in BENCHMARK_ROWS:
        cells = table.add_row().cells
        for cell, value in zip(cells, row):
            cell.text = value
    target._p.addprevious(table._tbl)
    insert_paragraph_before(
        target,
        "Q3 cải thiện mạnh ở cả hai DBMS; MongoDB Q2 cũng giảm rất lớn. Q5, Q6 và "
        "Q8 được cải thiện ở các mức khác nhau. Q4 chậm hơn sau khi thêm index, còn "
        "Q1/Q7 thay đổi nhỏ và cần được nhìn nhận trong giới hạn độ nhiễu đo."
    )
    insert_paragraph_before(
        target,
        "Index build time: ở 100.000 đơn, MySQL 0,767 giây và MongoDB 1,051 giây; "
        "ở 1.000.000 đơn, lần lượt 6,767 giây và 10,271 giây. Tổng index bytes "
        "baseline → indexed: 100.000 đơn, MySQL 19,12 → 21,25 MB và MongoDB "
        "5,12 → 11,18 MB; 1.000.000 đơn, MySQL 162,68 → 185,70 MB và MongoDB "
        "40,28 → 106,23 MB."
    )
    insert_paragraph_before(
        target,
        "Giới hạn: 10.000.000 đơn chưa được benchmark vì file dữ liệu thô ước lượng "
        "khoảng 7 GB, chưa tính database files và index. Hai quy mô được chạy trên "
        "CPU model khác nhau nên không dùng chênh lệch tuyệt đối để suy ra scaling. "
        "CI dùng một client tuần tự, không đo throughput đồng thời, CPU, I/O hoặc "
        "cache hit/miss. Raw CSV, summary CSV và metadata được lưu trong artifact "
        "benchmark-s và benchmark-m của GitHub Actions run #7."
    )

def main():
    if not DOCX.exists():
        raise SystemExit(f"Missing report: {DOCX}")

    doc = Document(DOCX)

    # Remove the earlier text-only duplicate; retain the section that contains the table.
    headings = [
        p for p in doc.paragraphs
        if p.text.strip() == "12. KẾT QUẢ BENCHMARK VÀ TRẢ LỜI RQ5–RQ6"
    ]
    if len(headings) > 1:
        paragraphs = list(doc.paragraphs)
        first_index = next(i for i, p in enumerate(paragraphs) if p._p is headings[0]._p)
        second_index = next(i for i, p in enumerate(paragraphs) if p._p is headings[1]._p)
        for p in paragraphs[first_index:second_index]:
            p._element.getparent().remove(p._element)

    paragraphs = list(doc.paragraphs)

    replace_first(
        paragraphs,
        "Vì vậy, báo cáo trả lời đầy đủ khía cạnh lý thuyết",
        "RQ4 và RQ5 đã có bằng chứng định lượng ở hai quy mô 100.000 và "
        "1.000.000 đơn. RQ6 mới có kết quả ở hai mức này, chưa đủ để kết "
        "luận xu hướng ở 10 triệu đơn. Khuyến nghị RQ7 phụ thuộc workload, "
        "mô hình dữ liệu, index và tài nguyên triển khai."
    )
    replace_first(
        paragraphs,
        "Đề cương yêu cầu ma trận hai DBMS nhân với các cấu hình index",
        "Trong phạm vi cấu hình đã thử, workload secondary index làm giảm "
        "median latency của phần lớn truy vấn, nhưng mức cải thiện khác "
        "nhau theo query và DBMS. Benchmark chỉ so sánh một bộ secondary "
        "index với baseline; chưa tách riêng đóng góp của từng index đơn, "
        "compound, covering hoặc multikey. Không có cơ sở kết luận DBMS "
        "nào nhanh hơn một cách tổng quát."
    )
    replace_first(
        paragraphs,
        "Vì chỉ có một mức pilot và không có số liệu latency theo quy mô",
        "Đã benchmark hai quy mô 100.000 và 1.000.000 đơn. Không thể xem "
        "chênh lệch latency giữa hai mức là phép đo scaling hoàn toàn "
        "được kiểm soát vì CPU model của hai runner khác nhau. Mức "
        "10.000.000 đơn chưa chạy do file thô ước lượng khoảng 7 GB, "
        "chưa tính database files và index."
    )
    replace_first(
        paragraphs,
        "12.1. Kế hoạch đo bổ sung",
        "12.2. Giới hạn diễn giải và kế hoạch tiếp theo"
    )

    # Remove the obsolete benchmark plan bullets and insert current limitations.
    obsolete = (
        "Tạo ba mức dữ liệu đã chốt",
        "Mỗi mức chạy hai DBMS với cùng bộ tham số",
        "Warm-up, chạy tối thiểu nhiều lần",
        "Đo riêng read, write, import",
        "Lưu explain, raw CSV"
    )
    for p in list(doc.paragraphs):
        if any(p.text.strip().startswith(prefix) for prefix in obsolete):
            p._element.getparent().remove(p._element)

    rq7_heading = next(
        (p for p in doc.paragraphs if p.text.strip().startswith("13. RQ7")),
        None
    )
    if rq7_heading:
        insert_paragraph_before(
            rq7_heading,
            "sequential_ops_per_second trong summary là nghịch đảo mean latency "
            "cho một client tuần tự, không phải throughput dưới tải đồng thời. "
            "CI chưa thu CPU utilization, I/O throughput hoặc cache hit ratio "
            "trong từng truy vấn."
        )
        insert_paragraph_before(
            rq7_heading,
            "p95/p99 và 30 mẫu latency được lưu trong raw/summary CSV của "
            "artifact GitHub Actions run #7. Kết luận chính sử dụng median. "
            "Muốn đánh giá production cần đo concurrency, tải hỗn hợp đọc/ghi, "
            "cold-cache và nhiều lần lặp trên cùng phần cứng."
        )
        insert_paragraph_before(
            rq7_heading,
            "Các bước còn lại là chạy mức 10 triệu đơn trên máy đủ dung lượng, "
            "tách riêng từng loại secondary index và đo thêm tài nguyên hệ thống."
        )

    # Correct numbering and update the limitations section.
    replace_first(
        paragraphs,
        "13. HẠN CHẾ, HƯỚNG PHÁT TRIỂN VÀ KẾT LUẬN",
        "14. HẠN CHẾ, HƯỚNG PHÁT TRIỂN VÀ KẾT LUẬN"
    )
    replace_first(
        paragraphs,
        "Môi trường kiểm thử là một máy Windows",
        "Chưa thử sharding hoặc cụm nhiều máy; benchmark đọc được chạy trên "
        "runner GitHub Actions riêng."
    )
    replace_first(
        paragraphs,
        "Không có đầy đủ log CPU, RAM, I/O, cache, concurrency",
        "CI ghi nhận CPU model, số logical CPU, RAM tổng và cấu hình cache; "
        "chưa thu CPU utilization, I/O và cache hit/miss theo từng truy vấn."
    )
    replace_first(
        paragraphs,
        "Các bản script vừa được chỉnh cần chạy nghiệm thu lại",
        "CI tích hợp nghiệp vụ chạy trên fixture nhỏ; chưa thay thế kiểm thử "
        "lại toàn bộ pilot trên máy nhóm."
    )

    # Refresh the future-work list.
    replace_first(
        paragraphs,
        "Bổ sung harness benchmark chung cho MySQL và MongoDB",
        "Chạy benchmark 10 triệu đơn trên máy/VM đủ dung lượng và RAM, giữ "
        "phần cứng cố định giữa các quy mô."
    )
    replace_first(
        paragraphs,
        "Tách các mức index và kiểm soát index bắt buộc",
        "Tách cấu hình index đơn, compound, covering và multikey để đánh giá "
        "đóng góp riêng của từng index."
    )
    replace_first(
        paragraphs,
        "Đo warm/cold cache, concurrency, throughput",
        "Đo warm/cold cache, concurrency, throughput và latency percentiles."
    )
    replace_first(
        paragraphs,
        "Chạy các mức dữ liệu theo khả năng tài nguyên",
        "Thu thập CPU, RAM, I/O, cache hit/miss, chi phí import và dung lượng "
        "database/index."
    )

    # Update appendix interpretation notes.
    replace_first(
        paragraphs,
        "Mọi con số pilot trong báo cáo là kết quả kiểm thử chức năng",
        "Số liệu pilot 1.000 đơn là kết quả kiểm thử chức năng. Số liệu "
        "latency trong mục 12 lấy từ artifact benchmark GitHub Actions run #7, "
        "gồm raw CSV, summary CSV, metadata phần cứng/phần mềm và index build "
        "time. Mỗi truy vấn có 30 mẫu sau 5 lượt warm-up. CPU utilization, I/O "
        "và cache hit/miss chưa được thu thập."
    )
    replace_first(
        paragraphs,
        "Báo cáo này là bản tổng hợp kỹ thuật trung thực theo bằng chứng hiện có",
        "Benchmark chỉ áp dụng cho hai quy mô 100.000 và 1.000.000 đơn, hai "
        "cấu hình index đã thử và môi trường CI được mô tả trong báo cáo. "
        "Quy mô 10 triệu đơn chưa được benchmark."
    )

    # Verify the Word file contains exactly one complete benchmark table.
    benchmark_tables = [
        table for table in doc.tables
        if len(table.columns) == 6
        and len(table.rows) == 33
        and table.rows[0].cells[3].text.strip() == "Baseline (ms)"
        and table.rows[0].cells[4].text.strip() == "Indexed (ms)"
    ]
    if len(benchmark_tables) != 1:
        raise SystemExit(
            f"Expected exactly one 32-row benchmark table, found {len(benchmark_tables)}"
        )

    doc.core_properties.comments = (
        "Word report synchronized with benchmark run #7; 100k and 1M measured, "
        "10M explicitly not run."
    )
    doc.save(DOCX)
    print(f"Updated {DOCX}")
    print("Verified benchmark table rows:", len(benchmark_tables[0].rows) - 1)


if __name__ == "__main__":
    main()
