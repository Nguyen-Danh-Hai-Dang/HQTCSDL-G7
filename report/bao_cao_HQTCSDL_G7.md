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
soát, nhóm phát hiện một số điểm chưa an toàn ở thao tác ghi: W1 MySQL
ban đầu không thực hiện rollback thật khi thiếu tồn kho; W2 chưa kiểm
tra tính nhất quán giữa đơn và thanh toán; W1 MongoDB không transaction
có nguy cơ để lại đơn hàng chưa trừ kho. Các script đã được chỉnh theo
hướng kiểm tra điều kiện, transaction và rollback, nhưng bản chỉnh sửa
mới cần được chạy xác nhận lại trên môi trường của nhóm trước khi xem là
đã nghiệm thu.

Thực nghiệm pilot 1.000 đơn được dùng để xác nhận chức năng, không dùng
để kết luận hiệu năng ở quy mô lớn. Pilot ghi nhận 1.000 đơn, 2.705 dòng
chi tiết, 1.042 thanh toán, 20.000 dòng tồn kho và doanh thu gộp
601.330,15. Q1–Q8 đã được đối chiếu kết quả nghiệp vụ giữa hai hệ trong
các lần kiểm thử cục bộ trước đó. Chưa có bộ số liệu latency/throughput
được đo lặp có kiểm soát, cũng chưa chạy các mức 100 nghìn, 1 triệu và
10 triệu đơn trong điều kiện benchmark.

Vì vậy, báo cáo trả lời đầy đủ khía cạnh lý thuyết và thiết kế cho
RQ1–RQ4, nhưng giới hạn kết luận thực nghiệm đối với RQ4–RQ6. Các khuyến
nghị ở RQ7 được trình bày có điều kiện, dựa trên đặc điểm workload,
index và execution plan quan sát được, không khẳng định hệ nào nhanh hơn
trong mọi trường hợp.

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

Cả ba job đều PASS trên commit `8f42f2c` của nhánh
`fix/generator-w1-parity`. Đây là kiểm thử tích hợp tự động trên fixture
nhỏ, nhằm xác nhận cú pháp procedure, transaction và các nhánh nghiệp vụ
quan trọng. Nó không thay thế kiểm thử lại trên toàn bộ pilot 1.000 đơn,
không xác nhận Q1–Q8 trên commit mới và không phải benchmark latency/
throughput. Các kết quả pilot lịch sử ở mục 9.1 được giữ riêng, không
đánh đồng với fixture CI.

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

Về cơ chế, index phù hợp có thể giảm rows/docs examined và loại bỏ sort
hoặc lookup bổ sung. Execution plan pilot xác nhận Q1/Q2 sử dụng index.
Tuy nhiên, chưa có ma trận đo thời gian trước/sau index với nhiều lần
lặp, cũng chưa có số liệu p95/p99 hoặc throughput. Do đó, kết luận hiện
tại là có bằng chứng về việc optimizer sử dụng index, chưa đủ bằng chứng
định lượng mức giảm thời gian.

# 12. RQ5 VÀ RQ6: GIỚI HẠN BẰNG CHỨNG THỰC NGHIỆM

## RQ5. Có/không có Index trong cùng workload và quy mô

Đề cương yêu cầu ma trận hai DBMS nhân với các cấu hình index (chỉ
PK/\_id, index đơn, compound/covering), cùng dữ liệu logic, phần cứng,
cấu hình bộ nhớ và công cụ đo. Chỉ số cần thu thập gồm latency trung
bình, median, p95, p99, throughput, CPU/RAM/I/O, kích thước index và
thời gian tạo index.

Bộ script hiện có một cấu hình secondary index phục vụ workload. Nó chưa
tách thành đầy đủ các cấp độ no-secondary-index, single, compound và
covering cho từng truy vấn. Không có bộ benchmark latency/throughput
được xác minh, do đó RQ5 chưa thể kết luận MySQL hay MongoDB nhanh hơn,
hoặc index giúp bao nhiêu phần trăm. Kết quả pilot chỉ xác nhận tính
đúng đắn và đường truy cập index.

