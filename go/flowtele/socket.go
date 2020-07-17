package main

import (
	"fmt"
	"os"
	"time"
	"reflect"

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

type quicDbusInterface struct {
	
}

func main() {
	var fdbus fshaperDbus
	// dbus setup
	fdbus.openSessionBus()
	defer fdbus.closeSessionBus()

	// start QUIC instances

	// register method and listeners
	fdbus.register()

	// listen for feedback from QUIC instances and forward to athena
	fdbus.mainLoop()

	// // main loop
	// fmt.Println("Listening ...")
	// for {
	// 	select {
	// 	case <-time.After(2*time.Second):
	// 		// emit signal
	// 		t := time.Now()

	// 		// params := []interface{}{}
	// 		// params = append(params, int32(0))
	// 		// params = append(params, uint64(42))
	// 		// params = append(params, uint32(42))
	// 		// params = append(params, uint32(42))
	// 		// params = append(params, uint32(42))
	// 		// // params = append(params, int32(42))
	// 		// params = append(params, uint32(42))
	// 		// if err := conn.Emit(OBJECT_PATH, INTERFACE_NAME+".reportCwnd", params...); err != nil {
	// 		// 	panic(err)
	// 		// }

	// 		// field_list := transform_struct_to_field_list(signalTypeTwoValues{Flow: 42, TvSec: uint64(t.Unix()), TvNsec: uint32(t.Nanosecond()), Value: 77, Value2: 88, Line: 99999})
	// 		x := signalTypeTwoValues{Flow: 42, TvSec: uint64(t.Unix()), TvNsec: uint32(t.Nanosecond()), Value: 77, Value2: 88, Line: 99999}
	// 		field_list := (&x).get_field_list()
	// 		fmt.Println(field_list)
	// 		if err := conn.Emit(OBJECT_PATH, INTERFACE_NAME+".reportCwnd", field_list...); err != nil {
	// 			panic(err)
	// 		}

	// 		// if err := conn.Emit(OBJECT_PATH, INTERFACE_NAME+".reportRtt", signalTypeOneValue{Flow: 42, TvSec: uint64(t.Unix()), TvNsec: uint32(t.Nanosecond()), Value: 77, Line: 99999}); err != nil {
	// 		// 	panic(err)
	// 		// }
	// 	}
	// }
}

type QuicDbusSignalType int

const (
	Rtt QuicDbusSignalType = iota // = 0
	Lost
	Cwnd
	Pacing
	BbrRtt
	BbrBW
	Delivered
	DeliveredAdjust
	GainLost
)

type DbusSignal interface {
	Name() string
	Value() interface{}
	IntrospectSignal() introspect.Signal
}

func CreateQuicDbusSignalRtt(flow uint32, time time.Time, rtt uint32) DbusSignal {
	return dbusSignalStruct{Rtt, quicSignalTypeUint32{flow, time.Unix(), time.Nanosecond(), rtt}}
}

func CreateFshaperDbusSignal(name string, value interface{}) DbusSignal {
	switch name {
	case "reportRtt":
		return dbusSignalStruct{Rtt, fshaperSignalTypeUint32{value[0], value[1], value[2], value[3], 0}}
	default:
		panic("unimplemented signal")
	}
}

type dbusSignalStruct struct {
	Type QuicDbusSignalType
	Value interface{}
}

func (s *dbusSignalStruct) Name() string {
	switch s.Type {
	case Rtt:
		return "reportRtt"
	case Lost:
		return "reportLost"
	case Cwnd:
		return "reportCwnd"
	case Pacing:
		return "reportPacing"
	case BbrRtt:
		return "reportBbrRtt"
	case BbrBW:
		return "reportBbrBW"
	case Delivered:
		return "reportDelivered"
	case DeliveredAdjust:
		return "reportDeliveredAdjust"
	case GainLost:
		return "reportGainLost"
	default:
		panic("invalid signal type")
	}
}

func (s *dbusSignalStruct) Value() interface{} {
	return transform_struct_to_field_list(s.Value)
}

func (s *dbusSignalStruct) IntrospectSignal() introspect.Signal {
	var arg_list []introspect.Arg
	t := reflect.TypeOf(s.Value)
	for i := 0; i < t.NumField(); i++ {
		arg_list = append(arg_list, introspect.Arg{t.Field(i).Name, dbus.SignatureOfType(t.Field(i).Type()), "out"})
	}
	return introspect.Signal{Name: "mysignal", Args: arg_list}
}

type FshaperDbus struct {
	service_name string
	interface_name string
	object_path string
	conn *dbus.Conn
	signalListener chan *dbus.Signal
}

func (fshaperDbus *FShaperDbus) ApplyControl(dType uint32, flow uint32, flow0 uint64, flow1 uint64, flow2 uint64, flow3 uint64, flow4 uint64, flow5 uint64, flow6 uint64, flow7 uint64, flow8 uint64, flow9 uint64, flow10 uint64) (ret bool, dbusError *dbus.Error) {
	// apply CC params to QUIC connections
	fmt.Printf("dType = %d\n", dType)
	if dbusError != nil {
		fmt.Println(dbusError)
	}
	return true, nil
}

func (fshaperDbus *FshaperDbus) forward(s QuicDbusSignal) {
	if err := fshaperDbus.conn.Emit(fshaperDbus.object_path, fshaperDbus.interface_name+"."+s.Name(), s.Value()...); err != nil {
		panic(err)
	}
}

func (fshaperDbus *FshaperDbus) mainLoop() {
	for v := range fshaperDbus.signalListener {
		fmt.Println(v)
		// find v's structure
		fshaperDbus.forward(CreateFshaperDbusSignal(v.Name, v.Value))
	}
}

func (fshaperDbus *FshaperDbus) openSessionBus() {
	fshaperDbus.conn, err := dbus.ConnectSessionBus()
	if err != nil {
		fmt.Fprintln(os.Stderr, "Failed to connect to session bus:", err)
		os.Exit(1)
	}

	reply, err := fshaperDbus.conn.RequestName(fshaperDbus.service_name, dbus.NameFlagDoNotQueue)
	if err != nil {
		panic(err)
	}
	if reply != dbus.RequestNameReplyPrimaryOwner {
		fmt.Fprintln(os.Stderr, "name already taken")
		os.Exit(1)
	}
}

func (fshaperDbus *FshaperDbus) closeSessionBus() {
	fshaperDbus.conn.Close()
}

func (fshaperDbus *FshaperDbus) registerMethods() {
	conn.Export(*fshaperDbus, fshaperDbus.object_path, fshaperDbus.interface_name)
}

func (fshaperDbus *FshaperDbus) registerSignalListeners() {
	if err = conn.AddMatchSignal(
		dbus.WithMatchObjectPath(fshaperDbus.object_path),
		dbus.WithMatchInterface(fshaperDbus.interface_name),
		// dbus.WithMatchMember("mysignal"),
		// dbus.WithMatchSender(REMOTE_SERVICE_NAME),
	); err != nil {
		panic(err)
	}

	fshaperDbus.signalListener := make(chan *dbus.Signal, 1)
	conn.Signal(fshaperDbus.signalListener)
}

func (fshaperDbus *FshaperDbus) registerIntrospectMethod() {
	n := &introspect.Node{
		Name: fshaperDbus.object_path,
		Interfaces: []introspect.Interface{
			introspect.IntrospectData,
			{
				Name:       fshaperDbus.interface_name,
				Methods:    introspect.Methods(f),
				Signals:    []introspect.Signal{introspect.Signal{Name: "mysignal"}},
			},
		},
	}
	conn.Export(introspect.NewIntrospectable(n), fshaperDbus.object_path, "org.freedesktop.DBus.Introspectable")
}

func (fshaperDbus *FshaperDbus) register() {
	fshaperDbus.registerMethods()
	fshaperDbus.registerSignalListeners()
	fshaperDbus.registerIntrospectMethod()
}

type quicSignalTypeUint32 struct {
	Flow int32 	// probably int32 but it depends on what type json.loads( ... "id") returns in python
	TvSec uint64
	TvNsec uint32
	Value uint32
}

type quicSignalTypeUint32Int32 struct {
	Flow int32 	// probably int32 but it depends on what type json.loads( ... "id") returns in python
	TvSec uint64
	TvNsec uint32
	Value uint32
	Value2 int32
}

type fshaperSignalTypeUint32 struct {
	Flow int32 	// probably int32 but it depends on what type json.loads( ... "id") returns in python
	TvSec uint64
	TvNsec uint32
	Value uint32
	Line uint32
}

type fshaperSignalTypeUint32Int32 struct {
	Flow int32 	// probably int32 but it depends on what type json.loads( ... "id") returns in python
	TvSec uint64
	TvNsec uint32
	Value uint32
	Value2 int32
	Line uint32
}

func transform_struct_to_field_list(in_struct interface{}) ([]interface{}) {
	var field_list []interface{}
	v := reflect.ValueOf(in_struct)
	t := reflect.TypeOf(in_struct)
	for i := 0; i < t.NumField(); i++ {
		field_list = append(field_list, v.Field(i).Interface())
	}
	return field_list
}
