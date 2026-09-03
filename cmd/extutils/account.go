package main

import (
	//"bufio"
	"crypto/rand"
	"encoding/json"
	"fmt"
	"github.com/ethereum/go-ethereum/accounts/keystore"
	"io"
	//"github.com/ethereum/go-ethereum/cmd/utils"
	"github.com/ethereum/go-ethereum/internal/debug"
	"github.com/ethereum/go-ethereum/log"
	"github.com/google/uuid"
	"github.com/urfave/cli/v2"
	"os"
	"strings"
)

var decrKeyCommand = &cli.Command{
	Action:      decryptKey,
	Name:        "decryptkey",
	Usage:       "to decrypt keyfile with passwordfile",
	ArgsUsage:   "<keyfile> <passwordfile>",
	Flags:       []cli.Flag{},
	Description: `to decrypt the key`,
}
var encrKeyCommand = &cli.Command{
	Action:      encryptKey,
	Name:        "encryptkey",
	Usage:       "to encrypt keyfile with passwordfile",
	ArgsUsage:   "<keyfile> <passwordfile>",
	Flags:       []cli.Flag{},
	Description: `to encrypt the key`,
}

var genkeyCommand = &cli.Command{
	Action:      genKey,
	Name:        "genkey",
	Usage:       "to generate keyfile with random file default crypto.rand",
	ArgsUsage:   "[keyfile]  [randfile]",
	Flags:       []cli.Flag{},
	Description: `to generate the key`,
}

func loadEncryptKey(keyfile string, passwordfile string) (retp *keystore.Key, err error) {
	var keyjsons []byte
	var passstr string
	var inb []byte

	retp = nil
	inb, err = os.ReadFile(keyfile)
	if err != nil {
		return
	}
	keyjsons = inb

	inb, err = os.ReadFile(passwordfile)
	if err != nil {
		return
	}
	passstr = string(inb)
	passstr = strings.TrimRight(passstr, "\r\n")

	log.Info(fmt.Sprintf("passstr [%s]", passstr))
	log.Info(fmt.Sprintf("keyjsons\n%s", string(keyjsons)))
	retp, err = keystore.DecryptKey(keyjsons, passstr)

	return
}

type forgeKey struct {
	Id uuid.UUID `json:"id,omitempty"` // Version 4 "random" for unique id not derived from key data
	// to simplify lookups we also store the address
	Address string
	// we only store privkey as pubkey/address can be derived from it
	// privkey in this struct is always in plaintext
	PrivateKey string
	Version    int `json:"version,omitempty"`
}

func decryptKey(ctx *cli.Context) (err error) {
	debug.Setup(ctx)
	if ctx.Args().Len() < 2 {
		return fmt.Errorf("need <keyfile> <passwordfile>")
	}
	var keyfile string
	var passwordfile string
	var key *keystore.Key
	var outb []byte

	keyfile = ctx.Args().Get(0)
	passwordfile = ctx.Args().Get(1)

	key, err = loadEncryptKey(keyfile, passwordfile)
	if err != nil {
		return
	}
	outb, err = json.Marshal(key)
	if err != nil {
		return
	}
	fmt.Printf("%s\n", string(outb))

	return nil
}

func makeEncryptKey(keyfile string, passwordfile string) (outb []byte, err error) {
	var passstr string
	var passb []byte
	var fkey *forgeKey
	var key *keystore.Key
	var inb []byte

	f, err := os.Open(keyfile)
	if err != nil {
		return
	}
	defer f.Close()

	outb = []byte{}
	fkey = &forgeKey{}
	err = json.NewDecoder(f).Decode(fkey)
	if err != nil {
		return
	}

	if len(fkey.Id.String()) == 0 || fkey.Id.String() == "00000000-0000-0000-0000-000000000000" {
		fkey.Id, err = uuid.NewRandomFromReader(rand.Reader)
		if err != nil {
			return
		}
	}

	if strings.HasPrefix(fkey.Address, "0x") || strings.HasPrefix(fkey.Address, "0X") {
		fkey.Address = fkey.Address[2:]
	}

	if strings.HasPrefix(fkey.PrivateKey, "0x") || strings.HasPrefix(fkey.PrivateKey, "0X") {
		fkey.PrivateKey = fkey.PrivateKey[2:]
	}

	if fkey.Version == 0 {
		/*we make sure complicated ones*/
		fkey.Version = 3
	}

	inb, err = json.Marshal(fkey)
	if err != nil {
		return
	}
	log.Info(fmt.Sprintf("inb\n%s", string(inb)))

	key = &keystore.Key{}
	err = json.Unmarshal(inb, key)
	if err != nil {
		return
	}

	passb, err = os.ReadFile(passwordfile)
	if err != nil {
		return
	}
	passstr = string(passb)
	passstr = strings.TrimRight(passstr, "\r\n")

	log.Info(fmt.Sprintf("passstr [%s]", passstr))

	outb, err = keystore.EncryptKey(key, passstr, keystore.StandardScryptN, keystore.StandardScryptP)

	return

}

func encryptKey(ctx *cli.Context) (err error) {
	debug.Setup(ctx)
	if ctx.Args().Len() < 2 {
		return fmt.Errorf("need <keyfile> <passwordfile>")
	}
	var keyfile string
	var passwordfile string
	var outb []byte

	keyfile = ctx.Args().Get(0)
	passwordfile = ctx.Args().Get(1)

	outb, err = makeEncryptKey(keyfile, passwordfile)
	if err != nil {
		return
	}
	fmt.Printf("%s\n", string(outb))

	return nil
}

func genKey(ctx *cli.Context) (err error) {
	debug.Setup(ctx)
	var randfile io.Reader
	var key *keystore.Key
	var outb []byte
	var infil *os.File = nil
	var outfile string

	randfile = rand.Reader

	if ctx.Args().Len() > 1 {
		infil, err = os.Open(ctx.Args().Get(1))
		if err != nil {
			return
		}
		randfile = infil
	}

	defer func() {
		if infil != nil {
			infil.Close()
			infil = nil

		}
	}()

	key = keystore.NewKeyForDirectICAP(randfile)
	outb, err = json.Marshal(key)
	if err != nil {
		return
	}

	if ctx.Args().Len() > 0 {
		outfile = ctx.Args().Get(0)
		err = os.WriteFile(outfile, outb, 0640)
		if err != nil {
			return
		}
	} else {
		fmt.Printf("%s\n", string(outb))
	}

	err = nil
	return

}
