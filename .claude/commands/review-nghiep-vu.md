---
description: Rà soát thay đổi hiện tại theo quy tắc nghiệp vụ, phân quyền và dữ liệu nhạy cảm
argument-hint: "[phạm vi, ví dụ: diff hiện tại | backend/app/modules/ban_hang]"
---
Rà soát **$ARGUMENTS**. Nếu để trống thì rà diff chưa commit cộng các commit chưa push (`git diff` và `git log @{u}..` nếu có upstream).

Giao việc cho agent `nghiep-vu-reviewer`: đưa danh sách file thay đổi và yêu cầu kiểm tra theo checklist của agent. Khi agent trả kết quả:

1. Với mỗi phát hiện mức **Cao**: tự xác minh lại bằng cách đọc code hoặc viết test tái hiện. Phát hiện đúng thì sửa ngay và thêm test.
2. Mức **Trung bình**: sửa nếu nằm trong phạm vi task; ngoài phạm vi thì ghi vào "Việc phát sinh" của lộ trình.
3. Mức **Thấp**: liệt kê cho người dùng, không tự sửa.

Kết thúc bằng bảng tóm tắt gồm: phát hiện, mức độ, đã sửa hay chưa, test chứng minh.
