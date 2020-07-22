package main

import (
	"time"
	"net"
	"os"
	"fmt"
	"flag"
	"crypto/tls"
	
	"github.com/lucas-clemente/quic-go"
)

var (
	tlsConfig tls.Config
	listenAddr = flag.String("ip", "127.0.0.1", "IP address to listen on")
	listenPort = flag.Int("port", 5500, "Port number to listen on")
	nConnections = flag.Int("num", 12, "Number of QUIC connections using increasing port numbers")
	keyPath = flag.String("key", "go/flowtele/tls.key", "TLS key file")
	pemPath = flag.String("pem", "go/flowtele/tls.pem", "TLS certificate file")
)

// create certificate and key with
// openssl req -new -newkey rsa:4096 -x509 -sha256 -days 365 -nodes -out tls.pem -keyout tls.key
func initTlsCert() error {
	cert, err := tls.LoadX509KeyPair(*pemPath, *keyPath)
	if err != nil {
		fmt.Printf("Unable to load TLS cert (%s) or key (%s): %s\n", *pemPath, *keyPath, err)
		return err
	}
	tlsConfig.Certificates = []tls.Certificate{cert}
	return nil
}

func startListener(addr *net.UDPAddr) error {
	conn, err := net.ListenUDP("udp", addr)
	if err != nil {
		fmt.Printf("Error starting UDP listener: %s\n", err)
		return err
	}
	quicConfig := &quic.Config{}
	server, err := quic.Listen(conn, &tlsConfig, quicConfig)
	if err != nil {
		fmt.Printf("Error starting QUIC listener: %s\n", err)
		return err
	}
	defer server.Close()
	fmt.Printf("Listening for QUIC connections on %s\n", server.Addr().String())
	session, err := server.Accept()
	if err != nil {
		fmt.Printf("Error accepting sessions: %s\n", err)
		return err
	} else {
		fmt.Println("Accepted session")
	}
	stream, err := session.AcceptStream()
	if err != nil {
		fmt.Printf("Error accepting streams: %s\n", err)
		return err
	} else {
		fmt.Printf("Accepted stream %d\n", stream.StreamID)
	}
	message := make([]byte, 1000000)
	tInit := time.Now()
	nTot := 0
	for {
		tStart := time.Now()
		n, err := stream.Read(message)
		if err != nil {
			fmt.Printf("Error reading message: %s\n", err)
			return err
		}
		tEnd := time.Now()
		nTot += n
		tCur := tEnd.Sub(tStart).Seconds()
		tTot := tEnd.Sub(tInit).Seconds()
		// MBit/s
		curRate := float64(n)/tCur/1000000.0*8.0
		totRate := float64(nTot)/tTot/1000000.0*8.0
		fmt.Printf("cur: %.1fMBit/s [%.2fs], tot: %.1fMBit/s [%.2fs]\n", curRate, tCur, totRate, tTot)
	}
	return nil
}

func main() {
	flag.Parse()
	initTlsCert()
    errs := make(chan error)
	for i := 0; i < *nConnections; i++ {
		go func(port int) {
			if err := startListener(&net.UDPAddr{IP: net.ParseIP(*listenAddr), Port: port}); err != nil {
				errs <- err
			}
		}(*listenPort+i)
	}
	select {
	case err := <-errs:
		fmt.Printf("Error encountered (%s), stopping all listeners\n", err)
		os.Exit(1)
	}
}