## RQ6. Khi quy mô dữ liệu tăng

Đề cương đề xuất các mức 100 nghìn, 1 triệu và 10 triệu đơn, điều chỉnh
theo phần cứng. Cần đo xu hướng latency, index size, cache hit/miss,
I/O, chi phí import và tạo index; đồng thời xác định điểm chuyển khi dữ
liệu/index vượt khả năng cache. Nhóm mới chạy pilot 1.000 đơn để kiểm
tra chức năng. Mức 100 nghìn trở lên chưa được chạy benchmark do giới
hạn tài nguyên máy tại thời điểm thực hiện.

Vì chỉ có một mức pilot và không có số liệu latency theo quy mô, RQ6
chưa được trả lời bằng thực nghiệm. Không thể suy diễn tuyến tính từ
1.000 lên 100.000 hoặc 3 triệu đơn. Cần chạy lại trên máy có đủ dung
lượng và tài nguyên, hoặc dùng máy/VM được cấp riêng, giữ cấu hình cố
định và ghi nhận đầy đủ.

## 12.1. Kế hoạch đo bổ sung

8.  Tạo ba mức dữ liệu đã chốt, xác nhận manifest và tính tương đương
    trước khi benchmark.

9.  Mỗi mức chạy hai DBMS với cùng bộ tham số truy vấn và các cấu hình
    index tách biệt.

10. Warm-up, chạy tối thiểu nhiều lần cho mỗi truy vấn; báo cáo median,
    p95, p99 và độ lệch chuẩn.

11. Đo riêng read, write, import và index build; không trộn thời gian
    sinh dữ liệu vào thời gian nạp DB.

12. Lưu explain, raw CSV, cấu hình phần cứng và log hệ thống cho từng
    lượt.

# 13. RQ7 (BỔ SUNG): KHUYẾN NGHỊ THEO NGHIỆP VỤ

Các khuyến nghị dưới đây là định hướng thiết kế, không phải kết luận xếp
hạng hiệu năng. Chúng cần được xác nhận bằng benchmark có kiểm soát
trước khi áp dụng ngoài phạm vi project.

| **Nghiệp vụ**                | **Chiến lược gợi ý**                                          | **Điều kiện / lưu ý**                                  |
|------------------------------|---------------------------------------------------------------|--------------------------------------------------------|
| Tra cứu đơn theo mã          | PK trong MySQL; \_id trong MongoDB                            | Equality lookup, chi phí thấp và ổn định               |
| Lịch sử mua hàng             | Compound (customer_id, order_date); Mongo thêm \_id tie-break | Thứ tự trường bám filter và sort                       |
| Lọc đơn theo trạng thái/ngày | Compound (status, order_date)                                 | Kiểm tra selectivity của status                        |
| Chi tiết đơn hàng            | MySQL JOIN theo FK; Mongo embedding items/payments            | Mongo document có giới hạn kích thước và số phần tử    |
| Báo cáo doanh thu            | Index hỗ trợ lọc ngày; tối ưu aggregation và đo scan          | Index không loại bỏ chi phí group/sum lớn              |
| Top sản phẩm/danh mục        | Index product_id / items.product_id                           | Multikey index hỗ trợ lọc mảng; group vẫn cần xử lý    |
| Ghi đơn và trừ kho           | Transaction MySQL; Mongo transaction đa document              | Index cần thiết nhưng tránh dư thừa vì tăng write cost |

## 13.1. Khi nào nghiêng về MySQL?

Khi nghiệp vụ yêu cầu quan hệ chặt, nhiều ràng buộc FK, truy vấn JOIN
linh hoạt và giao dịch nhiều bảng là trung tâm, MySQL/InnoDB là lựa chọn
tự nhiên. Các truy vấn phân tích quan hệ và ràng buộc dữ liệu có thể
được biểu diễn trực tiếp trong SQL.

## 13.2. Khi nào nghiêng về MongoDB?

Khi dữ liệu có cấu trúc document rõ, nhiều thao tác đọc một aggregate
như đơn hàng cùng items/payments, và schema cần linh hoạt theo sản phẩm,
MongoDB có thể giảm số lượt đọc/join. Khi thao tác chạm nhiều document
như tồn kho, transaction vẫn cần thiết; không nên đánh đồng embedding
với việc mọi giao dịch đều chỉ atomic trên một document.

