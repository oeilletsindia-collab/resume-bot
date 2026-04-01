from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from openai import OpenAI
from docx import Document
from fpdf import FPDF
import asyncio
import os



# 🔑 ADD YOUR KEYS


ADMIN_ID = int(os.getenv("ADMIN_ID"))
BOT_TOKEN = os.getenv("BOT_TOKEN")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

users = {}

# 🤖 Generate AI Resume
def generate_resume(data):
    prompt = f"""
Create a professional ATS-friendly resume.

STRICT RULES:
- Do NOT add any introduction like "Sure" or "Here is"
- Do NOT add explanations
- Output ONLY the resume content
- Start directly with the person's NAME
- Use clean formatting

Name: {data['name']}
Contact: {data['contact']}
Skills: {data['skills']}
Education: {data['education']}
Experience/Projects: {data['experience']}

Make it clean, well structured with headings:
- Summary
- Skills
- Experience
- Education
- Contact Information
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    return response.choices[0].message.content


def clean_text(text):
    replacements = {
        "’": "'",
        "‘": "'",
        "“": '"',
        "”": '"',
        "–": "-",
        "—": "-",
    }

    for k, v in replacements.items():
        text = text.replace(k, v)

    return text.encode("latin-1", "ignore").decode("latin-1")


# 📄 Create DOC file
def create_doc(resume_text, filename="resume.docx"):
    doc = Document()
    for line in resume_text.split("\n"):
        doc.add_paragraph(line)
    doc.save(filename)


# 📑 Create PDF file (FIXED)
def create_pdf(resume_text, filename="resume.pdf"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=10)

    # ✅ CLEAN TEXT HERE
    resume_text = clean_text(resume_text)

    for line in resume_text.split("\n"):
        if line.strip() == "":
            pdf.ln(5)
        else:
            pdf.multi_cell(0, 6, line)

    pdf.output(filename)


# ▶️ Start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    # ✅ Only create user if not exists
    if uid not in users:
        users[uid] = {
            "step": "name",
            "count": 0
        }
    else:
        # Only reset step, NOT count
        users[uid]["step"] = "name"

    await update.message.reply_text(
        "👋 Welcome!\n\nCreate your professional resume in 30 seconds.\n\nWhat is your full name?"
    )


# 💬 Handle Messages
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    
    
    # 📸 If user sends screenshot (ADD HERE)
    if update.message.photo:
        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=update.message.photo[-1].file_id,
            caption=f"📸 Payment Screenshot\n\nUser ID: {uid}"
        )

        await update.message.reply_text(
            "✅ Screenshot received.\n\nAdmin will verify and unlock access."
        )
        return
    
    
    #text = update.message.text
    
    text = update.message.text if update.message.text else ""

    if uid not in users:
        #users[uid] = {"step": "name", "count": 0}
        users[uid] = {
    "step": "name",
    "count": 0,
    "paid": False
}

    step = users[uid]["step"]

    # 1️⃣ Name
    if step == "name":
        users[uid]["name"] = text
        users[uid]["step"] = "contact"
        await update.message.reply_text(
            "📞 Enter your phone + email (or type 'skip'):"
        )

    # 2️⃣ Contact (skip allowed)
    elif step == "contact":
        if text.lower() == "skip":
            users[uid]["contact"] = "Not provided"
        else:
            users[uid]["contact"] = text

        users[uid]["step"] = "skills"
        await update.message.reply_text("💼 Enter your skills (comma separated):")

    # 3️⃣ Skills
    elif step == "skills":
        users[uid]["skills"] = text
        users[uid]["step"] = "education"
        await update.message.reply_text("🎓 Enter your education:")

    # 4️⃣ Education
    elif step == "education":
        users[uid]["education"] = text
        users[uid]["step"] = "experience"
        await update.message.reply_text(
            "💻 Enter your experience/projects:\n\nExample:\n- Built website using HTML\n- Intern at XYZ company"
        )

    # 5️⃣ Experience → Generate Resume
    elif step == "experience":
        users[uid]["experience"] = text

        # 💰 Free limit
        if users[uid]["count"] >= 2:
            await update.message.reply_text(
                f"❌ Free limit over.\n\nPay ₹99 here:\nhttps://rzp.io/rzp/ZwNJ3Tsh\n\n"
                f"⚠️ If amount is not coming in PhonePe then open link in Chrome or other Browser:\n\n"
                f"📸 Send payment screenshot.\n\n"
               f"🆔 Your User ID: {uid}\n\n"
               f"Then wait for approval."   
            )
            return
        # Paid limit
        if users[uid].get("paid", False) and users[uid]["count"] >= 100:
           await update.message.reply_text(
        "⚠️ You have reached your 100 resume limit.\n\nPay ₹99 here:\nhttps://rzp.io/rzp/ZwNJ3Tsh\n\n"
                f"📸 Send payment screenshot.\n\n"
               f"🆔 Your User ID: {uid}\n\n"
               f"Then wait for approval."
    )
           return
       
        users[uid]["count"] += 1

        await update.message.reply_text("⏳ Creating your professional resume...")

        try:
            resume = generate_resume(users[uid])

            # Send resume text
            await update.message.reply_text(resume)

            # UX message
            await update.message.reply_text("📄 Your resume is ready!\nDownloading files...")

            # DOC
            create_doc(resume)
            await update.message.reply_document(document=open("resume.docx", "rb"))

            # Delay to prevent timeout
            await asyncio.sleep(1)

            # PDF
            create_pdf(resume)
            await update.message.reply_document(document=open("resume.pdf", "rb"))

        except Exception as e:
            await update.message.reply_text("⚠️ Error generating resume. Try again later.")
            print("Error:", e)

        users[uid]["step"] = "done"

    else:
        await update.message.reply_text("Type /start to create a new resume.")



async def unlock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    try:
        user_id = int(context.args[0])

        if user_id not in users:
           # users[user_id] = {"step": "name", "count": 0}
           users[user_id] = {
                "step": "name",
                "count": 0,
                "paid": False
            }

        
        users[user_id]["paid"] = True
        users[user_id]["count"] = 0  # reset for fresh 100 resumes

        await update.message.reply_text(f"✅ User {user_id} unlocked")

    except:
        await update.message.reply_text("Usage: /unlock user_id")




# 💰 Payment Unlock
async def paid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    if uid not in users:
        users[uid] = {
            "step": "name",
            "count": 0,
            "paid": False
        }
    else:
        users[uid]["step"] = "name"

    await update.message.reply_text(
        "📸 After payment, Please send screenshot and your User ID.\n\nAdmin will verify and unlock access."
    )


# 🚀 Run Bot (with timeout fix)
app = ApplicationBuilder().token(BOT_TOKEN).connect_timeout(30).read_timeout(30).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("paid", paid))
app.add_handler(CommandHandler("unlock", unlock))
#app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
app.add_handler(MessageHandler(filters.ALL, handle))

print("🤖 Bot is running...")
app.run_polling()
