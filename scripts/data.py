import pandas as pd
from brownie import Contract, VestSplitter

# Estimated start and endblocks for crvUSD depeg
DEPLOY_BLOCK = 19999153
START_BLOCK = 20080100
END_BLOCK = 20081600
crvusd_controller = Contract('0xB536FEa3a01c95Dd09932440eC802A75410139D6')
susde = Contract('0x9D39A5DE30e57443BfF2A8307A4256c8797A3497')

def main():
    losses = compute_losses()

def get_affected_users():
    logs = crvusd_controller.events.Borrow.get_logs(fromBlock=DEPLOY_BLOCK, toBlock=END_BLOCK)
    users = set()
    for log in logs:
        user = log.args['user']
        debt = crvusd_controller.user_state(user, block_identifier=START_BLOCK)[2]
        if debt == 0:
            continue
        users.add(user)

    print(f'{len(users)} users found')
    return list(users)

def compute_losses():
    # Fetch sUSDe conversion rates at start and end blocks
    pps_start = susde.convertToAssets(10 ** 18, block_identifier=START_BLOCK) / 10 ** 18
    pps_end = susde.convertToAssets(10 ** 18, block_identifier=END_BLOCK) / 10 ** 18

    loss_data = []
    affected_users = get_affected_users()

    for user in affected_users:
        # Fetch user state at start block
        before = crvusd_controller.user_state(user, block_identifier=START_BLOCK)
        approx_usde_value_before = before[0] * pps_start / 10 ** 18
        approx_crvusd_value_before = before[2] / 10 ** 18
        approx_pos_value_before = approx_usde_value_before - approx_crvusd_value_before

        # Fetch user state at end block
        after = crvusd_controller.user_state(user, block_identifier=END_BLOCK)
        approx_usde_value_after = after[0] * pps_end / 10 ** 18
        approx_crvusd_value_after = after[2] / 10 ** 18
        approx_pos_value_after = approx_usde_value_after - approx_crvusd_value_after

        # Calculate diffs
        approx_pos_diff = approx_pos_value_after - approx_pos_value_before
        approx_loss = min(-approx_pos_diff, approx_pos_value_before)

        loss_data.append({
            'user': user,
            'usde_before': approx_usde_value_before,
            'crvusd_before': approx_crvusd_value_before,
            'pos_val_before': approx_pos_value_before,
            'usde_after': approx_usde_value_after,
            'crvusd_after': approx_crvusd_value_after,
            'pos_val_after': approx_pos_value_after,
            'pos_diff': approx_pos_diff,
            'approx_loss': approx_loss
        })


    df = pd.DataFrame(loss_data)
    print(f'approx total loss: {df["approx_loss"].sum()}')
    print(df)

    # Trim to only include users with losses > 0
    return {data['user']: data['approx_loss'] for data in loss_data if data['approx_loss'] > 0}

if __name__ == "__main__":
    compute_losses()