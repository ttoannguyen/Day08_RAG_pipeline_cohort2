# DANH SÁCH NGUỒN DỮ LIỆU CẦN TẢI (DATA SOURCES FOR RAG PIPELINE)

Tài liệu này tổng hợp toàn bộ thông tin chi tiết, đường dẫn và các tham số kỹ thuật cần thiết để tải về các tài liệu pháp lý và các bài báo phục vụ cho **Task 1** và **Task 2** của dự án RAG Pipeline.

---

## I. Văn Bản Pháp Luật Về Ma Túy & Chất Cấm (Task 1)

Các văn bản dưới đây được tra cứu từ **Cơ sở dữ liệu quốc gia về Văn bản quy phạm pháp luật (vbpl.vn)**. 

Do hệ thống `vbpl.vn` sử dụng **Next.js Server Actions** cho việc tải file, dưới đây là chi tiết đường dẫn giao diện và tham số JSON Payload tương ứng để thực hiện yêu cầu POST giải mã file (nếu tải tự động).

### 1. Luật Phòng, chống ma túy 2021
* **Số ký hiệu:** 73/2021/QH14
* **Ngày ban hành:** 30/03/2021 | **Hiệu lực:** 01/01/2022
* **Đường dẫn chi tiết trên VBPL:** [vbpl.vn - Luật 73/2021/QH14](https://vbpl.vn/van-ban/chi-tiet/luat-phong-chong-ma-tuy-so-73-2021-qh14--152501?tabs=tai-ve)
* **Thông số tải file (Next.js Server Action):**
  * **URL gửi request:** `https://vbpl.vn/van-ban/chi-tiet/luat-phong-chong-ma-tuy-so-73-2021-qh14--152501?tabs=tai-ve`
  * **Headers:**
    * `Accept`: `text/x-component`
    * `Next-Action`: `bad13391811d5f14d7670e66189def56c08ceb1f`
    * `Content-Type`: `text/plain;charset=UTF-8`
  * **JSON Payload:**
    ```json
    [{
      "bucketName": "vbpl",
      "folderName": "152501",
      "objectName": "73_2021_QH14 (2).doc",
      "preview": null
    }]
    ```
  * **Tên file đầu ra khuyến nghị:** `luat-phong-chong-ma-tuy-2021.doc`

### 2. Nghị định số 105/2021/NĐ-CP
* **Mô tả:** Quy định chi tiết và hướng dẫn thi hành một số điều của Luật Phòng, chống ma túy.
* **Số ký hiệu:** 105/2021/NĐ-CP
* **Ngày ban hành:** 04/12/2021 | **Hiệu lực:** 01/01/2022
* **Đường dẫn chi tiết trên VBPL:** [vbpl.vn - Nghị định 105/2021/NĐ-CP](https://vbpl.vn/van-ban/chi-tiet/nghi-dinh-so-105-2021-nd-cp-quy-dinh-chi-tiet-va-huong-dan-thi-hanh-mot-so-dieu-cua-luat-phong-chong-ma-tuy--154992?tabs=tai-ve)
* **Thông số tải file (Next.js Server Action):**
  * **URL gửi request:** `https://vbpl.vn/van-ban/chi-tiet/nghi-dinh-so-105-2021-nd-cp-quy-dinh-chi-tiet-va-huong-dan-thi-hanh-mot-so-dieu-cua-luat-phong-chong-ma-tuy--154992?tabs=tai-ve`
  * **Headers:**
    * `Accept`: `text/x-component`
    * `Next-Action`: `bad13391811d5f14d7670e66189def56c08ceb1f`
    * `Content-Type`: `text/plain;charset=UTF-8`
  * **JSON Payload:**
    ```json
    [{
      "bucketName": "vbpl",
      "folderName": "154992",
      "objectName": "105.2021.NĐ.CP.doc",
      "preview": null
    }]
    ```
  * **Tên file đầu ra khuyến nghị:** `nghi-dinh-105-2021.doc`

### 3. Bộ luật Hình sự 2015 (sửa đổi, bổ sung 2017)
* **Mô tả:** Chương XX - Các tội phạm về ma túy (Từ Điều 247 đến Điều 259).
* **Số ký hiệu:** 100/2015/QH13
* **Ngày ban hành:** 27/11/2015 | **Hiệu lực:** 01/01/2018
* **Đường dẫn chi tiết trên VBPL:** [vbpl.vn - Bộ luật hình sự 2015](https://vbpl.vn/van-ban/chi-tiet/bo-luat-hinh-su-so-100-2015-qh13--96122?tabs=tai-ve)
* **Thông số tải file (Next.js Server Action):**
  * **URL gửi request:** `https://vbpl.vn/van-ban/chi-tiet/bo-luat-hinh-su-so-100-2015-qh13--96122?tabs=tai-ve`
  * **Headers:**
    * `Accept`: `text/x-component`
    * `Next-Action`: `bad13391811d5f14d7670e66189def56c08ceb1f`
    * `Content-Type`: `text/plain;charset=UTF-8`
  * **JSON Payload:**
    ```json
    [{
      "bucketName": "vbpl",
      "folderName": "96122",
      "objectName": "100.2015.QH13.doc",
      "preview": null
    }]
    ```
  * **Tên file đầu ra khuyến nghị:** `bo-luat-hinh-su-2015.doc`

### 4. Nghị định số 28/2026/NĐ-CP (Danh mục chất ma túy mới nhất)
* **Mô tả:** Ban hành Danh mục các chất ma túy và tiền chất (thay thế hoàn toàn Nghị định 57/2022/NĐ-CP và 90/2024/NĐ-CP).
* **Số ký hiệu:** 28/2026/NĐ-CP
* **Ngày ban hành:** 19/01/2026 | **Hiệu lực:** 19/01/2026
* **Đường dẫn tải trực tiếp file PDF:** 
  * [Tải file PDF từ Công báo Chính phủ](https://congbaocdn.chinhphu.vn/180507251028987904/2026/2/4/28signed-1770197502883408446461.pdf)

---

## II. Các Bài Báo Về Nghệ Sĩ Liên Quan Đến Ma Túy (Task 2)

Dưới đây là 5 bài viết chi tiết từ báo chính thống **Dân Trí (dantri.com.vn)** để crawl nội dung văn bản.

### 1. Bài viết 1: Vụ án ca sĩ Chi Dân & Người mẫu Andrea Aybar (An Tây)
* **Tiêu đề:** Truy tố ca sĩ Chi Dân, người mẫu An Tây
* **URL:** [https://dantri.com.vn/phap-luat/truy-to-ca-si-chi-dan-nguoi-mau-an-tay-20260402122649916.htm](https://dantri.com.vn/phap-luat/truy-to-ca-si-chi-dan-nguoi-mau-an-tay-20260402122649916.htm)
* **Nội dung:** Viện Kiểm sát nhân dân TP.HCM truy tố ca sĩ Chi Dân và người mẫu An Tây liên quan đến hành vi tổ chức sử dụng và tàng trữ trái phép chất ma túy.

### 2. Bài viết 2: Vụ án diễn viên hài Hữu Tín
* **Tiêu đề:** Diễn viên hài Hữu Tín khai sử dụng ma túy do tò mò
* **URL:** [https://dantri.com.vn/phap-luat/dien-vien-hai-huu-tin-khai-su-dung-ma-tuy-do-to-mo-20230428133813927.htm](https://dantri.com.vn/phap-luat/dien-vien-hai-huu-tin-khai-su-dung-ma-tuy-do-to-mo-20230428133813927.htm)
* **Nội dung:** Kết án sơ thẩm của Tòa án nhân dân Quận 8 đối với diễn viên hài Hữu Tín khai nhận hành vi phạm tội tại tòa.

### 3. Bài viết 3: Vụ án ca sĩ Chu Bin
* **Tiêu đề:** Ca sĩ Chu Bin bị tạm giữ vì liên quan đến ma túy
* **URL:** [https://dantri.com.vn/phap-luat/ca-si-chu-bin-bi-tam-giu-vi-lien-quan-den-ma-tuy-20240606183158183.htm](https://dantri.com.vn/phap-luat/ca-si-chu-bin-bi-tam-giu-vi-lien-quan-den-ma-tuy-20240606183158183.htm)
* **Nội dung:** Cơ quan công an Quận 10, TP.HCM kiểm tra hành chính và tạm giữ ca sĩ Chu Bin liên quan đến sử dụng ma túy.

### 4. Bài viết 4: Vụ án diễn viên Lệ Hằng (Hoài "Thát-chơ")
* **Tiêu đề:** Nữ diễn viên đóng Hoài "Thát-chơ" có thể đối mặt hình phạt nào?
* **URL:** [https://dantri.com.vn/phap-luat/nu-dien-vien-dong-hoai-that-cho-co-the-doi-mat-hinh-phat-nao-20230424092227771.htm](https://dantri.com.vn/phap-luat/nu-dien-vien-dong-hoai-that-cho-co-the-doi-mat-hinh-phat-nao-20230424092227771.htm)
* **Nội dung:** Diễn viên thủ vai Hoài "Thát-chơ" phim *Xin hãy tin em* bị khởi tố về tội mua bán trái phép chất ma túy và đối mặt mức án 2-7 năm tù.

### 5. Bài viết 5: Vụ án người mẫu Nhikolai Đinh
* **Tiêu đề:** Nam người mẫu bị bắt trong đường dây ma túy ở khu Mả Lạng
* **URL:** [https://dantri.com.vn/phap-luat/nam-nguoi-mau-bi-bat-trong-duong-day-ma-tuy-o-khu-ma-lang-20240625231501020.htm](https://dantri.com.vn/phap-luat/nam-nguoi-mau-bi-bat-trong-duong-day-ma-tuy-o-khu-ma-lang-20240625231501020.htm)
* **Nội dung:** Cựu thí sinh Vietnam's Next Top Model và nam chính MV ca nhạc bị bắt quả tang khi đang giao dịch tàng trữ trái phép chất ma túy.
