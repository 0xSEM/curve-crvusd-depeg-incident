import brownie
from brownie import Contract, chain, ZERO_ADDRESS
import pytest

CRV_PRICE = 0.2846 # Price taken from governance proposal here: https://gov.curve.fi/t/curve-grant-compensation-for-affected-users-of-the-june-12th-crvusd-de-peg-incident/10182

def test_ops(admin, factory, vest_splitter, dev, crv, user_losses):
    # Loss data
    total_losses = sum(user_losses.values()) * 10 ** 18
    crv_amount = total_losses / CRV_PRICE

    users = []
    fractions = []
    for item in user_losses:
        users.append(item)
        fractions.append(user_losses[item] * 10 ** 18)

    # Deploy vesting contract
    tx = factory.deploy_vesting_contract(
        crv,
        vest_splitter,
        crv_amount,
        True,
        86400 * 365, # Min vesting duration
        {'from': admin}
    )

    new_vest = tx.return_value
    vest_splitter.set_vest(new_vest, {'from': dev})
    with brownie.reverts():
        vest_splitter.set_vest(ZERO_ADDRESS, {'from': dev})
    vest_splitter.set_vest(new_vest, {'from': admin})
    vest_splitter.save_distribution(users, fractions, {'from': dev})
    vest_splitter.finalize_distribution({'from': dev})

    claims = {}

    chain.sleep(86400 * 365)
    chain.mine()

    for user in users:
        user_fraction = vest_splitter.fractions(user) / vest_splitter.total_fraction()
        tx = vest_splitter.claim({'from': user})
        amount = tx.events['Claim'][1]['claimed'] # 2 claim events fire. we want the second one, from the splitter.
        if user not in claims:
            claims[user] = amount
        else:
            claims[user] += amount
        print(f'{user} fraction: {user_fraction*100:.2f}% | Claimed: {amount}')

    print(claims)