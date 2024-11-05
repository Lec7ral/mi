import logging
import asyncio 
from database import db
from config import Config
from translation import Translation
from pyrogram import Client, filters
from .test import get_configs, update_configs, CLIENT, parse_buttons, get_bot_groups
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, InputMediaVideo
from .utils import STS


CLIENT = CLIENT()
user_states = {}  # Diccionario para almacenar estados en memoria
CHANNEL_ID = -1002422039132  # Reemplaza con tu ID de canal
last_messages = {}  # Para almacenar los IDs de los últimos mensajes enviados


@Client.on_message(filters.private & filters.command(['userSettings']))
async def settings_user(client, message):
    text="<b>Change Your Settings As Your Wish</b>"
    try:
        await message.reply_text(
        text=text,
        reply_markup=main_buttons(),
        quote=True
        )
    except Exception as e:
        logging.error(f"fallo al llamar los bototnes{e}")


    
@Client.on_callback_query(filters.regex(r'^userSettings'))
async def user_settings_query(bot, query):
  logging.info(f"Callback data received: {query.data}")
  user_id = query.from_user.id
  i, type = query.data.split("#")
  logging.info(f"Callback data received2: {type}")
  buttons = [[InlineKeyboardButton('↩ Back', callback_data="userSettings#main")]]
  _bot = await db.get_bot(user_id)
 

  
  if type=="main":
     try:
         await query.message.edit_text(
          "<b>Cambia tu configuración como desees</b>",
          reply_markup=main_buttons())
     except Exception as e:
        logging.error(f"fallo al llamar los bototnes{e}")      
  if type=="groups":
     buttons = []
     channels = await db.get_user_channels(user_id)
     for channel in channels:
        buttons.append([InlineKeyboardButton(f"{channel['title']}",
                         callback_data=f"userSettings#editchannels_{channel['chat_id']}")])
     buttons.append([InlineKeyboardButton('✚ Add Grupo ✚', 
                      callback_data="userSettings#addchannel")])
     buttons.append([InlineKeyboardButton('↩ Back', 
                      callback_data="userSettings#main")])
     await query.message.edit_text( 
       "<b><u>Mis Grupos</u></b>\n\nPuede administrar sus chats objetivo aquí",
       reply_markup=InlineKeyboardMarkup(buttons))


  elif type == "addchannel":
    await query.message.delete()
    channels = await db.get_user_channels(user_id)
    try:
        logging.info("Iniciando el proceso para listar grupos del usuario.")
        
        text = await bot.send_message(user_id, "<b>🔄 Loading your groups...</b>")
        
        # Obtener grupos del usuario
        groups = []
        try:
            groups = await get_bot_groups(CLIENT.client(_bot))
        except Exception as e:  
            logging.error(f"Error al iniciar el cliente: {str(e)}")       
        if not groups:
            logging.warning("No se encontraron grupos.")
            return await text.edit_text(
                "No groups found!",
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        try:
         existing_chat_ids = {channel['chat_id'] for channel in channels}
        except Exception as e:
            logging.error("esta aqui")
        # Filtrar grupos para obtener solo aquellos que no están en channels
        grupos_filtrados = [group for group in groups if group['id'] not in existing_chat_ids]
        # Crear botones para cada grupo
        group_buttons = []
        for group in grupos_filtrados:
            group_buttons.append([
                InlineKeyboardButton(
                    f"{group['title']}",
                    callback_data=f"userSettings#selectgroup_{group['id']}"
                )
            ])
        # Agregar botón de cancelar
        group_buttons.append([InlineKeyboardButton('↩ Back', callback_data="userSettings#main")])
        logging.info("hasta aqui bien")
        await text.edit_text(
           "<b>Select a group to add:</b>\n\n"
           "Choose from your groups below:",
           reply_markup=InlineKeyboardMarkup(group_buttons)
        )
    except Exception as e:
        logging.error(f"Error al enviar mensaje inicial: {str(e)}")
        await bot.send_message(
            user_id,
            f"❌ An error occurred while loading groups: {str(e)}"
        )        
    
  elif type=="adduserbot":
     text = Translation.START_TXT_USER.format(query.from_user.mention) 
     await query.message.delete()
     user = await CLIENT.add_session(bot, query)
     if user != True: return
     await query.message.reply_text(
        text = text,
        reply_markup=user_main_buttons(user_id))
     await bot.answer_callback_query(query.id, text = "Sesión agregada correctamente a la base de datos", show_alert=False) 
      
  elif type=="bots": 
     bot = await db.get_bot(user_id)
     TEXT = Translation.BOT_DETAILS if bot['is_bot'] else Translation.USER_DETAILS
     buttons = [[InlineKeyboardButton('❌ Remove ❌', callback_data=f"userSettings#removebot")
               ],
               [InlineKeyboardButton('↩ Back', callback_data="userSettings#main")]]
     await query.message.edit_text(
        TEXT.format(bot['name'], bot['id'], bot['username']),
        reply_markup=InlineKeyboardMarkup(buttons))
                                             
  elif type=="removebot":
     await db.remove_bot(user_id)
     await query.message.edit_text(
           "Eliminado correctamente\n"
           "Las funciones del bot solo están disponibles si existe una sesión\n\n"
           "<b>Presione</b> /start <b>para iniciar sesión</b>"
            )


  elif type.startswith("editchannels"): 
     chat_id = type.split('_')[1]
     chat = await db.get_channel_details(user_id, chat_id)
     buttons = [[InlineKeyboardButton('❌ Remove ❌', callback_data=f"userSettings#removechannel_{chat_id}")
               ],
               [InlineKeyboardButton('↩ Back', callback_data="userSettings#groups")]]
     await query.message.edit_text(
        f"<b><u>📄 Channel Details</b></u>\n\n<b>Title :</b> <code>{chat['title']}</code>\n<b>Channel ID :</b> <code>{chat['chat_id']}</code>\n<b>Username :</b> {chat['username']}",
        reply_markup=InlineKeyboardMarkup(buttons))



    
  elif type.startswith("selectgroup"):
     logging.warning("Brinco bien hasta aqui id")
     chat_id = int(type.split('_')[1])
     logging.warning(f"Brinco bien hasta aqui id{chat_id}")
     groups = await get_bot_groups(CLIENT.client(_bot))
     groups_in_db = await db.get_user_channels(user_id)
     logging.warning(f"Bien hasta aqui {groups}")
     selected_group = next(
                   (g for g in groups if g["id"] == chat_id),
                   None
         )
     logging.warning(selected_group)
     if selected_group is None:
        logging.error(f"Grupo seleccionado no encontrado: {chat_id}")
        await query.message.edit_text("Grupo no encontrado.")
        return  # Salir si no se encuentra el grupo
     try:    
         await db.add_channel(
                   user_id,
                   chat_id,
                   selected_group['title'],
                   selected_group['username']
              )
     except Exception as e:
         logging.error(f"Tuvo fallo en: {e}")
     logging.warning("Adiciono")
     try: 
        text = "Adicionado correctamente" 
        await bot.answer_callback_query(query.id, text=text, show_alert=False)
     except Exception as e:
         logging.error(f"Tuvo fallo en: {e}")    
      #Eliminar el grupo de la lista de grupos
     try: 
         existing_chat_ids = {channel['chat_id'] for channel in groups_in_db}
     except Exception as e:
         logging.error(f"flitrado por {e}")
     try:
         grupos_filtrados = [g for g in groups if g["id"] != chat_id]
     except Exception as e:
         logging.error(f"flitrado por {e}")
     try:
         grupos_filtrados = [group for group in grupos_filtrados if group['id'] not in existing_chat_ids]
     except Exception as e:
         logging.error(f"flitrado por {e}")
      #Actualizar la vista para eliminar el grupo seleccionado
     group_buttons = []
     for group in grupos_filtrados:
           group_buttons.append([
              InlineKeyboardButton(
                  f"{group['title']}",
                  callback_data=f"userSettings#selectgroup_{group['id']}"
              )
           ])
            
           #Agregar botón de cancelar
     group_buttons.append([InlineKeyboardButton('↩ Back', callback_data="userSettings#main")])
     try:  
         await query.message.edit_text(
                   "<b>Select a group to add:</b>\n\n"
                   "Choose from your groups below:",
                   reply_markup=InlineKeyboardMarkup(group_buttons)
               )
     except Exception as e:
         logging.error(f"Fue al reescribir {e}")

  
  elif type.startswith("removechannel"):
     chat_id = type.split('_')[1]
     buttons = [[InlineKeyboardButton('↩ Back', callback_data="userSettings#groups")]]
     await db.remove_channel(user_id, chat_id)
     await query.message.edit_text(
        "Eliminado correctamente",
        reply_markup=InlineKeyboardMarkup(buttons))



  
  
  
  
  
  elif type == "message":
    try:
        # Eliminar mensajes anteriores
        if user_id in last_messages:
            for msg_id in last_messages[user_id]:
                try:
                    await bot.delete_messages(user_id, msg_id)
                except Exception as e:
                    logging.error(f"Error al eliminar mensaje anterior: {e}")
            last_messages[user_id] = []
        
        text, keyboard = await messages_menu(user_id)
        edit = None
        try:
           edit = await query.message.edit_text(text, reply_markup=keyboard)
        except Exception as e:
            logging.error(f"Dio error y brinco: {e, edit}")
        if not edit:
            logging.warning(edit)
            try:
                await bot.send_message(user_id, text, reply_markup=keyboard)
            except Exception as e:
                logging.error(f"Error al mandar mensajes: {e}")
    except Exception as e:
        logging.error(f"Error en el menú de mensajes: {e}")

  elif type == "addmessage":
      user_states[user_id] = "waiting_message"  # Establece el estado
      try:
          # Primero intentamos eliminar el mensaje actual
          await query.message.delete()
      except Exception as e:
          logging.error(f"Error al eliminar mensaje anterior: {e}")
      
      # Enviar el nuevo mensaje
      try:
          await bot.send_message(
              chat_id=user_id,
              text="Por favor, envía el mensaje que deseas guardar.\n"
                   "Puede ser texto, foto o video con descripción.",
              reply_markup=InlineKeyboardMarkup([
                  [InlineKeyboardButton("🔙 Cancelar", callback_data="userSettings#message")]
              ])
          )
      except Exception as e:
          logging.error(f"Error al enviar nuevo mensaje: {e}")
          await query.answer("Error al cambiar al modo de entrada de mensaje")
  
  elif type.startswith("view_"):
      try:
          index = int(type.split("_")[1])
          message_ids = await db.get_message_ids(user_id)
          logging.info(message_ids)
          if not message_ids or index >= len(message_ids):
              text, keyboard = await messages_menu(user_id)
              await query.message.edit_text(text, reply_markup=keyboard)
              return
          
          message_id = message_ids[index]['id']
          logging.error(message_id)
          message_type = message_ids[index].get('type', 'single')
          logging.error(message_type)# Obtener el tipo de mensaje
          try:
              message = await get_message(bot, message_ids[index])
              logging.warning(message)
          except Exception as e:
              logging.error(f"Error al obtener el mensaje: {e}")
          if not message:
              await query.answer("Mensaje no encontrado")
              return
          
          # Crear el teclado de navegación
          keyboard = []
          nav_row = []
          if index > 0:
              nav_row.append(InlineKeyboardButton("⬅️", callback_data=f"userSettings#view_{index-1}"))
          nav_row.append(InlineKeyboardButton("❌", callback_data=f"userSettings#delete_{index}"))
          if index < len(message_ids) - 1:
              nav_row.append(InlineKeyboardButton("➡️", callback_data=f"userSettings#view_{index+1}"))
          
          keyboard.append(nav_row)
          keyboard.append([InlineKeyboardButton("🔙 Volver", callback_data="userSettings#message")])
          reply_markup = InlineKeyboardMarkup(keyboard)
  
          # Si es una colección
          if message_type == 'media_group':
              await send_collection_message(bot, user_id, message, index, len(message_ids), reply_markup)
          else:
              # Tu código existente para mensajes individuales
              if message.text:
                    # Eliminar mensajes anteriores
                    if user_id in last_messages:
                        for msg_id in last_messages[user_id]:
                            try:
                                await bot.delete_messages(user_id, msg_id)
                            except Exception as e:
                                logging.error(f"Error al eliminar mensaje anterior: {e}")
                    await query.message.delete()
                    sent_msg = await bot.send_message(
                        text=f"📝 Mensaje {index + 1} de {len(message_ids)}\n\n{message.text}",
                        chat_id=user_id,
                        reply_markup=reply_markup
                    )
                    last_messages[user_id] = [sent_msg.id]
              elif message.photo:
                    # Eliminar mensajes anteriores
                    if user_id in last_messages:
                        for msg_id in last_messages[user_id]:
                            try:
                                await bot.delete_messages(user_id, msg_id)
                            except Exception as e:
                                logging.error(f"Error al eliminar mensaje anterior: {e}")
                    
                    await query.message.delete()
                    photo_file_id = message.photo[-1].file_id if isinstance(message.photo, list) else message.photo.file_id
                    sent_msg = await bot.send_photo(
                        chat_id=user_id,
                        photo=photo_file_id,
                        caption=f"📝 Mensaje {index + 1} de {len(message_ids)}\n\n{message.caption or ''}",
                        reply_markup=reply_markup
                    )
                    last_messages[user_id] = [sent_msg.id]
              elif message.video:
                    # Eliminar mensajes anteriores
                    if user_id in last_messages:
                        for msg_id in last_messages[user_id]:
                            try:
                                await bot.delete_messages(user_id, msg_id)
                            except Exception as e:
                                logging.error(f"Error al eliminar mensaje anterior: {e}")
                    
                    await query.message.delete()
                    sent_msg = await bot.send_video(
                        chat_id=user_id,
                        video=message.video.file_id,
                        caption=f"📝 Mensaje {index + 1} de {len(message_ids)}\n\n{message.caption or ''}",
                        reply_markup=reply_markup
                    )
                    last_messages[user_id] = [sent_msg.id]
              else:
                  await query.answer("Tipo de mensaje no soportado")
      except Exception as e:
          logging.error(f"Error al mostrar mensaje: {e}")
          logging.exception("Detalles completos del error:")  # Esto mostrará el traceback completo
          await query.answer("Error al mostrar el mensaje")
    

  elif type.startswith("delete_"):
      try:
          index = int(type.split("_")[1])
          message_ids = await db.get_message_ids(user_id)
          
          if message_ids and 0 <= index < len(message_ids):
              # Obtener el ID del mensaje del diccionario
              message_id_to_delete = message_ids[index]
              if isinstance(message_id_to_delete, dict) and message_id_to_delete.get('type') == 'media_group':
                  media_group_id = message_id_to_delete['id']
                  # Obtener todos los mensajes del grupo
                  try:
                      media_messages = await bot.get_media_group(CHANNEL_ID, media_group_id)
                      for msg in media_messages:
                          await bot.delete_messages(CHANNEL_ID, msg.id)
                  except Exception as e:
                      logging.error(f"Error al eliminar colección: {e}")
              else:  
              # Eliminar el mensaje del canal
                  try:
                      await bot.delete_messages(CHANNEL_ID, message_id_to_delete['id'])
                  except Exception as e:
                      logging.error(f"Error al eliminar mensaje del canal: {e}")
            
              # Eliminar el ID del mensaje de la BD del usuario
              await db.remove_message_id(user_id, message_id_to_delete['id'])
          
          text, keyboard = await messages_menu(user_id)
          await query.message.edit_text(text, reply_markup=keyboard)
      except Exception as e:
          logging.error(f"Error en delete_: {e}")
          await query.answer("Error al eliminar el mensaje")
  
  













    
                              

  
  elif type=="button":
     buttons = []
     button = (await get_configs(user_id))['button']
     if button is None:
        buttons.append([InlineKeyboardButton('✚ Add Botón ✚', 
                      callback_data="userSettings#addbutton")])
     else:
        buttons.append([InlineKeyboardButton('👀 See Botón', 
                      callback_data="userSettings#seebutton")])
        buttons[-1].append(InlineKeyboardButton('🗑️ Desechar Botón ', 
                      callback_data="userSettings#deletebutton"))
     buttons.append([InlineKeyboardButton('↩ Back', 
                      callback_data="userSettings#main")])
     await query.message.edit_text(                                                                                  #modificar esto en deploy
        "<b><u>Botón personalizado</b></u>\n\nPuede configurar un botón en línea para mensajes.\n\n<b><u>Formato :</b></u>\n`[My bot][buttonurl:https://t.me/#]`\n",
        reply_markup=InlineKeyboardMarkup(buttons))
  
  elif type=="addbutton":
     await query.message.delete()
     try:
         txt = await bot.send_message(user_id, text="**Envía tu botón personalizado.\n\nFORMATO:**\n`[My bot][buttonurl:https://t.me/#]`\n")
         ask = await bot.listen(chat_id=user_id, timeout=300)
         button = parse_buttons(ask.text.html)
         if not button:
            await ask.delete()
            return await txt.edit_text("Botón no válido")
         await update_configs(user_id, 'button', ask.text.html)
         await ask.delete()
         await txt.edit_text("Botón agregado con éxito",
            reply_markup=InlineKeyboardMarkup(buttons))
     except asyncio.exceptions.TimeoutError:
         await txt.edit_text('El proceso se ha cancelado automáticamente', reply_markup=InlineKeyboardMarkup(buttons))
  
  elif type=="seebutton":
      button = (await get_configs(user_id))['button']
      button = parse_buttons(button, markup=False)
      button.append([InlineKeyboardButton("↩ Back", "userSettings#button")])
      await query.message.edit_text(
         "**Tu botón personalizado**",
         reply_markup=InlineKeyboardMarkup(button))
      
  elif type=="deletebutton":
     await update_configs(user_id, 'button', None)
     await query.message.edit_text(
        "Botón eliminado con éxito",
        reply_markup=InlineKeyboardMarkup(buttons))
   
 
  elif type.startswith("alert"):
    alert = type.split('_')[1]
    await query.answer(alert, show_alert=True)

async def get_user_groups(client: Client):
    groups = []
    async for dialog in client.get_dialogs():
        if dialog.chat.type in ["group", "supergroup"]:
            groups.append({
                "id": dialog.chat.id,
                "title": dialog.chat.title,
                "username": dialog.chat.username,
                "members_count": dialog.chat.members_count
            })
    return groups

# Manejador de mensajes de texto
@Client.on_message(filters.photo & filters.private)
async def handle_photo(client, message):  # Asegúrate de recibir el parámetro client
    await handle_media_message(client, message, "Foto")  # Pasa el client como parámetro

@Client.on_message(filters.video & filters.private)
async def handle_video(client, message):  # Asegúrate de recibir el parámetro client
    await handle_media_message(client, message, "Video")

@Client.on_message(filters.text & filters.private)
async def handle_text(client, message):  # Asegúrate de recibir el parámetro client
    await handle_media_message(client, message, "Mensaje")

# Crear un conjunto para almacenar los media_group_id procesados
processed_media_groups = set()

async def handle_media_message(client, message, media_type):
    user_id = message.from_user.id
    state = user_states.get(user_id)
    
    if state == "waiting_message":
        try:
            if message.media_group_id:
                # Si ya procesamos este grupo de medios, ignoramos
                if message.media_group_id in processed_media_groups:
                    return
                
                # Marcar este grupo como procesado
                processed_media_groups.add(message.media_group_id)
                
                # Esperar un momento para asegurarse de recibir todos los mensajes
                await asyncio.sleep(0.5)
                
                try:
                    media_group = await client.get_media_group(
                        chat_id=message.chat.id,
                        message_id=message.id
                    )
                except Exception as e:
                    logging.error(f"Error al obtener grupo de medios: {e}")
                    processed_media_groups.discard(message.media_group_id)  # Eliminar del conjunto si hay error
                    return
                
                try:
                    forwarded_msgs = await client.forward_messages(
                        chat_id=CHANNEL_ID,
                        from_chat_id=message.chat.id,
                        message_ids=[msg.id for msg in media_group]
                    )
                    await db.add_message_id(user_id, forwarded_msgs[0].id, is_media_group=True)
                except Exception as e:
                    logging.error(f"Error al reenviar mensajes: {e}")
                    processed_media_groups.discard(message.media_group_id)  # Eliminar del conjunto si hay error
                    return
                
                # Opcional: Programar la limpieza del media_group_id después de un tiempo
                asyncio.create_task(clean_processed_media_group(message.media_group_id))
                
            else:
                forwarded_msg = await message.forward(CHANNEL_ID)
                await db.add_message_id(user_id, forwarded_msg.id)
            
            user_states.pop(user_id, None)
            
            await message.reply_text(
                f"✅ {media_type} guardado correctamente!",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Volver al menú", callback_data="userSettings#message")]
                ])
            )
        except Exception as e:
            logging.error(f"Error al guardar {media_type}: {e}")
            if message.media_group_id:
                processed_media_groups.discard(message.media_group_id)
            await message.reply_text(f"❌ Error al guardar el {media_type}.")

