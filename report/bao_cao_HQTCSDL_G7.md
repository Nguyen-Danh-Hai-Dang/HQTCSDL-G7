**ĐẠI HỌC QUỐC GIA HÀ NỘI  
TRƯỜNG ĐẠI HỌC CÔNG NGHỆ**

**BÁO CÁO PROJECT  
HỌC PHẦN HỆ QUẢN TRỊ CƠ SỞ DỮ LIỆU**

**MONGODB VÀ MYSQL TRONG CƠ SỞ DỮ LIỆU  
QUẢN LÝ BÁN HÀNG LỚN,  
KẾT HỢP NGHIÊN CỨU CÁC PHƯƠNG PHÁP INDEX**

| **Thông tin**  | **Nội dung**                  |
|----------------|-------------------------------|
| Nhóm           | Nhóm 7                        |
| Trưởng nhóm    | Nguyễn Danh Hải Đăng          |
| Thành viên     | Lê Quang Vinh; Lưu Trung Trực |
| Phạm vi đề tài | A4 + B2                       |

Hà Nội, tháng 11 năm 2026

# TÓM TẮT

Báo cáo trình bày quá trình xây dựng một bài toán quản lý bán hàng trên
MySQL và MongoDB, đồng thời khảo sát vai trò của Index đối với truy vấn.
Hai hệ thống sử dụng chung một bộ sinh dữ liệu xác định bằng seed, nhưng
tổ chức dữ liệu theo hai cách khác nhau: MySQL dùng mô hình quan hệ
chuẩn hoá; MongoDB dùng document, nhúng chi tiết đơn hàng và thanh toán
vào document đơn hàng, đồng thời tham chiếu khách hàng, sản phẩm và cửa
hàng bằng mã định danh.

Phần mã nguồn gồm schema, validator, index, bộ sinh dữ liệu, workload
Q1–Q8, thao tác ghi W1–W3 và script nạp dữ liệu. Trong quá trình rà
soát, nhóm phát hiện và sửa các điểm chưa an toàn ở thao tác ghi: W1
MySQL được bổ sung kiểm tra đầu vào, transaction và rollback thật khi
thiếu tồn kho; W1 MongoDB dùng transaction đa document; W2 kiểm tra
trạng thái đơn và payment; W3 kiểm soát miền số lượng tồn kho. Sau khi
chỉnh sửa, ba job CI đã chạy thành công: kiểm thử generator, tích hợp
MySQL 8.4 và MongoDB 8.0 replica set. Các job này xác nhận những nhánh
nghiệp vụ trọng yếu trên fixture nhỏ, không thay thế benchmark hoặc
kiểm thử lại toàn bộ pilot.

Thực nghiệm pilot 1.000 đơn được dùng để xác nhận chức năng; benchmark
được chạy bổ sung trên hai quy mô 100.000 và 1.000.000 đơn bằng GitHub
Actions. Mỗi truy vấn Q1–Q8 có 5 lượt warm-up và 30 lượt đo, chạy tuần tự
với một client. MySQL 8.4.13 và MongoDB 8.0.38 được giới hạn cache 1 GiB
mỗi hệ; runner có 4 logical CPU và khoảng 16 GB RAM. Kết quả cho thấy
secondary index cải thiện mạnh một số truy vấn, đặc biệt Q3 và MongoDB
Q2, nhưng Q4 không cải thiện và Q7 gần như không đổi. Bộ dữ liệu 10 triệu
đơn chưa được benchmark vì ước lượng file dữ liệu thô khoảng 7 GB, chưa
tính dung lượng hai CSDL và index.

Vì vậy, RQ4 và RQ5 đã có bằng chứng định lượng ở hai quy mô; RQ6 mới có
kết quả ở 100 nghìn và 1 triệu đơn, chưa đủ để kết luận xu hướng ở 10
triệu đơn. Các khuyến nghị RQ7 vẫn phụ thuộc workload, mô hình dữ liệu,
index và tài nguyên triển khai, không khẳng định hệ nào nhanh hơn trong
mọi trường hợp.

Từ khóa: MySQL, MongoDB, InnoDB, WiredTiger, Index, B-Tree, compound
index, multikey index, execution plan, workload bán hàng.

# MỤC LỤC

- 1\. Giới thiệu và phạm vi nghiên cứu

- 2\. Tổng quan MySQL và MongoDB

- 3\. Thiết kế dữ liệu và mô hình triển khai

- 4\. Cơ sở lý thuyết về Index

- 5\. Chiến lược Index cho workload bán hàng

- 6\. Bộ dữ liệu và workload

- 7\. Môi trường, triển khai và phương pháp kiểm thử

- 8\. Kết quả kiểm thử pilot

- 9\. Execution Plan và diễn giải

- 10\. Trả lời câu hỏi nghiên cứu RQ1–RQ7

- 11\. Hạn chế, hướng phát triển và kết luận

- Tài liệu tham khảo và phụ lục

## Danh mục thuật ngữ

| **Thuật ngữ**     | **Ý nghĩa**                                         |
|-------------------|-----------------------------------------------------|
| DBMS              | Hệ quản trị cơ sở dữ liệu                           |
| Index             | Cấu trúc phụ trợ giúp định vị dữ liệu               |
| PK / FK           | Primary Key / Foreign Key                           |
| 3NF               | Dạng chuẩn thứ ba trong chuẩn hoá quan hệ           |
| BSON              | Binary JSON, định dạng tài liệu của MongoDB         |
| IXSCAN / COLLSCAN | Quét index / quét toàn collection trong MongoDB     |
| p95 / p99         | Phân vị 95% / 99% của độ trễ                        |
| W1–W3             | Các thao tác ghi: tạo đơn, đổi trạng thái, nhập kho |

# 1. GIỚI THIỆU VÀ PHẠM VI NGHIÊN CỨU

Hệ thống bán hàng tạo ra nhiều loại dữ liệu có quan hệ chặt chẽ: khách
hàng, sản phẩm, danh mục, cửa hàng, tồn kho, đơn hàng, dòng hàng và
thanh toán. Những nghiệp vụ này kết hợp truy vấn tra cứu theo khoá, lịch
sử mua hàng, lọc theo thời gian, báo cáo tổng hợp và cập nhật đồng thời.
Việc lựa chọn DBMS và chiến lược Index ảnh hưởng đến tính toàn vẹn, độ
phức tạp truy vấn, tốc độ đọc, chi phí ghi và dung lượng lưu trữ.

