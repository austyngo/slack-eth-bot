import requests
from web3 import Web3
import json
import os
from dotenv import load_dotenv

load_dotenv()

config = json.loads(open('config.json', 'r').read())
poolConfig = json.loads(open('poolConfig.json', 'r').read())

api_url = os.environ.get('WEB3_API')
wethAddress = config['WETH_ADDRESS']
usdcAddress = config['USDC_ADDRESS']

uni_pool_address = poolConfig["WETH_USDC_POOL_ADDRESS"]
uni_pool_ABI = poolConfig["WETH_USDC_POOL_ABI"]
erc20_abi_url = 'https://unpkg.com/@uniswap/v2-core@1.0.1/build/IERC20.json'
web3 = Web3(Web3.HTTPProvider(api_url))

def get_eth_gas():
    latest = web3.eth.blockNumber
    gas = str(round(int(web3.eth.getBlock(latest)['baseFeePerGas']) / 10 ** 9, 2))
    return gas

def get_eth_balance(address):
    return str(round(int(web3.eth.get_balance(address)) / 10 **18 , 2))

def get_price(exchange):
    latest = web3.eth.blockNumber
    if exchange.lower() == 'uniswap': 
        #load from uniswap smart contract
        pool_contract = web3.eth.contract(address=uni_pool_address, abi=uni_pool_ABI)
    
        slot0 = pool_contract.functions.slot0().call()
        #calculate price
        current_price = 2 ** 192 / slot0[0] ** 2 * 10**12
        return str(round(current_price, 4))
    else:
        raise ValueError("invalid exchange name/not currently supported")

def verify_web_hook(form):
    if not form or form.get('token') != os.environ.get('VERIFICATION_TOKEN'):
        raise ValueError('Invalid request/credentials')


def handle_request(request, response_url):
    command = ""
    valid_command = False

    if (request):
        #grab command item from request - first item after '/ethbot'
        #eg. /ethbot gas
        commandElements = request.split()
        command = commandElements[0]
        params = commandElements[1:]

    if (command == 'gas'):
        valid_command = True
        message = f"Current base fee per gas is {get_eth_gas()} gwei"
    
    #eth balance in a wallet
    #/ethbot balance:<address or ens name>
    elif command.split(':')[0] == 'balance':
        address = command.split(':')[1]
        try:
            message = f"{address} contains: {get_eth_balance(address)} ETH"       
        except:
            message = "Not a valid Ethereum address or ENS name"
        valid_command = True
    
    #get price of eth on different decentralized exchanges
    #/ethbot price:<exchange name>
    #currently only Uniswap
    elif command.split(':')[0] == 'price':
        exchange = command.split(':')[1]
        try:
            message = f"Current ETH/USDC price on {exchange.title()} is {get_price(exchange)}"
        except:
            message = "Invalid exchange name or exchange currently not supported"
        valid_command = True

    else:
        message = f"{command} is not a valid command"
    
    #create response based on result
    target_url = ''
    if valid_command == True:
        target_url = response_url
        slack_data = {
            'response_type': 'in_channel',
            'text': message
        }
    
    else:
        target_url = response_url
        slack_data = {
            'response_type': 'ephemeral',
            'text': message
        }

    response = requests.post(
        target_url, data=json.dumps(slack_data),
        headers = {'Content-Type': 'application/json'}
    )

#entry point
def get_info(request):
    if request.method != 'POST':
        return 'Only POST requests are accepted', 405
    
    verify_web_hook(request.form)
    response_url = request.form.get('response_url')
    print(request.form)

    handle_request(request.form.get('text'), response_url)

    #return empty string to reduce spam
    return ''