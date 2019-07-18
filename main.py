# -*- coding: utf-8 -*-
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode, InputMediaPhoto, ChatAction
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackQueryHandler, Filters, run_async
from telegram.error import (TelegramError, Unauthorized, BadRequest, TimedOut, NetworkError)
import sys
import os
import time
import re
import matplotlib.pyplot as plt
import matplotlib as mpl
from datetime import datetime
from models import User, Show
from constants import help_msg, about_msg, building_msg, houses_arr, greeting_msg
from classes import filt_integers, filt_call_err, block_filter
from config import log, log_chat, log_msg
from functools import wraps

KEY = sys.argv[1]
ADMIN_ID = sys.argv[2]
print('key ...' + KEY[-6:] + ' successfully used')


def send_typing_action(func):
    """Sends typing action while processing func command."""
    @wraps(func)
    def command_func(*args, **kwargs):
        bot, update = args
        bot.send_chat_action(chat_id=update.effective_message.chat_id, action=ChatAction.UPLOAD_DOCUMENT)
        return func(bot, update, **kwargs)
    return command_func


def chosen_owns(update):
    user_id = update.effective_user.id
    try:
        user = User.select().where(User.user_id == user_id)[Show.get(user_id=user_id).owns or 0]
    except IndexError:
        user = User.select().where(User.user_id == user_id)[0]
    return user


def is_changed(update):
    log.info(log_msg(update))
    # check if user exist in DB (both tables). If not - create
    username = update.effective_user.username
    user_id = update.effective_user.id
    full_name = update.effective_user.full_name

    user, created = User.get_or_create(user_id=user_id)
    Show.get_or_create(user_id=update.effective_user.id)

    if not created:
        # check if user changed own name attributes. If so - update
        if user.username != username or user.full_name != full_name:
            for user in User.select().where(User.user_id == user_id):
                user.username = username
                user.full_name = full_name
                if user.updated:
                    user.updated = datetime.now().strftime('%y.%m.%d %H:%M:%S.%f')[:-4]
                user.save()
    else:
        user.username = update.effective_user.username
        user.full_name = full_name
        user.save()


def start_command(bot, update):
    """handle /start command"""
    log.info(log_msg(update))
    is_changed(update)
    if update.callback_query:
        update.callback_query.answer()
    menu_kbd(bot, update)


def help_command(bot, update):
    """handle /help command"""
    log.info(log_msg(update))
    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton('Меню', callback_data='_menu')]])
    bot.sendMessage(chat_id=update.effective_user.id, text=help_msg, parse_mode=ParseMode.HTML,
                    reply_markup=reply_markup)


def about_command(bot, update):
    """handle /about command"""
    log.info(log_msg(update))
    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton('Меню', callback_data='_menu')]])
    bot.sendMessage(chat_id=update.effective_user.id, text=about_msg,
                    parse_mode=ParseMode.HTML, disable_web_page_preview=True, reply_markup=reply_markup)


def building(bot, update):
    """CallbackQueryHandler. pattern ^building$"""
    log.info(log_msg(update))
    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton('Меню', callback_data='_menu')]])
    bot.sendMessage(chat_id=update.effective_user.id, text=building_msg,
                    parse_mode=ParseMode.HTML, disable_web_page_preview=True, reply_markup=reply_markup)
    update.callback_query.answer()


def new_neighbor_report(bot, update, created_user):
    """Send message for users who enabled notifications"""
    log.info(log_msg(update))
    # query for users who set notifications as _notify_house
    query_params = Show.select(Show.user_id).where(Show.notification_mode == '_notify_house')
    query_users = User.select(User.user_id).where(User.house == created_user.house)
    query = query_params & query_users
    # prevent telegram blocking spam
    for i, user in enumerate(query):
        if i % 29 == 0:
            time.sleep(1)
        try:
            bot.sendMessage(chat_id=user.user_id, parse_mode=ParseMode.HTML,
                            text=f'Новий сусід\n{created_user.joined_str()}')
        except BadRequest as err:
            bot.sendMessage(chat_id=ADMIN_ID, text=f'failed to send notification for user {user.user_id} {err}',
                            parse_mode=ParseMode.HTML)

    # query for users who set notifications as _notify_section    
    query_params = Show.select(Show.user_id).where(Show.notification_mode == '_notify_section')
    query_users = query_users.where(User.section == created_user.section)
    query = query_params & query_users
    for i, user in enumerate(query):
        if i % 29 == 0:
            time.sleep(1)
        try:
            bot.sendMessage(chat_id=user.user_id, parse_mode=ParseMode.HTML,
                            text=f'Новий сусід\n{created_user.joined_str()}')
        except BadRequest as err:
            bot.sendMessage(chat_id=ADMIN_ID, text=f'failed to send notification for user {user.user_id} {err}',
                            parse_mode=ParseMode.HTML)


