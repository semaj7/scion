package flowteledbus

import (
	"fmt"
	"os"
	"time"

	"github.com/godbus/dbus"
	"github.com/godbus/dbus/introspect"
)

type DbusBase struct {
	ServiceName    string
	ObjectPath     dbus.ObjectPath
	InterfaceName  string
	Conn           *dbus.Conn
	SignalListener chan *dbus.Signal

	ExportedMethods    interface{}
	SignalMatchOptions []dbus.MatchOption
	ExportedSignals    []introspect.Signal

	SignalMinInterval map[QuicDbusSignalType]time.Duration
	lastSignalSent    map[QuicDbusSignalType]time.Time

	LogPrefix string
}

func (db *DbusBase) Init() {
	db.SignalMinInterval = make(map[QuicDbusSignalType]time.Duration)
	db.lastSignalSent = make(map[QuicDbusSignalType]time.Time)
}

func (db *DbusBase) SetMinIntervalForAllSignals(interval time.Duration) {
	db.SignalMinInterval[Rtt] = interval
	db.SignalMinInterval[Lost] = interval
	db.SignalMinInterval[Cwnd] = interval
	db.SignalMinInterval[Pacing] = interval
	db.SignalMinInterval[BbrRtt] = interval
	db.SignalMinInterval[BbrBW] = interval
	db.SignalMinInterval[Delivered] = interval
	db.SignalMinInterval[DeliveredAdjust] = interval
	db.SignalMinInterval[GainLost] = interval
}

func (db *DbusBase) ShouldSendSignal(s DbusSignal) bool {
	t := s.SignalType()
	interval, ok := db.SignalMinInterval[t]
	if !ok {
		// no min interval is set
		return true
	}
	lastSignalTime, ok := db.lastSignalSent[t]
	now := time.Now()
	if !ok || now.Sub(lastSignalTime) > interval {
		db.lastSignalSent[t] = now
		return true
	} else {
		return false
	}
}

func (db *DbusBase) Send(s DbusSignal) {
	// db.Log("send signal %s (%+v)", s.Name(), s.Values())
	if err := db.Conn.Emit(db.ObjectPath, db.InterfaceName+"."+s.Name(), s.Values()...); err != nil {
		panic(err)
	}
}

func (db *DbusBase) OpenSessionBus() {
	var err error
	db.Conn, err = dbus.ConnectSessionBus()
	if err != nil {
		fmt.Fprintln(os.Stderr, "Failed to connect to session bus:", err)
		os.Exit(1)
	}

	reply, err := db.Conn.RequestName(db.ServiceName, dbus.NameFlagDoNotQueue)
	if err != nil {
		panic(err)
	}
	if reply != dbus.RequestNameReplyPrimaryOwner {
		fmt.Fprintf(os.Stderr, "name (%s) already taken\n", db.ServiceName)
		os.Exit(1)
	}
}

func (db *DbusBase) Close() {
	db.Conn.Close()
}

func (db *DbusBase) registerMethods() {
	db.Conn.Export(db.ExportedMethods, db.ObjectPath, db.InterfaceName)
}

func (db *DbusBase) registerSignalListeners() {
	if err := db.Conn.AddMatchSignal(
		db.SignalMatchOptions...,
	// dbus.WithMatchObjectPath(db.ObjectPath),
	// dbus.WithMatchInterface(db.InterfaceName),
	// dbus.WithMatchMember("mysignal"),
	// dbus.WithMatchSender(REMOTE_SERVICE_NAME),
	); err != nil {
		panic(err)
	}

	db.SignalListener = make(chan *dbus.Signal, 1)
	db.Conn.Signal(db.SignalListener)
}

func (db *DbusBase) registerIntrospectMethod() {
	// fmt.Printf("Name: %s, methods: %+v\n", db.InterfaceName, introspect.Methods(db.ExportedMethods))
	n := &introspect.Node{
		Name: string(db.ObjectPath),
		Interfaces: []introspect.Interface{
			introspect.IntrospectData,
			{
				Name:    db.InterfaceName,
				Methods: introspect.Methods(db.ExportedMethods),
				Signals: db.ExportedSignals,
			},
		},
	}
	db.Conn.Export(introspect.NewIntrospectable(n), db.ObjectPath, "org.freedesktop.DBus.Introspectable")
}

func (db *DbusBase) Register() {
	db.registerMethods()
	db.registerSignalListeners()
	db.registerIntrospectMethod()
}

func (db *DbusBase) Log(formatString string, args ...interface{}) {
	fmt.Printf(db.LogPrefix+": "+formatString+"\n", args...)
}
