from brownie import accounts, Contract, VestSplitter
import pytest
import pandas as pd

@pytest.fixture(scope='session')
def dev():
    yield accounts[0]


@pytest.fixture(scope='session')
def crv():
    yield Contract('0xD533a949740bb3306d119CC777fa900bA034cd52')


@pytest.fixture(scope='session')
def admin():
    yield accounts.at('0x40907540d8a6C65c637785e8f8B742ae6b0b9968', force=True)


@pytest.fixture(scope='session')
def factory():
    yield Contract('0xe3997288987E6297Ad550A69B31439504F513267')


@pytest.fixture(scope='session')
def vest_splitter(dev, crv):
    yield dev.deploy(VestSplitter, crv)


@pytest.fixture(scope='session')
def user_losses():
    df = pd.read_csv('user_losses.csv', header=None, names=['address', 'loss'])
    # Convert to dict
    yield df.set_index('address')['loss'].to_dict()

