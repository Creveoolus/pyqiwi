# -*- coding: utf-8 -*-
"""
Python Qiwi API Wrapper 2.1
by mostm

See pyQiwi Documentation: pyqiwi.readthedocs.io
"""
import datetime
from functools import partial
from urllib.parse import urlencode

from . import apihelper, types, util

proxyy = {}
class Wallet:
    """
    Visa QIWI Кошелек

    Parameters
    ----------
    token : str
        `Ключ Qiwi API`_ пользователя.
    number : Optional[str]
        Номер для указанного кошелька.
        По умолчанию - ``None``.
        Если не указан, статистика и история работать не будет.
    contract_info : Optional[bool]
        Логический признак выгрузки данных о кошельке пользователя.
        По умолчанию - ``True``.
    auth_info : Optional[bool]
        Логический признак выгрузки настроек авторизации пользователя.
        По умолчанию - ``True``.
    user_info : Optional[bool]
        Логический признак выгрузки прочих пользовательских данных.
        По умолчанию - ``True``.
    proxy : Optional[list]
        Логический признак выгрузки прочих пользовательских данных.
        По умолчанию - ``None``.

    Attributes
    -----------
    accounts : iterable of :class:`Account <pyqiwi.types.Account>`
        Все доступные счета на кошельке.
        Использовать можно только рублевый Visa QIWI Wallet.
    profile : :class:`Profile <pyqiwi.types.Profile>`
        Профиль пользователя.
    offered_accounts : iterable of :class:`Account <pyqiwi.types.Account>`
        Доступные счета для создания
    """

    def __str__(self):
        return '<Wallet(number={0}, token={1})>'.format(self.number, self.token)

    @property
    def accounts(self):
        result_json = apihelper.funding_sources(self.token, proxy=self.proxy)
        accounts = []
        for account in result_json['accounts']:
            accounts.append(types.Account.de_json(account))
        return accounts

    @property
    def cross_rates(self):
        """
        Курсы валют QIWI Кошелька

        Returns
        -------
        list
            Состоит из:
            :class:`Rate <pyqiwi.types.Rate>` - Курса.
        """
        result_json = apihelper.cross_rates(self.token, proxy=self.proxy)
        rates = []
        for rate in result_json['result']:
            rates.append(types.Rate.de_json(rate))
        return rates

    def balance(self, currency=643):
        """
        Баланс Visa QIWI Кошелька

        Parameters
        ----------
        currency : int
            ID валюты в ``number-3 ISO-4217``.
            Например, ``643`` для российского рубля.

        Returns
        -------
        float
            Баланс кошелька.

        Raises
        ------
        ValueError
            Во всех добавленных вариантах оплаты с указанного Qiwi-кошелька нет информации об балансе и его сумме.
            Скорее всего это временная ошибка Qiwi API, и вам стоит попробовать позже.
            Так же, эта ошибка может быть вызвана только-что зарегистрированным Qiwi-кошельком,
             либо довольно старым Qiwi-кошельком, которому необходимо изменение пароля.
        """
        for account in self.accounts:
            if account.currency == currency and account.balance and account.balance.get('amount'):
                return account.balance.get('amount')
        raise ValueError("There is no Payment Account that has balance and amount on it."
                         " Maybe this is temporary Qiwi API error, you should try again later."
                         " Also, this error can be caused by just registered Qiwi Account or "
                         "really old Qiwi Account that needs password change.")

    @property
    def profile(self):
        result_json = apihelper.person_profile(self.token, self.auth_info_enabled,
                                               self.contract_info_enabled, self.user_info_enabled, proxy=self.proxy)
        return types.Profile.de_json(result_json)

    def history(self, rows=20, operation=None, start_date=None, end_date=None, sources=None, next_txn_date=None,
                next_txn_id=None):
        """
        История платежей

        Warning
        -------
        Максимальная интенсивность запросов истории платежей - не более 100 запросов в минуту
         для одного и того же номера кошелька.
        При превышении доступ к API блокируется на 5 минут.

        Parameters
        ----------
        rows : Optional[int]
            Число платежей в ответе, для разбивки отчета на части.
            От 1 до 50, по умолчанию 20.
        operation : Optional[str]
            Тип операций в отчете, для отбора.
            Варианты: ALL, IN, OUT, QIWI_CARD.
            По умолчанию - ALL.
        start_date : Optional[datetime.datetime]
            Начальная дата поиска платежей.
        end_date : Optional[datetime.datetime]
            Конечная дата поиска платежей.
        sources : Optional[list]
            Источники платежа, для отбора.
            Варианты: QW_RUB, QW_USD, QW_EUR, CARD, MK.
            По умолчанию - все указанные.
        next_txn_date : Optional[datetime.datetime]
            Дата транзакции для отсчета от предыдущего списка (равна параметру nextTxnDate в предыдущем списке).
        next_txn_id : Optional[int]
            Номер предшествующей транзакции для отсчета от предыдущего списка
            (равен параметру nextTxnId в предыдущем списке).

        Note
        ----
        Если вы хотите использовать start_date или end_date, вы должны указать оба параметра.
        Такое же использование и у next_txn_date и next_txn_id.
        Максимальный допустимый интервал между start_date и end_date - 90 календарных дней.

        Returns
        -------
        dict
            Состоит из:
            transactions[list[:class:`Transaction <pyqiwi.types.Transaction>`]] - Транзакции.
            next_txn_date[datetime.datetime] - Дата транзакции(для использования в следующем использовании).
            next_txn_id[int] - Номер транзакции.
        """
        result_json = apihelper.payment_history(self.token, self.number, rows, operation=operation,
                                                start_date=start_date, end_date=end_date, sources=sources,
                                                next_txn_date=next_txn_date, next_txn_id=next_txn_id, proxy=self.proxy)
        transactions = []
        for transaction in result_json['data']:
            transactions.append(types.Transaction.de_json(transaction))
        ntd = None
        if result_json.get("nextTxnDate") is not None:
            ntd = types.JsonDeserializable.decode_date(result_json.get("nextTxnDate"))
        return {"transactions": transactions,
                "next_txn_date": ntd,
                "next_txn_id": result_json.get('nextTxnId')}

    def transaction(self, txn_id, txn_type):
        """
        Получение транзакции из Qiwi API

        Parameters
        ----------
        txn_id : str
            ID транзакции.
        txn_type : str
            Тип транзакции (IN/OUT/QIWI_CARD).

        Returns
        -------
        :class:`Transaction <pyqiwi.types.Transaction>`
            Транзакция
        """
        result_json = apihelper.get_transaction(self.token, txn_id, txn_type, proxy=self.proxy)
        return types.Transaction.de_json(result_json)

    def stat(self, start_date=None, end_date=None, operation=None, sources=None):
        """
        Статистика платежей

        Note
        ----
        Изначально берется статистика с начала месяца

        Parameters
        ----------
        operation : Optional[str]
            Тип операций в отчете, для отбора.
            Варианты: ALL, IN, OUT, QIWI_CARD.
            По умолчанию - ALL.
        start_date : Optional[datetime.datetime]
            Начальная дата поиска платежей.
        end_date : Optional[datetime.datetime]
            Конечная дата поиска платежей.
        sources : Optional[list]
            Источники платежа, для отбора.
            Варианты: QW_RUB, QW_USD, QW_EUR, CARD, MK.
            По умолчанию - все указанные.

        Returns
        -------
        :class:`Statistics <pyqiwi.types.Statistics>`
            Статистика
        """
        if start_date:
            pass
        else:
            start_date = datetime.datetime.utcnow()
            start_date = start_date.replace(day=1, hour=0, minute=0, second=1)
        if end_date:
            pass
        else:
            end_date = datetime.datetime.utcnow()
        result_json = apihelper.total_payment_history(self.token, self.number, start_date, end_date,
                                                      operation=operation, sources=sources, proxy=self.proxy)
        return types.Statistics.de_json(result_json)

    def commission(self, pid, recipient, amount):
        """
        Расчет комиссии для платежа

        Parameters
        ----------
        pid : str
            Идентификатор провайдера.
        recipient : str
            Номер телефона (с международным префиксом) или номер карты/счета получателя.
            В зависимости от провайдера.
        amount : float/int
            Сумма платежа.
            Положительное число, округленное до 2 знаков после десятичной точки.
            При большем числе знаков значение будет округлено до копеек в меньшую сторону.

        Returns
        -------
        :class:`OnlineCommission <pyqiwi.types.OnlineCommission>`
            Комиссия для платежа
        """
        result_json = apihelper.online_commission(self.token, recipient, pid, amount, proxy=self.proxy)
        return types.OnlineCommission.de_json(result_json)

    def send(self, pid, recipient, amount, comment=None, fields=None):
        """
        Отправить платеж

        Parameters
        ----------
        pid : str
            Идентификатор провайдера.
        recipient : str
            Номер телефона (с международным префиксом) или номер карты/счета получателя.
            В зависимости от провайдера.
        amount : float/int
            Сумма платежа.
            Положительное число, округленное до 2 знаков после десятичной точки.
            При большем числе знаков значение будет округлено до копеек в меньшую сторону.
        comment : Optional[str]
            Комментарий к платежу.
        fields : dict
            Ручное добавление dict'а в платежи.
            Требуется для специфичных платежей.
            Например, перевод на счет в банке.

        Returns
        -------
        :class:`Payment <pyqiwi.types.Payment>`
            Платеж
        """
        result_json = apihelper.payments(self.token, pid, amount, recipient, comment=comment, fields=fields, proxy=self.proxy)
        return types.Payment.de_json(result_json)

    def identification(self, birth_date, first_name, middle_name, last_name, passport, inn=None, snils=None, oms=None):
        """
        Идентификация пользователя

        Данный запрос позволяет отправить данные для упрощенной идентификации своего QIWI кошелька.

        Warnings
        --------
        Данный метод не тестируется, соответственно я не могу гарантировать того что он будет работать как должен.
        Вы делаете это на свой страх и риск.

        Parameters
        ----------
        birth_date : str
            Дата рождения пользователя (в формате “ГГГГ-ММ-ДД”)
        first_name : str
            Имя пользователя
        middle_name : str
            Отчество пользователя
        last_name : str
            Фамилия пользователя
        passport : str
            Серия и номер паспорта пользователя (только цифры)
        inn : str
            ИНН пользователя
        snils : str
            Номер СНИЛС пользователя
        oms : str
            Номер полиса ОМС пользователя

        Returns
        -------
        :class:`Identity <pyqiwi.types.Identity>`
            Текущая идентификация пользователя.
            Параметр внутри отвечающий за подтверждение успешной идентификации: Identity.check
        """
        result_json = apihelper.identification(self.token, self.number, birth_date, first_name, middle_name, last_name,
                                               passport, inn, snils, oms, proxy=self.proxy)
        result_json['base_inn'] = inn
        return types.Identity.de_json(result_json)

    def create_account(self, account_alias):
        """
        Создание счета-баланса в Visa QIWI Wallet

        Parameters
        ----------
        account_alias : str
            Псевдоним нового счета.
            Один из доступных в Wallet.offered_accounts.

        Returns
        -------
        bool
            Был ли успешно создан счет?
        """
        created = apihelper.create_account(self.token, self.number, account_alias, proxy=self.proxy)
        return created

    @property
    def offered_accounts(self):
        result_json = apihelper.get_accounts_offer(self.token, self.number, proxy=self.proxy)
        accounts = []
        for account in result_json:
            accounts.append(types.Account.de_json(account))
        return accounts

    def cheque(self, txn_id, txn_type, file_format='PDF', email=None):
        """
        Получение чека по транзакции, на E-Mail или файл.

        Parameters
        ----------
        txn_id : int
            ID транзакции
        txn_type : str
            Тип указанной транзакции
        file_format : str
            Формат файла(игнорируется при использовании email)
        email : str
            E-Mail, куда отправить чек, если это необходимо.
        Returns
        -------
        binary
            ??? | Прямой возврат ответа от Qiwi API
        """
        if email:
            return apihelper.cheque_send(self.token, txn_id, txn_type, email, proxy=self.proxy)
        else:
            return apihelper.cheque_file(self.token, txn_id, txn_type, file_format, proxy=self.proxy)

    def qiwi_transfer(self, account, amount, comment=None):
        """
        Перевод на Qiwi Кошелек

        Parameters
        ----------
        account : str
            Номер Qiwi Кошелька
        amount : float
            Сумма перевода
        comment : str
            Комментарий

        Returns
        -------
        :class:`Payment <pyqiwi.types.Payment>`
            Платеж
        """
        return self.send("99", account, amount, comment=comment)

    def mobile(self, account, amount):
        """
        Оплата мобильной связи.

        Parameters
        ----------
        account : str
            Номер мобильного телефона (с кодом страны, 7/8, без +)
        amount : float
            Сумма платежа

        Returns
        -------
        :class:`Payment <pyqiwi.types.Payment>`
            Платеж

        Raises
        ------
        ValueError
            В случае, если не удалось определить провайдера.
        """
        pid = detect_mobile(account)
        if pid:
            return self.send(pid, account[1:], amount)
        else:
            raise ValueError("Не удалось определить провайдера!")

    def __init__(self, token, number=None, contract_info=True, auth_info=True, user_info=True, proxy=None):
        if isinstance(number, str):
            self.number = number.replace('+', '')
            if self.number.startswith('8'):
                self.number = '7' + self.number[1:]
        self.token = token
        self.auth_info_enabled = auth_info
        self.contract_info_enabled = contract_info
        self.user_info_enabled = user_info
        self.proxy = proxy
        proxyy = proxy
        self.get_commission = partial(get_commission, self.token)
        self.headers = {'Accept': 'application/json',
                        'Content-Type': 'application/json',
                        'Authorization': "Bearer {0}".format(self.token)}
        if self.contract_info_enabled:
            self.number = str(self.profile.contract_info.contract_id)