## 13.3. Index nên tránh

Tránh tạo index chỉ vì một cột xuất hiện trong schema. Cần chứng minh
truy vấn sử dụng, selectivity đủ tốt và lợi ích đọc vượt chi phí
ghi/dung lượng. Index trùng lặp, compound sai thứ tự hoặc index trên
trường có cardinality thấp trong workload không phù hợp có thể làm hệ
thống nặng hơn.

# 14. HẠN CHẾ, HƯỚNG PHÁT TRIỂN VÀ KẾT LUẬN

## 14.1. Hạn chế

- Dữ liệu tổng hợp, phân phối Zipf và trạng thái đơn là giả định; không
  đại diện dữ liệu bán hàng thực.

- Chỉ pilot 1.000 đơn được xác nhận; chưa có benchmark
  latency/throughput ở quy mô lớn.

- Chưa hoàn thành ma trận cấu hình index đơn, compound, covering và
  baseline một cách tách biệt.

- Môi trường kiểm thử là một máy Windows; chưa thử sharding hoặc cụm
  nhiều máy.

- Không có đầy đủ log CPU, RAM, I/O, cache, concurrency và số lần lặp
  cho phép so sánh hiệu năng thống kê.

- Các script hiện tại đã qua CI tích hợp trên MySQL 8.4 và MongoDB 8.0
  với fixture nhỏ; cần đối chiếu lại trên bộ pilot đầy đủ trước khi phát
  hành và trước khi chạy benchmark.

## 14.2. Hướng phát triển

13. Bổ sung harness benchmark chung cho MySQL và MongoDB, xuất raw CSV
    và cấu hình máy.

14. Tách các mức index và kiểm soát index bắt buộc (PK/\_id, unique, FK
    support) khỏi secondary index theo workload.

15. Đo warm/cold cache, concurrency, throughput và latency percentiles.

16. Chạy các mức dữ liệu theo khả năng tài nguyên; ghi thời gian import,
    build index, dung lượng database/index.

17. Bổ sung test âm cho W1/W2/W3, kiểm tra rollback và race condition.

18. Thử workload thực tế hơn, dữ liệu từ nhiều cửa hàng và các mẫu báo
    cáo mở rộng.

## 14.3. Kết luận

Project đã hình thành được hai mô hình dữ liệu tương ứng, bộ sinh dữ
liệu chung, workload Q1–Q8, các thao tác ghi W1–W3 và các index chính
phục vụ truy vấn. Pilot 1.000 đơn xác nhận dữ liệu được sinh và nạp, kết
quả truy vấn nghiệp vụ đối chiếu khớp trong các lần kiểm thử đã ghi
nhận; execution plan cho thấy các index chính được sử dụng ở Q1/Q2.

Tuy nhiên, câu hỏi về mức cải thiện thời gian truy vấn và ảnh hưởng khi
quy mô tăng vẫn cần benchmark có kiểm soát. Kết luận có trách nhiệm hiện
tại là: Index có vai trò quan trọng về đường truy cập, nhưng lợi ích
định lượng và lựa chọn DBMS tối ưu phụ thuộc workload, mô hình dữ liệu,
cấu hình hệ thống và quy mô. Không có cơ sở để tuyên bố một hệ luôn
nhanh hơn hệ còn lại.

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

Mọi con số pilot trong báo cáo là kết quả kiểm thử chức năng đã được
nhóm ghi nhận ở quy mô 1.000 đơn. Không có con số latency, throughput,
p95, p99, CPU, RAM hoặc I/O nào được dựng thêm. Khi benchmark được chạy,
cần bổ sung raw results, thông tin cấu hình, số lần lặp và biểu đồ có
nguồn dữ liệu đi kèm.

Báo cáo này là bản tổng hợp kỹ thuật trung thực theo bằng chứng hiện có;
các kết luận RQ5 và RQ6 được đánh dấu chưa đủ dữ liệu thay vì suy đoán.