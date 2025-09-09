import os, random, sqlite3, asyncio, typing as T
from dataclasses import dataclass, field
from dotenv import load_dotenv

import discord
from discord import app_commands, Interaction, Embed
from discord.ui import View, Button

# ========== CONFIG ==========
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

INTENTS = discord.Intents.default()
INTENTS.message_content = False
CLIENT = discord.Client(intents=INTENTS)
TREE = app_commands.CommandTree(CLIENT)

DB_PATH = "couple_quiz.db"

# ==========: DB INIT ==========
def db_init():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS couples(
        a INTEGER NOT NULL,
        b INTEGER NOT NULL,
        PRIMARY KEY(a,b)
    )""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS scores(
        a INTEGER NOT NULL,
        b INTEGER NOT NULL,
        total_rounds INTEGER NOT NULL DEFAULT 0,
        total_matches INTEGER NOT NULL DEFAULT 0,
        last_played INTEGER NOT NULL DEFAULT (strftime('%s','now')),
        PRIMARY KEY(a,b)
    )""")
    con.commit()
    con.close()

def norm_pair(u1: int, u2: int) -> tuple[int,int]:
    return (u1, u2) if u1 < u2 else (u2, u1)

def db_add_round(u1: int, u2: int, match: bool):
    a,b = norm_pair(u1,u2)
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("INSERT OR IGNORE INTO couples(a,b) VALUES(?,?)", (a,b))
    cur.execute("INSERT OR IGNORE INTO scores(a,b,total_rounds,total_matches) VALUES(?,?,0,0)", (a,b))
    cur.execute("""
        UPDATE scores
        SET total_rounds = total_rounds + 1,
            total_matches = total_matches + ?,
            last_played = strftime('%s','now')
        WHERE a=? AND b=?
    """, (1 if match else 0, a, b))
    con.commit()
    con.close()

def db_get_score(u1: int, u2: int) -> tuple[int,int]:
    a,b = norm_pair(u1,u2)
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("SELECT total_rounds,total_matches FROM scores WHERE a=? AND b=?", (a,b))
    row = cur.fetchone()
    con.close()
    if not row: return (0,0)
    return (row[0], row[1])

# ==========: QUESTION BANK ==========
Q_BANK: dict[str, list[dict]] = {
  "favorites": [
    {"type":"either","q":"Lebih pilih **nonton film** atau **denger musik**?","a":"Nonton film","b":"Denger musik"},
    {"type":"either","q":"Makan **manis** atau **asin**?","a":"Manis","b":"Asin"},
    {"type":"either","q":"**Pantai** atau **pegunungan**?","a":"Pantai","b":"Pegunungan"},
    {"type":"either","q":"**Kopi** atau **teh**?","a":"Kopi","b":"Teh"},
    {"type":"either","q":"**Ayam geprek** atau **mie ayam**?","a":"Ayam geprek","b":"Mie ayam"},
    {"type":"either","q":"**Siang** vs **malam** orangnya?","a":"Siang","b":"Malam"},
    {"type":"either","q":"Main **game** atau **scroll sosmed**?","a":"Game","b":"Sosmed"},
    {"type":"either","q":"**Indomie kuah** atau **goreng**?","a":"Kuah","b":"Goreng"},
    {"type":"either","q":"**Kucing** atau **anjing**?","a":"Kucing","b":"Anjing"},
    {"type":"either","q":"**Staycation** atau **jalan-jalan jauh**?","a":"Staycation","b":"Jalan jauh"},
    {"type":"either","q":"**Es krim** atau **coklat**?","a":"Es krim","b":"Coklat"},
    {"type":"either","q":"**Drama** atau **komedi**?","a":"Drama","b":"Komedi"},
    {"type":"either","q":"**Street food** atau **resto fancy**?","a":"Street food","b":"Resto"},
    {"type":"either","q":"**Burger** atau **pizza**?","a":"Burger","b":"Pizza"},
    {"type":"either","q":"**Sneakers** atau **sandal**?","a":"Sneakers","b":"Sandal"},
  ],
  "habits": [
    {"type":"who","q":"Siapa yang **lebih sering telat**?"},
    {"type":"who","q":"Siapa yang **lebih bawel**?"},
    {"type":"who","q":"Siapa yang **lebih cuek**?"},
    {"type":"who","q":"Siapa yang **lebih rapi**?"},
    {"type":"who","q":"Siapa yang **lebih hemat**?"},
    {"type":"who","q":"Siapa yang **lebih mager**?"},
    {"type":"who","q":"Siapa yang **lebih gampang ngambek**?"},
    {"type":"who","q":"Siapa yang **lebih suka chat panjang**?"},
    {"type":"who","q":"Siapa yang **lebih cepat bales**?"},
    {"type":"who","q":"Siapa yang **lebih kompetitif** pas main game?"},
    {"type":"who","q":"Siapa yang **lebih romantis**?"},
    {"type":"who","q":"Siapa yang **lebih sering lapar malam**?"},
    {"type":"who","q":"Siapa yang **lebih pelupa**?"},
    {"type":"who","q":"Siapa yang **lebih cerewet soal makanan**?"},
    {"type":"who","q":"Siapa yang **lebih suka selfie**?"},
  ],
  "memories": [
    {"type":"either","q":"Date pertama ideal: **nonton** atau **makan**?","a":"Nonton","b":"Makan"},
    {"type":"either","q":"Lebih memorable: **chat maraton** atau **tele lama**?","a":"Chat maraton","b":"Tele lama"},
    {"type":"either","q":"Foto couple: **mirror** atau **kamera belakang**?","a":"Mirror","b":"Kamera belakang"},
    {"type":"either","q":"Kado favorit: **surprise kecil** vs **satu hadiah besar**?","a":"Surprise kecil","b":"Satu hadiah besar"},
    {"type":"who","q":"Siapa yang **nyatain perasaan duluan (vibe-nya)**?"},
    {"type":"who","q":"Siapa yang **lebih sering minta maaf duluan**?"},
    {"type":"who","q":"Siapa yang **lebih sering inisiatif ketemu**?"},
    {"type":"who","q":"Siapa yang **lebih sering simpen foto momen**?"},
    {"type":"who","q":"Siapa yang **lebih sering bilang kangen** duluan?"},
    {"type":"who","q":"Siapa yang **lebih sering ngasih panggilan sayang**?"},
  ],
  "future": [
    {"type":"either","q":"Mau tinggal di **kota rame** atau **kota tenang**?","a":"Kota rame","b":"Kota tenang"},
    {"type":"either","q":"Target dulu: **tabungan** atau **liburan**?","a":"Tabungan","b":"Liburan"},
    {"type":"either","q":"**Nikah simple** atau **resepsi besar** (kalau ada duit)?","a":"Simple","b":"Besar"},
    {"type":"either","q":"Pelihara **satu hewan** atau **nggak pelihara**?","a":"Pelihara","b":"Tidak"},
    {"type":"either","q":"Punya **rumah dulu** atau **mobil dulu**?","a":"Rumah dulu","b":"Mobil dulu"},
    {"type":"scale","q":"Seberapa pengen **keliling dunia bareng**? (1-5)"},
    {"type":"scale","q":"Seberapa penting **kerja bareng satu kota**? (1-5)"},
    {"type":"scale","q":"Seberapa siap **menabung bareng**? (1-5)"},
    {"type":"scale","q":"Seberapa sering **quality time ideal** per minggu? (1-5)"},
    {"type":"scale","q":"Seberapa pengen **punya project bareng**? (1-5)"},
  ],
  "random": [
    {"type":"either","q":"Chat **pagi** vs **malam**?","a":"Pagi","b":"Malam"},
    {"type":"either","q":"Tipe **planner** atau **spontan**?","a":"Planner","b":"Spontan"},
    {"type":"either","q":"Lebih takut **ketinggian** atau **ruangan gelap**?","a":"Ketinggian","b":"Gelap"},
    {"type":"either","q":"Main **co-op** atau **1v1**?","a":"Co-op","b":"1v1"},
    {"type":"either","q":"Pilih **hemat** atau **treat yourself**?","a":"Hemat","b":"Treat"},
    {"type":"either","q":"**Sarapan** wajib atau skip aja?","a":"Wajib","b":"Skip"},
    {"type":"either","q":"**Chat tiap saat** atau **quality chat** aja?","a":"Tiap saat","b":"Quality chat"},
    {"type":"either","q":"**Telpon** atau **VC**?","a":"Telpon","b":"VC"},
    {"type":"either","q":"**Keju** atau **cabe**?","a":"Keju","b":"Cabe"},
    {"type":"either","q":"**Nyemil** atau **sekali makan banyak**?","a":"Nyemil","b":"Sekali banyak"},
  ],
  "spicy_sfw": [
    {"type":"either","q":"Peluk **lama** atau **sering**?","a":"Lama","b":"Sering"},
    {"type":"either","q":"Lebih suka **PDA kecil** atau **private affection**?","a":"PDA kecil","b":"Private"},
    {"type":"either","q":"Kirim **voice note** atau **teks panjang**?","a":"VN","b":"Teks panjang"},
    {"type":"either","q":"Lebih bikin baper **kata manis** atau **gesture kecil**?","a":"Kata manis","b":"Gesture"},
    {"type":"who","q":"Siapa yang **lebih bikin baper**?"},
    {"type":"who","q":"Siapa yang **lebih suka dipuji**?"},
    {"type":"scale","q":"Seberapa suka **surprise romantis**? (1-5)"},
    {"type":"scale","q":"Seberapa penting **anniversary-an**? (1-5)"},
    {"type":"scale","q":"Seberapa pengen **date rutin** tiap minggu? (1-5)"},
    {"type":"scale","q":"Seberapa nyaman **public photos** bareng? (1-5)"},
  ],
  # 🔥 kategori 18+ (tetep soft/flirty & aman untuk Discord)
  "spicy_18": [
    {"type":"either","q":"Lebih suka **cium lama** atau **cium singkat tapi sering**?","a":"Lama","b":"Singkat"},
    {"type":"either","q":"Mending **pelukan erat** atau **cium pipi random**?","a":"Pelukan erat","b":"Cium pipi"},
    {"type":"either","q":"Lebih bikin deg-degan **bisikan di telinga** atau **tatapan intens**?","a":"Bisikan","b":"Tatapan"},
    {"type":"either","q":"Kalau lagi berduaan: **nonton film** atau **'main' sendiri**?","a":"Nonton","b":"Main"},
    {"type":"either","q":"**Light bite (gigit manja)** atau **kecup halus**?","a":"Light bite","b":"Kecup halus"},
    {"type":"either","q":"**PDA kecil di publik** atau **full private**?","a":"PDA kecil","b":"Private"},
    {"type":"who","q":"Siapa yang **lebih suka mulai duluan** pas lagi mesra?"},
    {"type":"who","q":"Siapa yang **lebih sering bikin kangen fisik**?"},
    {"type":"who","q":"Siapa yang **lebih gampang malu kalau di-puji seksi**?"},
    {"type":"who","q":"Siapa yang **lebih berani coba hal baru**?"},
    {"type":"scale","q":"Seberapa suka **cuddle sambil tidur**? (1-5)"},
    {"type":"scale","q":"Seberapa sering pengen **quality time intim** per minggu? (1-5)"},
    {"type":"scale","q":"Seberapa nyaman **eksperimen bareng**? (1-5)"},
    {"type":"scale","q":"Seberapa penting **aftercare pelukan** setelah mesra? (1-5)"},
    {"type":"scale","q":"Seberapa sering pengen **kirim chat/flirty 18+**? (1-5)"},
  ],
}
ALL_CATS = list(Q_BANK.keys())

# ==========: SESSION ==========
@dataclass
class AnswerState:
    me: dict[int, str] = field(default_factory=dict)  # uid -> answer
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)

@dataclass
class QuizSession:
    channel_id: int
    p1: int
    p2: int
    questions: list[dict]
    idx: int = 0
    matches: int = 0
    total: int = 0
    answers: AnswerState = field(default_factory=AnswerState)
    active: bool = True
    category: str = "mix"

SESSIONS: dict[int, QuizSession] = {}  # channel_id -> session

def build_quiz(partner1: int, partner2: int, rounds: int, category: str) -> list[dict]:
    pool: list[dict] = []
    if category == "mix":
        for cat in ALL_CATS:
            pool.extend(Q_BANK[cat])
    else:
        pool.extend(Q_BANK.get(category, []))
    random.shuffle(pool)
    if rounds > len(pool):
        rounds = len(pool)
    return pool[:rounds]

# ==========: VIEWS ==========
class EitherView(View):
    def __init__(self, sess: QuizSession, a: str, b: str, timeout: float = 45):
        super().__init__(timeout=timeout)
        self.sess = sess
        self.add_item(AnsButton(label=a, value="A", sess=sess))
        self.add_item(AnsButton(label=b, value="B", sess=sess))

class WhoView(View):
    def __init__(self, sess: QuizSession, timeout: float = 45):
        super().__init__(timeout=timeout)
        self.sess = sess
        self.add_item(WhoButton("Aku", "ME", sess))
        self.add_item(WhoButton("Kamu", "YOU", sess))

class ScaleView(View):
    def __init__(self, sess: QuizSession, timeout: float = 45):
        super().__init__(timeout=timeout)
        for n in range(1,6):
            self.add_item(AnsButton(label=str(n), value=str(n), sess=sess, style=discord.ButtonStyle.secondary))

class AnsButton(Button):
    def __init__(self, label: str, value: str, sess: QuizSession, style=discord.ButtonStyle.primary):
        super().__init__(label=label, style=style)
        self.value = value
        self.sess = sess

    async def callback(self, itx: Interaction):
        sess = self.sess
        if not sess.active:
            return await itx.response.send_message("Sesi sudah selesai.", ephemeral=True)
        if itx.user.id not in (sess.p1, sess.p2):
            return await itx.response.send_message("Buat couple ini doang ya 😄", ephemeral=True)
        async with sess.answers.lock:
            if itx.user.id in sess.answers.me:
                return await itx.response.send_message("Kamu udah pilih. Tunggu pasanganmu~", ephemeral=True)
            sess.answers.me[itx.user.id] = self.value
            await itx.response.send_message(f"Jawaban kamu: **{self.label}** ✅", ephemeral=True)
            await maybe_resolve_question(itx, sess)

class WhoButton(Button):
    def __init__(self, label: str, internal_value: str, sess: QuizSession):
        super().__init__(label=label, style=discord.ButtonStyle.primary)
        self.internal = internal_value
        self.sess = sess

    async def callback(self, itx: Interaction):
        sess = self.sess
        if not sess.active:
            return await itx.response.send_message("Sesi sudah selesai.", ephemeral=True)
        if itx.user.id not in (sess.p1, sess.p2):
            return await itx.response.send_message("Buat couple ini doang ya 😄", ephemeral=True)
        # normalisasi: simpan jawaban sebagai 'P1'/'P2' relatif ke p1
        val = f"{'P1' if (self.internal=='ME' and itx.user.id==sess.p1) or (self.internal=='YOU' and itx.user.id==sess.p2) else 'P2'}"
        async with sess.answers.lock:
            if itx.user.id in sess.answers.me:
                return await itx.response.send_message("Kamu udah pilih. Tunggu pasanganmu~", ephemeral=True)
            sess.answers.me[itx.user.id] = val
            await itx.response.send_message(f"Jawaban kamu: **{self.label}** ✅", ephemeral=True)
            await maybe_resolve_question(itx, sess)

# ==========: FLOW ==========
async def maybe_resolve_question(itx: Interaction, sess: QuizSession):
    if len(sess.answers.me) < 2:
        return
    q = sess.questions[sess.idx]
    match = False

    if q["type"] in ("either","scale"):
        vals = list(sess.answers.me.values())
        if q["type"] == "either":
            match = vals[0] == vals[1]
        else:
            try:
                a,b = int(vals[0]), int(vals[1])
                match = abs(a-b) <= 1  # toleransi
            except:
                match = False
    elif q["type"] == "who":
        vals = list(sess.answers.me.values())  # 'P1' / 'P2'
        match = vals[0] == vals[1]

    if match: sess.matches += 1
    sess.total += 1
    db_add_round(sess.p1, sess.p2, match)

    pct = round(sess.matches / sess.total * 100)
    desc = "KOMPAT! 🫶" if match else "Belum nyambung 😝"
    color = 0x2ecc71 if match else 0xe67e22
    embed = Embed(title="Hasil Soal", description=desc, color=color)
    embed.add_field(name="Soal", value=q["q"], inline=False)
    embed.add_field(name="Progress", value=f"{sess.idx+1}/{len(sess.questions)}", inline=True)
    embed.add_field(name="Match Rate (session)", value=f"{pct}%", inline=True)
    try:
        await itx.channel.send(embed=embed)
    except:
        pass

    # next
    sess.idx += 1
    sess.answers.me.clear()

    if sess.idx >= len(sess.questions):
        sess.active = False
        await end_session(itx, sess)
    else:
        await ask_next(itx, sess)

async def ask_next(itx: Interaction, sess: QuizSession):
    q = sess.questions[sess.idx]
    title = f"Couple Quiz • {sess.category.upper() if sess.category!='mix' else 'MIX'}"
    embed = Embed(title=title, description=q["q"], color=0x5865F2)
    embed.set_footer(text=f"Soal {sess.idx+1}/{len(sess.questions)} • Jawab pake tombol")

    if q["type"] == "either":
        view = EitherView(sess, q.get("a","A"), q.get("b","B"))
    elif q["type"] == "who":
        view = WhoView(sess)
    else:
        view = ScaleView(sess)
    await itx.channel.send(embed=embed, view=view)

async def end_session(itx: Interaction, sess: QuizSession):
    total = sess.total
    matches = sess.matches
    rate = 0 if total==0 else round(matches/total*100)
    a,b = db_get_score(sess.p1, sess.p2)
    lifetime_rate = 0 if a==0 else round(b/a*100)

    u1 = itx.guild.get_member(sess.p1)
    u2 = itx.guild.get_member(sess.p2)

    embed = Embed(
        title="✨ Sesi Selesai!",
        description=f"{u1.mention} × {u2.mention}\n**Match {matches}/{total} • {rate}%**",
        color=0x9b59b6
    )
    embed.add_field(name="Lifetime Compatibility", value=f"{lifetime_rate}% (total {a} soal)", inline=True)
    tips = random.choice([
        "Kalian makin sinkron! Coba kategori *memories* besok.",
        "Nice run! Pengen tantangan? Main *spicy_18* (aman & flirty).",
        "Cobain skala 1–5 di *future* buat rencana bareng.",
        "Bikin ritual harian 5 soal setiap malam 🌙."
    ])
    embed.set_footer(text=tips)
    await itx.channel.send(embed=embed)
    SESSIONS.pop(sess.channel_id, None)

# ==========: COMMANDS ==========
@TREE.command(name="quiz_start", description="Mulai Couple Quiz bareng pasangan")
@app_commands.describe(partner="Mention pasanganmu", rounds="Jumlah soal (default 10, max 30)", category="Kategori: mix/favorites/habits/memories/future/random/spicy_sfw/spicy_18")
async def quiz_start(itx: Interaction, partner: discord.User, rounds: app_commands.Range[int,1,30]=10, category: str="mix"):
    me = itx.user.id
    you = partner.id
    if me == you:
        return await itx.response.send_message("Harus mention pasanganmu ya, bukan dirimu sendiri 😆", ephemeral=True)
    if itx.channel.id in SESSIONS and SESSIONS[itx.channel.id].active:
        return await itx.response.send_message("Channel ini lagi ada sesi berjalan. `/quiz_stop` dulu kalau mau ganti.", ephemeral=True)
    category = category.lower()
    if category != "mix" and category not in Q_BANK:
        return await itx.response.send_message(f"Kategori gak valid. Pilih: `mix`, {', '.join(Q_BANK.keys())}", ephemeral=True)

    qs = build_quiz(me, you, rounds, category)
    if not qs:
        return await itx.response.send_message("Soal di kategori itu kosong 😅", ephemeral=True)

    sess = QuizSession(
        channel_id=itx.channel.id,
        p1=me, p2=you,
        questions=qs,
        idx=0, matches=0, total=0,
        category=category
    )
    SESSIONS[itx.channel.id] = sess

    embed = Embed(
        title="Couple Quiz Started 💞",
        description=f"{itx.user.mention} × {partner.mention}\nRounds: **{len(qs)}** • Kategori: **{category}**\n\n**Rules:**\n• Jawab via tombol.\n• Poin nambah kalau jawaban kalian **match**.\n• Untuk skala (1–5), selisih ≤ 1 dianggap match.",
        color=0xFEE75C
    )
    await itx.response.send_message(embed=embed)
    await ask_next(itx, sess)

@TREE.command(name="quiz_stop", description="Hentikan sesi quiz yang sedang berjalan")
async def quiz_stop(itx: Interaction):
    sess = SESSIONS.get(itx.channel.id)
    if not sess or not sess.active:
        return await itx.response.send_message("Tidak ada sesi aktif di channel ini.", ephemeral=True)
    if itx.user.id not in (sess.p1, sess.p2):
        return await itx.response.send_message("Hanya pemain sesi ini yang bisa stop.", ephemeral=True)
    sess.active = False
    await itx.response.send_message("Sesi dihentikan. Terima kasih sudah main! 💗")
    await end_session(itx, sess)

@TREE.command(name="quiz_score", description="Lihat lifetime compatibility kamu berdua")
@app_commands.describe(partner="(opsional) pasanganmu; kalau kosong pakai pasangan terakhir di channel ini")
async def quiz_score(itx: Interaction, partner: discord.User | None = None):
    sess = SESSIONS.get(itx.channel.id)
    if partner is None:
        if not sess:
            return await itx.response.send_message("Sebutkan pasangan: `/quiz_score @nama`", ephemeral=True)
        u1, u2 = sess.p1, sess.p2
    else:
        u1, u2 = itx.user.id, partner.id
        if u1 == u2:
            return await itx.response.send_message("Pilih pasangan yang bener dong 😅", ephemeral=True)

    total, matched = db_get_score(u1, u2)
    rate = 0 if total==0 else round(matched/total*100)
    embed = Embed(
        title="Lifetime Compatibility",
        description=f"<@{u1}> × <@{u2}>\nMatch **{matched}/{total}** • **{rate}%**",
        color=0x1ABC9C
    )
    await itx.response.send_message(embed=embed)

@TREE.command(name="quiz_bank", description="Lihat jumlah soal per kategori")
async def quiz_bank(itx: Interaction):
    rows = [f"• **{k}**: {len(v)} soal" for k,v in Q_BANK.items()]
    rows.append(f"• **mix**: {sum(len(v) for v in Q_BANK.values())} soal total")
    await itx.response.send_message("\n".join(rows))

# ==========: BOT LIFECYCLE ==========
@CLIENT.event
async def on_ready():
    db_init()
    try:
        await TREE.sync()
    except Exception as e:
        print("Sync error:", e)
    print(f"Logged in as {CLIENT.user}")

if __name__ == "__main__":
    if not TOKEN:
        raise SystemExit("DISCORD_TOKEN kosong di .env")
    CLIENT.run(TOKEN)