# Función para limpiar media_group_id después de un tiempo
async def clean_processed_media_group(media_group_id, delay=60):  # 60 segundos de delay
    await asyncio.sleep(delay)
    processed_media_groups.discard(media_group_id)


def main_buttons():
    buttons = [[
        InlineKeyboardButton('🤖 Bᴏᴛs',
                     callback_data='userSettings#bots'),
        InlineKeyboardButton('👥 Grupos',
                     callback_data='userSettings#groups')
    ],[
        InlineKeyboardButton('🔘 Bᴏᴛóɴ',
                     callback_data='userSettings#button'),
        InlineKeyboardButton('💬 Mensajes',
                     callback_data='userSettings#message')
    ],[
        InlineKeyboardButton('🚀 Impulsa tu experiencia', 
                     callback_data='pay')
    ],[
        InlineKeyboardButton('⌫ Bᴀᴄᴋ', 
                     callback_data='back')
    ]]
    return InlineKeyboardMarkup(buttons)
async def user_main_buttons(user_id):
  status = await db.get_user_status(user_id)
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
 

# Función para crear el menú principal
async def messages_menu(user_id):
    messages = await db.get_message_ids(user_id)
    text = "📝 Tus mensajes guardados:\n\n"
    text += f"Mensaje #1: {'✓' if len(messages) > 0 else '❌'}\n"
    text += f"Mensaje #2: {'✓' if len(messages) > 1 else '❌'}"
    
    keyboard = []
    if messages:
        keyboard.append([InlineKeyboardButton("👁️ Ver mensajes", callback_data="userSettings#view_0")])
    if len(messages) < 2:
        keyboard.append([InlineKeyboardButton("➕ Agregar nuevo", callback_data="userSettings#addmessage")])
    keyboard.append([InlineKeyboardButton("🔙 Volver al menú", callback_data="userSettings#main")])
    return text, InlineKeyboardMarkup(keyboard)