def get_commission(token, pid):
    """
    Получение стандартной комиссии

    Parameters
    ----------
    token : str
        `Ключ Qiwi API`_
    pid : str
        Идентификатор провайдера.

    Returns
    -------
    :class:`Commission <pyqiwi.types.Commission>`
        Комиссия для платежа
    """
    result_json = apihelper.local_commission(token, pid, proxy=proxyy)
    return types.Commission.de_json(result_json)


def generate_form_link(pid, account, amount, comment, blocked=None, account_type=None):
    """
    Создание автозаполненной платежной формы

    Parameters
    ----------
    pid : str
        ID провайдера
    account : str
        Счет получателя
    amount : float
        Сумма платежа
    comment : str
        Комментарий
    blocked : list[str]
        Список из значений "заблокированных" (не изменяемых на веб-странице) полей внутри ссылки.
        Варианты: sum, account, comment
    account_type : int or str
        Отвечает за вариант перевода при pid=99999 (вариация перевода на Qiwi Кошелек)
        Варианты: 0 (перевод по номеру телефона, phone), 1 (перевод по "никнейму", nickname),
         str (сами впишите вариант по соответствию с Qiwi API)

    Note
    ----
    Комментарий применяется только при переводе на Qiwi Кошелек по номеру (pid==99)
    Сумма платежа не может быть более 99999 из-за ограничений на один платеж.
    Тип счета для перевода на Qiwi Кошелек (pid=99999) с возможностью ввода "nickname" выбирается в account_type

    Returns
    -------
    str
        Ссылка

    Raises
    ------
    ValueError
        amount>99999 или список blocked неверен
    """
    url = "https://qiwi.com/payment/form/{0}".format(pid)
    params = {"currency": 643}
    params = util.merge_dicts(params, util.split_float(amount))
    if amount > 99999:
        raise ValueError('amount не может превышать 99999 из-за ограничений на один платеж внутри QIWI')
    if pid == "99" and comment:
        params["extra['comment']"] = comment
    if account:
        params["extra['account']"] = account
    if type(blocked) == list and len(blocked) > 0:
        for entry in blocked:
            if entry not in ['sum', 'account', 'comment']:
                raise ValueError('Заблокированное значение может быть только sum, account или comment')
        params = util.sources_list(blocked, params, name='blocked')
    if pid == "99999" and account_type == 0:
        params["extra['accountType']"] = 'phone'
    elif pid == "99999" and account_type == 1:
        params["extra['accountType']"] = 'nickname'
    elif pid == "99999" and type(account_type) == str:
        params["extra['accountType']"] = account_type

    encoded_params = urlencode(params)

    return url + '?' + encoded_params


def detect_mobile(phone):
    """
    Определение провайдера мобильного телефона

    Parameters
    ----------
    phone : str
        Номер телефона

    Returns
    -------
    str
        ID провайдера
    """
    return apihelper.detect(phone, proxy=proxyy)
