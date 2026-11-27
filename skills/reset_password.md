---
name: reset_password
description: Quy trình đặt lại mật khẩu khi nhân viên quên mật khẩu hoặc tài khoản bị khóa.
---
# Đặt lại mật khẩu

1. Hỏi nhân viên đang dùng máy công ty hay máy cá nhân.
2. Máy công ty: mở cổng https://id.opsdesk.local/reset, nhập mã nhân viên, nhận mã OTP qua ứng dụng OpsAuth (không qua SMS).
3. Máy cá nhân: phải bật VPN trước, rồi làm như bước 2.
4. Tài khoản bị khóa sau 5 lần sai: tự mở khóa sau 30 phút. Gấp thì gọi máy lẻ 4357 (chữ HELP trên bàn phím).
5. Mật khẩu mới phải theo chính sách: tối thiểu 12 ký tự, không trùng 5 mật khẩu gần nhất.
6. Không bao giờ hỏi hay nhận mật khẩu của nhân viên qua chat.