Đề tài thuộc phạm vi A4 + B2: xây dựng CSDL quản lý bán hàng trên
MongoDB, so sánh với MySQL trên cùng dữ liệu logic và nghiên cứu các
phương pháp Index. Mục tiêu không phải tuyên bố một hệ quản trị luôn tốt
hơn hệ còn lại, mà xác định điều kiện workload và mô hình dữ liệu khiến
một lựa chọn phù hợp hơn.

## 1.1. Mục tiêu

1.  Hệ thống hoá cơ sở lý thuyết Index và các phương pháp liên quan.

2.  So sánh đặc điểm MySQL và MongoDB trong nghiệp vụ bán hàng.

3.  Thiết kế mô hình dữ liệu, dữ liệu tổng hợp và workload tương đương.

4.  Xây dựng hai hệ thống và kiểm tra tính tương đương dữ liệu, truy
    vấn.

5.  Xây dựng kịch bản có/không có Index và đánh giá execution plan.

6.  Thiết kế benchmark có kiểm soát, thu thập số liệu có thể tái lập.

7.  Phân tích và đưa ra khuyến nghị có giới hạn theo môi trường thực
    nghiệm.

## 1.2. Câu hỏi nghiên cứu

- RQ1. MongoDB và MySQL có những điểm khác nhau nào về mô hình dữ liệu,
  cách lưu trữ, truy vấn và khả năng mở rộng khi xây dựng hệ thống CSDL
  quản lý bán hàng lớn?

- RQ2. Index là gì và vì sao Index có thể ảnh hưởng đến hiệu năng truy
  vấn?

- RQ3. Các phương pháp Index khác nhau hoạt động như thế nào và được sử
  dụng trong những trường hợp nào?

- RQ4. Việc sử dụng Index ảnh hưởng như thế nào đến thời gian thực hiện
  truy vấn trong bài toán bán hàng?

- RQ5. Trong cùng một workload và cùng quy mô dữ liệu, hiệu năng giữa
  MongoDB và MySQL thay đổi như thế nào khi có hoặc không có Index?

- RQ6. Khi quy mô dữ liệu tăng, ảnh hưởng của chiến lược Index đến hiệu
  năng có thay đổi hay không?

- RQ7 (bổ sung). Dựa trên kết quả thực nghiệm, chiến lược Index và hệ
  quản trị CSDL nào phù hợp với từng nhóm nghiệp vụ bán hàng lớn, và
  giới hạn của kết luận là gì?

# 2. TỔNG QUAN MYSQL VÀ MONGODB

## 2.1. MySQL và mô hình quan hệ

MySQL là hệ quản trị quan hệ, dữ liệu được tổ chức trong bảng với kiểu
dữ liệu và ràng buộc xác định. Trong project, InnoDB được sử dụng cho cả
tám bảng. Mô hình tách khách hàng, sản phẩm, danh mục, cửa hàng, tồn
kho, đơn hàng, chi tiết đơn và thanh toán. Khoá ngoại bảo đảm tham chiếu
hợp lệ; unique key ngăn trùng email và SKU; CHECK hỗ trợ các bất biến
miền dữ liệu.

InnoDB sử dụng clustered index để tổ chức dữ liệu hàng. Khi bảng có
PRIMARY KEY, khoá chính là clustered index; secondary index lưu khoá
định vị bản ghi trong clustered index \[1\]. Vì vậy, lựa chọn khoá chính
và thiết kế secondary index tác động đến cả truy vấn lẫn chi phí cập
nhật.

## 2.2. MongoDB và mô hình document

MongoDB lưu document BSON trong collection. Project có sáu collection:
categories, customers, products, stores, inventory và orders. Document
orders nhúng mảng items và payments vì các thành phần này thường được
đọc cùng đơn hàng và có giới hạn kích thước hợp lý. Các thực thể được
dùng chung hoặc cập nhật độc lập như customer, product và store được
tham chiếu bằng ID.

Mô hình document giảm nhu cầu JOIN trong một số nghiệp vụ đọc đơn hàng,
nhưng các truy vấn phân tích cần tổng hợp trên items vẫn sử dụng
\$unwind, \$group và \$lookup. MongoDB hỗ trợ atomicity ở cấp một
document; khi một nghiệp vụ cập nhật đồng thời document đơn hàng và
document tồn kho, transaction đa document được dùng để bảo đảm tất cả
cùng commit hoặc cùng rollback \[5\].

## 2.3. So sánh khái quát

| **Tiêu chí** | **MySQL / InnoDB**                                  | **MongoDB**                                     |
|--------------|-----------------------------------------------------|-------------------------------------------------|
| Mô hình      | Quan hệ, bảng, chuẩn hoá                            | Document BSON, nhúng và tham chiếu              |
| Liên kết     | JOIN, PK/FK                                         | \$lookup hoặc đọc theo ID                       |
| Ràng buộc    | FK, UNIQUE, CHECK, kiểu dữ liệu                     | Validator, unique index, kiểm tra ở ứng dụng    |
| Đơn hàng     | orders + order_item + payment                       | orders với items\[\] và payments\[\]            |
| Giao dịch    | ACID trên bảng InnoDB                               | Atomic một document; transaction nhiều document |
| Mở rộng      | Replication và partitioning; thiết kế theo workload | Replica set và sharding                         |

# 3. THIẾT KẾ DỮ LIỆU VÀ MÔ HÌNH TRIỂN KHAI

## 3.1. Mô hình MySQL

Mô hình quan hệ gồm tám bảng. category tự tham chiếu để biểu diễn danh
mục gốc và danh mục con. inventory là quan hệ N–N giữa store và product,
dùng khoá chính ghép (store_id, product_id). orders tham chiếu customer
và store. order_item dùng khoá ghép (order_id, line_no), lưu product_id,
quantity và unit_price tại thời điểm đặt hàng. payment tham chiếu order.

Không lưu total_amount trong orders vì giá trị này suy ra từ
SUM(quantity × unit_price) trên order_item. Việc lưu snapshot unit_price
giúp giữ giá tại thời điểm giao dịch ngay cả khi giá niêm yết sản phẩm
thay đổi. Tiền sử dụng DECIMAL để tránh sai số dấu phẩy động.

## 3.2. Mô hình MongoDB

MongoDB có sáu collection. Collection orders nhúng items\[\] và
payments\[\]. Mỗi item lưu line_no, product_id, quantity và unit_price;
mỗi payment lưu payment_id, method, amount, paid_at và status. Document
vẫn tham chiếu customer_id và store_id. Product và category nằm trong
collection riêng để tránh lặp dữ liệu mô tả sản phẩm trong mọi đơn hàng.

