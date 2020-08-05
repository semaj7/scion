package main

import (
	"fmt"
	"os"
	"time"

	"github.com/godbus/dbus"
	"github.com/godbus/dbus/introspect"
)

const (
	SERVICE_NAME = "edu.illinois.csl.mercurius"
	INTERFACE_NAME = "edu.illinois.csl.mercurius"
	OBJECT_PATH = "/edu/illinois/csl/mercurius/service"
)

type scionSocket struct {

}

func (s scionSocket) applyControl(param string, dbusError *dbus.Error) {
	fmt.Println("param = " + param)
	if dbusError != nil {
		fmt.Println(dbusError)
	}
}

type foo string

func (f foo) Foo() (string, *dbus.Error) {
	fmt.Println(f)
	return string(f), nil
}

func main() {
	connect_to_athena_and_listen_for_applyControl()
}

func connect_to_athena_and_listen_for_applyControl() {
	// analogue to: dbusctl --user
	conn, err := dbus.ConnectSessionBus()
	if err != nil {
		fmt.Fprintln(os.Stderr, "Failed to connect to session bus:", err)
		os.Exit(1)
	}
	defer conn.Close()

	// register/bind a service name for the dbus service
	reply, err := conn.RequestName(SERVICE_NAME,
		dbus.NameFlagDoNotQueue)
	if err != nil {
		panic(err)
	}
	if reply != dbus.RequestNameReplyPrimaryOwner {
		fmt.Fprintln(os.Stderr, "name already taken")
		os.Exit(1)
	}

	f := foo("Bar!")

	// make the function available (will be available as dbus method)
	// could also do it for signals (events) or properties
	conn.Export(f, OBJECT_PATH, INTERFACE_NAME)


	// Make it instrospectable
	n := &introspect.Node{
		Name: OBJECT_PATH,
		Interfaces: []introspect.Interface{
			introspect.IntrospectData,
			{
				Name:       INTERFACE_NAME,
				Methods:    introspect.Methods(f),
				Signals:    []introspect.Signal{introspect.Signal{Name: "mysignal"}},
			},
		},
	}
	conn.Export(introspect.NewIntrospectable(n), OBJECT_PATH, "org.freedesktop.DBus.Introspectable")

	fmt.Println("Listening ...")
	for {
		select {
		case <-time.After(2*time.Second):
			// emit signal
			if err := conn.Emit(OBJECT_PATH, INTERFACE_NAME+".mysignal", uint32(42)); err != nil {
				panic(err)
			}
		}
	}
}
