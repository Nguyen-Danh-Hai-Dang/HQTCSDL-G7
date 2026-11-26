# So sánh MySQL và MongoDB trong hệ thống quản lý bán hàng

> Project học phần Hệ quản trị cơ sở dữ liệu. Mục tiêu là so sánh mô hình dữ liệu, truy vấn, chỉ mục và thao tác ghi trên MySQL và MongoDB bằng cùng một bộ dữ liệu tổng hợp.

## 1. Mục tiêu và phạm vi

Project triển khai cùng một miền nghiệp vụ bán hàng trên hai hệ quản trị:

- **MySQL 8.x**: mô hình quan hệ chuẩn hoá, 8 bảng, khoá chính, khoá ngoại và các index phục vụ workload.
- **MongoDB 8.x**: document model, 6 collections, nhúng `items` và `payments` trong `orders`, tham chiếu thực thể dùng chung bằng ID.
- **Python**: sinh một bộ dữ liệu logic và xuất đồng thời CSV cho MySQL, Extended JSON Lines cho MongoDB.
- **Workload**: 8 truy vấn đọc (Q1–Q8), 3 thao tác ghi (W1–W3), kiểm tra tính đúng đắn và xem execution plan.

Dữ liệu là **dữ liệu tổng hợp**, không phải giao dịch của cửa hàng thật. Phân phối Zipf và tỷ lệ trạng thái là giả định mô phỏng, không được diễn giải thành thống kê thị trường.

## 2. Thành viên và phân công

| Thành viên | Phần việc chính |
|---|---|
| Nguyễn Danh Hải Đăng | Trưởng nhóm; lý thuyết Index; RQ2, RQ3, RQ7; phân tích execution plan, tổng hợp, kết luận, khuyến nghị và hạn chế |
| Lê Quang Vinh | MySQL/MongoDB; mô hình dữ liệu; schema, truy vấn, index, execution plan; RQ1, RQ4 |
| Lưu Trung Trực | Dataset, workload, benchmark, đo lường, trực quan hóa; RQ5, RQ6 |

## 3. Cấu trúc repository

```text
.
├── 01_mysql_schema.sql
├── 02_mysql_indexes.sql
├── 03_mongodb_schema.js
├── 03b_mongodb_indexes.js
├── 04_generate_data.py
├── 05_queries_mysql.sql
├── 06_queries_mongodb.js
├── 07_write_workload_mysql.sql
├── 08_load_mysql.sql
├── docs/
│   └── reference_manifest_3000000_seed42.json
├── report/
│   ├── bao_cao_HQTCSDL_G7.docx
│   └── bao_cao_HQTCSDL_G7.md
├── .gitignore
└── README.md
```

Dataset sinh ra, database dump, log, file tạm và bản test cục bộ không được đưa vào Git.

## 4. Yêu cầu môi trường

- Python 3.8 trở lên (chỉ dùng thư viện chuẩn, không cần cài package).
- MySQL Server 8.x và MySQL client/Workbench.
- MongoDB Server 7.x trở lên; khuyến nghị MongoDB 8.x.
- `mongosh`.
- MongoDB Database Tools (`mongoimport`).
- MongoDB replica set nếu chạy W1 bằng transaction.

Phiên bản từng được dùng trong kiểm thử chức năng cục bộ của nhóm: Python 3.14.6, MySQL 8.4.6, MongoDB 8.0.38, mongosh 2.14.3 và Database Tools 100.20.1. Đây là thông tin môi trường kiểm thử tại máy nhóm, không phải yêu cầu bắt buộc hoặc cấu hình benchmark hiệu năng.

## 5. Sinh dữ liệu

Tại thư mục project, chạy:

```powershell
python .\04_generate_data.py --orders 1000 --seed 42 --out data
```

Kết quả tại `data/custom_1000/`:

- `mysql/*.csv`: dữ liệu cho `LOAD DATA LOCAL INFILE`.
- `mongo/*.jsonl`: Extended JSON cho `mongoimport`.
- `manifest.json`: số lượng bản ghi, doanh thu, trạng thái đơn và thông tin độ lệch.

Các quy mô định nghĩa sẵn:

| Tham số | Số đơn |
|---|---:|
| `--scale s` | 100.000 |
| `--scale m` | 1.000.000 |
| `--scale l` | 10.000.000 |

