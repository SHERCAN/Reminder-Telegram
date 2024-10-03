import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import datetime
import json
import os
from dotenv import load_dotenv
load_dotenv()

# Configurar logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Archivo para almacenar los recordatorios
REMINDERS_FILE = 'reminders.json'

# Cargar recordatorios desde el archivo
def load_reminders():
    try:
        with open(REMINDERS_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

# Guardar recordatorios en el archivo
def save_reminders(reminders):
    with open(REMINDERS_FILE, 'w') as f:
        json.dump(reminders, f)

# Comando /crear
async def crear(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    args = context.args

    if len(args) < 2:
        await update.message.reply_text("Uso: /crear <días> <nombre>")
        return

    dias = args[0]
    nombre = ' '.join(args[1:])

    reminders = load_reminders()
    if str(chat_id) not in reminders:
        reminders[str(chat_id)] = []

    reminders[str(chat_id)].append({
        'nombre': nombre,
        'dias': dias,
        'proximo_aviso': (datetime.datetime.now() + datetime.timedelta(days=int(dias))).isoformat()
    })

    save_reminders(reminders)
    await update.message.reply_text(f"Recordatorio '{nombre}' creado para repetirse cada {dias} días.")

# Comando /borrar
async def borrar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    reminders = load_reminders()

    if str(chat_id) not in reminders or not reminders[str(chat_id)]:
        await update.message.reply_text("No hay recordatorios para borrar.")
        return

    keyboard = []
    for i, reminder in enumerate(reminders[str(chat_id)]):
        keyboard.append([InlineKeyboardButton(reminder['nombre'], callback_data=f"borrar_{i}")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Seleccione el recordatorio a borrar:", reply_markup=reply_markup)

# Manejar la selección del recordatorio a borrar
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    chat_id = update.effective_chat.id
    reminders = load_reminders()

    if query.data.startswith("borrar_"):
        index = int(query.data.split("_")[1])
        if str(chat_id) in reminders and index < len(reminders[str(chat_id)]):
            deleted = reminders[str(chat_id)].pop(index)
            save_reminders(reminders)
            await query.edit_message_text(f"Recordatorio '{deleted['nombre']}' borrado.")
        else:
            await query.edit_message_text("No se pudo borrar el recordatorio.")
    elif query.data.startswith("pagado_") or query.data.startswith("posponer_"):
        _, reminder_chat_id, reminder_name = query.data.split("_")
        reminder = next((r for r in reminders[reminder_chat_id] if r['nombre'] == reminder_name), None)
        if reminder:
            if query.data.startswith("pagado_"):
                reminder['proximo_aviso'] = (datetime.datetime.now() + datetime.timedelta(days=int(reminder['dias']))).isoformat()
                await query.edit_message_text(f"Recordatorio '{reminder['nombre']}' marcado como pagado. Próximo aviso en {reminder['dias']} días.")
            else:  # posponer
                reminder['proximo_aviso'] = (datetime.datetime.now() + datetime.timedelta(hours=12)).isoformat()
                await query.edit_message_text(f"Recordatorio '{reminder['nombre']}' pospuesto 12 horas.")
            save_reminders(reminders)
# Función para verificar y enviar recordatorios
async def check_reminders(context: ContextTypes.DEFAULT_TYPE) -> None:
    now = datetime.datetime.now()
    reminders = load_reminders()

    for chat_id, chat_reminders in reminders.items():
        for reminder in chat_reminders:
            if datetime.datetime.fromisoformat(reminder['proximo_aviso']) <= now:
                keyboard = [
                    [InlineKeyboardButton("Pagado", callback_data=f"pagado_{chat_id}_{reminder['nombre']}"),
                     InlineKeyboardButton("Posponer", callback_data=f"posponer_{chat_id}_{reminder['nombre']}")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await context.bot.send_message(chat_id=chat_id, text=f"¡Recordatorio: {reminder['nombre']}!", reply_markup=reply_markup)

# Función principal
def main() -> None:
    # Reemplaza 'TU_TOKEN' con el token de tu bot
    application = Application.builder().token(os.getenv('TOKEN')).build()

    application.add_handler(CommandHandler("crear", crear))
    application.add_handler(CommandHandler("borrar", borrar))
    application.add_handler(CallbackQueryHandler(button))

    # Programar la verificación de recordatorios cada minuto
    job_queue = application.job_queue
    job_queue.run_repeating(check_reminders, interval=60, first=10)

    application.run_polling()

if __name__ == '__main__':
    main()