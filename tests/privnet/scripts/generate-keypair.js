const fs = require('fs')
const Accounts = require('web3-eth-accounts')

const uri = ''

const accounts = new Accounts(uri)

const account = accounts.create()

fs.writeFile(`${account.address}.json`, JSON.stringify(account), 'utf8', (err) => {
  if (err) {
    console.log(`Error writing file: ${err}`)
  } else {
    console.log('File is written successfully!')
  }
})
