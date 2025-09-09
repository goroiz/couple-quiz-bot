# 💞 Couple Quiz Discord Bot (Ganbi Edition)

Fun mini-game bot khusus pasangan: tebak preferensi, kebiasaan, memori, future plan, sampai **spicy (SFW & 18+)**. Skor tersimpan dengan SQLite dan ada **lifetime compatibility**.

## ✨ Fitur
- `/quiz_start @pasangan [rounds] [category]` — mulai quiz (default 10 soal, kategori `mix`)
- `/quiz_stop` — stop sesi aktif
- `/quiz_score [@pasangan]` — lihat lifetime compatibility
- `/quiz_bank` — lihat jumlah soal per kategori

**Kategori:** `mix`, `favorites`, `habits`, `memories`, `future`, `random`, `spicy_sfw`, `spicy_18`  
> *Catatan:* `spicy_18` tetap soft & flirty, aman di Discord (nggak vulgar).

## 🛠 Setup (Discord Developer Portal)
1. Buka **https://discord.com/developers/applications** → **New Application** → namai (misal `CoupleQuiz`).
2. Tab **Bot** → **Add Bot** → aktifkan **MESSAGE CONTENT INTENT** ✅ (optional tapi aman).
3. Tab **OAuth2 → URL Generator**:
   - Scopes: **bot**, **applications.commands**
   - Bot Permissions: **Send Messages**, **Embed Links**, **Read Message History**, **Use Slash Commands**
   - Copy **Invite URL** → invite ke server kamu.

## 🚀 Jalankan Lokal / RDP (Windows)
```bash
# clone repo
git clone https://github.com/<username>/couple-quiz-bot.git
cd couple-quiz-bot

# siapkan env
copy .env.example .env
# edit .env, isi DISCORD_TOKEN

# install deps
pip install -r requirements.txt

# run
python bot.py
