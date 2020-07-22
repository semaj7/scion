package main

import (
	"fmt"
	"os"
	"net"
	"crypto/tls"
	"flag"
	
	"github.com/scionproto/scion/go/flowtele/dbus"
	"github.com/lucas-clemente/quic-go"
)

var (
	remoteAddr = flag.String("ip", "127.0.0.1", "IP address to connect to")
	remotePort = flag.Int("port", 5500, "Port number to connect to")
	nConnections = flag.Int("num", 12, "Number of QUIC connections using increasing port numbers")
)

func main() {
	flag.Parse()
	// first run
	// python3.6 athena_m10.py 12
	// clear; go run go/flowtele/quic_listener.go --num 2
	// clear; go run go/flowtele/socket.go --num 2
	
	// var fdbus fshaperDbus
	fdbus := flowteledbus.NewFshaperDbus()
	// dbus setup
	fdbus.OpenSessionBus()
	defer fdbus.Close()

	// start QUIC instances
	// TODO(cyrill) read flow specs from config/user_X.json
	remoteIp := net.ParseIP(*remoteAddr)
	remoteAddresses := []net.UDPAddr{}
	startPort := *remotePort
	fmt.Println(*nConnections)
	for ui := 0; ui < *nConnections; ui++ {
		remoteAddresses = append(remoteAddresses, net.UDPAddr{IP: remoteIp, Port: startPort+ui})
	}

    errs := make(chan error)
	for di, addr := range remoteAddresses {
		go func(remoteAddress net.UDPAddr, flowId int32) {
			err := startQuicSender(addr, flowId)
			if err != nil {
				errs <- err
			}
		}(addr, int32(di))
	}

	// register method and listeners
	fdbus.Register()

	// listen for feedback from QUIC instances and forward to athena
	go func() {
		for v := range fdbus.SignalListener {
			if fdbus.Conn.Names()[0] == v.Sender {
				fdbus.Log("ignore signal %s generated by socket", v.Name)
			} else {
				fdbus.Log("forwarding signal...")
				fdbus.Send(flowteledbus.CreateFshaperDbusSignal(v))
			}
		}
	}()

	select {
	case err := <-errs:
		fmt.Printf("Error encountered (%s), stopping all QUIC senders and SCION socket\n", err)
		os.Exit(1)
	}
}

func startQuicSender(remoteAddress net.UDPAddr, flowId int32) error {
	// start dbus
	qdbus := flowteledbus.NewQuicDbus(flowId)
	qdbus.OpenSessionBus()
	defer qdbus.Close()
	qdbus.Register()

	// start QUIC session
	conn, err := net.ListenUDP("udp", &net.UDPAddr{IP: net.IPv4zero, Port: 0})
	if err != nil {
		fmt.Printf("Error starting UDP listener: %s\n", err)
		return err
	}
	tlsConfig := &tls.Config{InsecureSkipVerify: true}
	quicConfig := &quic.Config{}
	session, err := quic.Dial(conn, &remoteAddress, "host:0", tlsConfig, quicConfig)
	if err != nil {
		fmt.Printf("Error starting QUIC connection to [%s]: %s\n", remoteAddress.String(), err)
		return err
	}
	qdbus.Log("session established. Opening stream...")
	stream, err := session.OpenStreamSync()
	if err != nil {
		fmt.Printf("Error opening QUIC stream to [%s]: %s\n", remoteAddress.String(), err)
		return err
	}
	qdbus.Log("stream opened %d", stream.StreamID())
	message := make([]byte, 100000000)
	for i := range message {
		message[i] = 42
	}
	for {
		fmt.Printf("Sending message of length %d\n", len(message))
		_, err = stream.Write([]byte(message))
		if err != nil {
			fmt.Printf("Error writing message to [%s]: %s\n", remoteAddress.String(), err)
			return err
		}
	}
	return nil
}
