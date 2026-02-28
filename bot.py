import os
import io
import time
import requests
from PyPDF2 import PdfMerger
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.constants import ParseMode

# --- CONFIG ---
TOKEN = "8766953945:AAG9_B9eHOa3Jt4ekdu6Jcvn13vNrP472Qo"
PIN_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjY5NWI0MmJjNzQwZGFkMjQzN2I1NzhlYiIsInJvbGUiOiJzdHVkZW50IiwiaXAiOiIxNTIuNTkuMTguMTM4IiwiZGV2aWNlIjoiTW96aWxsYS81LjAgKFdpbmRvd3MgTlQgMTAuMDsgV2luNjQ7IHg2NCkgQXBwbGVXZWJLaXQvNTM3LjM2IChLSFRNTCwgbGlrZSBHZWNrbykgQ2hyb21lLzE0NS4wLjAuMCBTYWZhcmkvNTM3LjM2IiwiaWF0IjoxNzcyMjY2NTU3LCJleHAiOjE4MzUzMzg1NTd9.vBUp5SWekeBxGy-oIqslR2IRzTpfXxcUqcojVyr5boM"

AUTH_HEADERS = {
    "user-agent": "Mozilla/5.0",
    "authorization": f"Bearer {PIN_TOKEN}",
    "referer": "https://ebooks.ssccglpinnacle.com/"
}
MAX_SIZE = 48 * 1024 * 1024  # 48MB per part (Safety side)

async def send_pdf_part(update, context, merger, title, part_no, total_parts=None):
    """PDF Part ko build karke bhejta hai"""
    pdf_out = io.BytesIO()
    merger.write(pdf_out)
    pdf_out.seek(0)
    
    size_mb = len(pdf_out.getvalue()) / (1024 * 1024)
    
    caption = (
        f"📚 **{title}**\n\n"
        f"📂 **File:** Part {part_no}\n"
        f"⚖️ **Size:** {size_mb:.2f} MB\n"
        f"✅ **Quality:** Original (High)"
    )
    
    await context.bot.send_document(
        chat_id=update.effective_chat.id,
        document=pdf_out,
        filename=f"{title[:40]}_Part_{part_no}.pdf",
        caption=caption,
        parse_mode=ParseMode.MARKDOWN
    )

async def process_book(update, context, b):
    book_id = b['_id']
    title = b.get('title', 'Pinnacle Book')
    img_url = b.get('image')

    # 1. Pehle Photo bhejenge
    if img_url:
        try:
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=img_url,
                caption=f"📥 **Downloading:** {title}\n\n_Please wait, merging chapters..._",
                parse_mode=ParseMode.MARKDOWN
            )
        except:
            pass

    # 2. Chapters download aur merge
    try:
        r = requests.get(f"https://auth.ssccglpinnacle.com/api/chapters-ebook/{book_id}", headers=AUTH_HEADERS)
        chapters = r.json()
        
        merger = PdfMerger()
        current_size = 0
        part_count = 1

        for chap in chapters:
            res = requests.get(f"https://auth.ssccglpinnacle.com/api/content-ebook/{chap['_id']}", headers=AUTH_HEADERS)
            if res.status_code == 200:
                chap_data = res.content
                # Agar agla chapter add karne se size limit cross ho rahi hai
                if current_size + len(chap_data) > MAX_SIZE:
                    await send_pdf_part(update, context, merger, title, part_count)
                    merger = PdfMerger() # Naya merger next part ke liye
                    current_size = 0
                    part_count += 1
                
                merger.append(io.BytesIO(chap_data))
                current_size += len(chap_data)

        # Last bacha hua part
        if current_size > 0:
            await send_pdf_part(update, context, merger, title, part_count)

    except Exception as e:
        print(f"Error processing {title}: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚀 **Pinnacle PDF Bot Started!**\nExtracting 227 books with original quality...", parse_mode=ParseMode.MARKDOWN)
    
    try:
        resp = requests.get("https://auth.ssccglpinnacle.com/api/ebooksforactive?active=true", headers={"user-agent": "Mozilla/5.0"}).json()
        for b in resp:
            await process_book(update, context, b)
            time.sleep(3) # Flood prevention
    except Exception as e:
        print(f"Main Error: {e}")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    print("✅ Bot is Live on Render!")
    app.run_polling()

if __name__ == "__main__":
    main()
