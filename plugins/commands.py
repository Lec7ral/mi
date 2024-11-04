import logging
import os
import sys
import asyncio 
from database import db, mongodb_version
from config import Config, temp
from platform import python_version
from translation import Translation
from pyrogram import Client, filters, enums, __version__ as pyrogram_version
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaDocument, BotCommand
from .settings import settings_query
from .userSettings import user_settings_query   
logging.basicConfig(level=logging.INFO)
main_buttons = [[
        InlineKeyboardButton('❗ ʜᴇʟᴘ', callback_data='help')],[
        InlineKeyboardButton('🎓 ᴀʙᴏᴜᴛ ', callback_data='about')
        ]]
async def user_main_buttons(user_id):
  status = await db.get_user_status(user_id)
  logging.info(f"tiene el status en {status}")
      # Alternar entre 'start' y 'stop' según el estado
  if status:
      start_stop_button = InlineKeyboardButton('🛑 Stop', callback_data='stopspam')
  else:
      start_stop_button = InlineKeyboardButton('▶️ Iniciar', callback_data='stspam')
  
  buttons = [[start_stop_button], [
      InlineKeyboardButton('⚙️ Ajustes', callback_data='userSettings#main')
      ], [
      InlineKeyboardButton('💲 Planes', callback_data='not_implemented')
      ]]
  
  return InlineKeyboardMarkup(buttons)


#===================Admin Start Function===================#
@Client.on_message(filters.private & filters.command(['start']))
async def fnciona(client, message):
    logging.error(f"Funciona y no entra xq no e da la gana {message}")
    await message.reply("Has usado el comando /stspam")
        
@Client.on_message(filters.private & filters.command(['start']) & filters.user(Config.OWNER_ID))
async def start_admin(client, message):
    user = message.from_user
    if not await db.is_user_exist(user.id):
        await db.add_user(user.id, user.first_name)
    reply_markup = InlineKeyboardMarkup(main_buttons)
    jishubotz = await message.reply_sticker("CAACAgEAAxkBAAEMLQ9mSt_K7_M9zPshnOI6pLz6Ysti3wACXQQAAsjRGETv0HseLYp8LR4E")
    await asyncio.sleep(2)
    await jishubotz.delete()
    text=Translation.START_TXT_ADMIN.format(user.mention)
    await message.reply_text(
        text=text,
        reply_markup=reply_markup,
        quote=True
    )

#==================User Start Function===============#
@Client.on_message(filters.private & filters.command(['start']) & ~filters.user(Config.OWNER_ID)) 
async def start_user(client, message):
    try:
            user = message.from_user
            if not await db.is_user_exist(user.id):
                await db.add_user(user.id, user.first_name)
            reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton('🔑 Iniciar sesion', callback_data='userSettings#adduserbot')]])
            reply_markup_settings = await user_main_buttons(user.id)
            jishubotz = await message.reply_sticker("CAACAgEAAxkBAAEMLQ9mSt_K7_M9zPshnOI6pLz6Ysti3wACXQQAAsjRGETv0HseLYp8LR4E")
            await asyncio.sleep(2)
            await jishubotz.delete()    
            try:
                    logging.info("Verificando si el bot existe...")
                    if not await db.is_bot_exist(user.id):
                        text = Translation.START_TXT.format(user.mention)
                        await message.reply_text(
                            text=text,
                            reply_markup=reply_markup,
                            quote=True
                        )
                    else:
                        text = Translation.START_TXT_USER.format(user.mention)
                        await message.reply_text(
                            text=text,
                            reply_markup=reply_markup_settings,
                            quote=True
                        )
                        logging.info(reply_markup_settings)    
            except Exception as e:
                logging.error(f"Error al verificar la existencia del bot: {e}")
                await message.reply_text("Ocurrió un error al verificar el bot. Por favor, inténtalo de nuevo más tarde.")
    except Exception as e:
            logging.error(f"Error al verificar la existencia del bot: {e}")
            await message.reply_text("Ocurrió un error al verificar el bot. Por favor, inténtalo de nuevo más tarde.")


#==================Restart Function==================#

@Client.on_message(filters.private & filters.command(['restart', "r"]) & filters.user(Config.OWNER_ID))
async def restart(client, message):
    msg = await message.reply_text(
        text="<i>Trying To Restarting.....</i>",
        quote=True
    )
    await asyncio.sleep(5)
    await msg.edit("<i>Server Restarted Successfully ✅</i>")
    os.execl(sys.executable, sys.executable, *sys.argv)
    


#==================Callback Functions==================#

@Client.on_callback_query(filters.regex(r'^help'))
async def helpcb(bot, query):
    await query.message.edit_text(
        text=Translation.HELP_TXT,
        reply_markup=InlineKeyboardMarkup(
            [[
            InlineKeyboardButton('ʜᴏᴡ ᴛᴏ ᴜsᴇ ᴍᴇ ❓', callback_data='how_to_use')
            ],[
            InlineKeyboardButton('⚙️ sᴇᴛᴛɪɴɢs ', callback_data='settings#main'),
            InlineKeyboardButton('📜 sᴛᴀᴛᴜs ', callback_data='status')
            ],[
            InlineKeyboardButton('↩ ʙᴀᴄᴋ', callback_data='back')
            ]]
        ))      


@Client.on_callback_query(filters.regex(r'^how_to_use'))
async def how_to_use(bot, query):
    await query.message.edit_text(
        text=Translation.HOW_USE_TXT,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 Back', callback_data='help')]]),
        disable_web_page_preview=True
    )



@Client.on_callback_query(filters.regex(r'^back') & ~filters.user(Config.OWNER_ID))
async def back_user(bot, query):
    logging.info(f"User  callback: {query.from_user.id}")
    reply_markup_user = await user_main_buttons(query.from_user.id)    
    await query.message.edit_text(
        reply_markup=reply_markup_user,
        text=Translation.START_TXT_USER.format(
        query.from_user.first_name))

@Client.on_callback_query(filters.regex(r'^back') & filters.user(Config.OWNER_ID))
async def back_owner(bot, query):
    logging.info(f"Owner callback: {query.from_user.id}")
    reply_markup = InlineKeyboardMarkup(main_buttons)   
    await query.message.edit_text(
        reply_markup=reply_markup,
        text=Translation.START_TXT_ADMIN.format(
        query.from_user.first_name))


@Client.on_callback_query(filters.regex(r'^about'))
async def about(bot, query):
    await query.message.edit_text(
        text=Translation.ABOUT_TXT.format(bot.me.mention),
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 Back', callback_data='back')]]),
        disable_web_page_preview=True,
        parse_mode=enums.ParseMode.HTML,
    )



@Client.on_callback_query(filters.regex(r'^status'))
async def status(bot, query):
    users_count, bots_count = await db.total_users_bots_count()
    total_channels = await db.total_channels()
    await query.message.edit_text(
        text=Translation.STATUS_TXT.format(users_count, bots_count, temp.forwardings, total_channels, temp.BANNED_USERS ),
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(' Back', callback_data='help')]]),
        parse_mode=enums.ParseMode.HTML,
        disable_web_page_preview=True,
    )
    