## 3.3. Nguyên tắc tương đương dữ liệu

- Dùng lại ID giữa hai hệ để đối chiếu 1–1.

- Giữ cùng khoảng thời gian, trạng thái, số lượng và đơn giá.

- Dùng Decimal trong MySQL và Decimal128 trong MongoDB.

- Lưu thời gian theo UTC; MySQL dùng DATETIME quy ước UTC, MongoDB dùng
  BSON Date.

- Tổng tiền được tính từ các dòng hàng, không lưu bản sao độc lập.

- Đối chiếu số lượng thực thể, số dòng chi tiết, số thanh toán và doanh
  thu.

Sự tương đương ở đây là tương đương dữ liệu logic và kết quả nghiệp vụ,
không phải hai hệ có cùng số lần đọc đĩa hoặc cùng cấu trúc lưu trữ. Đây
là khác biệt cần giữ rõ khi phân tích hiệu năng.

# 4. CƠ SỞ LÝ THUYẾT VỀ INDEX

## 4.1. Khái niệm

Index là cấu trúc dữ liệu phụ trợ được duy trì để tìm bản ghi theo một
hoặc nhiều trường mà không phải duyệt toàn bộ dữ liệu. Khi không có
đường truy cập phù hợp, hệ quản trị có thể phải quét toàn bảng hoặc toàn
collection. Với cấu trúc cây cân bằng, tìm kiếm theo khoá có thể có độ
phức tạp gần O(log n) theo số phần tử, thay vì O(n) của quét tuần tự;
tuy nhiên chi phí thực tế còn phụ thuộc kích thước trang, cache, độ chọn
lọc, số bản ghi cần lấy và kế hoạch của optimizer.

## 4.2. B-Tree và B+Tree

B-Tree/B+Tree giữ các khoá theo thứ tự và duy trì chiều cao cây tương
đối nhỏ. Cấu trúc này hỗ trợ tìm kiếm bằng, tìm theo khoảng và duyệt
theo thứ tự, phù hợp với truy vấn WHERE, ORDER BY và range scan. InnoDB
dùng B-tree index; tài liệu MySQL mô tả clustered và secondary index
trong InnoDB \[1\]. MongoDB cũng mô tả compound index dưới dạng B-tree
có thứ tự theo các trường trong index \[2\].

## 4.3. Hash index

Hash index ánh xạ khoá sang bucket bằng hàm băm, phù hợp với equality
lookup nhưng không tự nhiên hỗ trợ range scan hay thứ tự sắp xếp. Một số
engine hoặc cấu hình có thể cung cấp hash index; cần phân biệt hỗ trợ
của engine với cách MongoDB/MySQL mặc định tổ chức index trong workload
cụ thể. Không nên kết luận một loại index được hỗ trợ chỉ từ tên DBMS.

## 4.4. Optimizer và selectivity

Query optimizer lựa chọn kế hoạch dựa trên thống kê, cardinality ước
lượng, selectivity, chi phí đọc và các điều kiện truy vấn. Index có thể
tồn tại nhưng không được chọn nếu điều kiện lọc trả về phần lớn dữ liệu,
thống kê không phù hợp hoặc chi phí truy cập qua index cao hơn quét tuần
tự. Vì vậy, bằng chứng cần có cả execution plan lẫn số lượng bản ghi
được kiểm tra.

# 5. CÁC PHƯƠNG PHÁP INDEX

| **Loại Index**             | **Cơ chế / đặc điểm**                          | **Trường hợp sử dụng**                    |
|----------------------------|------------------------------------------------|-------------------------------------------|
| Single-field               | Đánh chỉ mục một trường                        | Tra cứu theo mã, email, trạng thái        |
| Compound                   | Khoá gồm nhiều trường có thứ tự                | Lọc khách hàng rồi sắp xếp theo ngày      |
| Unique                     | Cấm giá trị khoá trùng                         | Email, SKU, cặp cửa hàng–sản phẩm         |
| Clustered                  | Dữ liệu hàng tổ chức theo khoá                 | PK lookup trong InnoDB                    |
| Secondary                  | Cấu trúc phụ trỏ về bản ghi                    | Truy vấn theo trường ngoài PK             |
| Covering                   | Index chứa đủ trường cần lọc/trả về            | Giảm hoặc tránh lookup bản ghi            |
| Full-text                  | Chỉ mục từ/ngữ cho tìm kiếm văn bản            | Tìm tên/mô tả sản phẩm                    |
| Multikey                   | Tạo index từ trường mảng trong document        | Lọc items.product_id trong MongoDB        |
| Geospatial / TTL / Partial | Index theo không gian, thời hạn hoặc điều kiện | Vị trí cửa hàng, dữ liệu hết hạn, tập con |
| Hashed                     | Hash key, chủ yếu equality                     | Một số mẫu truy vấn/sharding phù hợp      |

Không phải mọi loại index đều phù hợp hoặc được hỗ trợ theo cùng cách ở
cả hai hệ. Ví dụ multikey là đặc trưng cho trường mảng của MongoDB;
index trên items.product_id tự động trở thành multikey khi trường này
chứa mảng \[3\]. Full-text, geospatial, TTL, partial và hashed có cơ
chế, giới hạn và mục đích riêng. Trong phạm vi project, phần triển khai
tập trung vào primary/\_id, unique, single-field, compound và multikey;
các loại còn lại chủ yếu được trình bày lý thuyết.

## 5.1. Compound index và tiền tố trái

Với index (customer_id, order_date), truy vấn theo customer_id hoặc
customer_id kết hợp order_date có thể tận dụng tiền tố index. Truy vấn
chỉ lọc order_date không được hỗ trợ tối ưu tương tự bởi tiền tố này.
Thứ tự trường vì thế phải bám sát mẫu truy vấn, điều kiện equality, sort
và range. Tài liệu MongoDB nhấn mạnh index compound hỗ trợ các tiền tố
đầu của index và thứ tự trường là quan trọng \[2\].

# 6. CHIẾN LƯỢC INDEX CHO WORKLOAD BÁN HÀNG

## 6.1. Mapping index trong project

