package main

import (
	"github.com/urfave/cli/v2"
)

var inputFlag = &cli.StringFlag{
	Name:    "input",
	Aliases: []string{"i"},
	Usage:   "input value",
	Value:   "",
}

var outputFlag = &cli.StringFlag{
	Name:    "output",
	Aliases: []string{"o"},
	Usage:   "output value",
	Value:   "",
}

var ExtFlags = []cli.Flag{
	inputFlag,
	outputFlag,
}
