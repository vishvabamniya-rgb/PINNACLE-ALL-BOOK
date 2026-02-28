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

HEADERS = {"user-agent": "Mozilla/5.0", "referer": "https://ebooks.ssccglpinnacle.com/"}
AUTH_HEADERS = {**HEADERS, "authorization": f"Bearer {PIN_TOKEN}"}

async def download_and_merge_single(book_id, title):
    try:
        r = requests.get(API_CHAPTERS.format(book_id=book_id), headers=AUTH_HEADERS, timeout=25)
        if r.status_code == 401: return "401"
        
        chapters = r.json()
        merger = PdfMerger()
        
        print(f"📦 Merging {title} as a SINGLE file...")
        
        count = 0
        for chap in chapters:
            res = requests.get(API_CONTENT.format(chapter_id=chap['_id']), headers=AUTH_HEADERS, timeout=30)
            if res.status_code == 200:
                merger.append(io.BytesIO(res.content))
                count += 1
        
        if count == 0: return None
        
        pdf_out = io.BytesIO()
        merger.write(pdf_out)
        pdf_out.seek(0)
        return pdf_out
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

async def start_fetching(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚀 SINGLE FILE MODE: Saari books ek-ek karke aana shuru ho rahi hain...")
    try:
        resp = requests.get(API_EBOOKS, headers=HEADERS).json()
        for b in resp:
            title = b.get('title', 'Book')
            pdf = await download_and_merge_single(b['_id'], title)
            
            if pdf == "401":
                await update.message.reply_text("❌ Token Expired!")
                break
            
            if pdf:
                size_mb = len(pdf.getvalue()) / (1024*1024)
                if size_mb > 49.5:
                    await update.message.reply_text(f"⚠️ {title} is {size_mb:.2f}MB (Too big for Telegram). Skipping to next...")
                    continue
                
                await context.bot.send_document(
                    chat_id=update.effective_chat.id,
                    document=pdf,
                    filename=f"{title[:50]}.pdf",
                    caption=f"✅ {title}\n⚖️ Size: {size_mb:.2f} MB"
                )
            time.sleep(5)
    except Exception as e:
        print(f"Main Loop Error: {e}")

def main():
    # ⚠️ LOCAL URL HATA DIYA HAI - Ab ConnectError nahi aayega
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start_fetching))
    print("✅ Bot is running on DIRECT API MODE...")
    app.run_polling()

if __name__ == "__main__":
    main()
