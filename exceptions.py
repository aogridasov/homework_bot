class ApiIsNotRespondingError(Exception):
    """Вызываем когда API недоступен."""

    pass


class ApiAnswerIsIncorrectError(Exception):
    """Вызываем когда ответ API не соответствует ожидаемому."""

    pass


class HomeworkStatusIsInvalidError(Exception):
    """Вызываем когда статус из ответа API нестандартен."""

    pass
