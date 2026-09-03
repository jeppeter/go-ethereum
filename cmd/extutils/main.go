// Copyright 2016 The go-ethereum Authors
// This file is part of go-ethereum.
//
// go-ethereum is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// go-ethereum is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with go-ethereum. If not, see <http://www.gnu.org/licenses/>.

package main

import (
	//"bufio"
	"encoding/json"
	"fmt"
	"github.com/ethereum/go-ethereum/accounts/keystore"
	//"github.com/ethereum/go-ethereum/cmd/utils"
	"github.com/ethereum/go-ethereum/internal/flags"
	"github.com/ethereum/go-ethereum/log"
	"github.com/urfave/cli/v2"
	"os"
	"strings"
)

var ()

var app = flags.NewApp("Ethereum extended utils")

func init() {
	decryptCommand := &cli.Command{
		Action:      decryptKey,
		Name:        "decryptkey",
		Usage:       "to decrypt keyfile with passwordfile",
		ArgsUsage:   "<keyfile> <passwordfile>",
		Flags:       []cli.Flag{},
		Description: `to decrypt the key`,
	}

	app.Commands = []*cli.Command{
		decryptCommand,
	}

	app.Name = "extutils"
	app.Action = version
}

func version(c *cli.Context) error {
	fmt.Printf("version 1.0\n")
	return nil
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

func decryptKey(ctx *cli.Context) (err error) {
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

func main() {
	log.SetDefault(log.NewLogger(log.NewTerminalHandlerWithLevel(os.Stderr, log.LevelInfo, true)))

	if err := app.Run(os.Args); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}
