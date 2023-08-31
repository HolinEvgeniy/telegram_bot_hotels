def history_search(conn, user_id: int) -> list[dict]:
    """
    Функция получения данных из таблицы базы данных sqlite3
    :param conn: объект Connect (соединение с базой данных)
    :param user_id: id пользователя
    :return: список ранее запрашиваемой информации
    """
    cur = conn.cursor()
    cur.execute('SELECT * FROM story;')
    content = cur.fetchall()

    result: list = [i_story for i_story in content if i_story[0] == user_id]
    return result