| **Nhu cầu**             | **MySQL**                 | **MongoDB**                     | **Mục tiêu**                  |
|-------------------------|---------------------------|---------------------------------|-------------------------------|
| Tra cứu đơn theo ID     | PRIMARY(order_id)         | \_id\_                          | Equality lookup               |
| Lịch sử đơn theo khách  | (customer_id, order_date) | (customer_id, order_date, \_id) | Filter + sort + limit         |
| Lọc ngày                | (order_date)              | (order_date)                    | Range scan                    |
| Trạng thái + ngày       | (status, order_date)      | (status, order_date, \_id)      | Equality + range + order      |
| Doanh thu theo sản phẩm | order_item(product_id)    | items.product_id                | Join/group theo sản phẩm      |
| Tra payment theo đơn    | payment(order_id)         | Embedded payments               | Thay đổi theo mô hình lưu trữ |
| SKU/email               | UNIQUE                    | UNIQUE                          | Toàn vẹn và lookup            |

## 6.2. Lợi ích và đánh đổi

Index giúp giảm số bản ghi phải kiểm tra và có thể hỗ trợ thứ tự kết
quả, nhưng mỗi INSERT/UPDATE/DELETE liên quan đến trường index đều có
thể phát sinh chi phí duy trì cấu trúc. Index chiếm dung lượng đĩa và
cache; quá nhiều index làm tăng thời gian import, cập nhật và chi phí
quản trị. Tài liệu MongoDB cũng cảnh báo index có thể cải thiện truy vấn
đọc nhưng làm tăng chi phí ghi vì mỗi thay đổi phải cập nhật index
\[6\].

## 6.3. Trường hợp index không hiệu quả

- Điều kiện lọc có selectivity thấp và trả về phần lớn bảng/collection.

- Truy vấn áp dụng hàm lên cột khiến index thường không được sử dụng
  trực tiếp.

- LIKE bắt đầu bằng wildcard không tận dụng được thứ tự tiền tố B-tree
  thông thường.

- Compound index có thứ tự trường không khớp điều kiện
  equality/sort/range.

- Truy vấn trả về quá nhiều cột hoặc bản ghi khiến lookup bổ sung vượt
  lợi ích index.

- Index chưa được cập nhật thống kê hoặc optimizer ước lượng cardinality
  sai.

# 7. BỘ DỮ LIỆU VÀ WORKLOAD

## 7.1. Bộ sinh dữ liệu

File 04_generate_data.py dùng thư viện chuẩn Python, seed mặc định 42 và
xuất cùng một lần sinh ra CSV và Extended JSON Lines. Generator tạo 10
danh mục gốc, 50 danh mục con, 50 cửa hàng; số khách hàng và sản phẩm
phụ thuộc quy mô. Mỗi sản phẩm có tồn kho tại 10 cửa hàng được chọn.
Ngày đơn hàng phân bố trong giai đoạn 2024–2025.

Độ lệch dữ liệu mô phỏng tính phổ biến không đồng đều: Zipf s=1,1 cho
sản phẩm và s=0,7 cho khách hàng. Đơn hàng có 1–8 dòng; số lượng mỗi
dòng từ 1–5; trạng thái và phương thức thanh toán theo các trọng số được
định nghĩa trong generator. Đây là giả định tạo dữ liệu, không phải phân
phối đo từ hệ thống bán hàng thực.

## 7.2. Workload đọc

| **Truy vấn** | **Nội dung**                                         | **Đặc trưng**                |
|--------------|------------------------------------------------------|------------------------------|
| Q1           | Tra cứu một đơn theo khoá và lấy chi tiết/thanh toán | Equality / PK                |
| Q2           | 20 đơn gần nhất của khách hàng                       | Filter + sort + limit        |
| Q3           | Đơn SHIPPED trong khoảng thời gian                   | Range + equality + sort      |
| Q4           | Doanh thu theo tháng, loại đơn huỷ/trả               | Aggregation                  |
| Q5           | Top 10 sản phẩm theo doanh thu                       | Join/unwind + group          |
| Q6           | Doanh thu theo danh mục                              | Nhiều thực thể + aggregation |
| Q7           | Chi tiết đơn kèm tên khách và sản phẩm               | Lookup/join                  |
| Q8           | Top 10 khách theo chi tiêu                           | Group + sort + limit         |

## 7.3. Workload ghi

W1 tạo đơn hàng, dòng hàng, thanh toán và giảm tồn kho; W2 chuyển trạng
thái đơn và payment sang PAID; W3 nhập thêm tồn kho. Tỷ trọng thiết kế
của workload là 80% đọc và 20% ghi. W1 là thao tác nhiều bản
ghi/collection nên yêu cầu transaction để bảo đảm nhất quán. W2 trong
MongoDB có thể cập nhật nguyên tử trên một document vì payment được
nhúng; MySQL cập nhật hai bảng trong transaction.

# 8. MÔI TRƯỜNG VÀ TRIỂN KHAI

## 8.1. Môi trường kiểm thử chức năng đã ghi nhận

| **Thành phần**         | **Phiên bản / cấu hình**           |
|------------------------|------------------------------------|
| Hệ điều hành           | Windows 11                         |
| Python                 | 3.14.6                             |
| MySQL Server           | 8.4.6                              |
| MongoDB Server         | 8.0.38                             |
| mongosh                | 2.14.3                             |
| MongoDB Database Tools | 100.20.1                           |
| MongoDB topology       | Replica set đơn nút rs0, localhost |
| MySQL service          | MySQL84; cổng mặc định 3306        |

Đây là môi trường chạy kiểm thử chức năng tại máy nhóm. Không có đầy đủ
thông số CPU, cấu hình cache, nhiệt độ, tải nền và tài nguyên I/O tại
từng lần đo; vì vậy không dùng bảng này để tuyên bố benchmark hiệu năng
có thể tái lập.

## 8.2. Pipeline triển khai

| **Bước** | **Thao tác**                   | **Sản phẩm**                       |
|----------|--------------------------------|------------------------------------|
| 1        | Sinh dữ liệu bằng seed cố định | CSV + JSONL + manifest             |
| 2        | Tạo schema và validator        | 8 bảng MySQL, 6 collection MongoDB |
| 3        | Import cùng dữ liệu logic      | Hai CSDL được nạp                  |
| 4        | Tạo index                      | Cấu hình index workload            |
| 5        | Chạy Q1–Q8                     | Kết quả đọc và đối chiếu           |
| 6        | Chạy W1–W3                     | Kiểm tra giao dịch và tồn kho      |
| 7        | Thu thập explain/EXPLAIN       | Bằng chứng execution plan          |

## 8.3. An toàn khi dựng lại

