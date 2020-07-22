package flowteledbus

import (
	"fmt"
	"time"

	"github.com/godbus/dbus"
)


const (
	QUIC_SERVICE_NAME = "ch.ethz.netsec.flowtele.quic"
	QUIC_INTERFACE_NAME = "ch.ethz.netsec.flowtele.quic"
	QUIC_OBJECT_PATH = "/ch/ethz/netsec/flowtele/quic"
)

type quicDbusMethodInterface struct {
	quicDbus *QuicDbus
}

func (qdbmi quicDbusMethodInterface) ApplyControl(dType uint32, beta float64, cwnd_adjust int16, cwnd_max_adjust int16, use_conservative_allocation bool) (ret bool, dbusError *dbus.Error) {
	// apply CC params to QUIC connections
	// quicDbusMethodInterface.dbusBase.Send(...)
	qdb := qdbmi.quicDbus
	qdb.Log("received ApplyControl(%d, %f, %d, %d, %t)", dType, beta, cwnd_adjust, cwnd_max_adjust, use_conservative_allocation)
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
	d.ExportedSignals = allQuicDbusSignals()
	return &d
}

func (qdb *QuicDbus) SendRttSignal(t time.Time, rtt uint32) {
	qdb.Send(CreateQuicDbusSignalRtt(qdb.FlowId, t, rtt))
}

func (qdb *QuicDbus) SendLostSignal(t time.Time, newSsthresh uint32) {
	qdb.Send(CreateQuicDbusSignalLost(qdb.FlowId, t, newSsthresh))
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