def user_created_report(bot, update, created_user, text):
    """when created new, or updated user - send report-message for admins"""
    bot.sendMessage(chat_id=ADMIN_ID, parse_mode=ParseMode.HTML, text=f'{text} {created_user.user_created()}')
    try:
        bot.sendMessage(chat_id=986555, parse_mode=ParseMode.HTML, text=f'{text} {created_user.user_created()}')
    except BadRequest:
        pass


def menu_kbd(bot, update):
    """show keyboard to chose: show neighbors or edit own info"""
    log.info(log_msg(update))
    if User.get(user_id=update.effective_user.id).house and User.get(user_id=update.effective_user.id).section:
        keyboard = [[InlineKeyboardButton('Дивитись сусідів 👫', callback_data='show')],
                    [InlineKeyboardButton('Змінити свої дані ✏', callback_data='edit')],
                    [InlineKeyboardButton('Важлива інфа ', callback_data='building')],
                    [InlineKeyboardButton('Статистика бота 📊️', callback_data='statistics')],
                    [InlineKeyboardButton('Мій будинок 🏠', callback_data='house_neighbors'),
                     InlineKeyboardButton('Мій під\'їзд 🔢', callback_data='section_neighbors')],
                    [InlineKeyboardButton('Сповіщення 🔔', callback_data='notifications')]]
    else:
        keyboard = [[InlineKeyboardButton('Дивитись сусідів 👫', callback_data='show')],
                    [InlineKeyboardButton('Додати свої дані 📝', callback_data='edit')],
                    [InlineKeyboardButton('Важлива інфа ', callback_data='building')],
                    [InlineKeyboardButton('Статистика бота 📊️', callback_data='statistics')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    bot.sendMessage(chat_id=update.effective_user.id, text='Меню:',
                    reply_markup=reply_markup, parse_mode=ParseMode.HTML)


def check_owns(bot, update):
    """check how many records for user in db"""
    log.info(log_msg(update))
    if not len(User.select().where(User.user_id == update.effective_user.id)) > 1:
        if update.callback_query.data == 'house_neighbors':
            show_house(bot, update)
            return
        elif update.callback_query.data == 'section_neighbors':
            show_section(bot, update)
            return
        else:
            if not User.get(user_id=update.effective_user.id).house:
                text = 'В якому Ви будинку ? 🏠 :'
                set_houses_kbd(bot, update, text)
            else:
                text = 'Змінюємо Ваші дані:\n' + User.get(
                    user_id=update.effective_user.id).setting_str() + '\nВ якому Ви будинку ? 🏠 :'
                set_houses_kbd(bot, update, text)
    # if more than 1 records for user, call func for select
    else:
        select_owns(bot, update)


def select_owns(bot, update):
    """if user have more than 1 records in db, select which one to show/edit"""
    log.info(log_msg(update))
    if update.callback_query.data == 'house_neighbors':
        text = 'Сусіди по якому будинку ? :'
        view_edit = 'view_my_house'
    elif update.callback_query.data == 'section_neighbors':
        text = 'Під\'їзд якої з Ваших квартир ? :'
        view_edit = 'view_my_secti'
    else:
        text = 'Яку адресу змінити? :'
        view_edit = 'edit'
    keyboard = []
    user_owns = User.select().where(User.user_id == update.effective_user.id)
    for i, j in enumerate(user_owns):
        keyboard.append([InlineKeyboardButton(str(j.edit_btn_str()), callback_data='set_owns' + str(i) + view_edit)])
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.callback_query.message.reply_text(text=text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
    update.callback_query.answer()


def owns_selected(bot, update):
    """save params to db"""
    log.info(log_msg(update))
    view_edit = update.callback_query.data[-13:]
    owns = [s for s in list(update.callback_query.data) if s.isdigit()]
    owns = int(''.join(owns))
    user = Show.get(user_id=update.effective_user.id)
    user.owns = owns
    user.save()

    if view_edit == 'view_my_house':
        show_house(bot, update)
    elif view_edit == 'view_my_secti':
        show_section(bot, update)
    else:
        user = User.select().where(User.user_id == update.effective_user.id)[owns]
        text = 'Змінюємо Ваші дані:\n' + user.setting_str() + '\nВ якому Ви будинку ? 🏠 :'
        set_houses_kbd(bot, update, text)
    update.callback_query.answer()


def houses_kbd(bot, update):
    """show keyboard to chose house to show"""
    log.info(log_msg(update))
    keyboard = [[InlineKeyboardButton('Будинок 85', callback_data='p_h85'),
                 InlineKeyboardButton('Будинок 87', callback_data='p_h87')],
                [InlineKeyboardButton('Будинок 89', callback_data='p_h89')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.callback_query.message.reply_text('Який будинок показати ? 🏠 :', reply_markup=reply_markup)
    update.callback_query.answer()


def section_kbd(bot, update):
    user_query = Show.get(user_id=update.effective_user.id)
    user_query.house = int(update.callback_query.data[-2:])
    user_query.save()

    keyboard = [[InlineKeyboardButton('П-зд №1', callback_data='p_s1'),
                 InlineKeyboardButton('П-зд №2', callback_data='p_s2')],
                [InlineKeyboardButton('П-зд №3', callback_data='p_s3'),
                 InlineKeyboardButton('П-зд №4', callback_data='p_s4')],
                [InlineKeyboardButton('П-зд №5', callback_data='p_s5'),
                 InlineKeyboardButton('П-зд №6', callback_data='p_s6')],
                [InlineKeyboardButton('Показати всіх в цьому будинку? ', callback_data='show_this_house')]]

    if user_query.house == 87:
        del keyboard[1:3]

    reply_markup = InlineKeyboardMarkup(keyboard)
    update.callback_query.message.reply_text('Який під\'їзд показати? ', reply_markup=reply_markup)
    update.callback_query.answer()


def save_params(bot, update):
    """callbackQuery from section_kbd(). save params to db table"""
    log.info(log_msg(update))
    user_query = Show.get(user_id=update.effective_user.id)
    user_query.section = int(update.callback_query.data[3])
    user_query.save()
    some_section = True
    show_section(bot, update, some_section)
    update.callback_query.answer()


def set_houses_kbd(bot, update, text=''):
    """show keyboard to chose its own house"""
    log.info(log_msg(update))
    if not User.get(user_id=update.effective_user.id).house:
        text = text
    elif len(User.select().where(User.user_id == update.effective_user.id)) > 1:
        text = text
    else:
        text = text
    keyboard = [[InlineKeyboardButton('Будинок №85', callback_data='_h85'),
                 InlineKeyboardButton('Будинок №87', callback_data='_h87')],
                [InlineKeyboardButton('Будинок №89', callback_data='_h89')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.callback_query.message.reply_text(text=text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
    update.callback_query.answer()


def set_section_kbd(bot, update):
    user = chosen_owns(update)
    user.house = int(update.callback_query.data[-2:])
    user.save()

    keyboard = [[InlineKeyboardButton('П-зд №1', callback_data='_s1'),
                 InlineKeyboardButton('П-зд №2', callback_data='_s2')],
                [InlineKeyboardButton('П-зд №3', callback_data='_s3'),
                 InlineKeyboardButton('П-зд №4', callback_data='_s4')],
                [InlineKeyboardButton('П-зд №5', callback_data='_s5'),
                 InlineKeyboardButton('П-зд №6', callback_data='_s6')],
                [InlineKeyboardButton('Завершити редагування', callback_data='_section_reject')]]

    if user.house == 87:
        del keyboard[1:3]

    reply_markup = InlineKeyboardMarkup(keyboard)
    update.callback_query.message.reply_text('В якому Ви під\'їзді? ', reply_markup=reply_markup)
    update.callback_query.answer()


def set_floor_kbd(bot, update):
    """callbackQuery from set_section_kbd(). show keyboard to chose its own floor"""
    log.info(log_msg(update))
    user = chosen_owns(update)
    user.section = int(update.callback_query.data[2])
    user.save()

    floors = houses_arr['house_' + str(user.house)]['section_' + str(user.section)]
    keyboard = []
    count_ = len(floors)
    while count_ > 0:
        floor = []
        for i in range(3):
            if count_ == 0:
                break
            floor.append(InlineKeyboardButton(str(floors[-count_]), callback_data='_f' + str(floors[-count_])))
            count_ -= 1
        keyboard.append(floor)

    reply_markup = InlineKeyboardMarkup(keyboard)
    update.callback_query.message.reply_text('На якому Ви поверсі ? 🧗 :', reply_markup=reply_markup)
    update.callback_query.answer()


def set_apartment_kbd(bot, update):
    """func show message with ask to tell its own appartment"""
    log.info(log_msg(update))
    floor = [s for s in list(update.callback_query.data) if s.isdigit()]
    floor = int(''.join(floor))

    user = chosen_owns(update)
    user.floor = floor
    user.save()

    user_mode = Show.get(user_id=update.effective_user.id)
    user_mode.msg_apart_mode = True
    user_mode.save()

    text = 'З якої Ви квартири? \nВкажіть в повідомленні номер квартири числом:'
    update.callback_query.message.reply_text(text=text)
    update.callback_query.answer()


def msg_handler(bot, update):
    """handle all text msg except other filters do"""
    msg = update.message.text
    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton('Меню', callback_data='_menu')]])
    bot.sendPhoto(chat_id=update.effective_user.id, photo=open(os.path.join('img', 'maybe.jpg'), 'rb'),
                  reply_markup=reply_markup,
                  caption=f'Я ще не розумію людської мови, але вчусь, і скоро буду розуміть деякі слова і фрази\n'
                  f'Краще скористайтесь меню')
    log.info(log_msg(update) + f' text: {msg}')


def group_chat_logging(bot, update):
    """handle text msgs in group chat. MessageHandler((Filters.text & Filters.group)"""
    msg = update.message.text
    log_chat.info(log_msg(update) + f' msg: {msg}')


def jubilee(bot, update, created_user):
    """Check if new added user is 'hero of the day' i.e some round number in db"""
    log.info(log_msg(update))
    celebration_count = [i for i in range(0, 1000, 50)]
    query = User.select().where(User.house, User.section)
    text = f'сусідів 🎇 🎈 🎉 🎆 🍹\nВітаємо\n{created_user.joined_str()}'

    # to do: celebrate once! There is a bug. It will be celebrate each time for house 1, until count will stay at 100
    if query.count() in celebration_count:
        text = f'Вже зареєстровано {query.count()} ' + text
    if query.where(User.house == 89).count() in celebration_count:
        text = f'В будинку №89 вже зареєстровано {query.where(User.house == 89).count()} ' + text
    elif query.where(User.house == 87).count() in celebration_count:
        text = f'В будинку №87 вже зареєстровано {query.where(User.house == 87).count()} ' + text
    elif query.where(User.house == 85).count() in celebration_count:
        text = f'В будинку №85 вже зареєстровано {query.where(User.house == 85).count()} ' + text
    else:
        return
    try:
        bot.sendMessage(chat_id=-1001076439601, text=text, parse_mode=ParseMode.HTML)  # test chat
    except BadRequest:
        bot.sendMessage(chat_id=-1001307649156, text=text, parse_mode=ParseMode.HTML)


def apartment_save(bot, update):
    """integer text handler"""
    log.info(log_msg(update))
    user_mode = Show.get(user_id=update.effective_user.id)
    text_success = '<b>Дякую, Ваші дані збережені</b>. Бажаєте подивитись сусідів?'
    if user_mode.msg_apart_mode:
        apartment = int(update.message.text)
        user = chosen_owns(update)
        user.apartment = apartment
        if not user.updated:
            text = 'В базу ДОДАНО сусіда:\n'
        else:
            text = 'В базі ОНОВЛЕНО сусіда:\n'
        user.updated = datetime.now().strftime('%y.%m.%d %H:%M:%S.%f')[:-4]
        user.save()
        bot.sendMessage(text=text_success, chat_id=update.effective_user.id, parse_mode=ParseMode.HTML)
        user_mode.msg_apart_mode = False
        user_mode.save()
        user_created_report(bot, update, created_user=user, text=text)
        new_neighbor_report(bot, update, created_user=user)
        menu_kbd(bot, update)


def save_user_data(bot, update):
    """callbackQuery from reject. save user data"""
    log.info(log_msg(update))
    user = chosen_owns(update)
    if not user.updated:
        text = 'В базу ДОДАНО сусіда:\n'
    else:
        text = 'В базі ОНОВЛЕНО сусіда:\n'

    if update.callback_query.data == '_apart_reject':
        user_mode = Show.get(user_id=update.effective_user.id)
        user_mode.msg_apart_mode = False
        user_mode.save()

        user.apartment = None

    user.updated = datetime.now().strftime('%y.%m.%d %H:%M:%S.%f')[:-4]
    user.save()

    update.callback_query.answer()
    user_created_report(bot, update, created_user=user, text=text)
    new_neighbor_report(bot, update, created_user=user)
    bot.sendMessage(chat_id=update.effective_user.id, parse_mode=ParseMode.HTML,
                    text='<b>Дякую, Ваші дані збережені</b>. Бажаєте подивитись сусідів?')
    start_command(bot, update)


def show_house(bot, update):
    """callbackQuery handler """
    log.info(log_msg(update))
    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton('Меню', callback_data='_menu')]])

    if update.callback_query.data == 'show_this_house':
        # if user want see selected house
        user_query = Show.get(user_id=update.effective_user.id)
    else:
        # if user want see own house and have one
        user_query = chosen_owns(update)
    neighbors = []
    sections = User.select(User.section).where(User.house == user_query.house).distinct().order_by(User.section)
    for i in sections:
        neighbors.append('\n' + '📭 <b>Під\'їзд '.rjust(30, ' ') + str(i.section) + '</b>' + '\n')
        for user in User.select().where(User.house == user_query.house, User.section == i.section).order_by(User.floor):
            neighbors.append(str(user) + '\n')
    show_list = ('<b>Мешканці будинку №' + str(user_query.house) + '</b>:\n'
                 + '{}' * len(neighbors)).format(*neighbors)

    if len(show_list) < 6200:
        bot.sendMessage(chat_id=update.effective_user.id, parse_mode=ParseMode.HTML, text=show_list,
                        reply_markup=reply_markup)
    else:
        part_1, part_2, part_3 = show_list.partition('📭 <b>Під\'їзд №4'.rjust(30, ' ') + '</b>' + '\n')
        bot.sendMessage(chat_id=update.effective_user.id, parse_mode=ParseMode.HTML, text=part_1[:-2])
        # to do: remove "." from 2nd msg. Without that dot, rjust not works
        bot.sendMessage(chat_id=update.effective_user.id, parse_mode=ParseMode.HTML, text='.' + part_2 + part_3,
                        reply_markup=reply_markup)
    update.callback_query.answer()


def show_section(bot, update, some_section=False):
    """Here need some documentation"""
    log.info(log_msg(update))
    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton('Меню', callback_data='_menu')]])

    if not some_section:
        user_query = chosen_owns(update)
    else:
        user_query = Show.get(user_id=update.effective_user.id)

    query = User.select().where(
        User.house == user_query.house,
        User.section == user_query.section).order_by(User.floor)
    neighbors = [str(user) + '\n' for user in query]

    show_list = (
                '<b>Мешканці під\'їзду № ' + str(user_query.section) + ' Будинку № ' + str(user_query.house) + '</b>:\n'
                + '{}' * len(neighbors)).format(*neighbors)

    bot.sendMessage(chat_id=update.effective_user.id, parse_mode=ParseMode.HTML,
                    disable_web_page_preview=True, text=show_list, reply_markup=reply_markup)
    update.callback_query.answer()


