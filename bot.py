import os
import io
import time
import requests
from PyPDF2 import PdfMerger
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# --- CONFIG ---
TOKEN = "8766953945:AAG9_B9eHOa3Jt4ekdu6Jcvn13vNrP472Qo"
PIN_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjY5NWI0MmJjNzQwZGFkMjQzN2I1NzhlYiIsInJvbGUiOiJzdHVkZW50IiwiaXAiOiIxNTIuNTkuMTguMTM4IiwiZGV2aWNlIjoiTW96aWxsYS81LjAgKFdpbmRvd3MgTlQgMTAuMDsgV2luNjQ7IHg2NCkgQXBwbGVXZWJLaXQvNTM3LjM2IChLSFRNTCwgbGlrZSBHZWNrbykgQ2hyb21lLzE0NS4wLjAuMCBTYWZhcmkvNTM3LjM2IiwiaWF0IjoxNzcyMjY2NTU3LCJleHAiOjE4MzUzMzg1NTd9.vBUp5SWekeBxGy-oIqslR2IRzTpfXxcUqcojVyr5boM"

API_EBOOKS = "https://auth.ssccglpinnacle.com/api/ebooksforactive?active=true"
API_CHAPTERS = "https://auth.ssccglpinnacle.com/api/chapters-ebook/{book_id}"
API_CONTENT = "https://auth.ssccglpinnacle.com/api/content-ebook/{chapter_id}"

HEADERS = {
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "referer": "https://ebooks.ssccglpinnacle.com/",
    "origin": "https://ebooks.ssccglpinnacle.com"
}
AUTH_HEADERS = {**HEADERS, "authorization": f"Bearer {PIN_TOKEN}"}

# 50MB limit (Telegram standard), safety ke liye hum 45MB use karenge
MAX_PART_SIZE = 45 * 1024 * 1024 

async def send_pdf_part(update, context, merger, title, part_no):
    """Memory se PDF part generate karke Telegram par bhejta hai"""
    pdf_out = io.BytesIO()
    merger.write(pdf_out)
    pdf_out.seek(0)
    
    size_mb = len(pdf_out.getvalue()) / (1024 * 1024)
    print(f"📤 Sending Part {part_no}: {size_mb:.2f} MB")
    
    clean_title = "".join([c for c in title if c.isalnum() or c in (' ', '.', '_')]).strip()
    
    await context.bot.send_document(
        chat_id=update.effective_chat.id,
        document=pdf_out,
        filename=f"{clean_title[:30]}_Part_{part_no}.pdf",
        caption=f"✅ {title}\n📂 **Part {part_no}**\n⚖️ Size: {size_mb:.2f} MB"
    )

async def process_and_send_book(update, context, book_id, title, img_url):
    try:
        # 1. Get Chapter list
        r = requests.get(API_CHAPTERS.format(book_id=book_id), headers=AUTH_HEADERS, timeout=20)
        if r.status_code == 401: return "401"
        
        chapters = r.json()
        merger = PdfMerger()
        current_part_size = 0
        part_count = 1
        
        print(f"📥 Processing: {title} ({len(chapters)} Chapters)")

        # Pehle photo bhej dete hain
        if img_url:
            try:
                await context.bot.send_photo(chat_id=update.effective_chat.id, photo=img_url, caption=f"📘 **{title}**\n🔄 Downloading all parts...")
            except: pass

        for chap in chapters:
            c_id = chap['_id']
            pdf_res = requests.get(API_CONTENT.format(chapter_id=c_id), headers=AUTH_HEADERS, timeout=30)
            
            if pdf_res.status_code == 200:
                content = pdf_res.content
                # Agar naya chapter add karne se size limit cross ho rahi hai
                if (current_part_size + len(content)) > MAX_PART_SIZE:
                    await send_pdf_part(update, context, merger, title, part_count)
                    # Reset for next part
                    merger = PdfMerger()
                    current_part_size = 0
                    part_count += 1
                
                merger.append(io.BytesIO(content))
                current_part_size += len(content)

        # Last part bhejein (agar kuch bacha hai)
        if current_part_size > 0:
            await send_pdf_part(update, context, merger, title, part_count)

        return "OK"
    except Exception as e:
        print(f"❌ Error in {title}: {e}")
        return None

async def start_fetching(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚀 PDF Extraction Shuru! Badi books automatic Parts mein aayengi.")
    
    try:
        resp = requests.get(API_EBOOKS, headers=HEADERS, timeout=20)
        books = resp.json()

        for b in books:
            res = await process_and_send_book(update, context, b['_id'], b['title'], b.get('image'))
            
            if res == "401":
                await update.message.reply_text("❌ Token Expire ho gaya! Naya dalo.")
                break
                
            print(f"Waiting 5s for next book...")
            time.sleep(5)
            
    except Exception as e:
        print(f"Main Loop Error: {e}")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start_fetching))
    print("✅ Bot is running... Telegram par /start dabao.")
    app.run_polling()

if __name__ == "__main__":
    main()
