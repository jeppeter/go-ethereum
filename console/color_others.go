//go:build !windows

package console

import (
	"os"
)

func SetColorConsole(_fp *os.File) (err error) {
	err = nil
	return
}