def catch_err(bot, update, error):
    """handle all telegram errors end send report. There is no 'update' so can't logging much info"""
    log.info(f'{error} {type(error)}')
    user_id = update.effective_user.id if update else 'no update'
    try:
        raise error
    except Unauthorized:
        bot.sendMessage(chat_id=ADMIN_ID, text=f'ERROR:\n {error}\n type {type(error)} id: {user_id}')
    except BadRequest:
        bot.sendMessage(chat_id=ADMIN_ID, text=f'ERROR:\n {error}\n type {type(error)} id: {user_id}')
    except (TimedOut, NetworkError, TelegramError):
        bot.sendMessage(chat_id=ADMIN_ID, text=f'ERROR:\n {error}\n type {type(error)} id: {user_id}')


# to do: apply to more then 1 custom filter
@run_async
def del_msg(bot, update):
    """message text handler for specific words in group chats MessageHandler((Filters.group & block_filter).
    See filters in classes module
    """
    chat_id = update.message.chat_id
    message_id = update.message.message_id
    pattern = block_filter(update.message)
    warn_msg = f'Повідомлення які містять <code>{pattern}</code> видаляються автоматично'

    bot.deleteMessage(chat_id=chat_id, message_id=message_id)
    deleted_msg = bot.sendMessage(chat_id=chat_id, parse_mode=ParseMode.HTML, text=warn_msg)
    time.sleep(5)
    bot.deleteMessage(chat_id=chat_id, message_id=deleted_msg.message_id)
    log.info(log_msg(update) + f' {pattern}')


