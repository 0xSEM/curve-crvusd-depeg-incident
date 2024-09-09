import os
from web3 import Web3
from tabulate import tabulate

controller_ABI = [{"stateMutability": "view", "type": "function", "name": "users_to_liquidate", "inputs": [],
                   "outputs": [{"name": "", "type": "tuple[]",
                                "components": [{"name": "user", "type": "address"},
                                               {"name": "x", "type": "uint256"},
                                               {"name": "y", "type": "uint256"},
                                               {"name": "debt", "type": "uint256"},
                                               {"name": "health", "type": "int256"}]
                                }]
                   },
                  {"stateMutability": "view", "type": "function", "name": "user_state",
                   "inputs": [{"name": "user", "type": "address"}],
                   "outputs": [{"name": "", "type": "uint256[4]"}]
                   }]

sUSDe_ABI = [{"inputs": [{"internalType": "uint256", "name": "shares", "type": "uint256"}],
              "name": "convertToAssets",
              "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
              "stateMutability": "view",
              "type": "function"}]


def run():
    affected_addys = [
        '0x83a59Ce2eF545c019e77c542552eC0f0f58402B6',
        '0x5a34897A6c1607811Ae763350839720c02107682',
        '0xd2BC4e7ECfA4Ec39069623854cD114Dcd8771B84',
        '0x823a1C41fd58cD2718cED091D50de8db9Ab19684',
        '0x5DD596C901987A2b28C38A9C1DfBf86fFFc15d77',
        '0xeA8a444fDCb9Ba3a5673a0D8C79B6C154201F8aA',
        '0x1aF987716159529e4B877B2FCff20EdE364e6341',
        '0xD0B53c43D3E0B58909c38487AA0C3af7DFa2d8C0',
        '0x142CAcA970Db463D0A50170b74e554E391D56Fc4',
        '0x1DD0144f4520E82DF504C1eDE96a218ee5ab5DBd',
    ]

    web3 = Web3(Web3.HTTPProvider(os.getenv('URI')))

    sUSDe = web3.eth.contract(address='0x9D39A5DE30e57443BfF2A8307A4256c8797A3497', abi=sUSDe_ABI)
    crvusd_controller = web3.eth.contract(address='0xB536FEa3a01c95Dd09932440eC802A75410139D6', abi=controller_ABI)

    # Estimated start and endblocks for crvUSD depeg
    STARTBLOCK = 20080100
    ENDBLOCK = 20081600

    liquidate_start = crvusd_controller.functions.users_to_liquidate().call(block_identifier=STARTBLOCK)
    liquidate_end = crvusd_controller.functions.users_to_liquidate().call(block_identifier=ENDBLOCK)

    sUSDe_price_start = sUSDe.functions.convertToAssets(10 ** 18).call(block_identifier=STARTBLOCK) / 10 ** 18
    sUSDe_price_end = sUSDe.functions.convertToAssets(10 ** 18).call(block_identifier=ENDBLOCK) / 10 ** 18

    entries = []

    for addy in affected_addys:
        before = crvusd_controller.functions.user_state(addy).call(
            block_identifier=STARTBLOCK)  # [collateral, stablecoin, dbt, N]
        approx_usde_value_before = before[0] * sUSDe_price_start / 10 ** 18  # Add approx USD value of USDe
        approx_crvusd_value_before = before[2] / 10 ** 18  # approx Position value
        approx_pos_value_before = approx_usde_value_before - approx_crvusd_value_before  # approx Position value

        after = crvusd_controller.functions.user_state(addy).call(block_identifier=ENDBLOCK)
        approx_usde_value_after = after[0] * sUSDe_price_end / 10 ** 18  # Add approx USD value of USDe
        approx_crvusd_value_after = after[2] / 10 ** 18  # approx Position value
        approx_pos_value_after = approx_usde_value_after - approx_crvusd_value_after  # approx Position value

        approx_pos_diff = approx_pos_value_after - approx_pos_value_before
        approx_loss = (min(-approx_pos_diff, approx_pos_value_before))
        entries.append([addy, approx_usde_value_before, approx_crvusd_value_before, approx_pos_value_before,
                        approx_usde_value_after, approx_crvusd_value_after, approx_pos_value_after, approx_pos_diff,
                        approx_loss])

    print(f'startblock: {STARTBLOCK}')
    print(f'endblock: {ENDBLOCK}')
    print(f'liquidatable at startblock: {liquidate_start}')
    print(f'liquidatable at endblock: {liquidate_end}')
    print(f'sUSDe rate startendblock: {sUSDe_price_start}')
    print(f'sUSDe rate endblock: {sUSDe_price_end}')

    print(f'approx total loss: {sum(x[8] for x in entries)}')

    print(tabulate(entries,
                   headers=['address', 'usde_before', 'crvusd_before', 'pos_val_before', 'usde_after', 'crvusd_after',
                            'pos_val_after', 'pos_diff', 'approx_loss']))


if __name__ == '__main__':
    run()