async def get_message(bot, message_data):
    """
    Recupera un mensaje o grupo de mensajes del canal
    Args:
        bot: Instancia del bot
        message_data: Puede ser un ID simple o un diccionario con información del mensaje
    Returns:
        Un mensaje individual o una lista de mensajes si es un media group
    """
    try:
        # Si message_data es un diccionario, verificar si es un media group
        if isinstance(message_data, dict):
            logging.warning("bien por aqui")
            try:
                if message_data.get('type') == 'media_group':
                    # Obtener el grupo de mensajes
                    messages = await bot.get_media_group(
                        chat_id=CHANNEL_ID,
                        message_id=int(message_data['id'])
                    )
                    logging.info(f"los mensajes recuperados son: {messages}")
                    return messages
            except Exception as e:
                logging.error(f"Error al recuperar el mensaje: {e}")    
            # Si tiene ID pero no es media_group, usar el ID
            message_id = int(message_data['id'])
        else:
            # Si es un ID simple (int o str)
            message_id = int(message_data)

        # Obtener mensaje individual
        message = await bot.get_messages(CHANNEL_ID, message_id)
        logging.info(f"es un mensaje individual: {message}")
        return message

    except Exception as e:
        logging.error(f"Error al recuperar el mensaje: {e}")
        return None
        