@run_async
def greeting(bot, update):
    """handle new chat members, and sent greeting message. Delete after delay. Running async"""
    log.info(log_msg(update))
    new_member_name = update.message.from_user.full_name
    text = greeting_msg.format(new_member_name)
    update.message.reply_text(text=text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)


def prepare_data():
    """Create show_list (string) for statistic message, and pie_values (list) for chart. 
    return from func if no users in db"""
    log.info('this func has no update')
    query = User.select()
    query_with = query.where(User.house, User.section)
    query_without = query.where(User.house.is_null() | User.section.is_null())
    houses = query_with.select(User.house).distinct().order_by(User.house)

    # did users indicate their info
    introduced = {'Yes': query_with.count(), 'No': query_without.count()}
    # last 3 joined users
    last_3_users = list(reversed(query_with.order_by(User.id)[-3:]))

    if not last_3_users:
        return

    neighbors = []
    pie_values = []
    bars_values = {}
    for house_ in houses:
        count = query_with.where(User.house == house_.house).count()
        pie_values.append(count)
        neighbors.append('\n' + '🏠 <b>Будинок '.rjust(30, ' ') + f'{house_.house}</b> <code>({count})</code>\n')
        sections = query_with.select(User.section).where(User.house == house_.house).distinct().order_by(User.section)
        section_dict = {}
        for section_ in sections:
            count = query_with.where(User.house == house_.house, User.section == section_.section).count()
            neighbors.append(f'Під\'їзд {section_.section} <code>({count})</code>\n')
            section_dict[section_.section] = count
        bars_values[house_.house] = section_dict

    show_list = (f'<b>Всього користувачів: {query.count()}</b>\n'
                 f'<i>Дані вказані {introduced["Yes"]}</i>\n'
                 f'<i>Дані не вказані {introduced["No"]}</i>\n'
                 + '{}' * len(neighbors)).format(*neighbors) + '\n<b>Нові сусіди</b>'

    # add to msg last 3 joined users
    for i in range(len(last_3_users)):
        show_list += f'\n{last_3_users[i].joined_str()}'

    return {'show_list': show_list, 'pie_values': pie_values, 'bars_values': bars_values, 'introduced': introduced}