Các script schema được chỉnh theo hướng không tự động DROP
bảng/collection. MySQL schema sẽ báo lỗi nếu bảng đã tồn tại; MongoDB
schema dừng nếu collection đích đã tồn tại. Người vận hành phải chủ động
sao lưu và xác nhận trước khi xoá database để dựng lại. Script import
giữ bật foreign_key_checks và yêu cầu database rỗng để tránh nhập chồng
dữ liệu.

# 9. KẾT QUẢ KIỂM THỬ PILOT

Pilot dùng 1.000 đơn hàng, seed 42, tạo bộ dữ liệu custom_1000. Đây là
quy mô kiểm thử logic nhỏ, không đại diện cho mức “bán hàng lớn” và
không đủ để đánh giá xu hướng hiệu năng theo quy mô.

| **Thực thể** | **Số lượng** |
|--------------|--------------|
| category     | 60           |
| store        | 50           |
| customer     | 1.000        |
| product      | 2.000        |
| inventory    | 20.000       |
| orders       | 1.000        |
| order_item   | 2.705        |
| payment      | 1.042        |

<img src="media/image1.png" style="width:6.3in;height:2.975in" />

*Hình 1. Số lượng thực thể trong pilot (trục log; không phải biểu đồ
hiệu năng).*

Doanh thu gộp của pilot là 601.330,15; doanh thu loại CANCELLED và
RETURNED là 529.555,44. Tổng số hàng quan hệ trong MySQL là 27.857.
MongoDB có 24.110 documents ở sáu collection; các dòng order_item và
payment được nhúng bên trong 1.000 documents orders nên không cộng như
collection độc lập.

## 9.1. Kiểm thử chức năng đã thực hiện

- MySQL: tạo 8 bảng, nạp CSV, đối chiếu số lượng và doanh thu với
  manifest.

- MongoDB: tạo validators/index, import 24.110 documents, xác nhận
  Decimal128 và BSON Date.

- Q1–Q8: chạy trên hai hệ với tham số và khoảng thời gian tương ứng;
  nhóm ghi nhận kết quả nghiệp vụ khớp.

- W1: tạo đơn và thanh toán, giảm tồn kho đúng lượng; MySQL kiểm tra
  rollback khi tồn kho không đủ và khi quantity vượt giới hạn.

- W2: chuyển đơn và payment PENDING sang PAID; W3: tăng tồn kho.

- Các thao tác ghi được thực hiện trên database test/clone, không làm
  thay đổi nguồn dữ liệu pilot gốc.

## 9.2. Kiểm thử hồi quy tự động trên commit hiện tại

GitHub Actions chạy ba job độc lập trên môi trường dùng một lần:

- **Generator:** sinh pilot 1.000 đơn; kiểm tra từng order item có inventory
  row tại đúng cửa hàng, không lặp product trong cùng đơn và CSV/JSONL
  giống hệt nhau giữa hai lần chạy cùng seed/tham số.
- **MySQL 8.4:** cài schema và stored procedures; W1 tạo đơn nhiều dòng,
  kiểm tra tổng payment và tồn kho; một ca thiếu hàng xảy ra sau khi dòng
  inventory đầu tiên đã cập nhật để xác nhận transaction rollback toàn
  bộ; W3 kiểm tra nhập kho thành công và từ chối vượt giới hạn INT có dấu.
- **MongoDB 8.0 replica set:** tạo collections/validators; W1 transaction
  nhiều dòng và rollback khi thiếu hàng; W2 chuyển đơn/payment sang PAID;
  W3 nhập kho thành công và từ chối tràn giới hạn INT32.

