# Example network config

#   └─matic-mainnet-3
#     ├─id: matic-mainnet-3
#     ├─chainid: 137
#     ├─explorer: https://api.polygonscan.com/api
#     ├─host: https://rpc-mainnet.maticvigil.com/v1/d6a3821ed91d7b17244f01163673599ce95fc0fc
#     └─timeout: 10

# To get into a shell to play with this code 

# export POLYGONSCAN_TOKEN=G1X5SQKMHU62NY4D7DIRASHYXI5NPWCCVU
# brownie console --network=matic-mainnet-3


from urllib.request import urlopen as req
import json

def getPrice(coin):
  url = "https://api.coingecko.com/api/v3/simple/price?ids=%s&vs_currencies=usd" % coin
  with req(url) as f:
    resp = json.load(f)
  return resp[coin]['usd']

def getLimitInTokens(limit, coin):
  price = getPrice(coin)
  return limit / price

def genLimits(muls):
  onem = 1_000_000
  limits = onem 
  limits = {
    # no change for stables
    'usdc': onem * muls['usdc'],
    'dai': onem * muls['dai'],
    'usdt': onem * muls['usdt'],
    'weth': getLimitInTokens(onem, 'ethereum') * muls['weth'],
    'wbtc': getLimitInTokens(onem, 'bitcoin') * muls['wbtc'],
    'wmatic': getLimitInTokens(onem, 'matic-network') * muls['wmatic'],
  }
  return limits

acct = accounts.load('cocodeployer')

from brownie.network.gas.strategies import LinearScalingStrategy
opts = {'from': acct, 'gas_price': LinearScalingStrategy("40 gwei", "150 gwei", 1.1, time_duration=10)}


# USEFUL GLOBAL CONSTANTS
usdc = '0x2791bca1f2de4661ed88a30c99a7a9449aa84174'
dai = '0x8f3cf7ad23cd3cadbd9735aff958023239c6a063'
weth = '0x7ceb23fd6bc0add59e62ac25578270cff1b9f619'
wbtc = '0x1bfd67037b42cf73acf2047067bd4f2c47d9bfd6'
wmatic = '0x0d500b1d8e8ef31e21c99d1db9a6444d3adf1270'
usdt = '0xc2132d05d31c914a87c6611c10748aeb04b58e8f'

icmatic = '0xca0f37f73174a28a64552d426590d3ed601ecca1'

matic_quickswap_router = '0xa5E0829CaCEd8fFDD4De3c43696c57F7D7A678ff'



# DEFAULTS WE HAVE DEPLOYED
registry = Registry.at('0xAa5893679788E1FAE460Ae6A96791a712FDC474F')
# TODO VERIFy the 2 foll.
GLYO = MaticStrategy.at('0x0509A73a3055a050E162f5c4c6af495D3183b3fB')
lender = GenericAaveMatic.at('0x8359C2aF49d654E30Cfe373a3D322440D5dACE67')
multisig = '0x28973e7886e07CCD8e7eD95671CE7FAFeEb5157d'
gelato_keepers = '0x527a819db1eb0e34426297b03bae11F2f8B3A19E'
stratFacade = '0xB31929bEC89Ba33A977147e223020Dd4b3b821e1'



governance = acct.address # launch vaults with self as gov for easy setup then convert ^
gaurdian = acct.address
rewards = acct.address

# DEFAULT LAUNCH ARGS FROM US
debtRatio = 10000  # this is max / 100% or 10k in BPS. for more strats, set this properly
minDebtPerHarvest = 0
# Hmm.. max uint256
maxDebtPerHarvest = "115792089237316195423570985008687907853269984665640564039457584007913129639935"
performanceFee = 1000 # 1% perf fee to strategist to start
vaultMgmtFee = 0 # set vault mgmt to 0
one_mill = 1000000
limit_muls = {
  'usdc': 1e6,
  'usdt': 1e6,
  'dai': 1e18,
  # 'weth': 0.00025*1e18,
  # 'wbtc': (1/60000)*1e8,
  # 'wmatic': (1/1.5)*1e18
  'weth': 1e18,
  'wbtc': 1e8,
  'wmatic': 1e18
}
intokens = {
  'usdc': usdc,
  'usdt': usdt,
  'dai': dai,
  'wbtc': wbtc,
  'wmatic': wmatic,
  'weth': weth
}