def statistics(bot, update):
    """callbackQuery handler. pattern:^statistics$"""
    log.info(log_msg(update))
    update.callback_query.answer()
    keyboard = [[InlineKeyboardButton('Меню', callback_data='_menu'),
                 InlineKeyboardButton('Графіка', callback_data='charts')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    show_list = prepare_data()['show_list']
    bot.sendMessage(chat_id=update.effective_user.id, parse_mode=ParseMode.HTML, text=show_list,
                    reply_markup=reply_markup)


def make_pie(prepared_data):
    """create pie total by houses"""
    log.info('this func has no update')

    # func for setting values format on pie
    def make_autopct(values):
        def my_autopct(pct):
            total = sum(values)
            val = int(round(pct * total / 100.0))
            return val

        return my_autopct

    # pie by house    
    values = prepared_data['pie_values']
    labels = [f'Буд. {i + 1}' for i in range(len(values))]

    fig = plt.figure(figsize=(10, 7))
    mpl.rcParams.update({'font.size': 20})
    plt.pie(values, autopct=make_autopct(values), radius=1.5, pctdistance=0.8,
            shadow=True, labels=labels, labeldistance=1.05)

    img_path = os.path.join('img', 'charts', '1_pie.png')
    fig.savefig(img_path)
    plt.clf()
    plt.close()

    # pie by introduced
    values = list(prepared_data['introduced'].values())
    labels = list(prepared_data['introduced'].keys())

    fig = plt.figure(figsize=None)
    mpl.rcParams.update({'font.size': 16})
    plt.title('Користувачі вказали свої дані', pad=15)
    plt.pie(values, autopct=make_autopct(values), radius=1.3, pctdistance=0.8,
            shadow=True, labels=labels, labeldistance=1.05)

    img_path = os.path.join('img', 'charts', '2_pie.png')
    fig.savefig(img_path)
    plt.clf()
    plt.close()


def make_bars(prepared_data):
    """create bars for houses sections count"""
    log.info('this func has no update')
    values_ = prepared_data['bars_values']

    def autolabel(rects, height_factor):
        for i, rect in enumerate(rects):
            height = rect.get_height()
            label = '%d' % int(height)
            ax.text(rect.get_x() + rect.get_width() / 2., height_factor * height,
                    '{}'.format(label),
                    ha='center', va='bottom')

    mpl.rcParams.update({'font.size': 15})

    for house in values_:
        sections = [f'Під\'їзд {i[-1]}' for i in houses_arr[f'house_{house}']]
        values = [values_[house].get(int(i[-1]), 0) for i in sections]

        plt.bar(sections, values)
        ax = plt.gca()
        ax.set_title(f'Будинок {house}')
        autolabel(ax.patches, height_factor=0.85)

        img_path = os.path.join('img', 'charts', f'bar{house}.png')
        plt.savefig(img_path, dpi=200)
        plt.clf()
        plt.close()


@send_typing_action
def charts(bot, update):
    """callbackQuery handler. pattern:^charts$. Show chart"""
    log.info(log_msg(update))
    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton('Меню', callback_data='_menu')]])

    prepared_data = prepare_data()
    make_pie(prepared_data)
    make_bars(prepared_data)

    charts_dir = os.path.join('img', 'charts')
    charts_list = sorted([f for f in os.listdir(charts_dir) if not f.startswith('.')])
    media = [InputMediaPhoto(open(os.path.join('img', 'charts', i), 'rb')) for i in charts_list]

    bot.sendMediaGroup(chat_id=update.effective_user.id, media=media)
    bot.sendMessage(chat_id=update.effective_user.id, parse_mode=ParseMode.HTML,
                    reply_markup=reply_markup, text='Повернутись в меню:')
    update.callback_query.answer()


