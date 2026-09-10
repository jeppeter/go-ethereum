package main

import (
	"encoding/json"
	"fmt"
	"github.com/cockroachdb/pebble"
	"github.com/ethereum/go-ethereum/internal/debug"
	"github.com/ethereum/go-ethereum/log"
	"github.com/ethereum/go-ethereum/rlp"
	"github.com/urfave/cli/v2"
	"math/big"
	"os"
)

var iterchainCommand = &cli.Command{
	Action:      iter_chain,
	Name:        "iterchain",
	Usage:       "to iter the chain data",
	ArgsUsage:   "chaindir",
	Flags:       []cli.Flag{},
	Description: `to iterater chain`,
}

var encgenCommand = &cli.Command{
	Action:      encode_generator,
	Name:        "encgen",
	Usage:       "jsonfile to make generator",
	ArgsUsage:   "jsonfile",
	Flags:       []cli.Flag{},
	Description: `to make generator`,
}

var decgenCommand = &cli.Command{
	Action:      decode_generator,
	Name:        "decgen",
	Usage:       "binfile to make generator",
	ArgsUsage:   "binfile",
	Flags:       []cli.Flag{},
	Description: `to decode generator`,
}

var encrlpvarCommand = &cli.Command{
	Action:      encode_rlp_variable,
	Name:        "encrlpvar",
	Usage:       "jsonfile to encode rlp variable",
	ArgsUsage:   "jsonfile",
	Flags:       []cli.Flag{},
	Description: `to encode rlp variable`,
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

// journalGenerator is a disk layer entry containing the generator progress marker.
type journalGenerator struct {
	// Indicator that whether the database was in progress of being wiped.
	// It's deprecated but keep it here for backward compatibility.
	Wiping bool `json:,omitemtpy`

	Done     bool   `json:,omitemtpy` // Whether the generator finished creating the snapshot
	Marker   []byte `json:,omitemtpy`
	Accounts uint64 `json:,omitemtpy`
	Slots    uint64 `json:,omitemtpy`
	Storage  uint64 `json:,omitemtpy`
}

func decode_generator(ctx *cli.Context) (err error) {
	var binfile string
	var inb []byte
	var gen *journalGenerator
	var outb []byte
	debug.Setup(ctx)
	if ctx.Args().Len() < 1 {
		err = fmt.Errorf("need binfile")
		return
	}
	binfile = ctx.Args().Get(0)
	inb, err = os.ReadFile(binfile)
	if err != nil {
		return
	}

	gen = &journalGenerator{}
	err = rlp.DecodeBytes(inb, gen)
	if err != nil {
		return
	}

	outb, err = json.Marshal(gen)
	if err != nil {
		return
	}

	fmt.Printf("%s", string(outb))

	err = nil
	return
}

func encode_generator(ctx *cli.Context) (err error) {
	var jsonfile string
	var inb []byte
	var gen *journalGenerator
	var outb []byte
	debug.Setup(ctx)
	if ctx.Args().Len() < 1 {
		err = fmt.Errorf("need jsonfile")
		return
	}
	jsonfile = ctx.Args().Get(0)
	inb, err = os.ReadFile(jsonfile)
	if err != nil {
		return
	}

	gen = &journalGenerator{}
	err = json.Unmarshal(inb, gen)
	if err != nil {
		return
	}

	outb, err = rlp.EncodeToBytes(gen)
	if err != nil {
		return
	}
	fmt.Printf("%v\n", outb)

	err = nil
	return
}

type BigInt struct {
	big.Int
}

func (b BigInt) MarshalJSON() ([]byte, error) {
	var outb []byte
	var newout []byte
	outb = []byte(b.String())
	if len(outb) < 32 {
		return []byte(outb), nil
	}
	newout = []byte(fmt.Sprintf("0x%x", b))

	return newout, nil
}

func (b *BigInt) UnmarshalJSON(p []byte) error {
	if string(p) == "null" {
		return nil
	}
	var z big.Int
	var base int = 10
	var newp []byte
	var err error
	newp = p

	if len(newp) >= 2 && newp[0] == byte('"') {
		if newp[len(newp)-1] != byte('"') {
			err = fmt.Errorf("not match string")
			return err
		}
		newp = newp[1:]
		newp = newp[:len(newp)-2]
	}

	if len(newp) >= 2 && (newp[0] == byte('0') && (newp[1] == byte('x') || newp[1] == byte('X'))) {
		newp = newp[2:]
		base = 16
	}

	_, ok := z.SetString(string(newp), base)
	if !ok {
		return fmt.Errorf("not a valid big integer: %s", p)
	}
	b.Int = z
	return nil
}

type RlpVariable struct {
	Bval bool    `json:"bval",omitemtpy` // to make Bval
	Sval string  `json:"sval",omitemtpy`
	Bint *BigInt `json:"bint",omitemtpy`
}

func encode_rlp_variable(ctx *cli.Context) (err error) {
	var jsonfile string
	var inb []byte
	var gen *RlpVariable
	var outb []byte
	var output string
	debug.Setup(ctx)
	if ctx.Args().Len() < 1 {
		err = fmt.Errorf("need jsonfile")
		return
	}
	jsonfile = ctx.Args().Get(0)
	inb, err = os.ReadFile(jsonfile)
	if err != nil {
		return
	}

	gen = &RlpVariable{}
	err = json.Unmarshal(inb, gen)
	if err != nil {
		return
	}

	outb, err = rlp.EncodeToBytes(gen)
	if err != nil {
		return
	}

	if ctx.IsSet(outputFlag.Name) {
		output = ctx.String(outputFlag.Name)
		err = os.WriteFile(output, outb, 0644)
		if err != nil {
			return
		}
	} else {
		fmt.Printf("%v\n", outb)
	}

	err = nil
	return
}
