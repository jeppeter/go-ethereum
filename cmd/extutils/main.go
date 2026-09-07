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
	"fmt"
	"github.com/ethereum/go-ethereum/console"
	"github.com/ethereum/go-ethereum/internal/debug"
	"github.com/ethereum/go-ethereum/internal/flags"
	"github.com/urfave/cli/v2"
	"os"
	"slices"
)

var app = flags.NewApp("Ethereum extended utils")

func init() {
	console.SetColorConsole(os.Stdout)
	app.Commands = []*cli.Command{
		decrKeyCommand,
		encrKeyCommand,
		genkeyCommand,
	}

	app.Flags = slices.Concat(app.Flags, debug.Flags, ExtFlags)

	app.Name = "extutils"
	app.Action = version
}

func version(c *cli.Context) error {
	fmt.Printf("version 1.0\n")
	return nil
}

func main() {
	//log.SetDefault(log.NewLogger(log.NewTerminalHandlerWithLevel(os.Stderr, log.LevelInfo, true)))

	if err := app.Run(os.Args); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}