def notifications_kbd(bot, update):
    """callbackQuery handler. pattern:^notifications$. Show notifications keyboard settings"""
    log.info(log_msg(update))
    keyboard = [[InlineKeyboardButton('В моєму будинку 🏠', callback_data='_notify_house')],
                [InlineKeyboardButton('В моєму під\'їзді 🔢', callback_data='_notify_section')],
                [InlineKeyboardButton('Вимкнути сповіщення 🔕', callback_data='_notify_OFF')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    user = Show.get(user_id=update.effective_user.id)
    _dict = {None: 'Вимкнено', '_notify_OFF': 'Вимкнено',
             '_notify_section': 'В моєму під\'їзді 🔢', '_notify_house': 'В моєму будинку 🏠'}
    text = f'Зараз сповіщення встановленні в режим\n' \
        f'<b>{_dict[user.notification_mode]}</b>\nОтримувати сповіщення коли з\'явиться новий сусід:'
    bot.editMessageText(chat_id=update.effective_user.id, parse_mode=ParseMode.HTML,
                        text=text, reply_markup=reply_markup, message_id=update.effective_message.message_id)
    update.callback_query.answer()


def notifications_save(bot, update):
    """callbackQuery handler. pattern: from notifications_kbd func. Save notifications settings to db"""
    log.info(log_msg(update))
    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton('Меню', callback_data='_menu')]])

    user = Show.get(user_id=update.effective_user.id)
    user.notification_mode = update.callback_query.data
    user.save()
    bot.editMessageText(text='Ок! Налаштування збережено', chat_id=update.effective_chat.id, parse_mode=ParseMode.HTML,
                        message_id=update.effective_message.message_id, reply_markup=reply_markup)
    update.callback_query.answer()


