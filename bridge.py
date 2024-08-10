from web3 import Web3
from web3.contract import Contract
from web3.providers.rpc import HTTPProvider
from web3.middleware import geth_poa_middleware
import json
import sys
from pathlib import Path

source_chain = 'avax'
destination_chain = 'bsc'
contract_info = "contract_info.json"

def connectTo(chain):
    if chain == 'avax':
        api_url = "https://api.avax-test.network/ext/bc/C/rpc"
    elif chain == 'bsc':
        api_url = "https://data-seed-prebsc-1-s1.binance.org:8545/"
    else:
        print(f"Invalid chain: {chain}")
        sys.exit(1)
    
    w3 = Web3(Web3.HTTPProvider(api_url))
    w3.middleware_onion.inject(geth_poa_middleware, layer=0)
    return w3

def getContractInfo(chain):
    p = Path(__file__).with_name(contract_info)
    try:
        with p.open('r') as f:
            contracts = json.load(f)
    except Exception as e:
        print("Failed to read contract info")
        print("Please contact your instructor")
        print(e)
        sys.exit(1)
    
    if chain in contracts:
        return contracts[chain]
    else:
        print(f"Chain {chain} not found in contract_info.json")
        sys.exit(1)

def scanBlocks(chain):
    if chain not in ['avax', 'bsc']:
        print(f"Invalid chain: {chain}")
        return

    contracts = getContractInfo(chain)
    w3 = connectTo(chain)

    contract = w3.eth.contract(address=contracts['address'], abi=contracts['abi'])

    latest_block = w3.eth.block_number
    for block_num in range(latest_block - 5, latest_block + 1):
        block = w3.eth.get_block(block_num, full_transactions=True)
        for tx in block.transactions:
            receipt = w3.eth.get_transaction_receipt(tx.hash)

            logs = contract.events.Deposit().processReceipt(receipt)
            for log in logs:
                if chain == 'avax':
                    destination_contracts = getContractInfo('bsc')
                    destination_w3 = connectTo('bsc')
                    destination_contract = destination_w3.eth.contract(
                        address=destination_contracts['address'],
                        abi=destination_contracts['abi']
                    )
                    destination_contract.functions.wrap(
                        log['args']['token'],
                        log['args']['recipient'],
                        log['args']['amount']
                    ).transact({'from': w3.eth.default_account})
                    print(f"Deposit event found in block {block_num}, called wrap() on destination")

            logs = contract.events.Unwrap().processReceipt(receipt)
            for log in logs:
                if chain == 'bsc':
                    source_contracts = getContractInfo('avax')
                    source_w3 = connectTo('avax')
                    source_contract = source_w3.eth.contract(
                        address=source_contracts['address'],
                        abi=source_contracts['abi']
                    )
                    source_contract.functions.withdraw(
                        log['args']['token'],
                        log['args']['recipient'],
                        log['args']['amount']
                    ).transact({'from': w3.eth.default_account})
                    print(f"Unwrap event found in block {block_num}, called withdraw() on source")

if __name__ == "__main__":
    scanBlocks('avax')
    scanBlocks('bsc')

