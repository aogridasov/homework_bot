class ApiIsNotRespondingException(Exception):
    """Вызываем когда API недоступен."""

    pass


class ApiAnswerIsIncorrectException(Exception):
    """Вызываем когда ответ API не соответствует ожидаемому."""

    pass
