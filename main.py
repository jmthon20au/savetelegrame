import re
import os
import asyncio
import telethon
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
from telethon.errors import (
    UserNotParticipantError,
    ChannelPrivateError,
    InviteHashExpiredError,
    InviteHashInvalidError,
    UserAlreadyParticipantError
)

# ----------------- الإعدادات -----------------
API_ID = 21100923
API_HASH = "32ad1f2eb62a60301e7bbcdf91c43641"
BOT_TOKEN = "8968514485:AAEOfJJe3GuJoGr5zLAL0SRjbIbkYBIkHhY"

# ضِع كود الجلسة الخاص بالحساب المساعد هنا
STRING_SESSION = "1ApWapzMBu3q3384_HayLnHqPdhiDUdjLmuWFy0Ub37dINlNklgS_XQ0Gicnw4B0sqb7rFwR0mZronXR-uZUEzEOt4mqyyxI9o6Z4wl6IoHcKmIl1xWu1pX-9zEULR0SRY3TIDfrR3OnYxHSwKVGftK0VVktJFI3jnIs1i72aeUvrZtSMfegB32PQM2NT60T8Zi8bZaxZUVviUZtZP0rmm7D_7xvCifKda5pTm7wmQeBbbcorkaP7eikw8ac5goWMF8sF_hmRCZLDZaUAySav-KJfT1u5bfv_ReA7rYMi_G6qqflnteIzH7ZO58kyFkRIrsy_CjOcBYCx__uNKdTnD8THyt6B5SI=" 

MUST_JOIN_CHANNEL = "xx28z"  # بدون @

# أزرار الحقوق المرفقة مع كل استجابة
RIGHTS_BUTTONS = [
    [Button.url("قناتنا 📢", "https://t.me/xx28z")],
    [Button.url("🤍 تلجرام", "https://t.me/altaee_z"), Button.url("🌐 موقعي", "https://www.ali-Altaee.free.nf")]
]

# ----------------- تهيئة العملاء -----------------
# حساب البوت
bot = TelegramClient('bot_session', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# حساب المساعد (Userbot)
user_client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)

# ذاكرة مؤقتة لحفظ الروابط المقيدة الخاصة بانتظار رابط الدعوة
user_pending_links = {}

# ----------------- الدوال المساعدة -----------------
async def check_subscription(user_id):
    """فحص الاشتراك الإجباري للمستخدم"""
    try:
        await bot.get_permissions(MUST_JOIN_CHANNEL, user_id)
        return True
    except UserNotParticipantError:
        return False
    except Exception as e:
        print(f"Error checking sub: {e}")
        return True

def get_sub_buttons():
    """زر الاشتراك الإجباري"""
    return [
        [Button.url("إشترك بالقناة أولاً 📢", f"https://t.me/{MUST_JOIN_CHANNEL}")],
        [Button.inline("تم الاشتراك ✅", data="check_sub")]
    ]

# ----------------- أحداث البوت -----------------

@bot.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    user_id = event.sender_id
    if not await check_subscription(user_id):
        await event.respond(
            f"⚠️ **عذراً عزيزي، عليك الاشتراك بالقناة لاستخدام البوت:**\n@{MUST_JOIN_CHANNEL}",
            buttons=get_sub_buttons()
        )
        return

    welcome_msg = (
        "أهلاً بك في بوت تحميل المحتوى المقيد 🚀\n\n"
        "أرسل لي رابط المنشور (من قناة عامة أو خاصة) وسيتم جلبه لك فوراً.\n\n"
        "⚪️ **حقوق التطوير:**\n"
        "🤍 تلجرام : @altaee_z\n"
        "🌐 موقعي : www.ali-Altaee.free.nf"
    )
    await event.respond(welcome_msg, buttons=RIGHTS_BUTTONS)

@bot.on(events.CallbackQuery(data="check_sub"))
async def callback_sub_check(event):
    user_id = event.sender_id
    if await check_subscription(user_id):
        await event.delete()
        await bot.send_message(user_id, "✅ تم التحقق من اشتراكك بنجاح! أرسل رابط المنشور الآن.", buttons=RIGHTS_BUTTONS)
    else:
        await event.answer("❌ لم تشترك في القناة بعد!", alert=True)