Cả ba job đều PASS trong GitHub Actions run
[#38](https://github.com/Nguyen-Danh-Hai-Dang/HQTCSDL-G7/actions/runs/45771934254),
trên PR head commit `32b123b1a660e8cd90f4c1e2f0b7abcc5a8c7f4b`.
PR #1 sau đó được merge vào `main` bằng merge commit
`ef47d88dc29bbcb6738868e1ad1bd861b6939d27`. Workflow hiện được cấu hình
chạy theo pull request nên run #38 xác nhận chính xác nội dung head đã
được merge, không phải một lần chạy mới trên merge commit. Đây là kiểm
thử tích hợp tự động trên fixture nhỏ, nhằm xác nhận cú pháp procedure,
transaction và các nhánh nghiệp vụ quan trọng. Nó không thay thế kiểm
thử lại trên toàn bộ pilot 1.000 đơn, không xác nhận Q1–Q8 trên commit
mới và không phải benchmark latency/throughput. Các kết quả pilot lịch
sử ở mục 9.1 được giữ riêng, không đánh đồng với fixture CI.

# 10. EXECUTION PLAN VÀ DIỄN GIẢI

## 10.1. MySQL

Trong lần kiểm tra Q1, MySQL dùng access type const và PRIMARY KEY với
ước lượng một hàng. Đây là hành vi phù hợp với phép so sánh bằng trên
khoá chính. Với Q2, optimizer dùng type ref và index
idx_orders_customer_date; số hàng ước lượng khoảng 49, truy vấn đọc 20
dòng đầu theo chiều quét ngược index và không cần filesort trong lần
kiểm tra đã ghi nhận.

Cần lưu ý rằng EXPLAIN cung cấp kế hoạch/ước lượng; EXPLAIN ANALYZE thực
thi câu lệnh và bổ sung thời gian, số hàng thực tế, vòng lặp và thông
tin iterator \[7\]. Không được nhầm rows ước lượng trong EXPLAIN với số
dòng thực tế.

## 10.2. MongoDB

Q1 sử dụng index mặc định \_id\_, ghi nhận EXPRESS_IXSCAN, nReturned=1,
totalKeysExamined=1 và totalDocsExamined=1. Q2 sử dụng compound index
customer_id/order_date/\_id, trả về 20 documents với 20 keys và 20
documents được kiểm tra trong lần kiểm tra pilot đã ghi nhận.

MongoDB explain executionStats cung cấp nReturned, totalKeysExamined,
totalDocsExamined và executionTimeMillis. Tài liệu chính thức lưu ý
executionTimeMillis không nhất thiết đại diện cho thời gian truy vấn ổn
định vì explain có thể bao gồm giai đoạn chọn kế hoạch và không bao gồm
thời gian truyền dữ liệu mạng \[4\].

## 10.3. Ý nghĩa và giới hạn

Hai execution plan cho thấy index phù hợp được chọn ở truy vấn tra cứu
theo khoá và lịch sử mua hàng. Tuy nhiên, số liệu trên pilot nhỏ và thời
gian hiển thị bằng 0 ms ở một số explain không đủ để xếp hạng hiệu năng
hai DBMS. Muốn kết luận cần chạy cùng số lần lặp, warm-up, concurrency,
cache và công cụ đo, đồng thời lưu raw result.

# 11. TRẢ LỜI RQ1–RQ4

## RQ1. Khác biệt mô hình, lưu trữ, truy vấn và mở rộng

MySQL biểu diễn quan hệ bằng bảng chuẩn hoá, có PK/FK và JOIN; MongoDB
biểu diễn bằng document BSON, hỗ trợ embedding và referencing. Trong
project, MySQL có 8 bảng trong khi MongoDB có 6 collection; chi tiết đơn
và thanh toán được nhúng trong orders. Điều này giúp đọc trọn đơn hàng
bằng một document, trong khi MySQL cần đọc orders, order_item và payment
riêng. Ngược lại, báo cáo nhiều thực thể trên MongoDB cần aggregation và
\$lookup, còn MySQL dùng JOIN.

Về toàn vẹn, MySQL kiểm tra FK ở tầng DBMS. MongoDB dùng validator,
unique index và logic ứng dụng; transaction đa document được dùng khi W1
cần cập nhật đơn và tồn kho. MongoDB hỗ trợ transaction ACID đa document
trên replica set/sharded cluster; thao tác một document vốn atomic
\[5\]. Về mở rộng, cả hai có replication; MongoDB hỗ trợ sharding, MySQL
có partitioning và các kiến trúc phân tán tuỳ triển khai. Project không
thực nghiệm sharding hoặc cụm nhiều máy.

## RQ2. Index là gì và vì sao ảnh hưởng?

Index là cấu trúc phụ trợ lưu khoá theo thứ tự hoặc ánh xạ để tìm dữ
liệu hiệu quả hơn. Index có thể giảm số trang/bản ghi cần kiểm tra, hỗ
trợ range scan và sort. Nhưng index không miễn phí: cần dung lượng,
cache và công việc duy trì khi ghi. Optimizer có thể không chọn index
nếu selectivity thấp hoặc chi phí ước lượng cao hơn scan.

## RQ3. Phương pháp Index hoạt động và trường hợp dùng

B-tree/B+Tree phù hợp equality, range và sort; hash chủ yếu equality;
compound index phục vụ nhiều điều kiện theo thứ tự trường; unique index
bảo đảm không trùng; covering index có thể trả kết quả chỉ từ index;
multikey của MongoDB lập chỉ mục các giá trị trong mảng. Full-text,
geospatial, partial, TTL và hashed phù hợp những nhu cầu đặc thù. Trong
project, trọng tâm thực nghiệm là PK/\_id, unique, single-field,
compound và multikey.

## RQ4. Index ảnh hưởng thời gian truy vấn như thế nào?

Benchmark run #7 đo latency trước và sau khi bổ sung workload secondary
index ở cả hai hệ. Ở quy mô 100.000 đơn, median Q3 giảm từ 9,375 xuống
0,386 ms ở MySQL và từ 35,723 xuống 0,409 ms ở MongoDB. Ở quy mô
1.000.000 đơn, Q3 giảm từ 160,858 xuống 0,959 ms ở MySQL và từ 559,381
xuống 0,745 ms ở MongoDB. MongoDB Q2 giảm từ 584,627 xuống 0,524 ms ở
quy mô một triệu đơn. Ngược lại, Q4 chậm hơn khoảng 2,2–10,9% tuỳ DBMS
và quy mô; Q7 thay đổi rất nhỏ. Kết quả xác nhận index có tác động phụ
thuộc truy vấn, không phải mọi truy vấn đều nhanh hơn.

# 12. KẾT QUẢ BENCHMARK VÀ TRẢ LỜI RQ5–RQ6

## 12.1. Phương pháp và môi trường đo

Benchmark được chạy trong GitHub Actions run #7, commit
d3e52159, trên hai quy mô generator: s (100.000 đơn) và m
(1.000.000 đơn). Mỗi quy mô chạy trên runner Ubuntu riêng, 4 logical
CPU, khoảng 16 GB RAM; CPU lần lượt là AMD EPYC 9V45 và AMD EPYC 7763.
Phiên bản phần mềm: Python 3.12.16, MySQL 8.4.13 và MongoDB 8.0.38.
InnoDB buffer pool và WiredTiger cache đều được đặt ở 1 GiB. Mỗi truy
vấn chạy 5 lượt warm-up và 30 lượt đo, concurrency = 1, một client tuần
tự. Database được restart trước lượt indexed; sau đó warm-up lại.

Hai chế độ được so sánh là baseline (không có workload secondary index,
nhưng vẫn giữ các index bắt buộc của schema/constraint) và indexed
(thêm bộ workload secondary index). Kết quả cardinality của Q1–Q8 khớp
giữa MySQL và MongoDB ở mọi lần đo thuộc cả hai chế độ. Đây là kiểm tra
số lượng kết quả, không phải phép so sánh từng giá trị trong result set.

Raw CSV, summary CSV, metadata và thời gian tạo index được lưu trong
artifact benchmark-s và benchmark-m của
[GitHub Actions run #7](https://github.com/Nguyen-Danh-Hai-Dang/HQTCSDL-G7/actions/runs/45774155670).
Bảng dưới đây dùng median latency (ms); phần trăm thể hiện mức giảm
latency khi thêm index. Số âm nghĩa là latency tăng.

| Quy mô | DBMS | Query | Baseline (ms) | Indexed (ms) | Giảm latency |
|---|---|---|---:|---:|---:|
| 100k | MySQL | Q1 | 0,441 | 0,437 | 0,9% |
| 100k | MySQL | Q2 | 0,223 | 0,181 | 18,8% |
| 100k | MySQL | Q3 | 9,375 | 0,386 | 95,9% |
| 100k | MySQL | Q4 | 183,546 | 187,660 | -2,2% |
| 100k | MySQL | Q5 | 22,922 | 16,497 | 28,0% |
| 100k | MySQL | Q6 | 27,562 | 21,407 | 22,3% |
| 100k | MySQL | Q7 | 0,213 | 0,244 | -14,7% |
| 100k | MySQL | Q8 | 19,922 | 12,838 | 35,6% |
| 100k | MongoDB | Q1 | 0,157 | 0,152 | 3,1% |
| 100k | MongoDB | Q2 | 31,187 | 0,243 | 99,2% |
| 100k | MongoDB | Q3 | 35,723 | 0,409 | 98,9% |
| 100k | MongoDB | Q4 | 295,364 | 327,647 | -10,9% |
| 100k | MongoDB | Q5 | 55,405 | 14,307 | 74,2% |
| 100k | MongoDB | Q6 | 80,595 | 40,301 | 50,0% |
| 100k | MongoDB | Q7 | 0,531 | 0,530 | 0,3% |
| 100k | MongoDB | Q8 | 51,788 | 14,463 | 72,1% |
| 1M | MySQL | Q1 | 1,060 | 0,987 | 6,8% |
| 1M | MySQL | Q2 | 0,490 | 0,447 | 8,7% |
| 1M | MySQL | Q3 | 160,858 | 0,959 | 99,4% |
| 1M | MySQL | Q4 | 3.049,647 | 3.160,366 | -3,6% |
| 1M | MySQL | Q5 | 412,866 | 286,763 | 30,5% |
| 1M | MySQL | Q6 | 472,748 | 351,112 | 25,7% |
| 1M | MySQL | Q7 | 0,496 | 0,498 | -0,4% |
| 1M | MySQL | Q8 | 377,022 | 238,862 | 36,6% |
| 1M | MongoDB | Q1 | 0,387 | 0,408 | -5,5% |
| 1M | MongoDB | Q2 | 584,627 | 0,524 | 99,9% |
| 1M | MongoDB | Q3 | 559,381 | 0,745 | 99,9% |
| 1M | MongoDB | Q4 | 4.548,580 | 4.884,114 | -7,4% |
| 1M | MongoDB | Q5 | 813,981 | 227,972 | 72,0% |
| 1M | MongoDB | Q6 | 1.220,147 | 632,492 | 48,2% |
| 1M | MongoDB | Q7 | 0,796 | 0,805 | -1,2% |
| 1M | MongoDB | Q8 | 831,448 | 243,674 | 70,7% |

Các số liệu cho thấy Q3 là truy vấn hưởng lợi rõ nhất ở cả hai DBMS.
Q2 của MongoDB cũng giảm rất mạnh khi index phù hợp được tạo. Q5, Q6
và Q8 có cải thiện đáng kể. Trái lại, Q4 chậm hơn sau khi thêm index;
đây có thể là truy vấn tổng hợp mà bộ index hiện tại không hỗ trợ đủ
hiệu quả. Các thay đổi rất nhỏ ở Q1/Q7 cần được xem trong bối cảnh
độ nhiễu đo, không nên diễn giải thành suy giảm hiệu năng có ý nghĩa.

## RQ5. Có/không có workload secondary index trong cùng workload và quy mô

Trong phạm vi cấu hình đã thử, index làm giảm median latency của phần
lớn truy vấn, nhưng mức cải thiện khác nhau rõ rệt theo query và DBMS.
Đây là câu trả lời định lượng cho so sánh baseline/indexed ở hai quy mô
100.000 và 1.000.000 đơn. Tuy nhiên, benchmark chỉ so sánh một bộ
secondary index theo workload với baseline; chưa tách riêng từng index
đơn, compound, covering hoặc multikey để quy kết đóng góp của từng index.
Không có cơ sở để tuyên bố MySQL hoặc MongoDB nhanh hơn một cách tổng
quát, vì mỗi hệ có truy vấn thắng/thua khác nhau.

## RQ6. Ảnh hưởng của quy mô dữ liệu

Đã chạy hai quy mô 100.000 và 1.000.000 đơn. Thời gian tạo workload
index ở quy mô 100.000 là 0,767 giây (MySQL) và 1,051 giây (MongoDB);
ở quy mô 1.000.000 là 6,767 giây và 10,271 giây tương ứng. Dung lượng
index tăng theo quy mô: ở 100.000 đơn, tổng index bytes ghi nhận là
19,12 MB (MySQL) và 5,12 MB (MongoDB) ở baseline, tăng lên 21,25 MB
và 11,18 MB ở indexed; ở 1.000.000 đơn, các giá trị lần lượt là
162,68 MB và 40,28 MB ở baseline, tăng lên 185,70 MB và 106,23 MB.
Đây là kích thước index tổng theo metadata DBMS, không chỉ riêng phần
index vừa tạo.

Không thể xem chênh lệch latency giữa hai quy mô là một phép đo scaling
hoàn toàn được kiểm soát, vì hai matrix job chạy trên CPU model khác
nhau (dù cùng 4 logical CPU và khoảng 16 GB RAM). Quy mô 10.000.000
đơn chưa chạy: riêng file dữ liệu thô ước lượng khoảng 7 GB, chưa tính
database files, index và overhead của hai DBMS, vượt ngân sách dung
lượng an toàn của runner hiện tại. Vì vậy RQ6 có bằng chứng ở hai mức
đầu, nhưng chưa kết luận được hành vi ở 10 triệu đơn hay điểm vượt cache.

## 12.2. Giới hạn diễn giải và kế hoạch tiếp theo

sequential_ops_per_second trong summary là nghịch đảo của mean latency
cho một client tuần tự, không phải throughput dưới tải đồng thời. CI
không thu thập CPU utilization, I/O throughput hoặc cache hit ratio
trong từng truy vấn. p95/p99 và 30 mẫu latency có trong raw/summary CSV
của artifact, nhưng kết luận chính ở đây dùng median để giảm ảnh hưởng
outlier. Muốn đánh giá production cần benchmark concurrency, tải hỗn
hợp đọc/ghi, cold-cache và nhiều lần lặp trên cùng phần cứng.

Các bước còn lại là chạy mức 10 triệu đơn trên máy có đủ dung lượng,
tách riêng từng loại secondary index và đo thêm tài nguyên hệ thống.
Không ngoại suy kết quả 100 nghìn/1 triệu thành kết luận cho 10 triệu.

# 13. HẠN CHẾ, HƯỚNG PHÁT TRIỂN VÀ KẾT LUẬN

## 13.1. Hạn chế

- Benchmark latency đã được xác nhận ở hai quy mô 100.000 và 1.000.000
  đơn; chưa chạy 10.000.000 đơn do giới hạn dung lượng runner.

- Chỉ so sánh baseline với một cấu hình workload secondary index; chưa
  cô lập đóng góp của từng index đơn, compound, covering và multikey.

- Hai quy mô benchmark chạy trên CPU model khác nhau; không dùng chênh
  lệch tuyệt đối giữa chúng để suy ra tốc độ tăng trưởng do dữ liệu.

- CI dùng một client tuần tự; chưa đo throughput đồng thời, CPU, RAM,
  I/O hoặc cache hit/miss trong từng truy vấn.

- Các script nghiệp vụ đã qua CI tích hợp trên MySQL 8.4 và MongoDB 8.0
  replica set với fixture nhỏ; CI benchmark là một luồng kiểm thử riêng.

## 13.2. Hướng phát triển

1. Chạy benchmark 10 triệu đơn trên máy/VM có đủ dung lượng và RAM, giữ
   phần cứng cố định giữa các quy mô.
2. Tách cấu hình index đơn, compound, covering và multikey để đánh giá
   đóng góp riêng của từng index.
3. Đo warm/cold cache, concurrency, throughput và latency percentiles.
4. Thu thập CPU, RAM, I/O, cache hit/miss, chi phí import và dung lượng
   database/index.
5. Bổ sung workload hỗn hợp đọc/ghi và kiểm tra race condition W1/W2/W3.
6. Thử workload thực tế hơn, dữ liệu từ nhiều cửa hàng và các mẫu báo
   cáo mở rộng.

## 13.3. Kết luận

Project đã hình thành được hai mô hình dữ liệu tương ứng, bộ sinh dữ
liệu chung, workload Q1–Q8, các thao tác ghi W1–W3 và các index chính
phục vụ truy vấn. Pilot 1.000 đơn xác nhận chức năng; benchmark có kiểm
soát ở 100.000 và 1.000.000 đơn cung cấp bằng chứng định lượng về ảnh
hưởng của workload secondary index.

Kết quả không cho thấy một DBMS thắng ở mọi truy vấn. Index cải thiện
rất mạnh Q3 ở cả hai hệ và MongoDB Q2, cải thiện Q5/Q6/Q8 ở các mức độ
khác nhau, nhưng Q4 chậm hơn và Q1/Q7 gần như không đổi. Do đó, lựa
chọn DBMS và index phải dựa trên workload cụ thể, chi phí dung lượng,
thời gian tạo/duy trì index và tài nguyên triển khai. Chưa có kết quả
10 triệu đơn nên không kết luận về giới hạn mở rộng ở quy mô đó.

# TÀI LIỆU THAM KHẢO

\[1\] Oracle, MySQL 8.4 Reference Manual, “Clustered and Secondary
Indexes”,
https://dev.mysql.com/doc/refman/8.4/en/innodb-index-types.html (truy
cập 24/11/2026).

\[2\] MongoDB, MongoDB Manual 8.0, “Compound Indexes” và “Index Types”,
https://www.mongodb.com/docs/v8.0/core/indexes/index-types/ (truy cập
24/11/2026).

