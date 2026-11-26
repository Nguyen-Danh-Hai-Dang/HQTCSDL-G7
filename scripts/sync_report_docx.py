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
    paragraphs = list(doc.paragraphs)

    # Refresh the abstract and existing RQ conclusions.
    replace_first(
        paragraphs,
        "Chưa có bộ số liệu latency/throughput",
        "Benchmark GitHub Actions đã đo Q1–Q8 ở 100.000 và 1.000.000 đơn, "
        "mỗi truy vấn 30 lần sau 5 lượt warm-up. Kết quả cho thấy secondary "
        "index cải thiện mạnh một số truy vấn, đặc biệt Q3 và MongoDB Q2; "
        "Q4 không cải thiện. Quy mô 10.000.000 đơn chưa được chạy."
    )
    replace_first(
        paragraphs,
        "chưa có ma trận đo thời gian trước/sau index",
        "Benchmark run #7 cho thấy median Q3 giảm từ 9,375 xuống 0,386 ms "
        "ở MySQL và 35,723 xuống 0,409 ms ở MongoDB tại 100.000 đơn; tại "
        "1.000.000 đơn, Q3 giảm từ 160,858 xuống 0,959 ms và 559,381 xuống "
        "0,745 ms tương ứng. MongoDB Q2 giảm từ 584,627 xuống 0,524 ms ở "
        "quy mô một triệu đơn. Q4 chậm hơn sau khi thêm index."
    )
    replace_first(
        paragraphs,
        "Không có bộ benchmark latency/throughput",
        "Đã có kết quả định lượng baseline/indexed ở 100.000 và 1.000.000 đơn. "
        "Tuy nhiên, chỉ một bộ workload secondary index được thử; chưa tách "
        "riêng đóng góp của từng index đơn, compound, covering và multikey. "
        "Không có cơ sở kết luận DBMS nào nhanh hơn một cách tổng quát."
    )
    replace_first(
        paragraphs,
        "Mức 100 nghìn trở lên chưa được chạy benchmark",
        "Benchmark đã chạy ở 100.000 và 1.000.000 đơn. Mức 10.000.000 đơn "
        "chưa chạy do file thô ước lượng khoảng 7 GB, chưa tính database "
        "files và index. Hai quy mô chạy trên CPU model khác nhau nên không "
        "thể dùng chênh lệch tuyệt đối để kết luận scaling."
    )
    replace_first(
        paragraphs,
        "Chỉ pilot 1.000 đơn được xác nhận",
        "Benchmark latency được xác nhận ở hai quy mô 100.000 và 1.000.000 "
        "đơn; chưa chạy 10.000.000 đơn do giới hạn dung lượng runner."
    )
    replace_first(
        paragraphs,
        "Tuy nhiên, câu hỏi về mức cải thiện thời gian truy vấn",
        "Benchmark có kiểm soát ở 100.000 và 1.000.000 đơn cung cấp bằng "
        "chứng định lượng về ảnh hưởng của workload secondary index. Index "
        "cải thiện mạnh Q3 và MongoDB Q2, cải thiện Q5/Q6/Q8 ở các mức độ "
        "khác nhau, nhưng Q4 chậm hơn và Q1/Q7 gần như không đổi. Chưa có "
        "kết quả 10 triệu đơn nên không kết luận về giới hạn mở rộng ở quy mô đó."
    )

    # Update the section heading and add the measured result table once.
    for p in doc.paragraphs:
        if "RQ5 VÀ RQ6: GIỚI HẠN BẰNG CHỨNG THỰC NGHIỆM" in p.text:
            p.clear()
            p.add_run("12. KẾT QUẢ BENCHMARK VÀ TRẢ LỜI RQ5–RQ6")
        if "14. HẠN CHẾ, HƯỚNG PHÁT TRIỂN VÀ KẾT LUẬN" in p.text:
            p.clear()
            p.add_run("13. HẠN CHẾ, HƯỚNG PHÁT TRIỂN VÀ KẾT LUẬN")

    all_text = "\n".join(p.text for p in doc.paragraphs)
    if "Median latency baseline/indexed (ms)" not in all_text:
        target = None
        for p in doc.paragraphs:
            if "RQ5. Có/không có Index" in p.text or "RQ5. Có/không có workload" in p.text:
                target = p
                break
        if target is None:
            target = doc.paragraphs[-1]
        insert_benchmark_table(doc, target)

    doc.core_properties.comments = (
        "Đồng bộ kết quả benchmark run #7 (100k/1M) với report Markdown; "
        "10M chưa chạy và được nêu rõ là giới hạn."
    )
    doc.save(DOCX)
    print(f"Updated {DOCX}")

if __name__ == "__main__":
    main()
