package flowteledbus

import (
	"time"
	"strings"

	"github.com/godbus/dbus"
)


func CreateFshaperDbusSignal(s *dbus.Signal) DbusSignal {
	elements := strings.Split(s.Name, ".")
	switch elements[len(elements)-1] {
	case "reportRtt":
		return createQuicDbusSignalUint32Uint32(Rtt, s.Body[0].(int32), time.Unix(int64(s.Body[1].(uint64)), int64(s.Body[2].(uint32))), s.Body[3].(uint32), 0)
	case "reportCwnd":
		return createQuicDbusSignalUint32Int32Uint32(Cwnd, s.Body[0].(int32), time.Unix(int64(s.Body[1].(uint64)), int64(s.Body[2].(uint32))), s.Body[3].(uint32), s.Body[4].(int32), 0)
	default:
		panic("unimplemented signal")
	}
}