Có thể dùng `--orders N` để chỉ định quy mô tuỳ chỉnh. N phải là số nguyên dương. Cùng phiên bản generator, seed và tham số sẽ tạo CSV/JSONL giống hệt nhau; `elapsed_seconds` trong manifest thay đổi theo thời gian chạy nên không dùng để so sánh byte-level. Mỗi đơn chỉ chọn sản phẩm có bản ghi inventory tại cửa hàng của đơn. Generator không trừ tồn kho tích lũy khi sinh lịch sử đơn hàng; inventory quantity bằng 0 vẫn là một bản ghi inventory hợp lệ. Việc sinh dữ liệu quy mô lớn cần đủ dung lượng cho CSV, JSONL, database và index; không nên chạy quy mô lớn trên máy thiếu RAM hoặc dung lượng trống.

## 6. Triển khai MySQL

### 6.1. Tạo schema

Trong PowerShell, dùng MySQL client tương ứng với máy của bạn:

```powershell
Get-Content .\01_mysql_schema.sql -Raw | & "C:\Program Files\MySQL\MySQL Server 8.4\bin\mysql.exe" -u root -p
```

Script tạo database `shop_bench` và 8 bảng. Script **không tự DROP bảng hoặc xoá dữ liệu**. Nếu database đã có bảng cùng tên, MySQL sẽ báo lỗi. Chỉ khi muốn dựng lại từ đầu, hãy sao lưu và chủ động xoá database trước.

### 6.2. Nạp CSV

1. Bật `local_infile` trên MySQL Server.
2. Bật tuỳ chọn `OPT_LOCAL_INFILE=1` trên client/Workbench.
3. Mở `08_load_mysql.sql`, thay `C:/PATH/TO/PROJECT` bằng đường dẫn project thực tế.
4. Chọn đúng thư mục quy mô. Ví dụ `--orders 1000`, đổi `data/s/mysql` thành `data/custom_1000/mysql`.
5. Chạy script và kiểm tra số dòng, `SHOW WARNINGS`, doanh thu.

Ví dụ chạy file SQL trong PowerShell:

```powershell
Get-Content .\08_load_mysql.sql -Raw | & "C:\Program Files\MySQL\MySQL Server 8.4\bin\mysql.exe" -u root -p
```

Script giữ bật kiểm tra khoá ngoại và nạp theo thứ tự phụ thuộc. Không chạy lại trên database đã có dữ liệu.

### 6.3. Tạo index phụ

Sau khi nạp dữ liệu:

```powershell
Get-Content .\02_mysql_indexes.sql -Raw | & "C:\Program Files\MySQL\MySQL Server 8.4\bin\mysql.exe" -u root -p
```

File tạo index phục vụ Q2–Q6 và payment lookup, sau đó chạy `ANALYZE TABLE`. Primary key, unique key và index hỗ trợ foreign key là thành phần nền tảng của schema, không thể coi là cấu hình “không có bất kỳ index nào”.

## 7. Triển khai MongoDB

### 7.1. Tạo collections và validators

```powershell
mongosh --file .\03_mongodb_schema.js
```

Script không tự drop collections. Nếu collection đích đã tồn tại, script dừng và báo tên collection xung đột để tránh mất dữ liệu. Muốn dựng lại, chỉ drop database sau khi đã xác nhận và sao lưu dữ liệu cần giữ.

### 7.2. Import JSONL

Ví dụ với quy mô tuỳ chỉnh 1000 đơn:

```powershell
mongoimport --uri "mongodb://localhost:27017" --db shop_bench --collection categories --file .\data\custom_1000\mongo\categories.jsonl
mongoimport --uri "mongodb://localhost:27017" --db shop_bench --collection stores --file .\data\custom_1000\mongo\stores.jsonl
mongoimport --uri "mongodb://localhost:27017" --db shop_bench --collection customers --file .\data\custom_1000\mongo\customers.jsonl
mongoimport --uri "mongodb://localhost:27017" --db shop_bench --collection products --file .\data\custom_1000\mongo\products.jsonl
mongoimport --uri "mongodb://localhost:27017" --db shop_bench --collection inventory --file .\data\custom_1000\mongo\inventory.jsonl
mongoimport --uri "mongodb://localhost:27017" --db shop_bench --collection orders --file .\data\custom_1000\mongo\orders.jsonl
```

Đổi tên thư mục quy mô tương ứng khi dùng tham số khác. Sau import, kiểm tra số documents và gọi `verifyLoad()`.

### 7.3. Tạo index

