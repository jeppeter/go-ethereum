const constants = require('./constants.js')
const utils = require('./utils.js')

const Web3 = require('web3')
const keythereum = require('keythereum')

const run = async () => {
  const password = (await utils.readFile('./secrets/password-api.secret')).trim()

  const web3 = new Web3(new Web3.providers.HttpProvider(constants.host))

  const datadir = './datadir-api'
  const address = constants.addressAPI

  const keyObject = keythereum.importFromFile(address, datadir)
  const privateKeyObject = keythereum.recover(password, keyObject)
  const privateKey = privateKeyObject.toString('hex')

  const rawTx = {
    from: address,
    to: constants.addressSigner,
    value: '0x6',
    gas: 2000000
  }

  const signPromise = web3.eth.accounts.signTransaction(rawTx, privateKey)

  signPromise.then((signedTx) => {
    // raw transaction string may be available in .raw or
    // .rawTransaction depending on which signTransaction
    // function was called
    const sentTx = web3.eth.sendSignedTransaction(signedTx.raw || signedTx.rawTransaction); sentTx.on('receipt', receipt => {
      // do something when receipt comes back
      console.log(receipt)
    })
    sentTx.on('error', err => {
      // do something on transaction error
      console.log(err)
    })
  }).catch((err) => {
    // do something when promise fails
    console.log(err)
  })
}

run()
