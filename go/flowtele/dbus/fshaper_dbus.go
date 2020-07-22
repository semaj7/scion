package flowteledbus

import (
	"strings"

	"github.com/godbus/dbus"
)

const (
	SERVICE_NAME = "ch.ethz.netsec.flowtele.scionsocket"
	INTERFACE_NAME = "ch.ethz.netsec.flowtele.scionsocket"
	OBJECT_PATH = "/ch/ethz/netsec/flowtele/scionsocket"
)
type fshaperDbusMethodInterface struct {
	dbusBase *DbusBase
}

func (fshaperDbus fshaperDbusMethodInterface) ApplyControl(dType uint32, flow uint32, flow0 uint64, flow1 uint64, flow2 uint64, flow3 uint64, flow4 uint64, flow5 uint64, flow6 uint64, flow7 uint64, flow8 uint64, flow9 uint64, flow10 uint64) (ret bool, dbusError *dbus.Error) {
	// apply CC params to QUIC connections
	// fshaperDbusMethodInterface.dbusBase.Send(...)
	flows := []uint64{flow0, flow1, flow2, flow3, flow4, flow5, flow6, flow7, flow8, flow9, flow10}
	fshaperDbus.dbusBase.Log("received ApplyControl(%d, %d, %+v)", dType, flow, flows)
	for i, f := range(flows) {
		serviceName := getQuicServiceName(int32(i))
		objectPath := getQuicObjectPath(int32(i))
		interfaceName := getQuicInterfaceName(int32(i))
		obj := fshaperDbus.dbusBase.Conn.Object(serviceName, objectPath)
		fshaperDbus.dbusBase.Log("calling ApplyControl on %s in %s", serviceName, objectPath)

		var beta float64
		var cwnd_adjust, cwnd_max_adjust int16
		var use_conservative_allocation bool
		beta = float64(int((f >> 48) & 0xffff))/1024
		cwnd_adjust = int16((f >> 32) & 0xffff)
		cwnd_max_adjust = int16((f >> 16) & 0xffff)
		use_conservative_allocation = bool((f & 0x1) == 1)
		call := obj.Call(interfaceName+".ApplyControl", 0, dType, beta, cwnd_adjust, cwnd_max_adjust, use_conservative_allocation)
		if call.Err != nil {
			panic(call.Err)
		}
		var res bool
		call.Store(&res)
		if res {
			fshaperDbus.dbusBase.Log("successfully updated flow %d", i)
		} else {
			fshaperDbus.dbusBase.Log("failed to update flow")
			return false, nil
		}
	}
	return true, nil
}

// type fshaperDbus struct {
// 	dbusBase
// 	methodInterface *fshaperDbusMethodInterface
// }

func NewFshaperDbus() *DbusBase {
	var d DbusBase
	d.ServiceName = SERVICE_NAME
	d.ObjectPath = dbus.ObjectPath(OBJECT_PATH)
	d.InterfaceName = INTERFACE_NAME
	d.LogPrefix = "SOCKET"
	d.ExportedMethods = fshaperDbusMethodInterface{dbusBase: &d}
	nsString := ""
	elements := strings.Split(string(d.ObjectPath), "/")
	for i := 1; i < len(elements)-1; i++ {
		nsString = nsString + "/" + elements[i]
	}
	namespace := dbus.ObjectPath(nsString)
	d.SignalMatchOptions = []dbus.MatchOption{dbus.WithMatchPathNamespace(namespace)}
	d.ExportedSignals = allFshaperDbusSignals()
	return &d
}