def del_command(bot, update):
    """For deleting commands sent in group chat. MessageHandler(Filters.command & Filters.group).
    If so - delete message from group chat. """
    command = re.sub(r'@.*', '', update.message.text)
    log.info(log_msg(update) + f' DEL {command}')
    chat_id = update.message.chat_id
    message_id = update.message.message_id
    bot.deleteMessage(chat_id=chat_id, message_id=message_id)
    commands = {'/start': start_command,
                '/help': help_command,
                '/about': about_command}
    try:
        commands[command](bot, update)
    except KeyError:
        pass


def talkative(bot, update):
    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton('Меню', callback_data='_menu')]])
    data = {}
    pattern = r' [0-9]{6,10} '
    with open('log_chatfile.log', mode='r', encoding='utf-8') as file:
        lines = file.readlines()
        for line in lines:
            try:
                id_ = line.partition(re.search(pattern, line).group(0))[1]
                name = line[line.find('name: ') + 6: line.find(' usrnm: ')]
                data[id_.strip()] = [0, 0, name]
            except AttributeError:
                pass

    for i in data:
        chat_file = open('log_chatfile.log', mode='r', encoding='utf-8')
        for line in chat_file.readlines():
            id_ = line.partition(re.search(pattern.strip(), i).group(0))[1]
            if id_.strip() == i:
                data[i][0] += len(line.split('msg: ')[1].strip())
                data[i][1] += 1

    by_chars = sorted(data.items(), key=lambda x: x[1][0], reverse=True)
    by_msgs = sorted(data.items(), key=lambda x: x[1][1], reverse=True)

    template = '<a href="tg://user?id={}">{}</a> {}'

    talkatives_chars = [template.format(user[0], user[1][2], user[1][0]) + '\n' for user in by_chars[:10]]
    talkatives_msgs = [template.format(user[0], user[1][2], user[1][1]) + '\n' for user in by_msgs[:10]]

    show_list = ('<b>Лідери по кількості знаків</b>\n' + '{}' * len(talkatives_chars)).format(*talkatives_chars) + \
                '\n' + ('<b>Лідери по кількості повідомлень</b>\n' + '{}' * len(talkatives_msgs)).format(
        *talkatives_msgs)

    bot.sendMessage(chat_id=update.effective_user.id, parse_mode=ParseMode.HTML,
                    disable_web_page_preview=True, text=show_list, reply_markup=reply_markup)


