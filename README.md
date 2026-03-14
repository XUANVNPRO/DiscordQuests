<div align="center">

# 🎮 Tzuan Quests

**Auto farm Discord Quest trực tiếp trên Terminal / Termux**
Không cần bot · Không cần server · Chạy ngay

---

![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20Termux-success?style=for-the-badge)
![License](https://img.shields.io/badge/License-Personal%20Use-blueviolet?style=for-the-badge)

</div>

---

## ✨ Tính Năng

| Tính năng | Mô tả |
|-----------|-------|
| 👥 **Đa tài khoản** | Thêm không giới hạn tài khoản, farm song song cùng lúc |
| 📡 **Live Progress** | Log tiến độ cập nhật liên tục, % hiện theo thời gian thực |
| 🤖 **AutoFarm** | Tự động tìm & farm quest mới mỗi 5 phút, chạy ngầm 24/7 |
| 🎨 **Giao diện màu** | Box ASCII đẹp, màu sắc đầy đủ, dễ đọc ngay trên terminal |
| 💾 **Lưu tự động** | Config & token lưu SQLite — tắt/mở lại không mất gì |
| 🛡️ **An toàn** | Token chỉ lưu local, không gửi đi bất kỳ đâu |

**Hỗ trợ loại quest:**
- 🎬 Xem Video (`WATCH_VIDEO`, `WATCH_VIDEO_ON_MOBILE`)
- 🎮 Chơi Game (`PLAY_ON_DESKTOP`)
- 📺 Stream (`STREAM_ON_DESKTOP`)
- 🕹️ Activity (`PLAY_ACTIVITY`)

---

## 📦 Yêu Cầu Hệ Thống

```
Python  3.9 trở lên
pip     (đi kèm Python)
```

### Thư viện

| Thư viện | Bắt buộc | Ghi chú |
|----------|----------|---------|
| `requests` | ✅ Có | Gọi Discord API |
| `colorama` | ⚪ Không | Màu trên Windows — Termux/Linux không cần |

---

## 🚀 Cài Đặt & Chạy

### 📱 Termux (Android)

```bash
pkg update && pkg upgrade -y
pkg install python -y
pip install requests
python tzuan_quest.py
```

### 🖥️ Windows

```batch
pip install requests colorama
python tzuan_quest.py
```

### 🐧 Linux / macOS

```bash
pip3 install requests colorama
python3 tzuan_quest.py
```

> 💡 Trên Linux/Termux màu ANSI hoạt động tự động, **không cần cài colorama**.

---

## 🕹️ Hướng Dẫn Sử Dụng

### Menu chính

```
╔══════════════════════════════════════════════════════╗
║              🎮  Tzuan Quests                        ║
╠══════════════════════════════════════════════════════╣
║  #1  @username  ◆AF   ⚙ 73% (2/3)                   ║
║  #2  @username2        ○ Rảnh                        ║
╠══════════════════════════════════════════════════════╣
║   1   👤  Quản lý tài khoản                          ║
║   2   🎯  Farm Quest                                  ║
║   3   🤖  AutoFarm                                    ║
║   4   🛑  Dừng Farm                                   ║
║   0   ❌  Thoát                                       ║
╚══════════════════════════════════════════════════════╝
```

---

### 1️⃣ Thêm tài khoản

```
Menu chính → [1] → [1] Thêm tài khoản → Nhập Token → Enter
```

Tool tự xác thực token và lưu vào database ngay lập tức.

---

### 2️⃣ Farm Quest

```
Menu chính → [2] → Chọn ID tài khoản → Chọn quest
```

**Chọn quest:**

| Nhập | Kết quả |
|------|---------|
| `1 3 2` | Farm quest 1 trước, rồi 3, rồi 2 |
| `1,3,2` | Tương tự (phẩy hay cách đều được) |
| `a` hoặc Enter | Farm tất cả theo thứ tự mặc định |

**Sau khi bắt đầu** tool hiển thị live log liên tục:

```
[10:25:31] 🎮 Game  Bắt đầu: Clash of Clans  (~12p)
│  Tiến độ: [████████░░░░░░░░]  52%  [1/3]
[10:37:44] ✅ Clash of Clans
[10:37:45] 🎬 Video  Bắt đầu: Discord Nitro  (~5p)
│  Tiến độ: [█░░░░░░░░░░░░░░░]   8%  [2/3]
```

> Nhấn `Ctrl+C` để về menu — **farm vẫn tiếp tục chạy ngầm.**

---

### 3️⃣ AutoFarm

```
Menu chính → [3] → Chọn tài khoản → [1] Bật
```

Sau khi bật, tool sẽ **tự động**:
1. Kiểm tra quest mới mỗi **5 phút**
2. Nhận quest nếu chưa nhận
3. Farm hết tất cả quest khả dụng
4. Lặp lại

Config AutoFarm lưu DB — **tắt tool rồi mở lại vẫn chạy tiếp.**

---

### 4️⃣ Dừng Farm

```
Menu chính → [4] → Nhập ID để dừng 1 acc  hoặc  a để dừng tất cả
```

---

## 📁 Cấu Trúc File

```
tzuan_quest/
├── tzuan_quest.py      ← Tool chính, chạy file này
├── tzuan.db            ← Database tự tạo khi chạy lần đầu
├── requirements.txt    ← Danh sách thư viện
└── README.md           ← File này
```

---

## ❓ Lỗi Thường Gặp

**`ModuleNotFoundError: No module named 'requests'`**
```bash
pip install requests
```

**`Token không hợp lệ`**
→ Copy lại token, đảm bảo không có khoảng trắng thừa ở đầu/cuối, không lấy dấu `"`

**`Không tìm thấy quest nào`**
→ Tài khoản hiện không có quest khả dụng, thử lại sau

**Màu không hiện trên Windows**
```bash
pip install colorama
```

---

## ⚠️ Lưu Ý Quan Trọng

> Tool **chỉ hoàn thành nhiệm vụ (task)**, **không tự nhận thưởng**.
> Sau khi farm xong, bạn phải **tự vào Discord để claim phần thưởng** thủ công.

---

<div align="center">

**Tzuan Quests**

</div>