async def send_collection_message(bot, user_id, messages, index, total_messages, reply_markup):
    # Eliminar mensajes anteriores si existen
    if user_id in last_messages:
        try:
            for msg_id in last_messages[user_id]:
                try:
                    await bot.delete_messages(user_id, msg_id)
                except Exception as e:
                    logging.error(f"Error al eliminar mensaje anterior: {e}")
        except Exception as e:
            logging.error(f"Error al procesar eliminación de mensajes: {e}")
        last_messages[user_id] = []

    media_group = []
    text_messages = []
    new_messages = []
    
    for msg in messages:
        if msg.text:
            text_messages.append(msg.text)
        elif msg.photo:
            photo = msg.photo[-1] if isinstance(msg.photo, list) else msg.photo
            media_group.append(InputMediaPhoto(media=photo.file_id, caption=msg.caption))
        elif msg.video:
            media_group.append(InputMediaVideo(media=msg.video.file_id, caption=msg.caption))
    
    # Enviar mensajes de texto
    if text_messages:
        combined_text = "\n\n".join(text_messages)
        sent_msg = await bot.send_message(
            chat_id=user_id,
            text=f"📝 Mensaje {index + 1} de {total_messages}\n\n{combined_text}",
            reply_markup=reply_markup
        )
        new_messages.append(sent_msg.id)
    
    # Enviar grupo de medios
    if media_group:
        sent_media = await bot.send_media_group(chat_id=user_id, media=media_group)
        new_messages.extend([msg.id for msg in sent_media])
        
        # Enviar mensaje con botones
        sent_msg = await bot.send_message(
            chat_id=user_id,
            text=f"📝 Mensaje {index + 1} de {total_messages}",
            reply_markup=reply_markup
        )
        new_messages.append(sent_msg.id)
    
    # Actualizar el registro de mensajes enviados
    last_messages[user_id] = new_messages
