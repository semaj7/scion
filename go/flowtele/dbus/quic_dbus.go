package flowteledbus

import (
	"fmt"
	"time"

	"github.com/godbus/dbus"
	"github.com/godbus/dbus/introspect"
)


const (
	QUIC_SERVICE_NAME = "ch.ethz.netsec.flowtele.quic"
	QUIC_INTERFACE_NAME = "ch.ethz.netsec.flowtele.quic"
	QUIC_OBJECT_PATH = "/ch/ethz/netsec/flowtele/quic"
)

type quicDbusMethodInterface struct {
	quicDbus *QuicDbus
}

func (qdbmi *quicDbusMethodInterface) ApplyControl(dType uint32, cwnd uint64) (ret bool, dbusError *dbus.Error) {
	// apply CC params to QUIC connections
	// quicDbusMethodInterface.dbusBase.Send(...)
	qdb := qdbmi.quicDbus
	qdb.Log("received ApplyControl(%d, %d)", dType, cwnd)
	// fmt.Printf("dType = %d, flow %d received cwnd %d\n", dType, qdb.FlowId, cwnd)
	// if dbusError != nil {
	// 	fmt.Println(dbusError)
	// }
	return true, nil
}

type QuicDbus struct {
	DbusBase
	FlowId int32
}

func NewQuicDbus(flowId int32) *QuicDbus {
	var d QuicDbus
	d.FlowId = flowId
	d.ServiceName = getQuicServiceName(flowId)
	d.ObjectPath = getQuicObjectPath(flowId)
	d.InterfaceName = getQuicInterfaceName(flowId)
	d.LogPrefix = fmt.Sprintf("QUIC_%d", d.FlowId)
	d.ExportedMethods = quicDbusMethodInterface{quicDbus: &d}
	d.SignalMatchOptions = []dbus.MatchOption{}
	d.ExportedSignals = []introspect.Signal{}
	return &d
}

func (qdb *QuicDbus) SendRttSignal(t time.Time, rtt uint32) {
	qdb.Send(CreateQuicDbusSignalRtt(qdb.FlowId, t, rtt))
}

func (qdb *QuicDbus) SendCwndSignal(t time.Time, cwnd uint32, pktsInFlight int32) {
	qdb.Send(CreateQuicDbusSignalCwnd(qdb.FlowId, t, cwnd, pktsInFlight))
}

func getQuicServiceName(flowId int32) string {
	return fmt.Sprintf("%s_%d", QUIC_SERVICE_NAME, flowId)
}

func getQuicObjectPath(flowId int32) dbus.ObjectPath {
	return dbus.ObjectPath(fmt.Sprintf("%s_%d", QUIC_OBJECT_PATH, flowId))
}

func getQuicInterfaceName(flowId int32) string {
	return fmt.Sprintf("%s_%d", QUIC_SERVICE_NAME, flowId)
}
