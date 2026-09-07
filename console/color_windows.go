//go:build windows

package console

import (
	"github.com/mattn/go-isatty"
	"golang.org/x/sys/windows"
	"os"
)

func SetColorConsole(fp *os.File) (err error) {
	if isatty.IsTerminal(fp.Fd()) {
		var mode uint32
		handle := windows.Handle(fp.Fd())
		windows.GetConsoleMode(handle, &mode)
		mode |= windows.ENABLE_VIRTUAL_TERMINAL_PROCESSING
		windows.SetConsoleMode(handle, mode)
	}
	err = nil
	return
}
