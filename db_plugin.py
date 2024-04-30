import datetime
from data import db_session
from data.users import User
from data.chats import Chat
from data.users_in_chats import UserInChat


def is_user_exists(user):
    db_sess = db_session.create_session()
    return db_sess.query(User).filter(User.id == user.id).first() is not None


def is_chat_exists(chat):
    db_sess = db_session.create_session()
    return db_sess.query(Chat).filter(Chat.id == chat.id).first() is not None


def is_user_in_chat(user, chat):
    db_sess = db_session.create_session()
    return db_sess.query(UserInChat).filter(UserInChat.user_id == user.id, UserInChat.chat_id == chat.id).first() is not None



def add_user(user):
    if not is_user_exists(user):
        db_sess = db_session.create_session()
        new_user = User(id=user.id,
                        first_name=user.first_name,
                        last_name=user.last_name,
                        full_name=user.full_name)
        db_sess.add(new_user)
        db_sess.commit()



def add_chat(chat):
    if not is_chat_exists(chat):
        db_sess = db_session.create_session()
        new_chat = Chat(id=chat.id,
                        title=chat.title)
        db_sess.add(new_chat)
        db_sess.commit()


def add_user_to_chat(user, chat):
    if not is_user_in_chat(user, chat):
        db_sess = db_session.create_session()
        new_connection = UserInChat(user_id=user.id, chat_id=chat.id)
        db_sess.add(new_connection)
        db_sess.commit()


def update_user(user):
    db_sess = db_session.create_session()
    if is_user_exists(user):
        user = db_sess.query(User).filter(User.id == user.id).first()
        user.first_name = user.first_name
        user.last_name = user.last_name
        user.full_name = user.full_name
        user.modified_date = datetime.datetime.now()
        db_sess.commit()
    else:
        add_user(user)


def get_user_rating(user):
    db_sess = db_session.create_session()
    update_user(user)
    all_chats_connections = db_sess.query(UserInChat).filter(UserInChat.user_id == user.id).all()
    res = {
        'played_games': 0,
        'wins': 0,
        'chat_games': []
    }

    for chat_connection in all_chats_connections:
        chat = db_sess.query(Chat).filter(Chat.id == chat_connection.chat_id).first()
        res['chat_games'].append({
            "id": chat.id,
            "title": chat.title,
            "modified_date": chat.modified_date,
            "played_games": chat_connection.played_games,
            "wins": chat_connection.wins
        })
        res['played_games'] += chat_connection.played_games
        res['wins'] += chat_connection.wins

    return res

def get_users_in_chat_rating(chat):
    db_sess = db_session.create_session()
    all_chat_connections = db_sess.query(UserInChat).filter(UserInChat.chat_id == chat.id).all()
    res = []

    for chat_connection in all_chat_connections:
        user = db_sess.query(User).filter(User.id == chat_connection.user_id).first()
        res.append({
            'played_games': chat_connection.played_games,
            'wins': chat_connection.wins,
            'user': user
        })
    return res

def raise_user_rating(user, chat, is_wined):
    db_sess = db_session.create_session()
    update_user(user)
    connection = db_sess.query(UserInChat).filter(UserInChat.user_id == user.id, UserInChat.chat_id == chat.id).first()
    connection.played_games += 1
    connection.wins += int(is_wined)
    db_sess.commit()