def main():
    updater = Updater(KEY)

    dispatcher = updater.dispatcher
    # group filters
    dispatcher.add_handler(MessageHandler(Filters.status_update.new_chat_members, greeting))
    dispatcher.add_handler(MessageHandler((Filters.command & Filters.group), del_command))
    dispatcher.add_handler(MessageHandler((Filters.group & block_filter), del_msg))
    dispatcher.add_handler(MessageHandler((Filters.text & Filters.group), group_chat_logging))

    dispatcher.add_handler(CommandHandler("start", start_command))
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(CommandHandler("about", about_command))

    dispatcher.add_handler(MessageHandler(filt_integers, apartment_save))
    dispatcher.add_handler(MessageHandler(filt_call_err, talkative))
    dispatcher.add_handler(MessageHandler(Filters.text, msg_handler))
    dispatcher.add_handler(CallbackQueryHandler(callback=start_command, pattern='^_menu$'))
    dispatcher.add_handler(CallbackQueryHandler(callback=building, pattern='^building$'))
    dispatcher.add_handler(CallbackQueryHandler(callback=statistics, pattern='^statistics$'))
    dispatcher.add_handler(CallbackQueryHandler(callback=charts, pattern='^charts$'))
    dispatcher.add_handler(CallbackQueryHandler(callback=notifications_kbd, pattern='^notifications$'))
    dispatcher.add_handler(
        CallbackQueryHandler(callback=notifications_save, pattern='^_notify_section$|^_notify_house$|^_notify_OFF$'))
    dispatcher.add_handler(CallbackQueryHandler(callback=houses_kbd, pattern='^show$'))
    dispatcher.add_handler(CallbackQueryHandler(callback=show_house, pattern='^show_this_house$'))
    dispatcher.add_handler(CallbackQueryHandler(callback=section_kbd, pattern='^p_h'))
    dispatcher.add_handler(CallbackQueryHandler(callback=save_params, pattern='^p_s'))
    dispatcher.add_handler(
        CallbackQueryHandler(callback=check_owns, pattern='^edit$|^house_neighbors$|section_neighbors'))
    dispatcher.add_handler(CallbackQueryHandler(callback=owns_selected, pattern='^set_owns'))
    dispatcher.add_handler(CallbackQueryHandler(callback=set_section_kbd, pattern='^_h'))
    dispatcher.add_handler(
        CallbackQueryHandler(callback=save_user_data, pattern='^_apart_reject$|^_floor_reject$|^_section_reject$'))
    dispatcher.add_handler(CallbackQueryHandler(callback=set_floor_kbd, pattern='^_s'))
    dispatcher.add_handler(CallbackQueryHandler(callback=set_apartment_kbd, pattern='^_f'))

    dispatcher.add_error_handler(catch_err)

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