```powershell
mongosh --file .\03b_mongodb_indexes.js
```

Các index hỗ trợ truy vấn khách hàng, khoảng thời gian, trạng thái, sản phẩm và inventory. Index trên `items.product_id` là multikey index.

## 8. Workload và cách chạy

### MySQL

- `05_queries_mysql.sql`: Q1–Q8, truy vấn đọc và đối chiếu dữ liệu.
- `07_write_workload_mysql.sql`: tạo stored procedures W1–W3. W1 và W2 có transaction, handler rollback và kiểm tra số dòng cập nhật.

Nạp procedure:

```powershell
Get-Content .\07_write_workload_mysql.sql -Raw | & "C:\Program Files\MySQL\MySQL Server 8.4\bin\mysql.exe" -u root -p shop_bench
```

W1 hiện nhận `p_lines` kiểu JSON và hỗ trợ từ 1 đến 50 sản phẩm khác nhau. Mỗi phần tử có dạng `{"pid": product_id, "qty": quantity}`; `pid` và `qty` phải là JSON integer dương, quantity tối đa 65.535. Trước khi gọi W1, tìm hai sản phẩm tại cùng cửa hàng và đủ tồn kho:

```sql
SELECT a.store_id, a.product_id, b.product_id
INTO @w1_store_id, @w1_product_1, @w1_product_2
FROM inventory a
JOIN inventory b ON b.store_id = a.store_id AND b.product_id > a.product_id
WHERE a.quantity >= 2 AND b.quantity >= 1
LIMIT 1;

SELECT customer_id INTO @w1_customer_id
FROM customer
LIMIT 1;
```

Dùng các ID vừa tìm được và customer_id được chọn tự động từ bảng customer.

```sql
CALL W1_create_order(
  100000001, 900000001, @w1_customer_id, @w1_store_id,
  JSON_ARRAY(
    JSON_OBJECT('pid', @w1_product_1, 'qty', 2),
    JSON_OBJECT('pid', @w1_product_2, 'qty', 1)
  )
);
```

Ví dụ W2 và W3:

```sql
CALL W2_mark_paid(100000001);

SELECT store_id, product_id
INTO @w3_store_id, @w3_product_id
FROM inventory
LIMIT 1;
CALL W3_restock(@w3_store_id, @w3_product_id, 50);
```

Các ID chỉ là ví dụ cho pilot đã kiểm thử. Hãy chọn ID tồn tại trong dataset hiện tại; không chạy lại cùng ID vì khoá chính sẽ trùng.

### MongoDB

Mở shell và nạp workload:

```powershell
mongosh
```

Trong shell:

```javascript
use shop_bench
load("06_queries_mongodb.js")
Q1()
Q2()
Q3()
Q4()
Q5()
Q6()
Q7()
Q8()
verifyLoad()
```

W1 yêu cầu replica set. Ví dụ chọn một inventory row đang có ít nhất 2 đơn vị và một customer hiện có:

```javascript
const inv = db.inventory.findOne({ quantity: { $gte: 2 } });
const customer = db.customers.findOne();
W1_txn(100000001, 900000001, customer._id, inv.store_id, [
  { pid: inv.product_id, qty: 2 }
])
```

W2 nhận order ID tường minh; W3 nhận store ID, product ID và số lượng tường minh:

```javascript
W2(100000001)
const restockRow = db.inventory.findOne();
W3(restockRow.store_id, restockRow.product_id, 50)
```

W1 kiểm tra ID, khách hàng, cửa hàng, sản phẩm, số lượng và tồn kho. Nếu một cập nhật tồn kho thất bại, transaction bị huỷ, tránh để lại đơn hàng không có phần trừ kho tương ứng.

## 9. Đối chiếu và kiểm thử

Sau khi import, đối chiếu:

- Số dòng của 8 bảng MySQL với `manifest.json`.
- Số documents của 6 collections MongoDB.
- Tổng số `items` và `payments` nhúng trong orders.
- Doanh thu gộp và phân bố trạng thái.
- Kết quả Q1–Q8 trên cùng tham số, khoảng thời gian và thứ tự sắp xếp.
- W1 thành công, W1 thất bại do thiếu hàng, W2 hợp lệ/không hợp lệ, W3 cập nhật tồn kho.

### Kết quả kiểm thử chức năng pilot đã ghi nhận

Nhóm đã chạy bộ dữ liệu pilot 1.000 đơn với seed 42 trên máy cục bộ. Manifest pilot ghi nhận:

| Thực thể | Số lượng |
|---|---:|
| category | 60 |
| store | 50 |
| customer | 1.000 |
| product | 2.000 |
| inventory | 20.000 |
| orders | 1.000 |
| order_item | 2.705 |
| payment | 1.042 |

Doanh thu gộp ghi nhận **601.330,15**; doanh thu loại đơn CANCELLED và RETURNED là **529.555,44**. Tổng là 27.857 dòng MySQL và 24.110 documents MongoDB (items/payments được nhúng trong orders).

**Lưu ý về phiên bản kiểm thử:** các kết quả dưới đây là log kiểm thử chức năng cục bộ của nhóm trước đợt chỉnh sửa code được đưa vào repository này. Chúng là bằng chứng lịch sử cho logic và dữ liệu pilot, không thay thế việc chạy lại trên đúng commit hiện tại.

Theo log kiểm thử cục bộ do nhóm ghi nhận:
- Q1–Q8 đã chạy trên cả hai hệ và kết quả nghiệp vụ được đối chiếu khớp.
- W1 thành công đã được kiểm tra trên cả hai hệ.
- MySQL W1 đã được kiểm tra rollback khi số lượng vượt miền dữ liệu và khi tồn kho không đủ; order/payment/item không còn sau rollback.
- W2 và W3 đã được kiểm tra ở luồng thành công.
- Các thay đổi mới trong `07_write_workload_mysql.sql`, `03_mongodb_schema.js` và `06_queries_mongodb.js` đã qua rà soát tĩnh; cần chạy lại kiểm thử runtime trên commit hiện tại trước khi nghiệm thu cuối.
- Execution Plan Q1 MySQL dùng PRIMARY; Q2 MySQL dùng `idx_orders_customer_date`. MongoDB Q1 dùng `_id_`; Q2 dùng index khách hàng/ngày.
- Đây là **kiểm thử chức năng và kiểm tra execution plan trên pilot**, không phải benchmark thời gian đủ điều kiện để kết luận hệ nào nhanh hơn.

## 10. Đo hiệu năng một cách công bằng

Khi benchmark:
1. Dùng cùng bộ dữ liệu, seed và tham số truy vấn.
2. Tách thời gian import, tạo index và thực thi truy vấn.
3. Warm-up trước khi đo; lặp nhiều lần và báo cáo median/percentile.
4. Ghi CPU, RAM, ổ đĩa, phiên bản server, cache, concurrency và trạng thái replica set.
5. Tách index nền tảng khỏi secondary index theo workload.
6. Đo cả read và write; không so transaction MySQL với thao tác MongoDB không transaction như thể cùng mức bảo đảm.
7. Lưu raw results và script benchmark để tái lập.

**Repository chưa có kết quả benchmark latency/throughput quy mô lớn đã được xác minh.** Không dùng thời gian chạy generator hoặc executionTimeMillis đơn lẻ trong explain làm benchmark tổng thể.

## 11. Execution Plan

MySQL:

```sql
EXPLAIN FORMAT=TREE
SELECT order_id, order_date, status
FROM orders
WHERE customer_id = 506
ORDER BY order_date DESC, order_id DESC
LIMIT 20;
```

MongoDB:

```javascript
db.orders.find(
  { customer_id: 506 },
  { order_date: 1, status: 1 }
).sort({ order_date: -1, _id: -1 }).limit(20).explain("executionStats")
```

Phân tích access path, index được chọn, số keys/documents examined, số dòng trả về, sort stage và điều kiện lọc. Không suy ra hiệu năng chỉ từ tên index.

## 12. Hạn chế

- Dữ liệu tổng hợp không mô tả đầy đủ phân bố giao dịch thực tế.
- Truy vấn phân tích phụ thuộc mạnh vào quy mô dữ liệu và cấu hình máy.
- MySQL chuẩn hoá và MongoDB nhúng document có hình dạng lưu trữ khác nhau; cần nêu rõ khác biệt khi diễn giải số lần đọc/ghi.
- Pilot dùng để xác nhận logic, không đại diện cho workload lớn.
- So sánh hiệu năng cần benchmark có kiểm soát, nhiều lần lặp và raw results.

## 13. Báo cáo

Báo cáo học thuật 18 trang được lưu trong thư mục `report/` ở cả định dạng Word và Markdown. Các tài liệu tham khảo trong báo cáo được phân biệt với số liệu thực nghiệm của nhóm.