@bot.on(events.NewMessage)
async def message_handler(event):
    if event.text.startswith('/start'):
        return

    user_id = event.sender_id
    text = event.text.strip()

    # التحقق من الاشتراك الإجباري
    if not await check_subscription(user_id):
        await event.respond(
            f"⚠️ **عذراً، يجب عليك الاشتراك بالقناة أولاً:**\n@{MUST_JOIN_CHANNEL}",
            buttons=get_sub_buttons()
        )
        return

    # 1. إذا كان المستخدم في مرحلة انتظار رابط الدعوة (Invite Link)
    if user_id in user_pending_links:
        if "t.me/+" in text or "t.me/joinchat/" in text:
            msg_status = await event.respond("⏳ جاري الانضمام إلى القناة وجلب المحتوى...")
            target_link = user_pending_links.pop(user_id)
            
            # استخراج الـ hash الخاص بالدعوة
            invite_hash = text.split('+')[-1].split('/')[-1]
            
            try:
                await user_client(telethon.functions.messages.ImportChatInviteRequest(hash=invite_hash))
            except UserAlreadyParticipantError:
                pass
            except (InviteHashExpiredError, InviteHashInvalidError):
                await msg_status.edit("❌ رابط الدعوة غير صالح أو منتهي الصلاحية.")
                return
            except Exception as e:
                await msg_status.edit(f"❌ حدث خطأ أثناء الانضمام: {e}")
                return

            # جلب المنشور بعد الانضمام
            await process_fetch_link(event, target_link, msg_status)
            return
        else:
            await event.respond("❌ يرجى إرسال رابط دعوة صالح (يحتوي على t.me/+ أو joinchat).")
            return

    # 2. معالجة روابط المنشورات
    if "t.me/" in text:
        msg_status = await event.respond("⏳ جاري جلب المحتوى...")
        
        if "/c/" in text:
            success = await process_fetch_link(event, text, msg_status, silent_fail=True)
            if not success:
                user_pending_links[user_id] = text
                await msg_status.edit(
                    "🔒 **هذه القناة/المجموعة خاصة والحساب المساعد ليس عضواً فيها.**\n\n"
                    "📥 **يرجى إرسال رابط الدعوة (Invite Link) للقناة الآن ليتمكن الحساب من الانضمام وجلب المنشور:**"
                )
        else:
            await process_fetch_link(event, text, msg_status)

async def process_fetch_link(event, link, status_msg, silent_fail=False):
    """دالة جلب المنشور وتمريره للمستخدم عبر الحساب المساعد"""
    try:
        # تنظيف الرابط من أي معلمات إضافية مثل ?single
        clean_link = link.split('?')[0]
        parts = clean_link.split('/')
        msg_id = int(parts[-1])
        
        if "/c/" in clean_link:
            chat_id = int("-100" + parts[-2])
        else:
            chat_id = parts[-2]

        message = await user_client.get_messages(chat_id, ids=msg_id)
        
        if not message:
            if not silent_fail:
                await status_msg.edit("❌ لم يتم العثور على الرسالة، قد تكون محذوفة.")
            return False

        await status_msg.edit("⏳ جاري رفع وإرسال المحتوى...")

        if message.media:
            file = await user_client.download_media(message)
            await bot.send_file(
                event.chat_id, 
                file, 
                caption=message.text or "", 
                buttons=RIGHTS_BUTTONS
            )
            if file and os.path.exists(file):
                os.remove(file)
        elif message.text:
            await bot.send_message(
                event.chat_id, 
                message.text, 
                buttons=RIGHTS_BUTTONS
            )

        await status_msg.delete()
        return True

    except ChannelPrivateError:
        if not silent_fail:
            await status_msg.edit("❌ القناة خاصة. يرجى إرسال رابط الدعوة للانضمام أولاً.")
        return False
    except Exception as e:
        if not silent_fail:
            await status_msg.edit(f"❌ حدث خطأ أثناء جلب المنشور: {str(e)}")
        return False

# ----------------- التشغيل -----------------
async def main():
    await user_client.start()
    print("Userbot Connected!")
    print("Bot Connected!")
    await bot.run_until_disconnected()

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
