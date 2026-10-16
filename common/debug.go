// Copyright 2015 The go-ethereum Authors
// This file is part of the go-ethereum library.
//
// The go-ethereum library is free software: you can redistribute it and/or modify
// it under the terms of the GNU Lesser General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// The go-ethereum library is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
// GNU Lesser General Public License for more details.
//
// You should have received a copy of the GNU Lesser General Public License
// along with the go-ethereum library. If not, see <http://www.gnu.org/licenses/>.

package common

import (
	"fmt"
	"io"
	"os"
	"runtime"
	"runtime/debug"
	"strconv"
	"strings"
	"sync"
)

// Report gives off a warning requesting the user to submit an issue to the github tracker.
func Report(extra ...interface{}) {
	fmt.Fprintln(os.Stderr, "You've encountered a sought after, hard to reproduce bug. Please report this to the developers <3 https://github.com/ethereum/go-ethereum/issues")
	fmt.Fprintln(os.Stderr, extra...)

	_, file, line, _ := runtime.Caller(1)
	fmt.Fprintf(os.Stderr, "%v:%v\n", file, line)

	debug.PrintStack()

	fmt.Fprintln(os.Stderr, "#### BUG! PLEASE REPORT ####")
}

// PrintDeprecationWarning prints the given string in a box using fmt.Println.
func PrintDeprecationWarning(str string) {
	line := strings.Repeat("#", len(str)+4)
	emptyLine := strings.Repeat(" ", len(str))
	fmt.Printf(`
%s
# %s #
# %s #
# %s #
%s

`, line, emptyLine, str, emptyLine, line)
}

func GetCallerString(skip int) (outs string) {
	var f string
	var lineno int
	var ok bool
	var sidx int = skip
	outs = ""
	for {
		_, f, lineno, ok = runtime.Caller(sidx)
		if !ok {
			break
		}
		if len(outs) > 0 {
			outs += ";"
		}
		outs += fmt.Sprintf("[%d][%s:%d]", sidx, f, lineno)
		sidx += 1
	}
	return
}

var common_test_logger io.Writer = nil
var common_test_level int = -1
var common_test_lock sync.Mutex
var common_test_inited int = 0
var common_test_no_stderr int = 0

func init() {
	InitTestFunc()
}

func InitTestFunc() {
	var envstr string
	var err error
	var fwriter io.Writer = nil
	if common_test_inited != 0 {
		return
	}

	envstr = os.Getenv("TEST_LEVEL")
	if len(envstr) > 0 {
		common_test_level, err = strconv.Atoi(envstr)
	}

	envstr = os.Getenv("TEST_NO_STDERR")
	if len(envstr) > 0 {
		common_test_no_stderr, err = strconv.Atoi(envstr)
	}

	envstr = os.Getenv("TEST_LOG_FILE")
	if len(envstr) > 0 {
		var fp *os.File
		fp, err = os.OpenFile(envstr, os.O_CREATE|os.O_WRONLY, 0640)
		if err == nil {
			fwriter = io.Writer(fp)
		}
		if common_test_no_stderr == 0 {
			common_test_logger = io.MultiWriter(os.Stderr, fwriter)
		} else {
			common_test_logger = io.MultiWriter(fwriter)
		}

	} else {
		if common_test_level > 0 {
			if common_test_no_stderr == 0 {
				common_test_logger = io.MultiWriter(os.Stderr)
			} else {
				common_test_logger = io.MultiWriter()
			}

		}
	}
	common_test_inited = 1
	return
}

func Testf(fmtstr string, a ...interface{}) {
	var outs string
	common_test_lock.Lock()
	defer common_test_lock.Unlock()
	if common_test_level <= 0 {
		return
	}
	_, f, l, ok := runtime.Caller(1)
	if ok {
		outs = fmt.Sprintf("[%s:%d] ", f, l)
	} else {
		outs = ""
	}
	outs += fmt.Sprintf(fmtstr, a...)
	outs += "\n"
	common_test_logger.Write([]byte(outs))
	return
}

func TestBufferf(inb []byte, fmtstr string, a ...interface{}) {
	var outs string
	var i int
	var lasti int
	common_test_lock.Lock()
	defer common_test_lock.Unlock()
	if common_test_level <= 0 {
		return
	}
	_, f, l, ok := runtime.Caller(1)
	if ok {
		outs = fmt.Sprintf("[%s:%d] ", f, l)
	} else {
		outs = ""
	}
	outs += fmt.Sprintf(fmtstr, a...)

	lasti = 0
	for i = 0; i < len(inb); i += 1 {
		if (i % 16) == 0 {
			if i > 0 {
				outs += fmt.Sprintf("    ")
				for lasti < i {
					if inb[lasti] >= byte(' ') && inb[lasti] <= byte('~') {
						outs += fmt.Sprintf("%c", inb[lasti])
					} else {
						outs += "."
					}
					lasti += 1
				}
			}
			outs += fmt.Sprintf("\n")
			outs += fmt.Sprintf("0x%08x: ", i)
			if len(outs) > 256 {
				common_test_logger.Write([]byte(outs))
				outs = ""
			}
		}
		outs += fmt.Sprintf(" 0x%02x", inb[i])
	}
	if lasti != i {
		for (i % 16) != 0 {
			outs += fmt.Sprintf("     ")
			i += 1
		}
		outs += fmt.Sprintf("    ")
		for lasti < len(inb) {
			if inb[lasti] >= byte(' ') && inb[lasti] <= byte('~') {
				outs += fmt.Sprintf("%c", inb[lasti])
			} else {
				outs += "."
			}
			lasti += 1
		}
	}
	outs += fmt.Sprintf("\n")
	common_test_logger.Write([]byte(outs))
	outs = ""

	return

}
