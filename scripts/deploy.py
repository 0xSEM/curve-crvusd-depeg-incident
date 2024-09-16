from brownie import accounts, Contract,VestSplitter
import pandas as pd

VESTING_FACTORY = '0xe3997288987E6297Ad550A69B31439504F513267'
CRV = '0xD533a949740bb3306d119CC777fa900bA034cd52'
CRV_PRICE = 0.2846
DESCRIPTION = "Compensation for victims of the June 12th crvUSD de-peg incident"

CURVE_DAO_OWNERSHIP = {
    "agent": "0x40907540d8a6C65c637785e8f8B742ae6b0b9968",
    "voting": "0xE478de485ad2fe566d49342Cbd03E49ed7DB3356",
    "token": "0x5f3b5DfEb7B28CDbD7FAba78963EE202a494e2A2",
    "quorum": 30,
}
# the intended target of the vote, should be one of the above constant dicts
TARGET = CURVE_DAO_OWNERSHIP


def main():
    # sem = accounts.load('sem') # Use this for real run
    sem = accounts.at('0x989AEb4d175e16225E39E87d0D97A3360524AD80', force=True) # Use this for testing

    # Prepare data
    users = []
    fractions = []
    df = pd.read_csv('user_losses.csv', header=None, names=['address', 'loss'])
    user_losses = df.set_index('address')['loss'].to_dict()
    total_losses = sum(user_losses.values()) * 10 ** 18
    crv_amount = total_losses / CRV_PRICE
    for item in user_losses:
        users.append(item)
        fractions.append(user_losses[item] * 10 ** 18)

    # 3 Setup transactions
    vest_splitter = sem.deploy(VestSplitter, CRV)
    vest_splitter.save_distribution(users, fractions, {'from': sem})
    vest_splitter.finalize_distribution({'from': sem})

    # Propose vote to fund the vesting contract
    id = propose_vote(vest_splitter.address, crv_amount, sem)
    print(f'Proposal id: {id} started')

    # Simulate vote to ensure it all works. For testing only. Should comment this out when running on chain.
    simulate_vote(id)


def propose_vote(vest_splitter, crv_amount, sem):
    import json, requests, os
    from dotenv import load_dotenv
    load_dotenv()
    text = json.dumps({"text": DESCRIPTION})
    auth = (os.environ['INFURA_PROJECT_ID'], os.environ['INFURA_PROJECT_SECRET'])
    response = requests.post("https://ipfs.infura.io:5001/api/v0/add", files={"file": text}, auth=auth)
    ipfs_hash = response.json()["Hash"]
    print(f"ipfs hash: {ipfs_hash}")

    aragon = Contract(TARGET["voting"])
    evm_script = prepare_evm_script(vest_splitter, crv_amount)
    tx = aragon.newVote(evm_script, f'ipfs:{ipfs_hash}', False, False, {'from': sem})
    return tx.events['StartVote']['voteId']

def prepare_evm_script(vest_splitter, crv_amount):
    agent = Contract(TARGET["agent"])
    evm_script = "0x00000001"

    # ("target", "fn_name", *args),
    # gauge controller, ...
    ACTIONS = [
        (
            VESTING_FACTORY, # Vesting Factory
            'deploy_vesting_contract', 
            CRV, # token
            vest_splitter,  # splitter
            crv_amount,   # crv amount
            True,
            86400 * 365, # Min vesting duration
        )
    ]

    for address, fn_name, *args in ACTIONS:
        contract = Contract(address)
        fn = getattr(contract, fn_name)
        calldata = fn.encode_input(*args)
        agent_calldata = agent.execute.encode_input(address, 0, calldata)[2:]
        length = hex(len(agent_calldata) // 2)[2:].zfill(8)
        evm_script = f"{evm_script}{agent.address[2:]}{length}{agent_calldata}"

    return evm_script

def simulate_vote(id):
    from brownie import chain
    convex = '0x989AEb4d175e16225E39E87d0D97A3360524AD80'
    aragon = Contract(TARGET["voting"])
    aragon.vote(id, True, False,{'from': convex})
    chain.sleep(86400 * 7)
    chain.mine()
    tx = aragon.executeVote(id, {'from':convex})

    assert 'Fund' in tx.events