limits = genLimits(limit_muls)




res_vaults = {}
res_strats = {}
res_lenders = {}

def deployVault(name):
  vault_name = '%s-vault' % name
  vaultsym = 'ac%s' % name
  txn_receipt = registry.newExperimentalVault(intokens[name], governance, gaurdian, rewards, vault_name, vaultsym, opts)
  vault = Vault.at(txn_receipt.events["NewExperimentalVault"]["vault"])

  res_vaults[name] = vault
  return vault

def postDeploy(name):
  # We petrify the vault a bit but changing it to owned by gov/multisig
  vault = res_vaults[name]
  vault.setDepositLimit(limits[name], opts)
  vault.setManagementFee(vaultMgmtFee, opts)
  vault.setManagement(multisig, opts)
  linkedStrat = res_strats[name]


def cloneGLYO(name):
  vault = res_vaults[name]
  txn_receipt = GLYO.clone(vault.address, opts)
  thisGLYO = MaticStrategy.at(txn_receipt.events["Cloned"]["clone"])
  res_strats[name] = thisGLYO

def cloneLender(name):
  strat = res_strats[name]
  lenderName = 'AAVELender-%s' % name
  txn_receipt = lender.cloneAaveLender(strat, name, _isIncentivized)
  thisLender = GenericAaveMultichain.at(txn_receipt.events["Cloned"]["clone"])
  res_lenders[name] = thisLender


# example deploy
# 1. Clone a vault with your token
# 2. Clone GenericLenderYieldOptimizer - this is the strat that deploys funds to lender contracts and optimizes
# 3. Clone the AAVELender 
# 4. Create dummy base contract if any of the above do not exist

for name, _ in intokens.items():
  deployVault(name)
  cloneGLYO(name)
  cloneLender(name)
  postDeploy(name)

print(res_vaults)
print(res_strats)
print(res_lenders)


# TODO CLEAN UP
def deployLender(name):
  strat = res_strats[name]
  name = '%s-AAVELender' % name
  _weth = wmatic
  _rewardsTokenToSell = wmatic
  _router = matic_quickswap_router
  isIncentivised = False
  lender = GenericAaveMultichain.deploy(
    strat,
    name,
    _weth,
    _rewardsTokenToSell,
    _router,
    isIncentivised,
    opts,
    publish_source=True
  )
  return lender



def deployGLYO(name):
  deployVault(name)
  vault = res_vaults[name]
  strat = MaticStrategy.deploy(vault.address, opts, publish_source=True)
  res_strats[name] = strat


def deployGLYO(name):
  deployVault(name)
  vault = res_vaults[name]

  # vault_name = '%s-vault' % name
  # vaultsym = 'ac%s' % name
  # txn_receipt = registry.newExperimentalVault(intokens[name], governance, gaurdian, rewards, vault_name, vaultsym, opts)
  # vault = Vault.at(txn_receipt.events["NewExperimentalVault"]["vault"])

  # res_vaults[name] = vault

  strat = MaticStrategy.deploy(vault.address, opts, publish_source=True)
  res_strats[name] = strat

  tx = vault.addStrategy(
    strat.address,
    debtRatio,
    minDebtPerHarvest,
    maxDebtPerHarvest,
    performanceFee, opts
  )
  vault.setDepositLimit(one_mill * limit_muls[name], opts)

  sf.addStrategy(strat.address, opts)
  strat.setKeeper(sf.address, opts)

return
# First deploy - todo rm 
v = '0x42c526eB3A6Dbd8b651DE4c8711C5faD71913678'
strat = MaticStrategy.deploy(v, opts, publish_source=True)

strat = MaticStrategy.deploy(vault.address, opts, publish_source=True)


lender = GenericAaveMatic.deploy(
  GLYO.address,
  'dummy clone base',
  False,
  opts,
  publish_source=True
)