\[3\] MongoDB, MongoDB Manual 8.0, “Multikey Indexes”,
https://www.mongodb.com/docs/v8.0/core/indexes/index-types/index-multikey/
(truy cập 24/11/2026).

\[4\] MongoDB, MongoDB Manual 8.0, “Explain Results”,
https://www.mongodb.com/docs/v8.0/reference/explain-results/ (truy cập
24/11/2026).

\[5\] MongoDB, MongoDB Manual 8.0, “Transactions”,
https://www.mongodb.com/docs/v8.0/core/transactions/ (truy cập
24/11/2026).

\[6\] MongoDB, MongoDB Manual 8.0, “Create an Index”,
https://www.mongodb.com/docs/v8.0/core/indexes/create-index/ (truy cập
24/11/2026).

\[7\] Oracle, MySQL 8.4 Reference Manual, “EXPLAIN Statement”,
https://dev.mysql.com/doc/refman/8.4/en/explain.html (truy cập
24/11/2026).

\[8\] Oracle, MySQL 8.4 Reference Manual, “START TRANSACTION, COMMIT,
and ROLLBACK”, https://dev.mysql.com/doc/refman/8.4/en/commit.html (truy
cập 24/11/2026).

\[9\] Oracle, MySQL 8.4 Reference Manual, “InnoDB Introduction”,
https://dev.mysql.com/doc/refman/8.4/en/innodb-introduction.html (truy
cập 24/11/2026).

