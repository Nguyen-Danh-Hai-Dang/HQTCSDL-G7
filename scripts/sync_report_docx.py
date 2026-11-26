from pathlib import Path
from docx import Document
from docx.text.paragraph import Paragraph
from docx.oxml import OxmlElement
from docx.shared import Pt

ROOT = Path(__file__).resolve().parents[1]
DOCX = ROOT / "report" / "bao_cao_HQTCSDL_G7.docx"

def insert_paragraph_before(target, text, style=None):
    element = OxmlElement("w:p")
    target._p.addprevious(element)
    paragraph = Paragraph(element, target._parent)
    if style:
        paragraph.style = style
    paragraph.add_run(text)
    return paragraph

def insert_bullet_before(target, text):
    return insert_paragraph_before(target, text, "List Bullet")

def main():
    if not DOCX.exists():
        raise SystemExit(f"Missing report: {DOCX}")

    doc = Document(DOCX)
    paragraphs = list(doc.paragraphs)

    # Bring the abstract up to date if it still says the corrected scripts
    # have not yet been validated.
    for p in paragraphs:
        t = p.text.strip()
        if "cần được chạy xác nhận lại trên môi trường của nhóm" in t:
            p.clear()
            p.add_run(
                "Các script đã được chỉnh theo hướng kiểm tra đầu vào, transaction "
                "và rollback. Ba job GitHub Actions đã PASS trên PR head được merge: "
                "generator, MySQL 8.4 và MongoDB 8.0 replica set. Các job xác nhận "
                "những nhánh nghiệp vụ trọng yếu trên fixture nhỏ, không thay thế "
                "benchmark hoặc kiểm thử toàn bộ pilot."
            )

    # Replace an old CI claim when this subsection already exists.
    for p in paragraphs:
        if "Cả ba job đều PASS trên commit" in p.text or "8f42f2c" in p.text:
            p.clear()
            p.add_run(
                "Cả ba job đều PASS trong GitHub Actions run #38 trên PR head commit "
                "32b123b1a660e8cd90f4c1e2f0b7abcc5a8c7f4b. PR #1 sau đó được merge "
                "vào main bằng merge commit ef47d88dc29bbcb6738868e1ad1bd861b6939d27. "
                "Workflow chạy theo pull request nên run #38 xác nhận nội dung head "
                "đã được merge, không phải một lần chạy mới trên merge commit."
            )

    all_text = "\n".join(p.text for p in doc.paragraphs)
    if "Kiểm thử hồi quy tự động trên commit đã merge" not in all_text:
        target = None
        for p in doc.paragraphs:
            normalized = " ".join(p.text.upper().split())
            if normalized.startswith("10. EXECUTION PLAN") or normalized.startswith("10. EXECUTION PLAN VÀ"):
                target = p
                break

        if target is None:
            target = doc.paragraphs[-1] if doc.paragraphs else None

        if target is None:
            doc.add_heading("9.2. Kiểm thử hồi quy tự động trên commit đã merge", level=2)
        else:
            insert_paragraph_before(
                target,
                "9.2. Kiểm thử hồi quy tự động trên commit đã merge",
                "Heading 2"
            )
            insert_paragraph_before(
                target,
                "GitHub Actions run #38 (27/11/2026 theo UTC của hệ thống CI) chạy trên "
                "PR head commit 32b123b1a660e8cd90f4c1e2f0b7abcc5a8c7f4b. PR #1 đã "
                "được merge vào main bằng merge commit ef47d88dc29bbcb6738868e1ad1bd861b6939d27."
            )
            insert_bullet_before(
                target,
                "Generator: sinh pilot 1.000 đơn; kiểm tra inventory row đúng cửa hàng, "
                "không trùng sản phẩm trong một đơn và CSV/JSONL tái lập."
            )
            insert_bullet_before(
                target,
                "MySQL 8.4: W1 nhiều dòng, tổng payment và tồn kho, rollback toàn bộ khi "
                "thiếu hàng ở bước cập nhật sau; W3 thành công và từ chối tràn INT."
            )
            insert_bullet_before(
                target,
                "MongoDB 8.0 replica set: W1 transaction nhiều dòng và rollback, W2 "
                "chuyển trạng thái đơn/payment, W3 thành công và từ chối tràn INT32."
            )
            insert_paragraph_before(
                target,
                "Giới hạn: đây là kiểm thử tích hợp trên fixture nhỏ, không phải kiểm "
                "thử lại toàn bộ pilot, không xác nhận Q1–Q8 trên commit mới và không "
                "phải benchmark latency/throughput."
            )

    doc.core_properties.comments = (
        "Đồng bộ phần xác nhận CI với report/bao_cao_HQTCSDL_G7.md sau khi PR #1 merge."
    )
    doc.save(DOCX)
    print(f"Updated {DOCX}")

if __name__ == "__main__":
    main()
