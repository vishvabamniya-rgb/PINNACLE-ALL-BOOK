import os
import io
import time
import requests
from PyPDF2 import PdfMerger
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# ==================== CONFIGURATION ====================
BOT_TOKEN = "8766953945:AAG9_B9eHOa3Jt4ekdu6Jcvn13vNrP472Qo"
API_ID = "YOUR_API_ID"       # <--- Yahan apna API ID dalo
API_HASH = "YOUR_API_HASH"   # <--- Yahan apna API HASH dalo

# Pinnacle Config
PIN_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjY5NWI0MmJjNzQwZGFkMjQzN2I1NzhlYiIsInJvbGUiOiJzdHVkZW50IiwiaXAiOiIxNTIuNTkuMTguMTM4IiwiZGV2aWNlIjoiTW96aWxsYS81LjAgKFdpbmRvd3MgTlQgMTAuMDsgV2luNjQ7IHg2NCkgQXBwbGVXZWJLaXQvNTM3LjM2IChLSFRNTCwgbGlrZSBHZWNrbykgQ2hyb21lLzE0NS4wLjAuMCBTYWZhcmkvNTM3LjM2IiwiaWF0IjoxNzcyMjY2NTU3LCJleHAiOjE4MzUzMzg1NTd9.vBUp5SWekeBxGy-oIqslR2IRzTpfXxcUqcojVyr5boM"

API_EBOOKS = "https://auth.ssccglpinnacle.com/api/ebooksforactive?active=true"
API_CHAPTERS = "https://auth.ssccglpinnacle.com/api/chapters-ebook/{book_id}"
API_CONTENT = "https://auth.ssccglpinnacle.com/api/content-ebook/{chapter_id}"

HEADERS = {"user-agent": "Mozilla/5.0", "referer": "https://ebooks.ssccglpinnacle.com/"}
AUTH_HEADERS = {**HEADERS, "authorization": f"Bearer {PIN_TOKEN}"}

# ==================== PDF ENGINE ====================

async def download_and_merge(book_id, title):
    try:
        r = requests.get(API_CHAPTERS.format(book_id=book_id), headers=AUTH_HEADERS, timeout=25)
        if r.status_code == 401: return "401"
        
        chapters = r.json()
        merger = PdfMerger()
        
        print(f"📦 Processing {title} ({len(chapters)} Chapters)...")
        
        count = 0
        for chap in chapters:
            c_id = chap['_id']
            res = requests.get(API_CONTENT.format(chapter_id=c_id), headers=AUTH_HEADERS, timeout=40)
            if res.status_code == 200 and len(res.content) > 500:
                merger.append(io.BytesIO(res.content))
                count += 1
        
        if count == 0: return None
        
        pdf_file = io.BytesIO()
        merger.write(pdf_file)
        pdf_file.seek(0)
        return pdf_file
    except Exception as e:
        print(f"❌ Error merging {title}: {e}")
        return None

# ==================== HANDLERS ====================

async def start_mass_download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_chat.id
    await update.message.reply_text("🔥 Local Server Mode Active! Unlimited Size Upload Start...")

    try:
        # Fetching list of all 227+ books
        resp = requests.get(API_EBOOKS, headers=HEADERS, timeout=20)
        all_books = resp.json()
        
        await update.message.reply_text(f"📚 Total {len(all_books)} books mili hain. Shuru kar raha hoon...")

        for b in all_books:
            b_id = b['_id']
            title = b.get('title', 'Pinnacle_Book')
            
            # 1. Merge the whole book (No splitting!)
            final_pdf = await download_and_merge(b_id, title)
            
            if final_pdf == "401":
                await update.message.reply_text("🚨 TOKEN EXPIRED! Please update PIN_TOKEN.")
                break
                
            if final_pdf:
                size_mb = len(final_pdf.getvalue()) / (1024*1024)
                print(f"📤 Sending {title} | Size: {size_mb:.2f} MB")
                
                # 2. Sending full document via Local Server (Supports up to 2GB)
                await context.bot.send_document(
                    chat_id=user_id,
                    document=final_pdf,
                    filename=f"{title[:50]}.pdf",
                    caption=f"✅ **{title}**\n⚖️ Size: {size_mb:.2f} MB\n💎 High Quality Original"
                )
            else:
                await update.message.reply_text(f"❌ Failed to merge: {title}")

            # Safety gap to prevent Telegram flood
            time.sleep(3)

    except Exception as e:
        print(f"🛑 Critical Error: {e}")

# ==================== MAIN START ====================

def main():
    # ⚠️ LOCAL SERVER KE LIYE BASE_URL SET KARNA JAROORI HAI
    # Default local server runs on port 8081
    local_url = "http://localhost:8081/bot" 
    
    app = Application.builder().token(BOT_TOKEN).base_url(local_url).build()
    
    app.add_handler(CommandHandler("start", start_mass_download))
    
    print("🚀 Bot is running via LOCAL SERVER...")
    print("Make sure 'telegram-bot-api' server is running on port 8081!")
    app.run_polling()

if __name__ == "__main__":
    main()
