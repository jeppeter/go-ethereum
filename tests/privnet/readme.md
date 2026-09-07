# Private Ethereum Blockchain

In this tutorial, we build a network of 2 Ethereum nodes.

As it is a private blockchain, we don't need to create blocks with proof of work.
Instead, we use the Proof of Authority consensus algorithm. The miner node is not called a miner but rather a signer.

*Why do we need two nodes?*

This is because the signer node must run with an unlocked account. This account is the account that will receive mining rewards. If we open the AIPs of the node, the account is insecure. So, we need a node that communicates with the signer node and that opens some APIs to the external world.

## Ressources
 - [Geth command line documentation](https://geth.ethereum.org/docs/interface/command-line-options)
 - geth private networks documentation: https://geth.ethereum.org/docs/interface/private-network
 - good tutorial for 2 nodes deployed on AWS: https://blockgeeks.com/two-node-setup-of-a-private-ethereum/
 - good tutorial for private Ethereum blockchain: https://www.edureka.co/blog/ethereum-private-network-tutorial
 - [Web3 documentation](https://web3js.readthedocs.io)

## Sensitive data
**WARNING:** Do not use any data from this repo, it contains private keys that anybody can read.

## Install requirements

	sudo apt-get install software-properties-common
	sudo add-apt-repository -y ppa:ethereum/ethereum
	sudo apt-get update
	sudo apt-get install ethereum

	npm install

## Generate accounts
### For the signer
Change the password in the file `./secrets/password-signer.secret`

Run this command:

	geth account new --datadir ./datadir-signer --password ./secrets/password-signer.secret

`--datadir ./datadir-signer` specifies the data directory for our blockchain.

`--password ./secrets/password-signer.secret` specifies the file where the account password is stored

### For the API
Do the same thing for the API node: change the password in the file `./secrets/password-api.secret` and run:

	geth account new --datadir ./datadir-api --password ./secrets/password-api.secret

### Generate key pair
If you want, you can generate a key pair with this command:

	node ./scripts/generate-keypair.js

It will generate a key pair and save it in a file.

**Warning:** the file contains the private key.

*Note*: this is not really useful for our blockchain.

## Signer node (Miner)
The signer node is the node that computes transactions.

To initialize a network with POA consensus algorithm, we need to specify a `clique` and `extradata` in the genesis file.

## API node
The API node is the node that receives RPC calls from clients and shares submitted transactions to the signer node.

It needs to open an API and be synchronized with the signer node.

## Initialization: the genesis file
All nodes of the network must have the same genesis file.

The first step is defining a chain ID.

Open the file `./common/genesis.json` and change the value of the `chainId` field.

Change the `alloc` section with the generated addresses, remove `0x` prefix.

In the `extradata` field, replace the address with the account generate in the `datadir-signer` folder (signer's address). This field must start with `0x`, then 64 `0`, the signer address (without the `0x`), and finish with 130 `0`.

## Initialize
### Initialize Signer node
Run:

	geth init --datadir ./datadir-signer ./common/genesis.json

### Initialize API node
Run:

	geth init --datadir ./datadir-api ./common/genesis.json

The two nodes are now initialized with the same genesis file.

## Run
### Run the signer node
In the command bellow, replace the signer's address and the network id:

	geth --networkid 2363 --datadir ./datadir-signer --nodiscover --port 30304 --mine --miner.threads=1 --miner.etherbase 0x815bd60b39e32d23793410c928e4d8a5459d2c2f --unlock 0x815bd60b39e32d23793410c928e4d8a5459d2c2f --password ./secrets/password-signer.secret

### Run the API node
For local host, run this command:

	geth --networkid 2363 --datadir ./datadir-api --nodiscover --http --http.addr 127.0.0.1 --http.api eth,net,web3

Again, don't forget to replace de network id.

Or, run this one for specifing networking options:

	geth --networkid 2363 --datadir ./datadir-api --nodiscover --netrestrict="10.0.0.0/28" --http --http.addr 10.0.0.11 --http.api eth,net,web3

 - `--netrestrict`: Restricts network communication to the given IP networks (CIDR masks)
 - `--http.addr`: HTTP-RPC server listening interface

#### Check the API node
This command shows the version of the web3 API of the node.
It can be used to know if the node is running and if we can communicate with it through web3.

Run this in a new terminal:

    curl -X POST -H "Content-Type: application/json" --data '{"jsonrpc":"2.0","method":"web3_clientVersion","params":[],"id":67}' http://localhost:8545

It should output something like `{"jsonrpc":"2.0","id":67,"result":"Geth/v1.10.2-stable-97d11b01/linux-amd64/go1.16"}`.

## Synchronize nodes
The API node needs to be synchronized with the signer node.
To make them communicate with each other, we simply add a file named `static-nodes.json` in the `geth` folder of the datadir of the API node.

In a new terminal, run the console of the signer node :

	geth attach --datadir ./datadir-signer

In the console, run:

	admin.nodeInfo.enode

It should output something like `"enode://79d6921e66fb9865e941555733124930c6394586ade5efb9a1ac8bebc25ac6dec6bebb725d00cb193c228f12d1adcd38d754e4c5bbdd1982079a380a74b2a008@10.0.0.12:30304?discport=0"`.

You can see that `10.0.0.12` is the IP address of the signer node.

Then, in the folder `./datadir-api/geth`, create a file `static-nodes.json` with this content:

    [
        <put here the output of the previous command>
    ]

Replace with the output and replace the IP address with the signer node's private IP address.

If you run both nodes on the same computer, the IP address is `127.0.0.1`.

At startup, the API node will try to connect to the signer node and will start to synchronize.

Restart the API node.

### Check the synchronization
Go back to the console of the signer node:

Type:

	admin.peers

It should output something like:

```
[{
    caps: ["eth/64", "eth/65", "eth/66", "snap/1"],
    enode: "enode://396c1447f79d164153641e2791034333ee6f75f4f757ed1e2d69e205dd021e44a72b1ecb726172b6a6537fe124b1cf0a206641e84d9a0cdbbb6ab6cda1aea050@127.0.0.1:60390",
    id: "d71ed1495f6616be0350bde4f1ffb219e93c568c389ba7e7f93d0d2845d1df98",
    name: "Geth/v1.10.2-stable-97d11b01/linux-amd64/go1.16",
    network: {
      inbound: true,
      localAddress: "127.0.0.1:30304",
      remoteAddress: "127.0.0.1:60390",
      static: false,
      trusted: false
    },
    protocols: {
      eth: {
        difficulty: 1,
        head: "0x74eaa02b8d78ff17130fbf524c1774d14a85ae770badcd4ef1b9707b84f3fb36",
        version: 66
      },
      snap: {
        version: 1
      }
    }
}]
```

You can see that it is a JSON object. If you see multiple JSON objects, this means that your miner node is connected with several other nodes. In this JSON object, the `enode` field is the node information of the API node.

The logs of the signer node should output some messages like `mined potential block`.

The logs of the API node should output some messages like `Imported new chain segment`.

## Interact
### Send ether
Open the file `./scripts/constants.js` and change the values of `addressSigner` and `addressAPI` with the one generated in the *Generate key pair* step.

In the `scripts` folder, you will find two different ways to send a transaction.

#### API node send ether to signer node
Run:

	node ./scripts/api-send-to-signer.js

When a transaction is broadcasted, API node should output `Submitted transaction`.

#### Check balances
In a new terminal window, open a console of the signer node by typing:

	geth attach --datadir ./datadir-signer

And type:

	web3.fromWei(eth.getBalance(eth.coinbase));

The output should be like `4000000000.000042000000000006`. The script sends 6 WEI, so the amount ends with 6.

To check the balance of the API node, you can do the same as previous: open a console of the API node.
However, you can run is any console node:

	web3.fromWei(eth.getBalance("0xf6eed716dd9a86a36b5be105dc45d4e74abbd775"));

And of course, replace the address with the one of the API node.

As the API node sends the transaction, it pays fees, so the output would look like `2999999999.999936999999999982`.

### Deploy contract
Now that we can submit simple transfer transactions, it is possible to use a framework to make some more complex actions, like deploy a smart contract and interact with it.

To do that, we just need the host of the API node, for example, `http://localhost:8545`. We can use Truffle: https://www.trufflesuite.com/docs/truffle/overview.

## Deploy the stack
Now that we have our network running, we can deploy both notes on separate servers, for example in VMs in a cloud provider.