## PHỤ LỤC A. Danh mục mã nguồn

| **Tệp**                     | **Vai trò**                                          |
|-----------------------------|------------------------------------------------------|
| 01_mysql_schema.sql         | Tạo database và 8 bảng MySQL; không tự drop dữ liệu. |
| 02_mysql_indexes.sql        | Tạo secondary index và ANALYZE TABLE.                |
| 03_mongodb_schema.js        | Tạo 6 collection và JSON Schema validator.           |
| 03b_mongodb_indexes.js      | Tạo index MongoDB, gồm compound và multikey.         |
| 04_generate_data.py         | Sinh CSV, JSONL và manifest tái lập theo seed.       |
| 05_queries_mysql.sql        | Workload đọc Q1–Q8 và đối chiếu.                     |
| 06_queries_mongodb.js       | Workload MongoDB Q1–Q8, W1–W3 và verifyLoad().       |
| 07_write_workload_mysql.sql | Stored procedures W1–W3 có kiểm tra/rollback.        |
| 08_load_mysql.sql           | Nạp CSV vào MySQL bằng LOAD DATA LOCAL INFILE.       |
| tests/test_generator_w1.py   | Kiểm tra generator, inventory integrity và tính tái lập. |
| tests/mysql_workload_integration.sql | Kiểm thử W1/W3 trên MySQL 8.4 bằng fixture CI. |
| tests/mongodb_workload_integration.js | Kiểm thử W1/W2/W3 trên MongoDB replica set. |
| .github/workflows/generator-validation.yml | Tự động chạy generator và integration tests trên CI. |

## PHỤ LỤC B. Quy ước diễn giải số liệu

Số liệu pilot 1.000 đơn là kết quả kiểm thử chức năng. Số liệu latency
trong mục 12 lấy từ artifact benchmark của GitHub Actions run #7, gồm
raw CSV, summary CSV, metadata phần cứng/phần mềm và index build time.
Mỗi truy vấn có 30 mẫu sau 5 lượt warm-up. Không dựng thêm số liệu CPU,
I/O hoặc cache hit/miss; các chỉ số này chưa được thu thập. Kết quả
benchmark chỉ áp dụng cho hai quy mô 100.000 và 1.000.000 đơn, hai cấu
hình index đã thử và môi trường CI được mô tả trong báo cáo.
