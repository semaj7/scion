package flowteledbus

import (
	"time"
)


func CreateQuicDbusSignalRtt(flow int32, t time.Time, rtt uint32) DbusSignal {
	return createQuicDbusSignalUint32(Rtt, flow, t, rtt)
}

func CreateQuicDbusSignalCwnd(flow int32, t time.Time, cwnd uint32, pktsInFlight int32) DbusSignal {
	return createQuicDbusSignalUint32Int32(Cwnd, flow, t, cwnd, pktsInFlight)
}
