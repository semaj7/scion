package main

import (
	"fmt"
	"os"

	"github.com/godbus/dbus"
)

const (
	SERVICE_NAME = "edu.illinois.csl.athena"
	INTERFACE_NAME = "edu.illinois.csl.athena"
	OBJECT_PATH = "/service"

	REMOTE_SERVICE_NAME = "edu.illinois.csl.mercurius"
	REMOTE_INTERFACE_NAME = "edu.illinois.csl.mercurius"
	REMOTE_OBJECT_PATH = "/edu/illinois/csl/mercurius/service"
)

func main() {
	athena_call_applyControl()
}

func athena_call_applyControl() {
	conn, err := dbus.ConnectSessionBus()
	if err != nil {
		fmt.Fprintln(os.Stderr, "Failed to connect to session bus:", err)
		os.Exit(1)
	}
	defer conn.Close()

	mercurius := conn.Object(REMOTE_SERVICE_NAME, REMOTE_OBJECT_PATH)

	// call method
	call := mercurius.Call(REMOTE_INTERFACE_NAME+".Foo", 0)
	if call.Err != nil {
		panic(call.Err)
	}
	var res string
	call.Store(&res)
	fmt.Println(res)

	// read out signal
	if err = conn.AddMatchSignal(
		dbus.WithMatchObjectPath(REMOTE_OBJECT_PATH),
		dbus.WithMatchInterface(REMOTE_INTERFACE_NAME),
		dbus.WithMatchMember("mysignal"),
		dbus.WithMatchSender(REMOTE_SERVICE_NAME),
	); err != nil {
		panic(err)
	}

	c := make(chan *dbus.Signal, 1)
	conn.Signal(c)
	for v := range c {
		fmt.Println(v)
	}
}
