package main

import (
	"fmt"
	"github.com/cockroachdb/pebble"
	"github.com/ethereum/go-ethereum/internal/debug"
	"github.com/ethereum/go-ethereum/log"
	"github.com/urfave/cli/v2"
)

var iterchainCommand = &cli.Command{
	Action:      iter_chain,
	Name:        "iterchain",
	Usage:       "to iter the chain data",
	ArgsUsage:   "chaindir",
	Flags:       []cli.Flag{},
	Description: `to iterater chain`,
}

func iter_chain(ctx *cli.Context) (err error) {
	debug.Setup(ctx)
	var opt *pebble.Options = &pebble.Options{}
	var dir string
	var db *pebble.DB = nil
	var niter *pebble.Iterator = nil
	opt.EnsureDefaults()
	if ctx.Args().Len() < 1 {
		err = fmt.Errorf("need chaindir to search")
		return
	}
	dir = ctx.Args().Get(0)

	db, err = pebble.Open(dir, opt)
	if err != nil {
		log.Error(fmt.Sprintf("open [%s]error %s", dir, err.Error()))
		return
	}
	defer db.Close()
	niter, err = db.NewIter(nil)
	if err != nil {
		log.Error(fmt.Sprintf("new iter %s error %s", dir, err.Error()))
		return
	}

	for niter.First(); niter.Valid(); niter.Next() {
		fmt.Printf("key %v=%v\n", niter.Key(), niter.Value())
	}

	err = nil
	return
}
