package flowteledbus

import (
	"fmt"
	"os"
	"sync"
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

	ackedBytesMutex sync.Mutex
	ackedBytes      uint32

	LogSignals           bool
	SignalLogMinInterval map[QuicDbusSignalType]time.Duration
	lastSignalLogged     map[QuicDbusSignalType]time.Time
	logMessagesSkipped   map[QuicDbusSignalType]uint64

	LogPrefix string
}

func (db *DbusBase) Init() {
	db.SignalMinInterval = make(map[QuicDbusSignalType]time.Duration)
	db.lastSignalSent = make(map[QuicDbusSignalType]time.Time)
	db.SignalLogMinInterval = make(map[QuicDbusSignalType]time.Duration)
	db.lastSignalLogged = make(map[QuicDbusSignalType]time.Time)
	db.logMessagesSkipped = make(map[QuicDbusSignalType]uint64)
}

func (db *DbusBase) Acked(ackedBytes uint32) uint32 {
	db.ackedBytesMutex.Lock()
	defer db.ackedBytesMutex.Unlock()
	db.ackedBytes += ackedBytes
	return db.ackedBytes
}

func (db *DbusBase) ResetAcked() {
	db.ackedBytesMutex.Lock()
	defer db.ackedBytesMutex.Unlock()
	db.ackedBytes = 0
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

func (db *DbusBase) SetLogMinIntervalForAllSignals(interval time.Duration) {
	db.SignalLogMinInterval[Rtt] = interval
	db.SignalLogMinInterval[Lost] = interval
	db.SignalLogMinInterval[Cwnd] = interval
	db.SignalLogMinInterval[Pacing] = interval
	db.SignalLogMinInterval[BbrRtt] = interval
	db.SignalLogMinInterval[BbrBW] = interval
	db.SignalLogMinInterval[Delivered] = interval
	db.SignalLogMinInterval[DeliveredAdjust] = interval
	db.SignalLogMinInterval[GainLost] = interval
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
	var logSignal bool
	if db.LogSignals {
		t := s.SignalType()
		interval, ok := db.SignalLogMinInterval[t]
		if !ok {
			// no min interval is set
			logSignal = true
		} else {
			lastSignalLogTime, ok := db.lastSignalLogged[t]
			now := time.Now()
			if !ok || now.Sub(lastSignalLogTime) > interval {
				db.lastSignalLogged[t] = now
				logSignal = true
			} else {
				// skip this log message and increase skipped counter
				db.logMessagesSkipped[t] += 1
			}
		}
		if logSignal {
			nSkipped := uint64(0)
			if val2, ok2 := db.logMessagesSkipped[t]; ok2 {
				nSkipped = val2
			}
			switch t {
			case Rtt:
				db.Log("RTT (skipped %d) srtt = %.1fms", nSkipped, float32(s.Values()[3].(uint32))/1000)
			case Lost:
				db.Log("Lost (skipped %d) ssthresh = %d", nSkipped, s.Values()[3])
			case Cwnd:
				db.Log("Cwnd (skipped %d) cwnd = %d, inflight = %d, acked = %d", nSkipped, s.Values()[3], s.Values()[4], s.Values()[5])
			}
			db.logMessagesSkipped[t] = 0
		}
	}
	if err := db.Conn.Emit(db.ObjectPath, db.InterfaceName+"."+s.Name(), s.Values()...); err != nil {
		panic(err)
	}
}

func (db *DbusBase) OpenSessionBus() {
	var err error
	db.Conn, err = dbus.SessionBus()
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
