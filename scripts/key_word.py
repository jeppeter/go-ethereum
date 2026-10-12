

PASSWORD_KEYWORD = 'PASSWORD.KEY'
ADDRESS_KEYWORD = 'address'
GENESIS_CONFIG = 'config'
GENESIS_CHAINID = 'chainId'
GENESIS_ALLOC = 'alloc'
GENESIS_BLANCE = 'balance'

NODE_DATADIR_KEYWORD = 'Node.DataDir'
NODE_IPCPATH_KEYWORD = 'Node.IPCPath'
NODE_JWTSECRET_KEYWORD = 'Node.JWTSecret'
NODE_AUTHADDR_KEYWORD = 'Node.AuthAddr'
NODE_AUTHPORT_KEYWORD = 'Node.AuthPort'
NODE_USERIDENT_KEYWORD = 'Node.UserIdent'

P2P_MAXPENDINGPEERS_KEYWORD = 'Node.P2P.MaxPendingPeers'
P2P_MAXPEERS_KEYWORD = 'Node.P2P.MaxPeers'
ETH_WEI = 0xde0b6b3a7640000
CFG_PORT_VALUES = ['Node.HTTPPort','Node.AuthPort','Node.WSPort','Metrics.Port']
CFG_LISTEN_PORT = 'Node.P2P.ListenAddr'
CFG_NETWORKID = 'Eth.NetworkId'
CFG_INFLUX_DB_PORT = 'Metrics.InfluxDBEndpoint'

CFG_DEF_VALUES = {
    'Node.P2P.BootstrapNodes' : [],
    'Node.P2P.BootstrapNodesV5' : [],
    'Eth.SyncMode' : 'full'
}
