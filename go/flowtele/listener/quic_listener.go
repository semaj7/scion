package main

import (
	"context"
	"crypto/tls"
	"flag"
	"fmt"
	"io"
	"net"
	"os"
	"time"

	"github.com/lucas-clemente/quic-go"

	"github.com/scionproto/scion/go/lib/addr"
	sd "github.com/scionproto/scion/go/lib/sciond"
	"github.com/scionproto/scion/go/lib/snet"
	"github.com/scionproto/scion/go/lib/snet/squic"
	"github.com/scionproto/scion/go/lib/sock/reliable"
)

var (
	tlsConfig   tls.Config
	localIAFlag addr.IA

	listenAddr   = flag.String("ip", "127.0.0.1", "IP address to listen on")
	listenPort   = flag.Int("port", 5500, "Port number to listen on")
	nConnections = flag.Int("num", 12, "Number of QUIC connections using increasing port numbers")
	keyPath      = flag.String("key", "go/flowtele/tls.key", "TLS key file")
	pemPath      = flag.String("pem", "go/flowtele/tls.pem", "TLS certificate file")
	messageSize  = flag.Int("message-size", 10000000, "size of the message that should be received as a whole")

	useScion       = flag.Bool("scion", false, "Open scion quic sockets")
	dispatcherFlag = flag.String("dispatcher", "", "Path to dispatcher socket")
	sciondAddrFlag = flag.String("sciond", sd.DefaultSCIONDAddress, "SCIOND address")
)

func init() {
	flag.Var(&localIAFlag, "local-ia", "ISD-AS address to listen on")
}

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

func getQuicListener(lAddr *net.UDPAddr) (quic.Listener, error) {
	quicConfig := &quic.Config{IdleTimeout: time.Hour}
	if *useScion {
		dispatcher := *dispatcherFlag
		sciondAddr := *sciondAddrFlag
		localIA := localIAFlag
		ds := reliable.NewDispatcher(dispatcher)
		sciondConn, err := sd.NewService(sciondAddr).Connect(context.Background())
		if err != nil {
			return nil, fmt.Errorf("Unable to initialize SCION network (%s)", err)
		}
		network := snet.NewNetworkWithPR(localIA, ds, &sd.Querier{
			Connector: sciondConn,
			IA:        localIA,
		}, sd.RevHandler{Connector: sciondConn})
		if err != nil {
			return nil, fmt.Errorf("Unable to initialize SCION network (%s)", err)
		}
		if err = squic.Init("", ""); err != nil {
			return nil, fmt.Errorf("Unable to load TLS server certificates: %s", err)
		}
		return squic.Listen(network, lAddr, addr.SvcNone, quicConfig)
	} else {
		conn, err := net.ListenUDP("udp", lAddr)
		if err != nil {
			fmt.Printf("Error starting UDP listener: %s\n", err)
			return nil, err
		}
		initTlsCert()
		// make QUIC idle timout long to allow a delay between starting the listeners and the senders
		return quic.Listen(conn, &tlsConfig, quicConfig)
	}
}

func startListener(lAddr *net.UDPAddr) error {
	server, err := getQuicListener(lAddr)
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
	message := make([]byte, *messageSize)
	tInit := time.Now()
	nTot := 0
	for {
		tStart := time.Now()
		n, err := io.ReadFull(stream, message)
		if err != nil {
			fmt.Printf("Error reading message: %s\n", err)
			return err
		}
		tEnd := time.Now()
		nTot += n
		tCur := tEnd.Sub(tStart).Seconds()
		tTot := tEnd.Sub(tInit).Seconds()
		// MBit/s
		curRate := float64(n) / tCur / 1000000.0 * 8.0
		totRate := float64(nTot) / tTot / 1000000.0 * 8.0
		fmt.Printf("%d cur: %.1fMBit/s (%.1fMB in %.2fs), tot: %.1fMBit/s (%.1fMB in %.2fs)\n", lAddr.Port, curRate, float64(n)/1000000, tCur, totRate, float64(nTot)/1000000, tTot)
	}
	return nil
}

func main() {
	flag.Parse()
	errs := make(chan error)
	for i := 0; i < *nConnections; i++ {
		go func(port int) {
			if err := startListener(&net.UDPAddr{IP: net.ParseIP(*listenAddr), Port: port}); err != nil {
				errs <- err
			}
		}(*listenPort + i)
	}
	select {
	case err := <-errs:
		fmt.Printf("Error encountered (%s), stopping all listeners\n", err)
		os.Exit(1)
	}
}
