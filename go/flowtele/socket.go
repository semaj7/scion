package main

import (
	"fmt"
	"os"
	"time"

	"github.com/godbus/dbus"
	"github.com/godbus/dbus/introspect"
)

const (
	// SERVICE_NAME = "edu.illinois.csl.mercurius"
	// INTERFACE_NAME = "edu.illinois.csl.mercurius"
	// OBJECT_PATH = "/edu/illinois/csl/mercurius/service"
	SERVICE_NAME = "ch.ethz.netsec.flowtele.scionsocket"
	INTERFACE_NAME = "ch.ethz.netsec.flowtele.scionsocket"
	OBJECT_PATH = "/ch/ethz/netsec/flowtele/scionsocket"
)

type fShaperDbusInterface struct {

}

func (s fShaperDbusInterface) ApplyControl(param string) (ret string, dbusError *dbus.Error) {
	fmt.Println("param = " + param)
	if dbusError != nil {
		fmt.Println(dbusError)
	}
	return "hello " + param, nil
}

type quicDbusInterface struct {
	
}

func main() {
	// dbus setup
	conn, err := dbus.ConnectSessionBus()
	if err != nil {
		fmt.Fprintln(os.Stderr, "Failed to connect to session bus:", err)
		os.Exit(1)
	}
	defer conn.Close()

	reply, err := conn.RequestName(SERVICE_NAME, dbus.NameFlagDoNotQueue)
	if err != nil {
		panic(err)
	}
	if reply != dbus.RequestNameReplyPrimaryOwner {
		fmt.Fprintln(os.Stderr, "name already taken")
		os.Exit(1)
	}
	
	// start QUIC instances

	// start listening to athena's call to applyControl using dbus and forward updated CC parameters to QUIC instances
	f := &fShaperDbusInterface{}
	conn.Export(f, OBJECT_PATH, INTERFACE_NAME)

	fmt.Println(introspect.Methods(f)[0].Name)
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

	// listen to CC feedback from QUIC instances and forward signals to athena
	if err = conn.AddMatchSignal(
		dbus.WithMatchObjectPath(REMOTE_OBJECT_PATH),
		dbus.WithMatchInterface(REMOTE_INTERFACE_NAME),
		dbus.WithMatchMember("mysignal"),
		// dbus.WithMatchSender(REMOTE_SERVICE_NAME),
	); err != nil {
		panic(err)
	}

	c := make(chan *dbus.Signal, 1)
	conn.Signal(c)
	for v := range c {
		fmt.Println(v)
	}

	// main loop
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

func connect_to_athena_and_listen_for_applyControl() {
	conn, err := dbus.ConnectSessionBus()
	if err != nil {
		fmt.Fprintln(os.Stderr, "Failed to connect to session bus:", err)
		os.Exit(1)
	}
	defer conn.Close()

	reply, err := conn.RequestName(SERVICE_NAME,
		dbus.NameFlagDoNotQueue)
	if err != nil {
		panic(err)
	}
	if reply != dbus.RequestNameReplyPrimaryOwner {
		fmt.Fprintln(os.Stderr, "name already taken")
		os.Exit(1)
	}

	f := &fShaperDbusInterface{}
	conn.Export(f, OBJECT_PATH, INTERFACE_NAME)

	fmt.Println(introspect.Methods(f)[0].Name)
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
