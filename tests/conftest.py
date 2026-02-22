"""Pytest configuration and shared fixtures."""

import pytest


@pytest.fixture
def sample_ticket_description():
    return "Здравствуйте. Не могу войти в приложение. Пароль не принимает."


@pytest.fixture
def sample_ticket_description_en():
    return "Hello, I am trying to complete my account verification."


@pytest.fixture
def sample_ticket_description_kz():
    return "Саламатсыздарма, қандай облигация теңгеге алуға болады?"
